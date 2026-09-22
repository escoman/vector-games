"""Побайтовый round-trip: ROM → экспорт → сборка → сравнение (ТЗ §27, §13).

Критерий один: собранный из ASM бинарь обязан совпасть с исходным образом
до байта. Всё, что меньше, — значит экспорт или тулчейн что-то потерял.

Сравнение делает Python (`memory_diff.reliable_memory_diff`), потому что ТЗ
§13 объявляет локальный полный diff авторитетным: MCP-сравнение умеет только
оценивать и может недооценить разницу. Здесь вообще нет эмулятора — два
файла на диске, оба IMAGE.

Каждый расходящийся диапазон подписывается именем RDB-объекта, если он
попадает под него: так находка сразу говорит, какой регион реконструкции
виноват, а не просто «0x2F61≠0x2F61».
"""
from __future__ import annotations

import argparse
import json
import os
import sys

from analyze import export_asm, memory_diff
from analyze.mcp_session import addr_hex, to_addr
from analyze.rdb import Rdb


def object_at(objects, address):
    """Имя RDB-объекта, накрывающего адрес (или None)."""
    for obj in objects:
        if obj.contains(address) or obj.address == address:
            return obj
    return None


def compare_bytes(reference, candidate, org=0x0100, objects=None):
    """Сравнить два образа; вернуть diff-отчёт с привязкой к RDB."""
    source_a = memory_diff.ImageSource(reference, org=org)
    source_b = memory_diff.ImageSource(candidate, org=org)
    lo = max(source_a.org, source_b.org)
    hi = min(source_a.hi, source_b.hi)
    diff = memory_diff.reliable_memory_diff(source_a, source_b, lo, hi)
    diff["sizes"] = {"reference": source_a.size, "candidate": source_b.size}
    diff["size_match"] = source_a.size == source_b.size
    if not diff["size_match"]:
        diff["ranges"].insert(0, {
            "start": addr_hex(max(source_a.hi, source_b.hi) + 1),
            "end": addr_hex(min(source_a.hi, source_b.hi) + abs(
                source_a.size - source_b.size)),
            "length": abs(source_a.size - source_b.size),
            "old": "(нет байт)" if source_a.size < source_b.size else "",
            "new": "(нет байт)" if source_b.size < source_a.size else "",
            "note": "размеры образов разные",
        })
    for item in diff["ranges"]:
        try:
            start = to_addr(item["start"])
        except (TypeError, ValueError):
            continue
        obj = object_at(objects or [], start)
        item["rdb_object"] = obj.name if obj is not None else None
        item["rdb_type"] = obj.type if obj is not None else None
    return diff


def run_verify(rom, out_dir, rdb=None, origin=0x0100, assemble=True,
               exporter=None, z80asm=None, candidate=None, entry="main.asm"):
    """Полный цикл: (пере)экспорт → сборка → сравнение с ROM."""
    result = {"rom": os.path.abspath(rom), "out_dir": os.path.abspath(out_dir),
              "origin": addr_hex(origin), "mcp_calls": 0, "status": "IMAGE"}
    rdb_path = rdb or os.path.splitext(rom)[0] + ".rdb"
    objects = []
    if os.path.isfile(rdb_path):
        result["rdb"] = rdb_path
        objects = [item for item in Rdb.load(rdb_path).objects if item.name]
    else:
        result["rdb"] = None
    if assemble:
        report, stdout, stderr, code, command = export_asm.run_export(
            rom, out_dir, exporter=exporter, rdb=rdb_path or None, origin=origin)
        result["export"] = {"command": command, "returncode": code,
                            "rom_size": (report or {}).get("rom_size")}
        if code != 0:
            result["verdict"] = "blocked: экспортёр вернул rc=%s" % code
            result["stderr_tail"] = (stderr or stdout).splitlines()[-8:]
            return result
        build = export_asm.assemble(out_dir, z80asm=z80asm, main=entry)
        result["assemble"] = {"command": build["command"],
                              "returncode": build["returncode"],
                              "output": build["output"],
                              "messages": build["messages"]}
        if build["returncode"] != 0:
            result["verdict"] = ("blocked: сборка не прошла, см. syntax_check "
                                 "по каталогу %s" % out_dir)
            return result
        candidate = build["output"]
    if not candidate or not os.path.isfile(candidate):
        result["verdict"] = "blocked: собранный образ не найден (%s)" % candidate
        return result
    result["candidate"] = os.path.abspath(candidate)
    diff = compare_bytes(rom, candidate, org=origin, objects=objects)
    result["diff"] = diff
    result["summary"] = {
        "compared_bytes": diff["compared_bytes"],
        "bytes_differing": diff["bytes_differing"],
        "runs": len(diff["ranges"]),
        "size_match": diff["size_match"],
    }
    if diff["identical"] and diff["size_match"]:
        verdict = "byte-for-byte identical"
        status = "OK"
    elif diff["identical"]:
        verdict = "байты в общем диапазоне совпали, но размеры разные"
        status = "MISMATCH"
    else:
        verdict = "%d байт(а) различается в %d диапазоне(ах)" % (
            diff["bytes_differing"], len(diff["ranges"]))
        status = "MISMATCH"
    result.update(verdict=verdict, status=status,
                  offenders=sorted({item["rdb_object"] for item in diff["ranges"]
                                    if item.get("rdb_object")}))
    return result


def format_report(result):
    lines = ["rom        %s" % result["rom"],
             "экспорт    %s" % result["out_dir"],
             "rdb        %s" % (result.get("rdb") or "—"), ""]
    build = result.get("assemble")
    if build:
        lines.append("сборка     rc=%s → %s" % (build["returncode"],
                                                build["output"]))
    candidate = result.get("candidate")
    if candidate:
        lines.append("кандидат   %s" % candidate)
    diff = result.get("diff")
    if diff:
        lines.append("размеры    ref=%s cand=%s %s"
                     % (diff["sizes"]["reference"], diff["sizes"]["candidate"],
                        "=" if diff["size_match"] else "≠"))
        lines.append("сравнено   %d байт, различий %d, диапазонов %d"
                     % (diff["compared_bytes"], diff["bytes_differing"],
                        len(diff["ranges"])))
        for item in diff["ranges"][:20]:
            lines.append("  %s–%s (%s)  %s"
                         % (item["start"], item["end"], item["length"],
                            item.get("rdb_object") or "без RDB-объекта"))
            lines.append("      было %s" % (item.get("old") or "")[:96])
            lines.append("      стало %s" % (item.get("new") or "")[:96])
        if len(diff["ranges"]) > 20:
            lines.append("  … ещё %d диапазонов(ов) в --json"
                         % (len(diff["ranges"]) - 20))
        if result.get("offenders"):
            lines.append("виновники (RDB): %s" % ", ".join(result["offenders"]))
    for tail in result.get("stderr_tail") or []:
        lines.append("  | " + tail)
    lines.append("")
    lines.append("ВЕРДИКТ  %s  [%s]  mcp_calls=%s" % (result["verdict"],
                                                      result["status"],
                                                      result["mcp_calls"]))
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="analyze.roundtrip_verify",
        description="ROM → v06c-asm-export → z80asm → побайтовое сравнение")
    parser.add_argument("--rom", required=True)
    parser.add_argument("--dir", default=None, help="каталог экспорта")
    parser.add_argument("--rdb", default=None)
    parser.add_argument("--org", type=lambda s: int(s, 0), default=0x0100)
    parser.add_argument("--exporter", default=None)
    parser.add_argument("--z80asm", default=None)
    parser.add_argument("--candidate", default=None,
                        help="только сравнить готовый бинарь (без пересборки)")
    parser.add_argument("--entry", default="main.asm")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    out_dir = args.dir or os.path.join(".scratch", "export",
                                       os.path.splitext(
                                           os.path.basename(args.rom))[0])
    result = run_verify(args.rom, out_dir, rdb=args.rdb, origin=args.org,
                        assemble=not args.candidate, exporter=args.exporter,
                        z80asm=args.z80asm, candidate=args.candidate,
                        entry=args.entry)
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str)
          if args.json else format_report(result))
    return 0 if result.get("status") == "OK" else 1


if __name__ == "__main__":
    sys.exit(main())
