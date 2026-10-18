#!/usr/bin/env python3
"""Оценка покрытия ROM с дроблением на чанки.

Обходит hard cap `debug_coverage_report`/`debug_analyze_code` (10000 инт.):
берёт все `function`-адреса из RDB и/или `label`-адреса, режет их на блоки
размером `chunk` (по умолчанию 32) и вызывает debug_analyze_code для каждого;
объединённое множество разобранных адресов даёт честный coverage.

Запуск:
    PYTHONPATH=utils python3 tools/coverage_split.py [--chunk 32] [--labels]

Флаг --labels добавляет label-адреса как точки входа (по умолчанию только
function — они ближе к реальным entry points).
"""
from __future__ import annotations
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
MODULE = os.path.dirname(HERE)
REPO = os.path.dirname(os.path.dirname(os.path.dirname(MODULE)))
sys.path.insert(0, os.path.join(REPO, "utils"))

from analyze.mcp_session import open_session, addr_hex, to_addr  # noqa: E402
from analyze.rdb import Rdb  # noqa: E402

ROM = os.path.join(MODULE, "src", "basic.r0m")
RDB = os.path.join(MODULE, "src", "basic.rdb")
LO = 0x0000
HI = 0x42FF


def subtract_ranges(ranges, lo, hi):
    """Множество [lo..hi] минус sorted-интервалы; возвращает дыры [(s,e)]."""
    out = []
    cursor = lo
    for s, e in sorted(ranges):
        if e < cursor or s > hi:
            continue
        s = max(s, cursor)
        if s > cursor:
            out.append((cursor, s - 1))
        cursor = max(cursor, e + 1)
        if cursor > hi:
            break
    if cursor <= hi:
        out.append((cursor, hi))
    return out


def chunk(lst, n):
    for i in range(0, len(lst), n):
        yield lst[i:i + n]


def analyze_chunk(session, addrs):
    res = session.call("debug_analyze_code",
                       {"addresses": addrs, "max_instructions": 10000})
    payload = res if isinstance(res, dict) else (res.get("result") or {})
    # debug_analyze_code -> {"ranges": [{"start": a, "end": b}, ...], "truncated": bool}
    ranges = [(to_addr(r.get("start")), to_addr(r.get("end")))
              for r in payload.get("ranges", [])]
    return ranges, bool(payload.get("truncated"))


def merge_ranges(parts):
    """Слияние перекрывающихся интервалов. parts: iterable of (a,b)."""
    items = sorted(parts)
    out = []
    for a, b in items:
        if out and a <= out[-1][1] + 1:
            if b > out[-1][1]:
                out[-1] = (out[-1][0], b)
        else:
            out.append((a, b))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--chunk", type=int, default=32)
    ap.add_argument("--labels", action="store_true",
                    help="добавить label-точки входа")
    ap.add_argument("--extra", default=None,
                    help="json-файл со списком доп. адресов")
    args = ap.parse_args(argv)

    rdb = Rdb.load(RDB)
    entries = sorted({o.address for o in rdb.objects
                      if o.type == "function"
                      or (args.labels and o.type == "label")})
    if args.extra:
        for x in json.load(open(args.extra)):
            entries.append(to_addr(x))
        entries = sorted(set(entries))
    print("entries: %d (chunk=%d)" % (len(entries), args.chunk),
          file=sys.stderr)

    session, cache = open_session(rom=ROM, org=LO)
    try:
        all_ranges = []
        truncated_chunks = 0
        for i, part in enumerate(chunk(entries, args.chunk)):
            ranges, trunc = analyze_chunk(session, part)
            all_ranges.extend(ranges)
            if trunc:
                truncated_chunks += 1
            if (i + 1) % 8 == 0:
                print("  chunk %d/%d, ranges=%d, bytes=%d" % (
                    i + 1, (len(entries) + args.chunk - 1) // args.chunk,
                    len(all_ranges),
                    sum(b - a + 1 for a, b in merge_ranges(all_ranges))),
                    file=sys.stderr)
        merged = merge_ranges(all_ranges)
        total = sum(b - a + 1 for a, b in merged)
        gaps = subtract_ranges(merged, LO, HI)
        gap_bytes = sum(e - s + 1 for s, e in gaps)
        image = HI - LO + 1
        print("truncated_chunks=%d/%d" % (truncated_chunks,
                                          (len(entries) + args.chunk - 1) // args.chunk),
              file=sys.stderr)
        out = {
            "coverage_percent": 100.0 * total / image,
            "code_bytes": total,
            "image_bytes": image,
            "gap_bytes": gap_bytes,
            "ranges": [[addr_hex(a), addr_hex(b)] for a, b in merged],
            "gaps": [[addr_hex(s), addr_hex(e)] for s, e in gaps],
        }
        print(json.dumps(out, ensure_ascii=False, indent=1))
    finally:
        session.close()


if __name__ == "__main__":
    sys.exit(main())
