"""Размеры RDB-объектов против реальной длины кода (ТЗ §11, §12, §19, §8).

Идея: RDB хранит заявленный `size`, а длину кода в байтах знает только
дизассемблер. Модуль берёт у отладчика ОДНУ линейную разборку окна ROM
(`debug_disassemble_image`) и дальше работает только интервальной
арифметикой и сложением длин — коды не декодируются, CFG не строится,
семантика не назначается (ТЗ §8).

Что находится:

* `instruction-crosses-end` — целая инструкция на границе объекта вылезает за
  заявленный конец: размер точно неверен, это ошибка, а не недоказанность;
* `trailing-partial-bytes` — в конец объекта не попадает ни одна целая
  инструкция, но остаются байты: размер рассогласован с границами;
* `decode-extends-past-size` — линейная разборка от начала объекта дотягивает
  дальше заявленного (кандидат: за ретом мог начаться следующий код, поэтому
  confidence низкая);
* `size-unknown` — размера в RDB нет; измеренный диапазон отдаётся как
  предположение;
* `objects-overlap` — два объекта накладываются: один из размеров завышен.

Ничего не предлагается «исправить» автоматически: вывод — CANDIDATE,
применение размера — решение человека или RdbWriter (ТЗ §34).
"""
from __future__ import annotations

import argparse
import json
import os
import sys

from analyze.capabilities import CapabilityProfile
from analyze.disassembly import StaticAnalysis
from analyze.mcp_session import addr_hex, open_session, session_fields, to_addr
from analyze.rdb import Rdb

CODE_TYPES = ("function", "code")
DATA_TYPES = ("data", "table", "string", "music", "variable", "label")
# Дальше этого числа инструкций от одного объекта не идём: защита от
# «линейная разборка ушла через весь ROM».
MAX_DECODE_SPAN = 0x2000


def instruction_map(instructions):
    """адрес → размер инструкции, по одной линейной разборке окна."""
    return {item.address: int(item.size or 1) for item in instructions}


def decode_extent(sizes, start, hard_stop):
    """Сумма длин целых инструкций от start до hard_stop (не включая).

    Возвращает (покрыто_байт, адрес_последней_инструкции, дошли_ли_до_стопы).
    Остановка — когда следующего адреса нет в карте разборки: это граница
    линейной разборки, а не вывод о смысле кода.
    """
    cursor = to_addr(start)
    total = 0
    last = None
    while cursor < hard_stop:
        size = sizes.get(cursor)
        if size is None:
            return total, last, False
        total += size
        last = cursor
        cursor += size
    return total, last, True


def neighbours(objects):
    """Объекты, отсортированные по адресу, с «следующим началом» для каждого."""
    ordered = sorted(objects, key=lambda obj: obj.address)
    for index, obj in enumerate(ordered):
        nxt = ordered[index + 1].address if index + 1 < len(ordered) else None
        yield obj, nxt


def measure(rdb, sizes, rom_lo, rom_hi, next_hint=None):
    findings, rows = [], []
    # За окном ROM измерять нечего: дизассемблируется образ, а RAM-объекты
    # (буфер глифов 0x6000, спрайты 0x7418) в нём отсутствуют.
    windowed = [item for item in rdb.objects
                if item.name and rom_lo <= item.address <= rom_hi]
    skipped = len([item for item in rdb.objects if item.name]) - len(windowed)
    for obj, nxt in neighbours(windowed):
        declared = obj.size if obj.size_known else None
        end = obj.end
        limit = min(nxt if nxt is not None else rom_hi + 1, rom_hi + 1)
        if limit <= obj.address:                       # следующий прижался вплотную
            limit = end + 1
        row = {"name": obj.name, "address": addr_hex(obj.address),
               "type": obj.type, "declared_size": declared,
               "declared_end": addr_hex(end), "decode_to_next": 0,
               "crosses_end_by": 0, "slack_bytes": 0}
        if declared is None:
            extent, last, reached = decode_extent(sizes, obj.address,
                                                 min(obj.address + MAX_DECODE_SPAN,
                                                     limit))
            row["measured_extent"] = extent
            rows.append(row)
            kind_hint = ("кандидат на заполнение size через "
                         "debug_update_rdb_object" if obj.is_code else
                         "для данных размер = до начала следующего объекта")
            findings.append({
                "rule": "size-unknown", "severity": "info", "object": obj.name,
                "detail": "размера в RDB нет; линейная разборка от %s даёт %d "
                          "байт(а) до %s"
                          % (addr_hex(obj.address), extent,
                             addr_hex(obj.address + extent - 1) if extent else "—"),
                "suggestion": "тип=%s, %s" % (obj.type, kind_hint)})
            continue
        # Помещается ли целая инструкция на границе конца
        boundary_size = sizes.get(end)
        if obj.is_code and boundary_size:
            covered, tail_addr, _ = decode_extent(sizes, obj.address, end + 1)
            if covered == 0:
                findings.append({
                    "rule": "entry-not-on-instruction-boundary", "severity": "warn",
                    "object": obj.name,
                    "detail": "от %s не стартует ни одна инструкция линейной "
                              "разборки: начало объекта попадает в середину "
                              "инструкции"
                              % addr_hex(obj.address),
                    "suggestion": "CANDIDATE: либо адрес объекта неверен, либо "
                                  "линейная разборка разошлась с true-потоком "
                                  "(проверить вызывающих)",
                    "evidence": ["размер заявлен %d байт" % declared]})
            elif covered > declared:
                over = covered - declared
                tail_size = sizes.get(tail_addr) if tail_addr is not None else None
                findings.append({
                    "rule": "instruction-crosses-end", "severity": "warn",
                    "object": obj.name,
                    "detail": "размер %d, но целых инструкций от начала "
                              "помещается %d (полезло на %d байт)"
                              % (declared, covered, over),
                    "suggestion": "кандидат: размер ≥ %d; следующий объект "
                                  "начинается с %s"
                                  % (covered, addr_hex(nxt) if nxt else "—"),
                    "evidence": ["последняя целая инструкция с %s длиной %s, "
                                 "конец %s"
                                 % (addr_hex(tail_addr), tail_size,
                                    addr_hex(tail_addr + tail_size - 1))
                                 if tail_size else "граница разборки не найдена"]})
                row["crosses_end_by"] = over
            elif covered < declared:
                slack = declared - covered
                findings.append({
                    "rule": "trailing-partial-bytes", "severity": "info",
                    "object": obj.name,
                    "detail": "размер %d, инструкций ровно %d, остаток %d байт"
                              % (declared, covered, slack),
                    "suggestion": "либо в хвосте данные (тогда size завышен для "
                                  "кода), либо объект короче на %d байт" % slack})
                row["slack_bytes"] = slack
        # Насколько дотягивает линейная разборка за заявленный конец
        if obj.is_code:
            extent, last, reached = decode_extent(sizes, obj.address,
                                                 min(end + MAX_DECODE_SPAN,
                                                     limit))
            row["decode_to_next"] = extent
            if extent > declared and not reached:
                findings.append({
                    "rule": "decode-extends-past-size", "severity": "info",
                    "object": obj.name,
                    "detail": "от начала читается %d байт инструкций против "
                              "заявленных %d (до %s)"
                              % (extent, declared, addr_hex(last) if last
                                 is not None else "—"),
                    "suggestion": "CANDIDATE: за пределом объекта может лежать "
                                  "следующий код или данные — решает человек"})
        rows.append(row)
    # наложения — чистая интервальная арифметика
    ordered = sorted(windowed, key=lambda obj: obj.address)
    pairs = []
    for index, left in enumerate(ordered):
        for right in ordered[index + 1:]:
            if right.address > left.end:
                break                      # дальше по адресу — уже не перекрывается
            pairs.append((left, right))
    for left, right in pairs:
        if right.address <= left.end:
            nested = left.address <= right.address and left.end >= right.end
            findings.append({
                "rule": "object-nested" if nested else "objects-overlap",
                "severity": "info" if nested else "warn",
                "object": left.name,
                "detail": ("%s (%s+%d) накрывает %s целиком"
                           if nested else
                           "%s (%s+%d) перекрывает %s на %d байт(а)")
                          % ((left.name, addr_hex(left.address), left.size,
                              right.name) if nested else
                             (left.name, addr_hex(left.address), left.size,
                              right.name, left.end - right.address + 1)),
                "suggestion": ("вложенность может быть намеренной (записи внутри "
                               "таблицы) — проверьте тип родителя"
                               if nested else
                               "заявленный размер одного из объектов завышен; "
                               "свериться с export.json code/data диапазонами"),
                "evidence": ["%s: %s–%s" % (left.name, addr_hex(left.address),
                                            addr_hex(left.end)),
                             "%s: %s–%s" % (right.name, addr_hex(right.address),
                                            addr_hex(right.end))]})
    return findings, rows, skipped


def build(rom, rdb_path=None, org=0x0100, server=None, cache_dir=None,
          types=None):
    """Один образ → одна линейная разборка → сравнение с RDB."""
    session, cache = open_session(rom=rom, org=org, server=server,
                                  cache_dir=cache_dir)
    try:
        caps = CapabilityProfile.from_session(session)
        caps.require("debug_disassemble_image")
        analysis = StaticAnalysis(session, cache=cache, caps=caps)
        size = os.path.getsize(rom)
        lo, hi = to_addr(org), to_addr(org) + size - 1
        instructions = analysis.disassemble_image(lo, size)
        sizes = instruction_map(instructions)
        rdb = Rdb.load(rdb_path) if rdb_path and os.path.isfile(rdb_path) \
            else Rdb.from_session(session)
        if types:
            wanted = tuple(item.strip().lower() for item in types if item.strip())
            rdb.objects = [item for item in rdb.objects if item.type in wanted]
        findings, rows, skipped = measure(rdb, sizes, lo, hi)
        # неустойчивые размеры важнее, чем «размера нет»: сортировка устойчивая,
        # порядок адресов внутри группы сохраняется
        findings.sort(key=lambda item: 0 if item["severity"] == "warn" else 1)
        counts = {}
        for item in findings:
            counts[item["rule"]] = counts.get(item["rule"], 0) + 1
        code_objects = [item for item in rdb.objects if item.is_code]
        declared_code = sum(item.size for item in code_objects if item.size_known)
        code_names = {item.name for item in code_objects}
        measured_code = sum(row["decode_to_next"] for row in rows
                            if row["name"] in code_names)
        return {
            "rom": os.path.basename(rom),
            "image": [addr_hex(lo), addr_hex(hi)],
            "rdb": rdb_path or "<из сессии>",
            "instructions": len(instructions),
            "decoded_bytes": sum(sizes.values()),
            "objects": len(rdb.objects),
            "in_window": len(rows),
            "out_of_window_skipped": skipped,
            "code_objects": len(code_objects),
            "declared_code_bytes": declared_code,
            "measured_code_bytes": measured_code,
            "by_rule": counts,
            "by_severity": {key: sum(1 for item in findings
                                     if item["severity"] == key)
                            for key in ("warn", "info")},
            "findings": findings,
            "rows": rows,
            "summary": {"warn": sum(1 for item in findings
                                    if item["severity"] == "warn"),
                        "info": len(findings)},
            "verdict": ("%d расхождений(я) размера из %d объектов"
                        % (len(findings), len(rdb.objects)) if findings
                        else "размеры объектов согласуются с разборкой"),
            "status": "CANDIDATE",
            "note": "дизассемблирует отладчик; Python складывает длины и "
                    "сравнивает интервалы (ТЗ §8)",
            **session_fields(session),
        }
    finally:
        session.close()


def format_report(result, limit=6):
    lines = ["rom            %s  окно %s–%s" % (result["rom"],
                                                result["image"][0],
                                                result["image"][1]),
             "разборка       %d инструкций, %d байт"
             % (result["instructions"], result["decoded_bytes"]),
             "rdb            %s, объектов %d (кода %d, в окне ROM %d, вне %s)"
             % (result["rdb"], result["objects"], result["code_objects"],
                result["in_window"], result["out_of_window_skipped"]),
             "байты кода     заявлено %d, измерено %d"
             % (result["declared_code_bytes"], result["measured_code_bytes"]),
             "по правилам    %s" % (result["by_rule"] or "—"),
             "по важности    %s" % result["by_severity"], ""]
    shown = {}
    for item in result["findings"]:
        shown[item["rule"]] = shown.get(item["rule"], 0) + 1
        if item["severity"] != "warn" and shown[item["rule"]] > limit:
            if shown[item["rule"]] == limit + 1:
                lines.append("… %s: ещё %d таких же (полный список в --json)"
                             % (item["rule"],
                                result["by_rule"][item["rule"]] - limit))
            continue
        lines.append("[%s] %-35s %s: %s" % (item["severity"], item["rule"],
                                            item.get("object"), item["detail"]))
        if item.get("suggestion"):
            lines.append("        → %s" % item["suggestion"])
        for evidence in item.get("evidence") or []:
            lines.append("        | %s" % evidence)
    lines.append("")
    lines.append("ВЕРДИКТ  %s  [%s]  mcp_calls=%s" % (result["verdict"],
                                                      result["status"],
                                                      result["mcp_calls"]))
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="analyze.measure_sizes",
        description="Заявленные размеры RDB против длин инструкций")
    parser.add_argument("--rom", required=True)
    parser.add_argument("--org", type=lambda s: int(s, 0), default=0x0100)
    parser.add_argument("--rdb", default=None)
    parser.add_argument("--types", default=None,
                        help="ограничить типы объектов (через запятую)")
    parser.add_argument("--cache", default=None)
    parser.add_argument("--server", default=None)
    parser.add_argument("--limit", type=int, default=6)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    result = build(args.rom, rdb_path=args.rdb, org=args.org,
                   server=args.server, cache_dir=args.cache,
                   types=tuple(args.types.split(",")) if args.types else None)
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str)
          if args.json else format_report(result, limit=args.limit))
    return 0


if __name__ == "__main__":
    sys.exit(main())
