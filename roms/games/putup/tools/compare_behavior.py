#!/usr/bin/env python3
"""Поведенческая сверка PUTUP_NEW vs оригинал (этап A шаг 5; этап B: --label B).

Один MCP-Session, ТРИ прогона подряд (debug_load_rom, НЕ debug_reset):
origA, NEW, origB. origA-vs-NEW — основной тест; origB-vs-origA — шумовой
пол (эмулятор real-time, фазы пауз/возвратов плывут). Если расхождения
NEW не превышают шума оригинал-против-оригинала — поведение идентично.

Фаза прогона: якорь по кадрам beam state (f0+200 заставка, +300/400 игра),
тапы SPACE/LEFT/RIGHT на паузе (latch до resume); захваты: регистры, VRAM
32768 Б, глиф-зона 0x6000..0x7FFF; в конце — карта записей и io-trace
(одна тяжёлая выдача, после неё не играем).

Артефакты: tools/capture_<label>_verdicts.json + tools/capture_*.{bin,json}.
Использование: python3 tools/compare_behavior.py [--new ROM] [--label A]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(HERE)
ROOT = os.path.abspath(os.path.join(PROJ, "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "utils", "analyze"))

from mcp_session import McpSession, bytes_of, to_addr  # noqa: E402

ORIG = os.path.join(ROOT, "roms", "redesign", "putup", "src", "putup.rom")
ORIG_GLYPH_BASE = 0x6000          # RAM-окно распаковки у оригинала


def new_glyph_base():
    """Адрес блока глифов в NEW из манифеста (свободная конкатенация: запечён
    в ROM по data_glyph_block, а не в RAM 0x6000 как у оригинала)."""
    p = os.path.join(HERE, "layout.json")
    if not os.path.exists(p):
        raise SystemExit("нет tools/layout.json — сначала `make` (пишет манифест)")
    return json.load(open(p, encoding="utf-8"))["glyph_base"]

REPORTS = os.path.join(PROJ, "tools")      # артефакты поведенческой сверки
MUSIC_PORTS = (0x09, 0x0A, 0x0B)
F_TITLE, F_PLAY1, F_PLAY2 = 200, 100, 100  # ОТНОСИТЕЛЬНЫЕ интервалы кадров CPU
F_LEFT, F_RIGHT = 30, 70                   # внутри play2-фазы (30+70=100)
WARMUP = 220  # > объёма io-буфера (60000 соб ≈ <100 кадров)


def frame_of(s):
    bs = s.call("debug_get_beam_state")
    return int(to_addr(bs.get("frame")) or 0)


def run_frames(s, span):
    """Ровно `span` CPU-кадров: цель считается сразу после resume; пока CPU
    стоит, луч дрейфует — абсолютные якоря плывут, интервалы — нет."""
    tgt = frame_of(s) + span
    s.call("debug_run")
    while frame_of(s) < tgt:
        time.sleep(0.05)
    s.call("debug_pause")


def pause_capture(s, glyph_base=ORIG_GLYPH_BASE, with_glyph=True):
    cap = {
        "frame": frame_of(s),
        "regs": s.call("debug_get_registers"),
        "vram": bytes_of(s.call("debug_get_vram_bytes", {"address": 0x8000, "length": 32768})),
    }
    if with_glyph:
        cap["glyph"] = bytes_of(s.call("debug_read_memory_range", {"address": glyph_base, "length": 8192}))
    return cap


def io_items(payload):
    items = payload if isinstance(payload, list) else payload.get("entries", payload.get("events", []))
    return [it for it in items if isinstance(it, dict)]


def last_seq(items):
    return max((int(it.get("sequence", 0)) for it in items), default=0)


def run_phase(s, rom_path, glyph_base=ORIG_GLYPH_BASE):
    s.load_rom(rom_path, org=0x0100)
    # разгон: заголовок уже на экране, io-буфер полностью от этого ROM
    run_frames(s, WARMUP)
    s0 = last_seq(io_items(s.call("debug_get_io_trace", {"max_entries": 5})))
    s.call("debug_clear_memory_access_map")  # карта — только фазы заставки/игры
    run_frames(s, F_TITLE)
    title = pause_capture(s, glyph_base)
    # детерминированное музыкальное окно: хвост фазы заставки (до первого
    # тапа SPACE) — фиксированный интервал CPU-кадров от старта, клавиши/фазы
    # на него не влияют; полный дамп хвоста прогона для этого непригоден
    # (кольцевое окно 10k событий + джиттер лаунча SPACE)
    io_title = io_items(s.call("debug_get_io_trace", {"max_entries": 10000}))
    st1 = last_seq(io_title)
    title_events = [e for e in io_title if s0 < int(e.get("sequence", 0)) <= st1]
    s.call("debug_type_key", {"key": "SPACE"})  # на паузе — latch до resume
    run_frames(s, F_PLAY1)
    play1 = pause_capture(s, glyph_base)
    s.call("debug_type_key", {"key": "LEFT"})
    run_frames(s, F_LEFT)
    s.call("debug_type_key", {"key": "RIGHT"})
    run_frames(s, F_RIGHT)
    play2 = pause_capture(s, glyph_base)
    accmap = s.call("debug_get_memory_access_map")
    io_end = io_items(s.call("debug_get_io_trace", {"max_entries": 60000}))
    events = [e for e in io_end if int(e.get("sequence", 0)) > s0]
    return {"rom": os.path.basename(rom_path), "title": title, "play1": play1,
            "play2": play2, "accmap": accmap, "seqlim": {"s0": s0, "s_end": last_seq(io_end)},
            "io_title_events": title_events, "io_events": events}


def count_diff(a, b):
    return sum(1 for x, y in zip(a, b) if x != y)


def music_seq(events):
    out = []
    for it in events:
        p = to_addr(it.get("port"))
        if p in MUSIC_PORTS:
            out.append((str(it.get("type")), "0x%02X" % p, str(it.get("value"))))
    return out


def music_stats(a, b):
    """Длины, мультимножества и лучший попарный процент при сдвиге +-40."""
    ca, cb = Counter(a), Counter(b)
    inter = sum((ca & cb).values())
    union = sum((ca | cb).values())
    best = (0, 0)
    for shift in range(-40, 41):
        x, y = (a[shift:], b[:len(a) - shift]) if shift >= 0 else (a[:len(b) + shift], b[-shift:])
        m = min(len(x), len(y))
        sc = sum(1 for p, q in zip(x, y) if p == q)
        if m and sc / m > best[0]:
            best = (sc / m, shift)
    return {"len_a": len(a), "len_b": len(b), "multiset_jaccard": round(inter / max(1, union), 3),
            "best_pairwise": round(best[0], 3), "best_shift": best[1]}


def glyph_write_blocks(accmap, glyph_base=ORIG_GLYPH_BASE):
    """Блоки страниц глиф-окна (0x60..0x7F или 0x46..0x65) с write_count>0."""
    lo_pg, hi_pg = glyph_base >> 8, (glyph_base + 8191) >> 8
    items = accmap if isinstance(accmap, list) else accmap.get("blocks", accmap.get("map", []))
    hit = []
    for it in items:
        if not isinstance(it, dict):
            continue
        try:
            a = to_addr(it.get("address"))
        except Exception:
            continue
        if a is None or not (lo_pg <= a >> 8 <= hi_pg):
            continue
        if it.get("write") or int(it.get("write_count", 0) or 0) > 0:
            hit.append(it)
    return hit


def compare(cap_main, cap_ref, label, diffs_out):
    lines = []
    for ph in ("title", "play1", "play2"):
        d = count_diff(cap_ref[ph]["vram"], cap_main[ph]["vram"])
        lines.append("%s VRAM %s: %d/32768" % (label, ph, d))
        diffs_out.setdefault(label, {})["vram_" + ph] = d
    for ph in ("title", "play1", "play2"):
        d = count_diff(cap_ref[ph]["glyph"], cap_main[ph]["glyph"])
        lines.append("%s глифы %s: %d/8192" % (label, ph, d))
        diffs_out.setdefault(label, {})["glyph_" + ph] = d
    ms = music_stats(music_seq(cap_ref["io_title_events"]), music_seq(cap_main["io_title_events"]))
    lines.append("%s музыка (окно заставки): %s" % (label, ms))
    diffs_out.setdefault(label, {})["music"] = ms
    return lines


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--new", default=os.path.join(PROJ, "putup_new.rom"))
    ap.add_argument("--label", default="A")
    ap.add_argument("--glyph-base", default=None,
                    help="адрес блока глифов в NEW (по умолчанию — из tools/layout.json)")
    args = ap.parse_args()
    os.makedirs(REPORTS, exist_ok=True)
    gb_new = int(args.glyph_base, 0) if args.glyph_base else new_glyph_base()

    with McpSession() as s:
        cap_o1 = run_phase(s, ORIG)
        cap_n = run_phase(s, args.new, glyph_base=gb_new)
        cap_o2 = run_phase(s, ORIG)

    diffs, verdicts = {}, []
    verdicts += compare(cap_n, cap_o1, "new-vs-orig", diffs)
    verdicts += compare(cap_o2, cap_o1, "noise(orig-vs-orig)", diffs)
    for cap, nm, gb in ((cap_o1, "origA", ORIG_GLYPH_BASE),
                        (cap_n, "new", gb_new),
                        (cap_o2, "origB", ORIG_GLYPH_BASE)):
        d = count_diff(cap["title"]["glyph"], cap["play2"]["glyph"])
        diffs.setdefault(nm, {})["glyph_self_stability"] = d
        verdicts.append("%s: глиф-окно @0x%04X за игру изменено %d/8192" % (nm, gb, d))
        w = glyph_write_blocks(cap["accmap"], gb)
        diffs[nm]["glyph_write_blocks_in_play"] = len(w)
        verdicts.append("%s: блоков окна @0x%04X с записями в игре: %d" % (nm, gb, len(w)))

    art = {"verdicts": verdicts, "diffs": diffs,
           "frames": {c["rom"] + "_" + n: {ph: c[ph]["frame"] for ph in ("title", "play1", "play2")}
                      for c, n in ((cap_o1, "o1"), (cap_n, "n"), (cap_o2, "o2"))},
           "seqlim": {c["rom"] + "_" + n: c["seqlim"] for c, n in ((cap_o1, "o1"), (cap_n, "n"), (cap_o2, "o2"))},
           "regs": {n: {ph: json.dumps(c[ph]["regs"], ensure_ascii=False)[:600]
                        for ph in ("title", "play1", "play2")}
                    for c, n in ((cap_o1, "origA"), (cap_n, "new"), (cap_o2, "origB"))}}
    json.dump(art, open(os.path.join(REPORTS, "capture_%s_verdicts.json" % args.label), "w"),
              ensure_ascii=False, indent=1, default=str)
    bindir = REPORTS
    os.makedirs(bindir, exist_ok=True)
    for cap, name in ((cap_o1, "origA"), (cap_n, "new"), (cap_o2, "origB")):
        for ph in ("title", "play1", "play2"):
            for key in ("vram", "glyph"):
                open(os.path.join(bindir, "%s_%s_%s_%s.bin" % (args.label, name, ph, key)), "wb").write(cap[ph][key])
        json.dump({"seqlim": cap["seqlim"], "music": music_seq(cap["io_title_events"]),
                   "music_full": music_seq(cap["io_events"]),
                   "io_events": cap["io_events"]},
                  open(os.path.join(bindir, "%s_%s_ports.json" % (args.label, name)), "w"),
                  ensure_ascii=False, default=str)
    print("\n".join(verdicts))


if __name__ == "__main__":
    main()
