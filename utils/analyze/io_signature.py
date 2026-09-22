"""Кандидатная аппаратная сигнатура портов (ТЗ §18, §19).

Порядок такой и только такой:

    debug_get_io_trace          port → направление → частота → значения
      ↓
    debug_find_bytecode_sequence / debug_find_immediate_in_range
                                порт → адреса инструкций, которые к нему обращаются
      ↓
    RDB (debugger)              адрес → функция
      ↓
    candidate hardware signature

Ничего из этого не называется «устройство X». Совпадение с документированной
картой портов Vector-06C оформляется полем `documented_role` + `match` и
остаётся КАНДИДАТОМ: права «объявить» сигнатуру фактом у этого модуля нет
(ТЗ §34).

Атрибуция адреса инструкции — слабое место, и это честно зафиксировано:
`debug_get_io_trace` отдаёт `{sequence, type, port, value}` без PC. Поэтому
адреса ищутся статически (поиск байтовых последовательностей + запрос к
анализатору значений операнда), а динамической привязки «вот эта конкретная
инструкция выполнилась» здесь нет. Направление (IN/OUT) берётся из opcode,
частота — из трассы.

`IN r, port` = DB <port>, `OUT port` = D3 <port> — единственные формы 8080,
где порт стоит непосредственным байтом (docs/VECTOR_CPU_COMMANDS.md).
"""
from __future__ import annotations

import argparse
import json
import sys

from analyze import naming
from analyze.capabilities import CapabilityProfile
from analyze.disassembly import StaticAnalysis, merge
from analyze.mcp_session import addr_hex, envelope, open_session, to_addr
from analyze.probe import RomRun
from analyze.rdb import Rdb

OPCODES = {
    "in": 0xDB,          # IN r,(imm8)
    "out": 0xD3,         # OUT (imm8),a
}

# Документированная карта портов Vector-06C. Только справочные метки для
# сопоставления кандидатов; источник — docs/, а не догадка по поведению ROM.
PORT_REFERENCE = {
    0x00: ("КР580ВВ55 #1 управляющее слово", "out", "docs/vector_techinfo.md#282, docs/VECTOR_VERIFIED.md#8.1"),
    0x01: ("КР580ВВ55 #1 порт C (магн/СС/УС/РУС)", "rw", "docs/VECTOR_VERIFIED.md#8.1"),
    0x02: ("КР580ВВ55 #1 порт B (бордюр, 512px, клавиатура)", "rw", "docs/VECTOR_VERIFIED.md#8.1"),
    0x03: ("КР580ВВ55 #1 порт A (верт. скролл, маска строк)", "rw", "docs/VECTOR_VERIFIED.md#8.1"),
    0x04: ("КР580ВВ55 #2 управляющее слово", "out", "docs/VECTOR_VERIFIED.md#8.2"),
    0x05: ("КР580ВВ55 #2 порт C #2", "rw", "docs/VECTOR_VERIFIED.md#8.2"),
    0x06: ("КР580ВВ55 #2 порт B #2 (covox)", "rw", "docs/VECTOR_VERIFIED.md#8.2"),
    0x07: ("КР580ВВ55 #2 порт A #2", "rw", "docs/VECTOR_VERIFIED.md#8.2"),
    0x08: ("КР580ВИ53 управляющее слово", "out", "docs/VECTOR_VERIFIED.md#8.3"),
    0x09: ("КР580ВИ53 счётчик канала 2", "rw", "docs/VECTOR_VERIFIED.md#8.3"),
    0x0A: ("КР580ВИ53 счётчик канала 1", "rw", "docs/VECTOR_VERIFIED.md#8.3"),
    0x0B: ("КР580ВИ53 счётчик канала 0", "rw", "docs/VECTOR_VERIFIED.md#8.3"),
    0x0C: ("палитра", "rw", "docs/VECTOR_VERIFIED.md#8.4"),
    0x10: ("банковая память", "out", "docs/VECTOR_VERIFIED.md#277"),
}


def port_events(io_trace):
    """Нормализация трассы: [(sequence, port, direction, value)]."""
    out = []
    for ev in io_trace.get("events") or []:
        port = ev.get("port")
        if port is None:
            continue
        out.append((int(ev.get("sequence") or 0), to_addr(port),
                    str(ev.get("type") or "").lower(), to_addr(ev.get("value"))))
    return sorted(out, key=lambda item: item[0])


def aggregate_ports(events):
    """port → статистика направлений/частот/значений (только арифметика)."""
    per_port = {}
    for sequence, port, direction, value in events:
        slot = per_port.setdefault(port, {
            "port": port, "in_count": 0, "out_count": 0, "other_count": 0,
            "values_in": [], "values_out": [], "sequences": [],
        })
        if direction == "in":
            slot["in_count"] += 1
            slot["values_in"].append(value)
        elif direction == "out":
            slot["out_count"] += 1
            slot["values_out"].append(value)
        else:
            slot["other_count"] += 1
        slot["sequences"].append(sequence)
    for slot in per_port.values():
        slot["total"] = slot["in_count"] + slot["out_count"] + slot["other_count"]
        slot["direction"] = _direction(slot)
        slot["window"] = [min(slot["sequences"]), max(slot["sequences"])] \
            if slot["sequences"] else None
        slot["bits"] = _bit_traits(slot["values_in"] + slot["values_out"])
        slot["distinct_values"] = _value_stats(slot)
        del slot["sequences"]
    return [per_port[port] for port in sorted(per_port)]


def _direction(slot):
    if slot["in_count"] and slot["out_count"]:
        return "rw"
    if slot["in_count"]:
        return "in"
    if slot["out_count"]:
        return "out"
    return "unknown"


def _bit_traits(values):
    """Какие биты порта вообще используются. Детерминированный признак,
    без трактовки «бит 4 = режим 512» — это поле `documented_role`."""
    if not values:
        return None
    used_or = 0
    for value in values:
        used_or |= value
    return {
        "or": addr_hex(used_or),          # хотя бы раз была единица
        "and": addr_hex(_and_all(values)),  # единица во всех записях
        "width": max(1, used_or.bit_length()),
    }


def _and_all(values):
    acc = 0xFF
    for value in values:
        acc &= value
    return acc


def _value_stats(slot):
    def distinct(values):
        return sorted(set(values))
    din, dout = distinct(slot["values_in"]), distinct(slot["values_out"])
    return {
        "in": [addr_hex(v) for v in din[:16]],
        "in_distinct": len(din),
        "out": [addr_hex(v) for v in dout[:16]],
        "out_distinct": len(dout),
    }


class IoSignatureFinder:
    """Собирает кандидатные сигнатуры: трасса + статический поиск адресов."""

    def __init__(self, session, cache=None, caps=None, static=None,
                 image_lo=0x0100, image_hi=0x3FFF, rom=None):
        self.session = session
        self.cache = cache
        self.caps = caps or CapabilityProfile.from_session(session)
        self.static = static or StaticAnalysis(session, cache, self.caps)
        self.rom = rom
        self._lo, self._hi = to_addr(image_lo), to_addr(image_hi)
        self._inventory = None
        self._image = None
        self._code_ranges = None
        self._rdb = None

    # -- статическая привязка портов к адресам ------------------------------

    def analyzed_code_ranges(self, entries, image_lo, image_hi):
        """Диапазоны разобранного кода: по ним отсекаются ложные срабатывания
        поиска байтов (данные тоже содержат DB/D3)."""
        report = self.static.coverage_report(entries, image_lo, image_hi)
        return merge([(start, end) for start, end in report.code_ranges])

    def find_port_sites(self, port, image_lo, image_hi, code_ranges):
        """Адреса инструкций IN/OUT с порт-операндом == port (из инвентаря)."""
        if code_ranges is not None:
            self._code_ranges = code_ranges
        return _dedup_sites([{"opcode": kind, "address": addr,
                             "in_code": self._in_code(addr),
                             "owner": self._owner_name(addr),
                             "source": "debug_find_bytecode_sequence"}
                             for kind, addr in self.inventory()
                             .get(to_addr(port), [])])

    def find_immediate_sites(self, port, image_lo, image_hi):
        if not self.caps.has("debug_find_immediate_in_range"):
            return []
        payload = self.session.call("debug_find_immediate_in_range", {
            "range_start": to_addr(image_lo), "range_end": to_addr(image_hi),
            "value": to_addr(port), "max_matches": 256,
        })
        matches = payload.get("matches") or payload.get("addresses") or []
        out = []
        for item in matches:
            address = to_addr(item.get("address") if isinstance(item, dict) else item)
            if address is not None:
                out.append(address)
        return sorted(set(out))

    # -- сборка ------------------------------------------------------------

    def collect(self, entries, image_lo, image_hi, run=None, rdb=None,
                io_trace=None, log=None):
        """Полный проход. `run` — готовый RomRun (иначе будет канонический
        boot, ТЗ §14)."""
        lo, hi = to_addr(image_lo), to_addr(image_hi)
        self._lo, self._hi = lo, hi
        self._inventory = None
        self._image = None if self.rom else self._image
        if io_trace is None:
            if run is None:
                run = RomRun(self.session, self.cache, rom=self.rom, caps=self.caps)
                run.scenario(seconds=1.0, pause_after=True)
            io_trace = run.evidence("io_probe").get("io_trace") or {}
        events = port_events(io_trace)
        traced = aggregate_ports(events)
        code_ranges = self.analyzed_code_ranges(entries, lo, hi)
        rdb = rdb or Rdb.from_session(self.session)
        traced_ports = {slot["port"] for slot in traced}

        signatures = []
        # Порт-адреса ищутся и для портов из трассы, и для всех известной
        # карты: «в ROM есть OUT 0Ch, но за 1 с не выполнилось» — тоже вывод.
        static_only = self._static_sweep_all(lo, hi, code_ranges, rdb,
                                            skip=traced_ports, log=log)
        for slot in traced:
            sites = self.find_port_sites(slot["port"], lo, hi, code_ranges)
            immediates = self.find_immediate_sites(slot["port"], lo, hi)
            signatures.append(self._signature(slot, sites, immediates, rdb,
                                             observed=True))
        signatures.extend(static_only)
        signatures.sort(key=lambda s: (-s["observed_weight"], s["port_int"]))
        return {
            "io_trace": {
                "tool": "debug_get_io_trace",
                "events": len(events),
                "note": ("в трассе нет поля PC: привязка к инструкции "
                         "статическая, не динамическая"),
            },
            "code_ranges": len(code_ranges),
            "signatures": signatures,
            "summary": _summary(signatures, events),
        }

    def _static_sweep_all(self, lo, hi, code_ranges, rdb, skip, log=None):
        """Порты, которые ROM трогает кодом, но трасса их не поймала."""
        out = []
        self._rdb = rdb
        self._code_ranges = code_ranges
        inventory = self.inventory()
        for port in sorted(set(inventory) - set(skip)):
            sites = self.find_port_sites(port, lo, hi, code_ranges)
            slot = {
                "port": port, "direction": _direction_of(sites),
                "in_count": 0, "out_count": 0, "other_count": 0, "total": 0,
                "bits": None, "distinct_values": None, "window": None,
            }
            out.append(self._signature(slot, sites, [], rdb, observed=False))
        if log:
            log("портов в трассе: %d, только-статических: %d, всего адресов "
                "IN/OUT в образе: %d" % (len(skip), len(out),
                                        sum(len(v) for v in inventory.values())))
        return out

    def inventory(self):
        """port → [(in|out, адрес)] по ВСЕМУ образу ROM.

        Два masked-поиска на весь диапазон (`pattern=[DB,00] mask=[FF,00]`
        находит все IN независимо от номера порта), номер порта дочитывается
        из IMAGE-образа по address+1 — это чтение известного операнда
        (docs/VECTOR_CPU_COMMANDS.md), а не декодирование инструкций.

        Ищем по всему образу, а не только по разобранному коду: иначе порт,
        который ROM трогает из области, куда analyze_code не дошёл, просто
        исчезнет из результатов. Ложные срабатывания в данных помечаются
        `in_code=False` и в уверенность не идут.
        """
        if self._inventory is not None:
            return self._inventory
        found = []                       # [(kind, address)]
        for kind, opcode in OPCODES.items():
            payload = self._evidence("debug_find_bytecode_sequence", {
                "range_start": self._lo, "range_end": self._hi,
                "pattern": [opcode, 0x00], "mask": [0xFF, 0x00],
                "max_matches": 1024,
            })
            for address in payload.get("addresses") or []:
                found.append((kind, to_addr(address)))
        image = self.image_source()
        data = image.read(self._lo, self._hi)
        inventory = {}
        for kind, address in found:
            offset = address + 1 - self._lo
            if not (0 <= offset < len(data)):
                continue                 # операнд за концом образа
            inventory.setdefault(data[offset], []).append((kind, address))
        for slot in inventory.values():
            slot.sort(key=lambda item: item[1])
        self._inventory = inventory
        return inventory

    def _in_code(self, address):
        return any(start <= address <= end
                   for start, end in (self._code_ranges or []))

    def _owner_name(self, address):
        obj = getattr(self, "_rdb", None)
        obj = obj.at(address) if obj is not None else None
        if obj is None:
            return None
        return obj.name

    def image_source(self):
        if self._image is None:
            from analyze.memory_diff import ImageSource
            path = self.rom or (self.session.rom or {}).get("path")
            if not path:
                raise RuntimeError("не известен путь к ROM-образу: передайте "
                                   "rom=… или загрузите ROM в сессию")
            self._image = ImageSource(path, self._lo)
        return self._image

    def _evidence(self, tool, args):
        if self.cache is not None:
            payload, _ = self.cache.get_or_call(self.session, tool, args,
                                                stamp=None, source="IMAGE")
            return payload
        return self.session.call(tool, args)

    def _signature(self, slot, sites, immediates, rdb, observed):
        port = slot["port"]
        owners = []
        for site in sites:
            owners.append({
                "address": addr_hex(site["address"]),
                "opcode": site["opcode"],
                "source": site["source"],
                "in_code": site.get("in_code"),
                "function": site.get("owner") or _function_of(rdb, site["address"]),
            })
        reference = PORT_REFERENCE.get(port)
        direction = slot["direction"]
        match = bool(reference) and (reference[1] in ("rw", direction))
        by_immediate = set(immediates)
        hit_by_immediate = sum(1 for site in sites if site["address"] in by_immediate)
        code_sites = sum(1 for site in sites if site.get("in_code"))
        confidence = _confidence(observed, direction, code_sites,
                                 hit_by_immediate, bool(reference))
        return {
            "port": addr_hex(port),
            "port_int": port,
            "observed": observed,
            "observed_weight": (2 if observed else 0) + slot["total"],
            "direction": direction,
            "frequency": {"in": slot["in_count"], "out": slot["out_count"],
                          "total": slot["total"], "window": slot["window"]},
            "values": slot["distinct_values"],
            "bits": slot["bits"],
            "sites": owners,
            "site_count": len(sites),
            "code_site_count": code_sites,
            "immediate_matches": [addr_hex(a) for a in immediates[:16]],
            "immediate_count": len(immediates),
            "documented_role": reference[0] if reference else None,
            "documented_source": reference[2] if reference else None,
            "documented_match": match if reference else None,
            "confidence": confidence,
            "status": "CANDIDATE",
            "name_hint": naming.propose("variable", "port_%02x" % port, port),
        }


def _function_of(rdb, address):
    obj = rdb.at(address) if rdb is not None else None
    return obj.name if obj else None


def _dedup_sites(sites):
    seen, out = set(), []
    for site in sites:
        key = (site["opcode"], site["address"])
        if key in seen:
            continue
        seen.add(key)
        out.append(site)
    return sorted(out, key=lambda s: s["address"])


def _direction_of(sites):
    kinds = {s["opcode"] for s in sites}
    if {"in", "out"} <= kinds:
        return "rw"
    return "in" if kinds == {"in"} else ("out" if kinds == {"out"} else "unknown")


def _confidence(observed, direction, site_count, immediate_hits, documented):
    """Правило простое и открытое: каждое наблюдение добавляет балл."""
    score = 0
    if observed:
        score += 2
    if site_count:
        score += 2
    if immediate_hits:
        score += 1
    if documented:
        score += 1
    if direction == "unknown" and not observed:
        score -= 1
    return {0: "very_low", 1: "low", 2: "low", 3: "medium",
            4: "medium", 5: "high", 6: "high"}[max(0, min(6, score))]


def _summary(signatures, events):
    return {
        "ports_observed": sum(1 for s in signatures if s["observed"]),
        "ports_static_only": sum(1 for s in signatures if not s["observed"]),
        "ports_matched_to_docs": sum(1 for s in signatures
                                     if s["documented_match"]),
        "events": len(events),
        "by_confidence": {level: sum(1 for s in signatures
                                     if s["confidence"] == level)
                          for level in ("high", "medium", "low", "very_low")},
    }


def format_table(result):
    lines = ["%-6s %-6s %-9s %-9s %-5s %-8s %s"
             % ("порт", "напр", "уверен.", "адр[вкоде]", "всего", "докум.",
                "роль/функции")]
    for sig in result["signatures"]:
        funcs = ", ".join(sorted({s["function"] for s in sig["sites"]
                                 if s["function"]})) or "—"
        role = sig["documented_role"] or "—"
        lines.append("%-6s %-6s %-9s %-9s %-5d %-8s %s | %s" % (
            sig["port"], sig["direction"], sig["confidence"],
            "%d[%d]" % (sig["site_count"], sig["code_site_count"]),
            sig["frequency"]["total"], ("есть" if sig["documented_match"]
                                        else ("нет" if sig["documented_match"] is False
                                              else "—")),
            role, funcs))
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="analyze.io_signature",
        description="Кандидатная аппаратная сигнатура портов ROM")
    parser.add_argument("--rom", required=True)
    parser.add_argument("--org", type=lambda s: int(s, 0), default=0x0100)
    parser.add_argument("--entry", action="append", default=[])
    parser.add_argument("--hi", type=lambda s: int(s, 0), default=None)
    parser.add_argument("--rdb", default=None)
    parser.add_argument("--seconds", type=float, default=1.0)
    parser.add_argument("--cache", default=None)
    parser.add_argument("--server", default=None)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    import os

    size = os.path.getsize(args.rom)
    lo = args.org
    hi = args.hi if args.hi is not None else lo + size - 1
    session, cache = open_session(rom=args.rom, org=args.org, server=args.server,
                                  cache_dir=args.cache)
    try:
        finder = IoSignatureFinder(session, cache, rom=args.rom)
        run = RomRun(session, cache, rom=args.rom, org=args.org)
        # Единственный канонический прогон (ТЗ §14): boot → run → пауза;
        # трасса берётся из этого же доказательства, а не из второй гонки.
        run.scenario(seconds=args.seconds)
        io_trace = run.evidence("io").get("io_trace") or {}
        entries = [to_addr(a) for a in args.entry] or [args.org]
        rdb = Rdb.load(args.rdb) if args.rdb else Rdb.from_session(session)
        result = finder.collect(entries, lo, hi, run=run, rdb=rdb,
                                io_trace=io_trace,
                                log=lambda m: print("# " + m, file=sys.stderr))
        result["rom"] = os.path.basename(args.rom)
        result["run_events"] = run.events
        order = ("very_low", "low", "medium", "high")
        ranked = sorted(result["signatures"],
                        key=lambda s: order.index(s["confidence"]),
                        reverse=True)
        candidates = [{
            "name": s["name_hint"],
            "confidence": s["confidence"],
            "object": "порт %s" % s["port"],
            "detail": "%s, в трассе: %s, участков кода: %d, роль по "
                      "документации: %s%s"
                      % (s["direction"], "да" if s["observed"] else "нет",
                         s["code_site_count"], s["documented_role"] or "нет",
                         "" if s["documented_match"] is not False
                         else " (расхождение)"),
        } for s in ranked[:8]]
        summary = result["summary"]
        result = envelope(
            result, module="io_signature", session=session, cache=cache,
            status="CANDIDATE", candidates=candidates,
            verdict="аппаратных подписей: %d, поймано в трассе %d, "
                    "пересечение с документацией %d"
                    % (len(result["signatures"]), summary["ports_observed"],
                       summary["ports_matched_to_docs"]),
            note="это кандидаты на подпись порта, а не вывод о железе: "
                 "совпадение с документацией проверяемо, направление — нет")
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(format_table(result))
            print(json.dumps(result["summary"], ensure_ascii=False, indent=2))
        stats = session.stats()
        print("# mcp calls: %d" % stats["total_calls"], file=sys.stderr)
    finally:
        session.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
