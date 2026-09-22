"""Lint RDB: целостность модели доверия (ТЗ §12, §28).

Проверяются только формальные свойства — ни семантики, ни угадывания:

    overlap                 два объекта накрывают один адрес
    duplicate address       два объекта начинаются в одном адресе
    invalid size            размер 0/отрицательный или вылезает за образ
    invalid range           адрес вне 0x0000..0xFFFF или вне ROM+RAM окна
    broken link             ссылка на несуществующий объект (или за образ)
    missing properties      нет комментария/доказательств у именованного объекта
    *_unknown               области, ещё не разобраные (список, не ошибка)
    bad name                имя вне шаблонов naming.py

Дополнительно (ТЗ §28, aliases/links/вложенность):

    duplicate_alias         один алиас в объекте встречается дважды
    alias_equals_name       алиас совпал с primary name этого же объекта
    alias_invalid           алиас не проходит шаблон имён для своего типа
    alias_collision         алиас = чужое primary name или закреплён за 2 объектов
    duplicate_link          одна и та же ссылка в объекте повторно
    self_link               объект ссылается на себя
    function_inside_function  функция целиком внутри другой функции
    label_inside_unrelated  метка внутри объекта не-кода

Отдельно (ТЗ §12): идентичность объекта против логических подэлементов и
меток. Отладчик хранит ОДИН объект на адрес, поэтому «подэлементы» (строка
внутри блока, глиф внутри шрифта) обязаны жить в properties/comment/links,
а не плодить объекты на том же адресе. `sub_element_candidates` находит
такие случаи и подсказывает, куда их перенести.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

from analyze import naming
from analyze.mcp_session import addr_hex, envelope, to_addr
from analyze.rdb import Rdb

SEVERITIES = ("error", "warning", "info")

# Обязательные поля для «взрослых» объектов: без доказательств объект не факт.
EVIDENCE_PROPERTIES = ("evidence", "params", "role", "runtime_bytes")


class Finding:
    __slots__ = ("code", "severity", "address", "message", "object_name")

    def __init__(self, code, severity, address, message, object_name=None):
        self.code = code
        self.severity = severity
        self.address = to_addr(address)
        self.message = message
        self.object_name = object_name

    def to_dict(self):
        return {
            "code": self.code,
            "severity": self.severity,
            "address": addr_hex(self.address) if self.address is not None else None,
            "object": self.object_name,
            "message": self.message,
        }

    def __repr__(self):
        return "%-8s %-18s %-7s %s" % (
            self.severity, self.code, addr_hex(self.address) if self.address is not None
            else "-", self.message)


def lint_rdb(rdb, image_lo=None, image_hi=None, require_comment=True):
    """Полный lint. Возвращает (findings, summary)."""
    findings = []
    objects = list(rdb.objects)

    # -- идентичность и адреса --------------------------------------------
    by_addr = {}
    for obj in objects:
        if obj.address is None or not (0x0000 <= obj.address <= 0xFFFF):
            findings.append(Finding("invalid_range", "error", obj.address,
                                    "адрес вне адресного пространства 8080", obj.name))
        by_addr.setdefault(obj.address, []).append(obj)
        if obj.size < 0 or obj.size > 0x10000 or obj.size == 0:
            findings.append(Finding(
                "missing_size", "warning", obj.address,
                "size=%s — длина области неизвестна (v06c-asm-export не сможет "
                "выделить байты без размера)" % obj.size, obj.name))

    for address, group in sorted(by_addr.items(), key=lambda kv: kv[0] or 0):
        if len(group) > 1:
            findings.append(Finding(
                "duplicate_address", "error", address,
                "несколько объектов на один адрес: %s — отладчик хранит один "
                "объект на адрес, подэлементы оформлять свойствами"
                % ", ".join(o.name for o in group), group[0].name))

    # -- пересечения -------------------------------------------------------
    ordered = sorted((o for o in objects if o.address is not None),
                     key=lambda o: o.address)
    for index in range(len(ordered) - 1):
        left, right = ordered[index], ordered[index + 1]
        if left.size_known and right.size_known and left.end >= right.address:
            findings.append(Finding(
                "overlap", "error", right.address,
                "%s (%s..%s) перекрывает начало %s"
                % (left.name, addr_hex(left.address), addr_hex(left.end),
                   right.name), left.name))

    # -- границы образа ----------------------------------------------------
    if image_lo is not None and image_hi is not None:
        lo, hi = to_addr(image_lo), to_addr(image_hi)
        for obj in objects:
            if obj.address < lo and obj.end >= lo and obj.type in ("function", "data"):
                findings.append(Finding(
                    "outside_image", "warning", obj.address,
                    "объект начинается до образа ROM (%s) — возможно, это "
                    "рантайм-ОЗУ; должно быть помечено в comment" % addr_hex(lo),
                    obj.name))
            if obj.end > hi:
                findings.append(Finding(
                    "past_image", "warning", obj.address,
                    "конец %s выходит за образ (%s)" % (addr_hex(obj.end), addr_hex(hi)),
                    obj.name))

    # -- ссылки ------------------------------------------------------------
    known = set(by_addr)
    # primary name → объект(ы): нужно, чтобы поймать коллизию «алиас = чужое имя».
    name_owner = {}
    for obj in objects:
        name_owner.setdefault(obj.name, []).append(obj)
    for obj in objects:
        link_counts = {}
        for target in obj.links:
            if target is None:
                findings.append(Finding("broken_link", "error", obj.address,
                                        "ссылка без адреса", obj.name))
                continue
            if target == obj.address:
                findings.append(Finding("self_link", "error", obj.address,
                                        "объект ссылается сам на себя", obj.name))
            link_counts[target] = link_counts.get(target, 0) + 1
            if not (0x0000 <= target <= 0xFFFF):
                findings.append(Finding("broken_link", "error", obj.address,
                                        "ссылка %s вне адресного пространства"
                                        % target, obj.name))
            elif target not in known:
                findings.append(Finding("unlinked_target", "info", obj.address,
                                        "ссылка на %s — по адресу нет объекта"
                                        % addr_hex(target), obj.name))
        for target, count in sorted(link_counts.items(),
                                    key=lambda kv: kv[0] if kv[0] is not None else 0):
            if count > 1:
                findings.append(Finding(
                    "duplicate_link", "warning", obj.address,
                    "ссылка на %s повторяется %d раз — links уникальны внутри "
                    "объекта" % (addr_hex(target), count), obj.name))

    # -- aliases (ТЗ §15, §28) --------------------------------------------
    alias_owner = {}
    for obj in objects:
        raw = _raw_alias_list(obj.properties.get("aliases"))
        counts = {}
        for alias in raw:
            counts[alias] = counts.get(alias, 0) + 1
        for alias, count in sorted(counts.items()):
            if count > 1:
                findings.append(Finding(
                    "duplicate_alias", "warning", obj.address,
                    "алиас %r встречается %d раз — внутри объекта алиасы "
                    "уникальны" % (alias, count), obj.name))
        for alias in obj.get_aliases():
            if alias == obj.name:
                findings.append(Finding(
                    "alias_equals_name", "warning", obj.address,
                    "алиас %r равен primary name — secondary-имя не должно "
                    "дублировать основное" % alias, obj.name))
            elif not naming.is_valid_alias(alias, obj.type):
                findings.append(Finding(
                    "alias_invalid", "error", obj.address,
                    "алиас %r не проходит шаблон имён для типа %s"
                    % (alias, obj.type), obj.name))
            alias_owner.setdefault(alias, []).append(obj)
            for other in name_owner.get(alias, []):
                if other.address != obj.address:
                    findings.append(Finding(
                        "alias_collision", "error", obj.address,
                        "алиас %r совпадает с primary name объекта по %s"
                        % (alias, addr_hex(other.address)), obj.name))
    for alias, owners in sorted(alias_owner.items()):
        addrs = {o.address for o in owners}
        if len(addrs) > 1:
            findings.append(Finding(
                "alias_collision", "error", min(addrs),
                "алиас %r закреплён за %d объектами по разным адресам"
                % (alias, len(addrs)), owners[0].name))

    # -- вложенность объектов (ТЗ §26, §27) -------------------------------
    sized = [o for o in objects if o.size_known and o.address is not None]
    for obj in sized:
        container = None
        for cand in sized:
            if cand is obj or not (cand.address < obj.address <= cand.end):
                continue
            if container is None or cand.address > container.address:
                container = cand
        if container is None:
            continue
        if obj.type == "function" and container.type == "function":
            findings.append(Finding(
                "function_inside_function", "warning", obj.address,
                "функция %s лежит внутри %s (%s..%s)"
                % (obj.name, container.name, addr_hex(container.address),
                   addr_hex(container.end)), obj.name))
        elif obj.type == "label" and container.type not in ("function", "code",
                                                            "label"):
            findings.append(Finding(
                "label_inside_unrelated", "info", obj.address,
                "метка %s внутри несвязанного объекта %s (тип %s)"
                % (obj.name, container.name, container.type), obj.name))

    # -- имена и доказательства -------------------------------------------
    for obj in objects:
        for severity, message in naming.validate(obj.name, obj.type):
            findings.append(Finding("bad_name", severity, obj.address, message,
                                    obj.name))
        has_evidence = any(key in obj.properties for key in EVIDENCE_PROPERTIES)
        if not obj.comment and require_comment and not obj.is_unknown:
            findings.append(Finding("missing_properties", "warning", obj.address,
                                    "нет комментария: непонятно, откуда знание",
                                    obj.name))
        if not has_evidence and not obj.is_unknown and obj.type != "label":
            findings.append(Finding("missing_evidence", "warning", obj.address,
                                    "нет ни одного свойства-доказательства (%s)"
                                    % "/".join(EVIDENCE_PROPERTIES), obj.name))

    # -- *_unknown ---------------------------------------------------------
    for obj in objects:
        if obj.is_unknown:
            findings.append(Finding("unknown_region", "info", obj.address,
                                    "недообследовано: %s (%d Б)" % (obj.name, obj.size),
                                    obj.name))

    summary = {
        "objects": len(objects),
        "findings": len(findings),
        "by_severity": {sev: sum(1 for f in findings if f.severity == sev)
                        for sev in SEVERITIES},
        "by_code": _histogram(f.code for f in findings),
        "unknowns": sum(1 for f in findings if f.code == "unknown_region"),
        "unknown_bytes": sum(o.size for o in objects if o.is_unknown),
    }
    return findings, summary


def sub_element_candidates(rdb):
    """Что просится в подэлементы одного объекта, а не в отдельные записи.

    Детерминированные признаки (все обязательны):
      * один и тот же тип и один и тот же размер;
      * объекты идут плотной чередой без промежутков;
      * не меньше трёх штук;
      * у имён общий корень длиннее префикса (var_/data_/…) — иначе это
        просто соседние по памяти переменные, а не массив.
    Это кандидат, а не решение: сливать объекты или нет решает AI.
    """
    out = []
    ordered = sorted(rdb.objects, key=lambda o: o.address)
    window = []
    for obj in ordered + [None]:
        contiguous = (obj is not None and window and obj.type == window[-1].type
                      and obj.size == window[-1].size and obj.size_known
                      and obj.address == window[-1].end + 1)
        if contiguous:
            window.append(obj)
            continue
        if len(window) >= 3 and _shares_stem(o.name for o in window):
            step = window[1].address - window[0].address
            out.append({
                "type": window[0].type,
                "start": addr_hex(window[0].address),
                "end": addr_hex(window[-1].end),
                "count": len(window),
                "stride": step,
                "suggestion": "один объект %s..%s size=%d + перечень элементов "\
                              "в properties" % (addr_hex(window[0].address),
                                                 addr_hex(window[-1].end),
                                                 step * len(window)),
                "names": [o.name for o in window[:6]],
            })
        window = [obj] if obj is not None else []
    return out


def _shares_stem(names, min_extra=2):
    """Есть ли у имён общий корень длиннее стандартного префикса."""
    names = list(names)
    stem = os.path.commonprefix(names)
    prefix_len = max((len(p) for p in naming.PREFIX_TYPE if stem.startswith(p)),
                     default=0)
    return len(stem) - prefix_len >= min_extra


def label_report(rdb):
    """Метки и затравки control flow: Labels не обязаны иметь размер."""
    labels = [o for o in rdb.objects if o.type == "label"]
    return {
        "labels": len(labels),
        "with_comment": sum(1 for o in labels if o.comment),
        "unknown_labels": [o.name for o in labels if o.is_unknown],
    }


def _histogram(items):
    out = {}
    for item in items:
        out[item] = out.get(item, 0) + 1
    return dict(sorted(out.items()))


def _raw_alias_list(value):
    """Список алиасов как он хранится (дубликаты сохраняются) — для duplicate-проверки.

    Допускает list и JSON-строку; get_aliases() для этого не годится — он
    схлопывает дубликаты, а линт обязан их увидеть.
    """
    if value is None:
        return []
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return []
        try:
            value = json.loads(text)
        except ValueError:
            return [text]
    if isinstance(value, (list, tuple)):
        return [str(a) for a in value]
    return []


def format_table(findings, limit=80):
    lines = ["%-8s %-18s %-7s %s" % ("level", "code", "addr", "message")]
    order = {"error": 0, "warning": 1, "info": 2}
    for item in sorted(findings, key=lambda f: (order.get(f.severity, 3),
                                                f.address or 0))[:limit]:
        lines.append(repr(item))
    if len(findings) > limit:
        lines.append("… ещё %d" % (len(findings) - limit))
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(prog="analyze.rdb_lint",
                                     description="Формальная проверка RDB")
    parser.add_argument("--rdb", required=True)
    parser.add_argument("--rom", default=None,
                        help="файл ROM для проверки границ образа")
    parser.add_argument("--org", type=lambda s: int(s, 0), default=0x0100)
    parser.add_argument("--sub-elements", action="store_true",
                        help="показать кандидатов на оформление подэлементами")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--limit", type=int, default=80)
    args = parser.parse_args(argv)

    rdb = Rdb.load(args.rdb)
    lo = hi = None
    if args.rom and os.path.exists(args.rom):
        lo = args.org
        hi = args.org + os.path.getsize(args.rom) - 1
    findings, summary = lint_rdb(rdb, lo, hi)
    summary["labels"] = label_report(rdb)
    if args.sub_elements:
        summary["sub_element_candidates"] = sub_element_candidates(rdb)
    errors = summary["by_severity"]["error"]
    result = envelope({
        "summary": summary,
        "findings": [f.to_dict() for f in findings],
        "rdb": os.path.abspath(args.rdb),
    }, module="rdb_lint", status="CANDIDATE",
        verdict="%d находок, %d блокирующих" % (summary["findings"], errors),
        note="формальные правила RDB: имена, размеры, пересечения, "
             "доказательства; семантику модуль не назначает")
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(format_table(findings, limit=args.limit))
        print("\n" + json.dumps(summary, ensure_ascii=False, indent=2))
    return 1 if summary["by_severity"]["error"] else 0


if __name__ == "__main__":
    sys.exit(main())
