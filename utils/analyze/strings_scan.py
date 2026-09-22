"""Поиск строк: ASCII и KOI8-R (ТЗ §21).

Python здесь делает только то, что ему разрешено: смотрит на байты и ищет
непрерывные участки «печатаемых» значений. Никакой семантики — найденное
это КАНДИДАТЫ на `str_*`, а не строки: решение за AI.

Кодировки:

    ascii  0x20..0x7E                (печатаемый ASCII)
    koi8   0x20..0x7E + 0xC0..0xFE   (буквы KOI8-R; 0x80..0xBF — псевдографика)

Терминаторы: 0x00 и 0xFF. В KOI8-R 0xFF — это ещё и «Я», поэтому по
умолчанию 0xFF считается терминатором (у putup на нём закончена каждая
строка: титры 0x0925 length 100 кончаются FF @0x0988), а буква «Я»
возвращается флагом `--allow-ya`; участок, оборванный на FF, помечается
`terminator_ambiguous`.

Два режима источника (ТЗ §16):
    IMAGE   — байты файла ROM (то, что в ПЗУ)
    RUNTIME — байты живой RAM (то, что ROM напечатал в текстовый буфер)
"""
from __future__ import annotations

import argparse
import json
import os
import sys

from analyze import naming
from analyze.mcp_session import addr_hex, envelope, open_session, to_addr
from analyze.memory_diff import ImageSource, RuntimeSource
from analyze.rdb import Rdb

ASCII_PRINTABLE = set(range(0x20, 0x7F))
KOI8_LETTERS = set(range(0xC0, 0xFF))      # 0xFF — и «Я», и терминатор
KOI8_YA = 0xFF
TERMINATORS = (0x00, 0xFF)

CHARSETS = {
    "ascii": ASCII_PRINTABLE,
    "koi8": ASCII_PRINTABLE | KOI8_LETTERS,
    "koi8_upper": KOI8_LETTERS,
}

CODEC = {"ascii": ("ascii", "replace"), "koi8": ("koi8_r", "replace")}


def printable_set(charsets, allow_ya=False):
    allowed = set()
    for name in charsets:
        allowed |= CHARSETS[name]
    if allow_ya:
        allowed.add(KOI8_YA)
    return allowed


def scan_bytes(data, base, allowed, min_len=4, terminators=TERMINATORS):
    """Непрерывные участки байтов, все из `allowed`. Возвращает dict-записи.

    Единственная «логика» — сравнение принадлежности байта множеству и
    арифметика индексов; декодирование символов не трактуется.
    """
    runs = []
    start = None
    for index, byte in enumerate(data):
        if byte in allowed:
            if start is None:
                start = index
        else:
            if start is not None and index - start >= min_len:
                runs.append(_run(data, base, start, index, byte, terminators))
            start = None
    if start is not None and len(data) - start >= min_len:
        runs.append(_run(data, base, start, len(data), None, terminators))
    return runs


def _run(data, base, start, stop, stop_byte, terminators):
    chunk = data[start:stop]
    entry = {
        "address": addr_hex(base + start),
        "end": addr_hex(base + stop - 1),
        "length": stop - start,
        "bytes": " ".join("%02X" % b for b in chunk[:32]),
        "koi8": _decode(chunk, "koi8"),
        "ascii": _decode(chunk, "ascii"),
        "koi8_share": round(sum(1 for b in chunk if b in KOI8_LETTERS) / len(chunk), 3),
        "ascii_share": round(sum(1 for b in chunk if b in ASCII_PRINTABLE) / len(chunk), 3),
        "distinct": len(set(chunk)),
    }
    entry["low_entropy"] = entry["distinct"] <= max(2, len(chunk) // 16)
    if stop_byte is None:
        entry["terminator"] = None
        entry["terminated"] = False
    else:
        entry["terminator"] = addr_hex(stop_byte)
        entry["terminated"] = stop_byte in terminators
        entry["terminator_ambiguous"] = stop_byte == 0xFF
    return entry


def _decode(chunk, charset):
    if charset not in CODEC:
        return None
    codec, errors = CODEC[charset]
    try:
        return chunk.decode(codec, errors)
    except Exception as exc:                     # pragma: no cover
        return "<decode error: %s>" % exc


def classify(entry, charsets):
    """Какой кодировке принадлежит участок — по доле байтов из её алфавита."""
    if entry["koi8_share"] > 0 and "koi8" in charsets:
        return "koi8"
    if "ascii" in charsets and entry["ascii_share"] == 1.0:
        return "ascii"
    return next(iter(charsets), "unknown")


class StringsScanner:
    """Кандидаты строк + сверка с RDB (что не находить уже найденное дважды)."""

    def __init__(self, session, cache=None, rom=None, org=0x0100,
                 charsets=("ascii", "koi8"), min_len=4, allow_ya=False):
        self.session = session
        self.cache = cache
        self.rom = rom
        self.org = to_addr(org)
        self.charsets = list(charsets)
        self.min_len = int(min_len)
        self.allow_ya = bool(allow_ya)

    def scan_image(self, rdb=None, source=None):
        """Кандидаты строк по ПЗУ-образу.

        `source` — готовый `ImageSource`; по умолчанию строится из `rom`.
        Базой служит org источника, поэтому скан корректен и для RAM-окна,
        и для образа целиком.
        """
        source = source or ImageSource(self.rom, self.org)
        data = source.read(source.org, source.hi)
        allowed = printable_set(self.charsets, self.allow_ya)
        runs = scan_bytes(data, source.org, allowed, self.min_len)
        return self._annotate(runs, "IMAGE", rdb)

    def scan_runtime(self, lo, hi, rdb=None):
        source = RuntimeSource(self.session, self.cache)
        data = source.read(lo, hi)
        allowed = printable_set(self.charsets, self.allow_ya)
        runs = scan_bytes(data, to_addr(lo), allowed, self.min_len)
        return self._annotate(runs, "RUNTIME", rdb)

    def _annotate(self, runs, memory_source, rdb):
        out = []
        for entry in runs:
            address = to_addr(entry["address"])
            obj = rdb.at(address) if rdb is not None else None
            covered = [o for o in (rdb.objects if rdb is not None else [])
                       if o.address is not None and o.contains(address)]
            entry["charset"] = classify(entry, self.charsets)
            entry["memory_source"] = memory_source
            entry["rdb_object"] = obj.name if obj else None
            entry["rdb_type"] = obj.type if obj else None
            entry["already_string"] = any(o.type == "string" for o in covered)
            entry["candidate_name"] = None if entry["already_string"] \
                else naming.unknown_for("string", address)
            entry["status"] = "CANDIDATE"
            entry["confidence"] = _confidence(entry)
            out.append(entry)
        out.sort(key=lambda e: (-e["length"], to_addr(e["address"])))
        return out


def _confidence(entry):
    """Открытое правило: обрыв-терминатор и известная оболочка решают."""
    if entry["low_entropy"]:
        return "noise"
    if entry["already_string"]:
        return "high"
    if entry.get("terminated") and entry["length"] >= 4:
        return "medium"
    return "low"


def compare_with_rdb(runs, rdb):
    """Что в RDB помечено строкой, но не найдено байтами, и наоборот."""
    found = {to_addr(r["address"]) for r in runs if r["already_string"]}
    declared = []
    for obj in (rdb.of_type("string") if rdb is not None else []):
        exact = any(to_addr(r["address"]) == obj.address for r in runs)
        inside = any(r["rdb_object"] == obj.name for r in runs)
        declared.append({"address": addr_hex(obj.address), "name": obj.name,
                        "size": obj.size, "run_starts_here": exact,
                        "covered_by_run": inside})
    return {
        "strings_in_rdb": len(declared),
        "rdb_strings_without_run": [d for d in declared
                                    if not d["run_starts_here"]
                                    and not d["covered_by_run"]],
        "runs_already_in_rdb": len(found),
        "runs_not_in_rdb": [r["address"] for r in runs if not r["already_string"]],
    }


def _preview(run, limit=44):
    """Текст прогона для человека: одна строка, без перевода каретки."""
    text = (run["koi8"] if run["charset"] == "koi8" else run["ascii"]) or ""
    return text.replace("\n", " ").strip()[:limit]


def format_table(runs, rows=40):
    lines = ["%-8s %-8s %5s %-6s %-8s %-9s %-7s %s"
             % ("адрес", "конец", "дл.", "обрыв", "кодировка", "в RDB", "уверен.",
                "текст")]
    for run in runs[:rows]:
        lines.append("%-8s %-8s %5d %-6s %-8s %-9s %-7s %s" % (
            run["address"], run["end"], run["length"],
            ("нет" if run.get("terminated") is False
             else ("FF?" if run.get("terminator_ambiguous") else "да")),
            run["charset"], run["rdb_object"] or "—", run["confidence"],
            _preview(run)))
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(prog="analyze.strings_scan",
                                     description="Кандидаты строк ASCII/KOI8-R")
    parser.add_argument("--rom", required=True)
    parser.add_argument("--org", type=lambda s: int(s, 0), default=0x0100)
    parser.add_argument("--hi", type=lambda s: int(s, 0), default=None)
    parser.add_argument("--rdb", default=None)
    parser.add_argument("--min-len", type=int, default=4)
    parser.add_argument("--charset", action="append", default=[],
                        choices=sorted(CHARSETS), help="по умолчанию ascii+koi8")
    parser.add_argument("--runtime", nargs=2, metavar=("LO", "HI"), default=None,
                        help="дополнительно просканировать RAM-диапазон")
    parser.add_argument("--allow-ya", action="store_true",
                        help="считать 0xFF буквой «Я», а не терминатором")
    parser.add_argument("--min-confidence", default="low",
                        choices=("noise", "low", "medium", "high"),
                        help="отбросить кандидатов ниже уровня")
    parser.add_argument("--cache", default=None)
    parser.add_argument("--server", default=None)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--rows", type=int, default=40)
    args = parser.parse_args(argv)

    charsets = args.charset or ["ascii", "koi8"]
    session, cache = open_session(rom=args.rom, org=args.org, server=args.server,
                                  cache_dir=args.cache)
    try:
        rdb = Rdb.load(args.rdb) if args.rdb else Rdb.from_session(session)
        scanner = StringsScanner(session, cache, rom=args.rom, org=args.org,
                                 charsets=charsets, min_len=args.min_len,
                                 allow_ya=args.allow_ya)
        image = ImageSource(args.rom, args.org, hi=args.hi)
        runs = scanner.scan_image(rdb=rdb, source=image)
        order = ("noise", "low", "medium", "high")
        keep = order[order.index(args.min_confidence):]
        runs = [r for r in runs if r["confidence"] in keep]
        result = {"rom": os.path.basename(args.rom), "charsets": charsets,
                  "allow_ya": args.allow_ya, "min_len": args.min_len,
                  "image_runs": runs,
                  "rdb_check": compare_with_rdb(runs, rdb)}
        if args.runtime:
            lo, rt_hi = [to_addr(v) for v in args.runtime]
            result["runtime_runs"] = [r for r in
                                      scanner.scan_runtime(lo, rt_hi, rdb=rdb)
                                      if r["confidence"] in keep]
        order = ("noise", "low", "medium", "high")
        ranked = sorted(runs, key=lambda r: order.index(r["confidence"]),
                        reverse=True)
        candidates = [{
            "name": r.get("rdb_object")
                    or naming.propose("string", addr=r["address"]),
            "confidence": r["confidence"],
            "object": r["address"],
            "detail": "%s, %d байт, %s%s: %s"
                      % (r["charset"], r["length"],
                         "с завершающим нулём" if r.get("terminated")
                         else "без завершающего нуля",
                         " уже в RDB" if r["already_string"] else "",
                         _preview(r)),
        } for r in ranked[:10]]
        check = result["rdb_check"]
        result = envelope(
            result, module="strings_scan", session=session, cache=cache,
            status="CANDIDATE", candidates=candidates,
            verdict="строковых прогонов: %d, из них уже строкой в RDB %d, "
                    "строк в RDB без прогона %d"
                    % (len(runs), check["runs_already_in_rdb"],
                       len(check["rdb_strings_without_run"])),
            note="прогон байтов, похожих на текст, — ещё не строка: "
                 "окончание и назначение задаёт адресат")
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print("IMAGE (ROM-образ):")
            print(format_table(runs, args.rows))
            print("\n%s" % json.dumps(result["rdb_check"], ensure_ascii=False,
                                      indent=2))
            if "runtime_runs" in result:
                print("\nRUNTIME (RAM):")
                print(format_table(result["runtime_runs"], args.rows))
        print("# mcp calls: %d" % session.stats()["total_calls"], file=sys.stderr)
    finally:
        session.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
