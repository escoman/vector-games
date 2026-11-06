#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Stage 9c: реконструкция звука выстрела/взрыва exolon из трассы TapeOut (PC0).

Подложка истины — живая трасса отладчика v06c-mcp `debug_get_raster_events`
(порт 0x00/0x01): каждое событие несёт `frame`, `v_cycle` (позиция луча в
видео-циклах), `pc` инструкции `OUT` и `value`. Видео-такт = 12 МГц
(frameVCycles = 768*312 = 239616 на кадр, ~50.08 Гц ⇒ ~19.97 мс/кадр), поэтому
`t = (frame*239616 + v_cycle) / 12_000_000` — честное wall-clock время, а
`v_cycle`-интервалы между фронтами PC0 = реальные длительности импульсов.

Декод PC0 повторяет модель ядра эмулятора (`vector-debug/src/debug_adapter.cpp`,
строки 242-259), чтобы реконструированный меандр совпадал с тем, что реально
слышит машина:

  * `OUT 01h` (порт C данные)  → PC0 := value & 1            (прямая запись)
  * `OUT 00h` control word (bit7=1) → ставит CW, PC НЕ трогает (PC0 без изменений)
  * `OUT 00h` BSR (bit7=0): номер бита = (value>>1)&7; если бит==0 → PC0 := value&1
    (BSR, целившийся в другой бит PC, PC0 НЕ трогает)

exolon пишет в PC0 только пять мест (см. Stage 9b/9c):
  0x0168/0x0186/0x0193  func_frame_sync   — CW-записи (0x88/0x8A) = PC0 постоянный ⇒ тишина
  0x1E36/0x1E43         func_beam_delay   — треск гонок с лучом (выстрел/отрисовка)
  0x06E1                func_update_objects_06f6 — RESET PC0 на каждую частицу (взрыв)
  0x4C9C                func_flash_video  — нисходящий chirp бонуса
  0x786B                boot              — OUT 00h инициализации

Выход: WAV (mono PCM 16-bit) + текстовые метрики (число фронтов, длительность,
средняя/медианная ширина импульса, доминирующая частота повторения по
автокорреляции, RMS, атрибуция фронтов по PC-источнику).

Использование:
  python3 tools/sfx_capture.py EVENTS.json --out shot.wav \
      --frames LO:HI  [--src beam|particle|all] [--rate 48000]
  EVENTS.json — JSON, сохранённый из ответа `debug_get_raster_events`.
"""
from __future__ import annotations
import argparse, json, math, os, struct, sys, wave

VCLK = 12_000_000          # видео-такт, Гц (12 МГц пиксельные часы)
FRAME_VCYCLES = 768 * 312  # 239616 v_cycle в одном кадре

# Источники-группы по PC. В трассе `debug_get_raster_events` для OUT фиксируется
# PC СЛЕДУЮЩЕЙ инструкции (адрес уже после выполнения OUT), поэтому адреса
# = адрес_OUT + длина(2). Функция и её OUT-адреса: beam 0x1E36/0x1E3F, particle 0x06E1.
SRC_PC = {
    "beam":     {0x1E38, 0x1E41},          # func_beam_delay: OUT 0x1E36/0x1E3F → выстрел/отрисовка
    "particle": {0x06E3},                  # func_update_objects_06f6: OUT 0x06E1 → взрыв
    "sync":     {0x0168, 0x0186, 0x0193},  # func_frame_sync  → CW (PC0 не меняет)
    "chirp":    {0x4C9E},                  # func_flash_video → бонус (OUT ~0x4C9C)
}


def load_events(path):
    with open(path, encoding="utf-8") as f:
        doc = json.load(f)
    evs = doc["events"] if isinstance(doc, dict) else doc
    out = []
    for e in evs:
        port = e["port"]
        if port not in (0, 1):
            continue
        pc = e["pc"] if isinstance(e["pc"], int) else int(e["pc"], 16)
        tick = e["frame"] * FRAME_VCYCLES + e["v_cycle"]
        out.append((tick, port, e["value"], pc, e["frame"]))
    out.sort(key=lambda x: x[0])
    return out


def decode_pc0(events):
    """Хронология уровня PC0: список (tick, level) только в моменты изменений."""
    level = 0
    edges = []            # (tick, new_level, pc) — только реальные смены уровня
    timeline = [(0, 0)]   # (tick, level) для синтеза
    for tick, port, value, pc, frame in events:
        new = None
        if port == 1:
            new = value & 1
        elif port == 0:
            if value & 0x80:
                continue                      # control word: PC не меняется
            else:
                bit = (value >> 1) & 7
                if bit == 0:
                    new = value & 1           # BSR PC0 set/reset
        if new is None:
            continue                          # это OUT не касается PC0
        if new != level:
            level = new
            edges.append((tick, level, pc))
            timeline.append((tick, level))
    return edges, timeline


def window(timeline, t0, t1):
    """Отрезок таймлайна [t0,t1) с корректным уровнем на границах."""
    seg = []
    cur = 0
    for tick, lvl in timeline:
        if tick < t0:
            cur = lvl
            continue
        if tick >= t1:
            break
        seg.append((tick, lvl))
        cur = lvl
    # уровень на входе в окно
    pre = 0
    for tick, lvl in timeline:
        if tick < t0:
            pre = lvl
        else:
            break
    return pre, seg


def synthesize(pre, seg, t0, t1, rate, amp):
    n = int(round((t1 - t0) / VCLK * rate))
    samples = array_fill(n, pre, amp)
    for tick, lvl in seg:
        idx = int(round((tick - t0) / VCLK * rate))
        if idx < 0:
            idx = 0
        if idx >= n:
            break
        val = amp if lvl else -amp
        for j in range(idx, n):
            samples[j] = val
    return samples


def array_fill(n, level, amp):
    v = amp if level else -amp
    return [v] * n


def write_wav(path, samples, rate):
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        frames = bytearray()
        for s in samples:
            frames += struct.pack("<h", int(max(-32767, min(32767, s))))
        w.writeframes(bytes(frames))


def analyze(edges, t0, t1):
    """Метрики окна: фронты, длительность, ширина импульсов, доминирующий темп."""
    ticks = [e[0] for e in edges]
    res = {
        "edges": len(ticks),
        "dur_ms": (t1 - t0) / VCLK * 1000.0,
    }
    if len(ticks) >= 2:
        gaps = [ticks[i + 1] - ticks[i] for i in range(len(ticks) - 1)]
        gaps_sorted = sorted(gaps)
        res["mean_gap_us"] = sum(gaps) / len(gaps) / VCLK * 1e6
        res["median_gap_us"] = gaps_sorted[len(gaps) // 2] / VCLK * 1e6
        res["min_gap_us"] = gaps_sorted[0] / VCLK * 1e6
        res["max_gap_us"] = gaps_sorted[-1] / VCLK * 1e6
        # доминирующая частота повторения фронтов (автокорреляция по бинам в мкс)
        res["dominant_rate_hz"] = dominant_rate(ticks)
    return res


def dominant_rate(ticks):
    if len(ticks) < 8:
        return 0.0
    span = ticks[-1] - ticks[0]
    if span <= 0:
        return 0.0
    # гистограмма межфронтовых интервалов → мода в мкс
    gaps = [ticks[i + 1] - ticks[i] for i in range(len(ticks) - 1)]
    us = [g / VCLK * 1e6 for g in gaps]
    lo, hi = min(us), max(us)
    bins = 40
    hist = [0] * bins
    for u in us:
        k = int((u - lo) / (hi - lo + 1e-9) * bins)
        hist[min(k, bins - 1)] += 1
    mode = max(range(bins), key=lambda i: hist[i])
    center = lo + (mode + 0.5) / bins * (hi - lo)
    return 1e6 / center if center > 0 else 0.0


def attribute(edges):
    by = {}
    for tick, lvl, pc in edges:
        by[pc] = by.get(pc, 0) + 1
    return by


def src_label(pc):
    for name, pcs in SRC_PC.items():
        if pc in pcs:
            return name
    return f"0x{pc:04X}"


def classify(att):
    """Класс всплеска по составу PC-источников фронтов."""
    pcs = set(att)
    if pcs & SRC_PC["particle"]:
        return "explosion"          # сбросы PC0 на частицы-осколки
    if pcs & SRC_PC["chirp"]:
        return "chirp"              # бонус
    if pcs & SRC_PC["beam"]:
        return "shot"               # треск гонок с лучом (выстрел/попадание)
    return "sync"                   # только CW func_frame_sync (тишина)


def bursts(edges, gap_ms=3.0):
    """Группировка фронтов во всплески: разрыв > gap_ms тишины = новый всплеск."""
    if not edges:
        return []
    thresh = int(gap_ms / 1000 * VCLK)
    groups = []
    cur = [edges[0]]
    for prev, e in zip(edges, edges[1:]):
        if e[0] - prev[0] > thresh:
            groups.append(cur)
            cur = [e]
        else:
            cur.append(e)
    groups.append(cur)
    out = []
    for g in groups:
        att = attribute(g)
        out.append({
            "t0": g[0][0], "t1": g[-1][0], "edges": len(g),
            "dur_ms": (g[-1][0] - g[0][0]) / VCLK * 1000.0,
            "att": att, "kind": classify(att),
        })
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("events", help="JSON из debug_get_raster_events")
    ap.add_argument("--out", default=None, help="файл .wav для --burst/--frames/--src")
    ap.add_argument("--frames", default=None, help="окно LO:HI по номеру кадра")
    ap.add_argument("--src", default=None, choices=["beam", "particle", "chirp"],
                    help="окно по первому сегменту источника PC0")
    ap.add_argument("--burst", type=int, default=None, help="отрендерить N-й всплеск")
    ap.add_argument("--list", action="store_true", help="таблица всплесков")
    ap.add_argument("--auto", action="store_true",
                    help="найти первый shot и первый explosion, записать shot.wav/explosion.wav")
    ap.add_argument("--gap-ms", type=float, default=3.0, help="порог разрыва всплеска")
    ap.add_argument("--rate", type=int, default=48000)
    ap.add_argument("--amp", type=int, default=12000)
    ap.add_argument("--pad-ms", type=float, default=20.0,
                    help="растянуть окно на N мс вокруг всплеска/сегмента")
    args = ap.parse_args()

    events = load_events(args.events)
    if not events:
        print("нет событий порта 0/1 в файле", file=sys.stderr)
        return 1
    edges, timeline = decode_pc0(events)
    t_first, t_last = events[0][0], events[-1][0]
    bs = bursts(edges, args.gap_ms)
    print(f"всего событий порт0/1: {len(events)}, смен уровня PC0: {len(edges)}, "
          f"всплесков (gap>{args.gap_ms} мс): {len(bs)}")

    def render(t0, t1, out, title):
        pad = int(args.pad_ms / 1000 * VCLK)
        t0 = max(t_first, t0 - pad); t1 = min(t_last + pad, t1 + pad)
        pre, seg = window(timeline, t0, t1)
        win = [e for e in edges if t0 <= e[0] < t1]
        a = analyze(win, t0, t1)
        print(f"\n== {title} ==")
        print(f"  кадры {t0//FRAME_VCYCLES}..{t1//FRAME_VCYCLES}  "
              f"длит. {(t1-t0)/VCLK*1000:.1f} мс  фронтов {len(win)}")
        if "mean_gap_us" in a:
            print(f"  межфронт. интервал: median={a['median_gap_us']:.1f} мкс "
                  f"min={a['min_gap_us']:.1f} max={a['max_gap_us']:.1f}")
            print(f"  доминирующий темп : {a['dominant_rate_hz']:.0f} фронтов/с")
        for pc, cnt in sorted(attribute(win).items(), key=lambda x: -x[1]):
            print(f"    {src_label(pc):10s} pc=0x{pc:04X}: {cnt}")
        if out:
            samples = synthesize(pre, seg, t0, t1, args.rate, args.amp)
            write_wav(out, samples, args.rate)
            print(f"  WAV → {out}  ({len(samples)/args.rate*1000:.1f} мс, "
                  f"{args.rate} Гц, mono16)")

    if args.list:
        for i, b in enumerate(bs):
            if b["kind"] == "sync":
                continue
            print(f"  #{i:3d} {b['kind']:9s} кадры {b['t0']//FRAME_VCYCLES}.."
                  f"{b['t1']//FRAME_VCYCLES}  {b['dur_ms']:.1f} мс  "
                  f"фронтов {b['edges']}  {dict((src_label(p),c) for p,c in b['att'].items())}")
        return 0

    if args.auto:
        shot = next((b for b in bs if b["kind"] == "shot"), None)
        boom = next((b for b in bs if b["kind"] == "explosion"), None)
        outdir = os.path.dirname(os.path.abspath(args.out or "."))
        if shot:
            render(shot["t0"], shot["t1"], os.path.join(outdir, "shot.wav"),
                   "ВЫСТРЕЛ (func_beam_delay)")
        else:
            print("нет всплеска типа shot")
        if boom:
            render(boom["t0"], boom["t1"], os.path.join(outdir, "explosion.wav"),
                   "ВЗРЫВ (func_update_objects_06f6, частицы)")
        else:
            print("нет всплеска типа explosion")
        return 0

    if args.burst is not None:
        if not (0 <= args.burst < len(bs)):
            print("нет такого всплеска", file=sys.stderr); return 1
        b = bs[args.burst]
        render(b["t0"], b["t1"], args.out, f"всплеск #{args.burst} ({b['kind']})")
        return 0

    if args.frames:
        lo, hi = (int(x) for x in args.frames.split(":"))
        render(lo * FRAME_VCYCLES, hi * FRAME_VCYCLES, args.out, f"окно кадров {lo}:{hi}")
        return 0

    if args.src:
        want = SRC_PC[args.src]
        seg_ticks = [tick for tick, lvl, pc in edges if pc in want]
        if not seg_ticks:
            print(f"нет фронтов источника {args.src}", file=sys.stderr); return 1
        render(seg_ticks[0], seg_ticks[-1], args.out, f"источник {args.src}")
        return 0

    render(t_first, t_last, args.out, "всё окно")
    return 0


if __name__ == "__main__":
    sys.exit(main())
