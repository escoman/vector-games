"""Порт-трасса → Standard MIDI File: универсальный считыватель мелодий Vector-06C.

Идея (обсуждение с пользователем): звук на Vector-06C порождается РОВНО
последовательностью `OUT` в порты КР580ВИ53 — обратной связи и невидимого
состояния у звука нет. Значит мелодию можно восстановить, НЕ зная алгоритма
генерации и НЕ декодируя партитуру: читаем, что пишется в порты таймера, и
переводим значение счётчика прямо в частоту `f = timer_hz / value`.

Чем этот путь отличается от `music2midi.py`:
  * `music2midi` читает БАЙТЫ партитуры из ROM/RAM и расшифровывает их по
    ROM-специфичной спеке (encoding, pitch_table, адреса дорожек);
  * `porttrace2midi` смотрит на ЖИВЫЕ `OUT` в порты и знает только
    стандартную распиновку КР580ВИ53 (фиксированные порты чипа) и вектор VBlank
    (`0x0038`, фиксированный 8080 RST 7). Это ROM-агностично: ни адресов, ни
    формата нот не требуется.

Что Python делает детерминированно (Layer A, факты):
  * снимает трассу портов по кадрам (сетка = BP на векторе VBlank);
  * раскладывает байты `OUT` в 16-битные затворы таймера по каждому голосу
    (младший байт раньше старшего — так грузит 8253 в режиме 3);
  * схлопывает повторные загрузки одного значения внутри шага;
  * считает высоту `midi = 69 + round(12*log2(f/440))`;
  * ищет петлю трека автокорреляцией по посигнатурному кадру (конец трека —
    единственная часть, которую нельзя вывести из значения порта, поэтому она
    детектируется структурно).

Чего Python НЕ делает: не угадывает темп «на слух» и не притворяется, что
точность по времени высока. Временна́я сетка равна кадру VBlank, а живая
латентность MCP склеивает соседние кадры в одну корзину — потому длительности
приближённые. Высота и мелодический контур при этом точные (это и есть смысл
порта как источника истины).

Тестуемость: `vi53_parse` и `detect_loop` — чистые функции без эмулятора. Трассу
можно снять один раз (`--dump-trace trace.json`) и далее разбирать офлайн
(`--trace trace.json`), в том числе в юнит-тестах.

    PYTHONPATH=utils python3 utils/analyze/cli.py porttrace2midi \
        --rom roms/redesign/riseout/src/riseout.rom --org 0x0100 \
        --out riseout_port.mid --dump-trace trace.json
"""
from __future__ import annotations

import argparse
import json
import math
import os
import struct
import sys
import time

from analyze.mcp_session import to_addr
from analyze.music2midi import chunk, end_of_track, meta, track_name_event, vlq

# --- Распиновка КР580ВИ53 (фиксированные порты чипа, НЕ зависят от ROM) ------
# Три счётчика-голоса грузятся парами lo/hi в свои порты; портовое слово
# (CW) в 0x08 выбирает счётчик и работает затвором (стаккато).
DEFAULT_CFG = {
    "cw_port": 0x08,
    # порт данных -> индекс голоса (0/1/2). На Vector voice1->0x0B, voice2->0x0A,
    # voice3->0x09 (порт=12*период; для высоты это безразлично — берём f из value).
    "data_ports": {0x0B: 0, 0x0A: 1, 0x09: 2},
    "timer_hz": 1497600,
    "a4_hz": 440.0,
    "fps": 50,               # VBlank на Vector-06C
    "grid": 0x0038,          # RST 7 = вектор прерывания = 1 кадр
    "ppq": 96,               # тиков в четверти; одна четверть = один кадр
}

FALLBACK_NOTE_FRAMES = 3   # длительность последней/одиночной ноты, если нет следующей


def freq_to_midi(freq, a4=440.0):
    """Частота -> ближайший MIDI-номер ноты (равнотемперированный строй)."""
    if freq <= 0:
        return None
    return 69 + int(round(12.0 * math.log2(freq / a4)))


def _pn(e):
    p = e.get("port")
    return int(p, 16) if isinstance(p, str) else int(p)


def _vn(e):
    v = e.get("value")
    return int(v, 16) if isinstance(v, str) else int(v)


# ---------------------------------------------------------------------------
# Layer A: трасса кадров -> ноты. Чистая функция (без эмулятора) — тестируется.
# ---------------------------------------------------------------------------

def vi53_parse(frames, cfg=None):
    """frames: список кадров; каждый кадр — список событий {type,port,value}
    (или кортежей (port, value)). Возвращает {voice: [(frame, value, midi), ...]}
    в хронологическом порядке, со схлопнутыми повторами одного значения подряд.

    Модель 8253 в режиме 3: два байта в порт данных = затвор таймера
    (младший первый). Значение = lo | hi<<8; f = timer_hz / value. Повторная
    загрузка того же значения для голоса не создаёт новой ноты (spec: lo/hi
    пишут несколько раз за шаг — безвредно).
    """
    cfg = {**DEFAULT_CFG, **(cfg or {})}
    data_ports = {int(k): v for k, v in cfg["data_ports"].items()}
    timer_hz = cfg["timer_hz"]
    a4 = cfg["a4_hz"]
    pend = {}                 # voice -> накопленный младший байт
    last_load = {}            # voice -> value последнего записанного затвора
    notes = {v: [] for v in set(data_ports.values())}
    for fi, evs in enumerate(frames):
        for e in evs:
            if isinstance(e, dict):
                if e.get("type") not in (None, "out"):
                    continue
                port, val = _pn(e), _vn(e)
            else:
                port, val = e[0], e[1]
            if port not in data_ports:
                continue
            v = data_ports[port]
            if pend.get(v) is None:
                pend[v] = val                       # младший байт
                continue
            lo, pend[v] = pend[v], None
            value = lo | (val << 8)
            if value == 0:
                continue
            if last_load.get(v) == value:           # повтор затвора в том же шаге
                continue
            last_load[v] = value
            notes[v].append((fi, value, freq_to_midi(timer_hz / value, a4)))
    return notes


def notes_to_segments(notes):
    """{voice: [(frame, value, midi)]} -> {voice: [(start, end, midi)]}.
    Длительность = кадры до следующей ноты того же голоса; висящую последнюю
    закрываем на FALLBACK."""
    segs = {}
    for v, lst in notes.items():
        out = []
        for i, (fr, _value, midi) in enumerate(lst):
            if midi is None:
                continue
            end = lst[i + 1][0] if i + 1 < len(lst) else fr + FALLBACK_NOTE_FRAMES
            out.append((fr, max(fr + 1, end), midi))
        segs[v] = out
    return segs


# ---------------------------------------------------------------------------
# Конец трека: автокорреляция посигнатурному кадру (структурная, не из значения)
# ---------------------------------------------------------------------------

def _frame_signature(frames, cfg):
    """Стабильная сигнатура кадра = отсортированный кортеж звуковых (port,val)."""
    sound = set(cfg["data_ports"]) | {cfg["cw_port"]}
    sig = []
    for evs in frames:
        items = []
        for e in evs:
            if isinstance(e, dict):
                if e.get("type") not in (None, "out"):
                    continue
                port = _pn(e)
                if port in sound:
                    items.append((port, _vn(e)))
            else:
                if e[0] in sound:
                    items.append((e[0], e[1]))
        sig.append(tuple(sorted(items)))
    return sig


def detect_loop(frames, cfg=None, min_period=4, min_repeats=2):
    """Возвращает (start, period) найденной петли или None.

    Ищем ранний offset `start`, после которого сигнатура кадра периодична с
    периодом `period` не менее `min_repeats` повторов. Период выбираем
    минимальным подходящим — это длина одного прогона мелодии (end-of-track).
    """
    cfg = {**DEFAULT_CFG, **(cfg or {})}
    sig = _frame_signature(frames, cfg)
    n = len(sig)
    # намек: первый непустой кадр — начало звучащей части
    first = next((i for i in range(n) if sig[i]), 0)
    best = None
    for start in range(first, min(first + 8, n)):
        for period in range(min_period, (n - start) // min_repeats + 1):
            matches, repeats = 0, 0
            ok = True
            for i in range(start, n - period):
                if sig[i] == sig[i + period]:
                    matches += 1
                else:
                    ok = False
                    break
            # считаем полные повторы в хвосте
            tail = n - start
            if ok and tail >= period * min_repeats:
                best = (start, period)
                break
        if best:
            break
    return best


# ---------------------------------------------------------------------------
# SMF-письмо (низкоуровневые хелперы переиспользуются из music2midi)
# ---------------------------------------------------------------------------

def events_to_bytes(events):
    """events: [(tick, order, message)] -> трек с дельтами (order: off<on)."""
    out = b""
    position = 0
    for tick, order, message in sorted(events, key=lambda it: (it[0], it[1])):
        out += vlq(tick - position) + message
        position = tick
    return out


def segs_to_smf(segs, cfg, title="Port-trace", velocity=100, programs=(0, 0, 0)):
    """{voice: [(start,end,midi)]} -> байты format-1 SMF, трек на голос."""
    ppq = cfg["ppq"]
    tick_per_frame = ppq                     # 1 кадр = 1 четверть
    tempo_us = int(round(1e6 / cfg["fps"]))  # четверть = кадр -> us/сек-долю
    tracks = []
    header = track_name_event(title)
    header += meta(0, 0x51, tempo_us.to_bytes(3, "big"))
    body = struct.pack(">HHH", 1, 1 + len(segs), ppq)
    smf = chunk(b"MThd", body)
    smf += chunk(b"MTrk", header + end_of_track())
    for voice in sorted(segs):
        ch = voice & 0x0F
        events = []
        prog = programs[voice] if voice < len(programs) else 0
        events.append((0, -1, bytes([0xC0 | ch, prog & 0x7F])))
        for start, end, midi in segs[voice]:
            events.append((start * tick_per_frame, 1,
                           bytes([0x90 | ch, midi, velocity])))
            events.append((end * tick_per_frame, 0,
                           bytes([0x80 | ch, midi, 0])))
        body = track_name_event("voice%d" % voice) + events_to_bytes(events) + end_of_track()
        smf += chunk(b"MTrk", body)
    return smf


# ---------------------------------------------------------------------------
# Живой захват трассы (слой транспорта; не нужен при --trace)
# ---------------------------------------------------------------------------

def _wait_pause(session, limit=5.0):
    t0 = time.time()
    while time.time() - t0 < limit:
        r = session.call("debug_is_running")
        if not (r.get("running") if isinstance(r, dict) else r):
            return True
        time.sleep(0.003)
    return False


def capture(session, cfg, max_frames=600, warm_seconds=2.0, keys=(),
            settle_frames=2, min_sound_frames=24, verbose=False):
    """Снимает трассу портов по кадрам VBlank до появления мелодии.

    1) свободный бег (+опциональные клавиши), чтобы дойти до звучащего экрана;
    2) BP на сетке VBlank; дельта-дрен io_trace каждый кадр;
    3) накапливаем кадры, пока не поймали достаточно звучащих кадров, затем
       ещё немного — для детекции петли.
    Возвращает frames: список списков {type,port,value} (только порты чипа).
    """
    sound = set(int(p) for p in cfg["data_ports"]) | {cfg["cw_port"]}
    grid = to_addr(cfg["grid"])
    session.call("debug_clear_breakpoints")
    session.call("debug_run")
    time.sleep(warm_seconds)
    for k in keys:
        try:
            session.call("debug_type_key", key=k)
            time.sleep(0.3)
        except Exception:
            pass
    time.sleep(warm_seconds)
    session.call("debug_pause")
    session.call("debug_set_breakpoint", address=grid)

    frames, seen = [], 0
    sounding = 0
    idle_after = 0
    for i in range(max_frames):
        session.call("debug_run")
        if not _wait_pause(session):
            if verbose:
                print("[capture] кадр %d: не пауза — стоп" % i, file=sys.stderr)
            break
        io = session.call("debug_get_io_trace", max_entries=8000)
        bucket = []
        for e in io.get("events") or []:
            sq = int(e.get("sequence") or 0)
            if sq <= seen:
                continue
            port = _pn(e)
            if port in sound and e.get("type", "out") == "out":
                bucket.append({"type": "out", "port": port, "value": _vn(e)})
            if sq > seen:
                seen = sq
        frames.append(bucket)
        if bucket:
            sounding += 1
            idle_after = 0
        else:
            idle_after += 1
        if sounding >= min_sound_frames and idle_after >= settle_frames:
            break
    session.call("debug_clear_breakpoints")
    return frames


# ---------------------------------------------------------------------------
# Оркестрация + CLI
# ---------------------------------------------------------------------------

def convert_rom(rom, org=0x0100, cfg=None, max_frames=600, warm_seconds=2.0,
                keys=(), server=None, verbose=False):
    """Живой путь: открыть сессию -> capture -> разбор -> сегменты + петля."""
    from analyze.mcp_session import open_session
    cfg = {**DEFAULT_CFG, **(cfg or {})}
    session, _cache = open_session(rom=rom, org=org, server=server, verbose=verbose)
    try:
        frames = capture(session, cfg, max_frames=max_frames,
                         warm_seconds=warm_seconds, keys=keys, verbose=verbose)
    finally:
        session.close()
    return frames


def build_midi(frames, cfg=None, title="Port-trace", programs=(0, 0, 0)):
    cfg = {**DEFAULT_CFG, **(cfg or {})}
    notes = vi53_parse(frames, cfg)
    segs = notes_to_segments(notes)
    loop = detect_loop(frames, cfg)
    smf = segs_to_smf(segs, cfg, title=title, programs=programs)
    summary = {
        "frames": len(frames),
        "sounding_frames": sum(1 for f in frames if f),
        "loop": {"start": loop[0], "period": loop[1]} if loop else None,
        "voices": {
            str(v): {
                "notes": len(notes[v]),
                "range": ([min(m for _s, _e, m in segs[v]),
                           max(m for _s, _e, m in segs[v])] if segs[v] else None),
            } for v in sorted(segs)
        },
        "bytes": len(smf),
    }
    return smf, summary


def load_trace(path):
    with open(path, "r", encoding="utf-8") as handle:
        data = json.load(handle)
    return data["frames"] if isinstance(data, dict) and "frames" in data else data


def dump_trace(path, frames, cfg):
    with open(path, "w", encoding="utf-8") as handle:
        json.dump({"cfg": {"data_ports": {hex(k): v for k, v in cfg["data_ports"].items()},
                           "cw_port": hex(cfg["cw_port"]), "timer_hz": cfg["timer_hz"],
                           "fps": cfg["fps"], "grid": hex(cfg["grid"])},
                   "frames": frames}, handle, ensure_ascii=False)


def main(argv=None):
    ap = argparse.ArgumentParser(prog="analyze.porttrace2midi",
        description="Трасса портов КР580ВИ53 -> Standard MIDI File (беззнание формата партитуры)")
    ap.add_argument("--rom", help="путь к ROM (живой захват)")
    ap.add_argument("--org", default="0x0100")
    ap.add_argument("--trace", help="разобрать ранее снятый trace.json (без эмулятора)")
    ap.add_argument("--dump-trace", dest="dump_trace", help="сохранить снятую трассу")
    ap.add_argument("-o", "--out", default="porttrace.mid")
    ap.add_argument("--title", default="Port-trace")
    ap.add_argument("--max-frames", type=int, default=600)
    ap.add_argument("--warm", type=float, default=2.0, help="сек свободного бега до сетки")
    ap.add_argument("--key", action="append", default=[], help="клавиша(и) для запуска экрана (повторяемо)")
    ap.add_argument("--fps", type=int, default=None)
    ap.add_argument("--timer-hz", type=int, default=None)
    ap.add_argument("--server", default=None)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    cfg = dict(DEFAULT_CFG)
    if args.fps:
        cfg["fps"] = args.fps
    if args.timer_hz:
        cfg["timer_hz"] = args.timer_hz

    if args.trace:
        frames = load_trace(args.trace)
    elif args.rom:
        frames = convert_rom(args.rom, org=to_addr(args.org), cfg=cfg,
                             max_frames=args.max_frames, warm_seconds=args.warm,
                             keys=args.key, server=args.server)
        if args.dump_trace:
            dump_trace(args.dump_trace, frames, cfg)
    else:
        raise SystemExit("нужно --rom (живой захват) или --trace (офлайн-разбор)")

    smf, summary = build_midi(frames, cfg, title=args.title)
    with open(args.out, "wb") as handle:
        handle.write(smf)
    summary["output"] = os.path.abspath(args.out)
    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        print("выпуск   %s (%d байт)" % (summary["output"], summary["bytes"]))
        print("кадров   %d (звучащих %d)" % (summary["frames"], summary["sounding_frames"]))
        lp = summary["loop"]
        print("петля    %s" % (("старт %d, период %d кадр (~%.2f с)"
              % (lp["start"], lp["period"], lp["period"] / cfg["fps"])) if lp else "не найдена"))
        for v, info in sorted(summary["voices"].items()):
            rng = "%d..%d" % tuple(info["range"]) if info["range"] else "—"
            print("  voice%-2s нот=%-4s диапазон=%s" % (v, info["notes"], rng))
    return 0


if __name__ == "__main__":
    sys.exit(main())
