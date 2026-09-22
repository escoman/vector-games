"""Адаптер статики: дизассемблирование и control-flow ОТ ИМЕНИ отладчика (ТЗ §8, §9, §34).

Модуль — единственное место, где остальной пакет получает разборку. Он
прячет ограничения и особенности MCP:

  * `start_address` против `addresses` в `debug_analyze_code` (решается по
    CapabilityProfile, а не проверкой строки в каждом вызывающем коде);
  * пакетный `debug_disassemble_image` с деградацией до N×
    `debug_disassemble_range`, если пакетного инструмента нет;
  * адреса-строки "0x0100" в ответах → int в модели;
  * кэширование каждого ответа (ТЗ §6).

Сам модуль НЕ декодирует опкоды, НЕ строит граф и НЕ решает, что означает
инструкция: мнемоники, размеры и branch_target приходят из Debugger (ТЗ §10,
§34). Всё, что здесь считается, — арифметика диапазонами и множеством.
"""
from __future__ import annotations

import argparse
import json
import sys

from analyze.capabilities import CapabilityProfile
from analyze.mcp_session import addr_hex, bytes_of, open_session, to_addr

# Разумный потолок для линейной разборки: серверный AgentLimits = 40000
# инструкций на изображение.
MAX_IMAGE_INSTRUCTIONS = 40000
# У debug_coverage_report своя планка: maxInstructions 1..10000.
MAX_COVERAGE_INSTRUCTIONS = 10000
# Размер чанка при деградации disassemble_image → disassemble_range.
FALLBACK_CHUNK = 4096


class Instruction:
    """Одна инструкция Так, как её вернул отладчик (без своей интерпретации)."""

    __slots__ = ("address", "mnemonic", "operands", "size", "bytes",
                 "branch_target", "branch_type")

    def __init__(self, address, mnemonic="", operands="", size=1, bytes=None,
                 branch_target=None, branch_type=None):
        self.address = to_addr(address)
        self.mnemonic = (mnemonic or "").strip().lower()
        self.operands = operands or ""
        self.size = int(size or 1)
        self.bytes = list(bytes or [])
        self.branch_target = to_addr(branch_target) if branch_target is not None else None
        self.branch_type = branch_type

    @classmethod
    def from_dict(cls, item):
        return cls(
            address=item.get("address"),
            mnemonic=item.get("mnemonic", ""),
            operands=item.get("operands", ""),
            size=item.get("size", 1),
            bytes=item.get("bytes"),
            branch_target=item.get("branch_target"),
            branch_type=item.get("branch_type"),
        )

    @property
    def text(self):
        return ("%s %s" % (self.mnemonic, self.operands)).strip()

    @property
    def end(self):
        return self.address + self.size - 1

    @property
    def is_branch(self):
        """Есть ли у инструкции цель перехода — по данным отладчика."""
        return self.branch_target is not None

    def to_dict(self):
        return {
            "address": addr_hex(self.address),
            "mnemonic": self.mnemonic,
            "operands": self.operands,
            "size": self.size,
            "branch_target": addr_hex(self.branch_target) if self.branch_target is not None else None,
            "branch_type": self.branch_type,
        }

    def __repr__(self):
        return "%s: %s" % (addr_hex(self.address), self.text)


class CodeAnalysis:
    """Ответ debug_analyze_code, разложенный по полочкам."""

    def __init__(self, entries, payload, source_tool):
        self.entries = [to_addr(a) for a in (entries if isinstance(entries, (list, tuple)) else [entries])]
        self.payload = payload
        self.source_tool = source_tool
        self.instructions = [Instruction.from_dict(i) for i in payload.get("instructions", [])]
        self.references = [
            {"from": to_addr(r.get("from")), "to": to_addr(r.get("to")),
             "type": r.get("type")}
            for r in payload.get("references", [])
        ]
        self.ranges = [(to_addr(r.get("start")), to_addr(r.get("end")))
                       for r in payload.get("ranges", [])]
        self.conflicts = payload.get("conflicts", []) or []
        self.instruction_count = payload.get("instruction_count", len(self.instructions))
        self.code_bytes = payload.get("code_bytes",
                                      sum(i.size for i in self.instructions))
        self.truncated = bool(payload.get("truncated"))

    @property
    def reachable(self):
        """Множество адресов, покрытых анализом (по границам range+размерам)."""
        out = set()
        for start, end in self.ranges:
            out.update(range(start, end + 1))
        return out

    def call_targets(self):
        return sorted({r["to"] for r in self.references if r["type"] == "call"})

    def jump_targets(self):
        return sorted({r["to"] for r in self.references
                       if r["type"] in ("jump", "conditional_jump", "branch", "rst")})

    def all_targets(self):
        return sorted({r["to"] for r in self.references if r["to"] is not None})

    def by_address(self):
        return {i.address: i for i in self.instructions}

    def summary(self):
        return {
            "entries": [addr_hex(a) for a in self.entries],
            "source_tool": self.source_tool,
            "instructions": self.instruction_count,
            "code_bytes": self.code_bytes,
            "ranges": [[addr_hex(a), addr_hex(b)] for a, b in self.ranges],
            "references": len(self.references),
            "truncated": self.truncated,
            "conflicts": len(self.conflicts),
        }


class StaticAnalysis:
    """Статика через MCP с кэшем и деградацией по возможностям сервера."""

    def __init__(self, session, cache=None, caps=None, timeout=None):
        self.session = session
        self.cache = cache
        self.caps = caps or CapabilityProfile.from_session(session)
        self.timeout = timeout

    # -- чтение байт -------------------------------------------------------

    def read_runtime(self, address, length):
        """Байты живого address space (RUNTIME, ТЗ §16)."""
        address, length = to_addr(address), int(length)
        payload, _ = self._evidence(
            "debug_read_memory_range", {"address": address, "length": length},
            source="RUNTIME")
        return bytes(bytes_of(payload))

    # -- дизассемблирование ------------------------------------------------

    def disassemble_range(self, address, size):
        """Один диапазон через debug_disassemble_range."""
        address, size = to_addr(address), int(size)
        payload, _ = self._evidence(
            "debug_disassemble_range", {"address": address, "size": size},
            source="IMAGE")
        return _instructions_of(payload)

    def disassemble_image(self, address, length):
        """Линейная разборка большого диапазона одним вызовом (если возможно)."""
        address, length = to_addr(address), int(length)
        if self.caps.has("debug_disassemble_image"):
            payload, _ = self._evidence(
                "debug_disassemble_image",
                {"address": address, "length": length},
                source="IMAGE", timeout=self.timeout)
            instructions = _instructions_of(payload)
            if payload.get("incomplete_instruction"):
                instructions = instructions  # хвост не дошёл до целой — так и есть
            return instructions
        # Деградация: режем на чанки и зовём обычный диапазон.
        out = []
        cursor = address
        stop = address + length
        while cursor < stop:
            chunk = min(FALLBACK_CHUNK, stop - cursor)
            part = self.disassemble_range(cursor, chunk)
            if not part:
                break
            out.extend(part)
            cursor = part[-1].end + 1
            if part[-1].size > chunk:
                break
        return out

    # -- control flow ------------------------------------------------------

    def analyze_code(self, entries, max_instructions=MAX_IMAGE_INSTRUCTIONS):
        """Анализ достижимого кода от одной или нескольких точек входа.

        Форму параметров (`start_address` / `addresses`) подбирает
        CapabilityProfile — вызывающий передаёт просто список адресов.
        """
        if isinstance(entries, (int, str)):
            entries = [entries]
        addrs = [to_addr(a) for a in entries]
        if not addrs:
            raise ValueError("нужна хотя бы одна точка входа")
        form = self.caps.analyze_code_form()
        args = {"max_instructions": int(max_instructions)}
        tool = "debug_analyze_code"
        if form in ("both", "either") or len(addrs) > 1:
            if form == "start_address":
                args["start_address"] = addrs[0]
            else:
                args["addresses"] = addrs
        else:
            args["start_address"] = addrs[0]
        payload, _ = self._evidence(tool, args, source="IMAGE", timeout=self.timeout)
        return CodeAnalysis(addrs, payload, tool)

    def coverage_report(self, entries, image_lo=None, image_hi=None,
                        max_instructions=MAX_COVERAGE_INSTRUCTIONS):
        """Отчёт покрытия: код, gaps, branch targets, слепые цели JCC.

        Если `debug_coverage_report` недоступен — считаем покрытие локально из
        `analyze_code` (только множеством адресов, без разборки).
        """
        if self.caps.has("debug_coverage_report"):
            args = {}
            addrs = [to_addr(a) for a in (entries if isinstance(entries, (list, tuple)) else [entries])]
            if len(addrs) == 1:
                args["start_address"] = addrs[0]
            else:
                args["addresses"] = addrs
            if image_lo is not None and image_hi is not None:
                args["range_start"] = to_addr(image_lo)
                args["range_length"] = to_addr(image_hi) - to_addr(image_lo) + 1
            args["max_instructions"] = min(int(max_instructions),
                                          MAX_COVERAGE_INSTRUCTIONS)
            payload, _ = self._evidence("debug_coverage_report", args,
                                        source="IMAGE", timeout=self.timeout)
            return CoverageReport(payload, self.caps)
        analysis = self.analyze_code(entries, max_instructions)
        return CoverageReport.from_analysis(analysis, image_lo, image_hi)

    # -- общий путь через кэш ---------------------------------------------

    def _evidence(self, tool, args, source="IMAGE", timeout=None):
        if self.cache is None:
            return self.session.call(tool, args, timeout=timeout), {}
        return self.cache.get_or_call(self.session, tool, args, source=source,
                                      timeout=timeout)


class CoverageReport:
    """Обёртка над debug_coverage_report: множества интервалов, без семантики."""

    def __init__(self, payload, caps=None):
        self.payload = payload
        image = payload.get("image") or {}
        self.image_lo = to_addr(image.get("start"))
        self.image_hi = to_addr(image.get("end"))
        self.code_ranges = [
            (to_addr(r.get("start")), to_addr(r.get("end")))
            for r in payload.get("code_ranges", [])
        ]
        self.uncovered_ranges = [
            (to_addr(r.get("start")), to_addr(r.get("end")))
            for r in payload.get("uncovered_ranges", [])
        ]
        self.branch_targets = [
            {"from": to_addr(b.get("from")), "to": to_addr(b.get("to")),
             "type": b.get("type")}
            for b in payload.get("branch_targets", [])
        ]
        blind = payload.get("uncovered_branch_targets") or []
        self.uncovered_branch_targets = [
            (to_addr(b.get("to")) if isinstance(b, dict) else to_addr(b))
            for b in blind
        ]
        stats = payload.get("stats") or {}
        self.stats = {
            "instruction_count": stats.get("instruction_count"),
            "code_bytes": stats.get("code_bytes"),
            "image_bytes": stats.get("image_bytes"),
            "coverage_percent": stats.get("coverage_percent"),
            "truncated": stats.get("truncated"),
        }

    # -- локальная арифметика интервалов (детерминированная, ТЗ §8) --------

    @classmethod
    def from_analysis(cls, analysis, image_lo=None, image_hi=None):
        covered = sorted(analysis.ranges)
        lo = to_addr(image_lo) if image_lo is not None else (covered[0][0] if covered else 0)
        hi = to_addr(image_hi) if image_hi is not None else (covered[-1][1] if covered else 0)
        uncovered = subtract((lo, hi), covered)
        payload = {
            "image": {"start": addr_hex(lo), "end": addr_hex(hi)},
            "code_ranges": [{"start": addr_hex(a), "end": addr_hex(b)} for a, b in covered],
            "uncovered_ranges": [{"start": addr_hex(a), "end": addr_hex(b)} for a, b in uncovered],
            "branch_targets": [{"from": addr_hex(r["from"]), "to": addr_hex(r["to"]),
                                "type": r["type"]} for r in analysis.references],
            "uncovered_branch_targets": [],
            "stats": {
                "instruction_count": analysis.instruction_count,
                "code_bytes": analysis.code_bytes,
                "image_bytes": hi - lo + 1,
                "coverage_percent": round(
                    100.0 * analysis.code_bytes / max(1, hi - lo + 1), 2),
                "truncated": analysis.truncated,
            },
        }
        return cls(payload)

    @property
    def blind_targets(self):
        """Цели переходов, для которых нет разобранного кода (кандидаты в seed)."""
        return sorted({a for a in self.uncovered_branch_targets if a is not None})

    def target_in_gap(self):
        """То же самое, но гарантированно из uncovered-интервалов."""
        out = set()
        for target in self.blind_targets:
            for start, end in self.uncovered_ranges:
                if start <= target <= end:
                    out.add(target)
                    break
        return sorted(out)

    def gap_bytes(self):
        return sum(end - start + 1 for start, end in self.uncovered_ranges)

    def percent(self):
        total = self.image_hi - self.image_lo + 1 if self.image_hi else 0
        if not total:
            return 0.0
        return round(100.0 * (total - self.gap_bytes()) / total, 2)

    def summary(self):
        return {
            "image": [addr_hex(self.image_lo), addr_hex(self.image_hi)],
            "code_ranges": len(self.code_ranges),
            "uncovered_ranges": [[addr_hex(a), addr_hex(b)]
                                 for a, b in self.uncovered_ranges],
            "uncovered_bytes": self.gap_bytes(),
            "coverage_percent": self.percent() or self.stats.get("coverage_percent"),
            "branch_targets": len(self.branch_targets),
            "blind_branch_targets": len(self.blind_targets),
            "stats": self.stats,
        }


def _instructions_of(payload):
    items = payload.get("instructions") if isinstance(payload, dict) else payload
    return [Instruction.from_dict(i) for i in (items or [])]


def merge(intervals):
    """[(a,b)] → непересекающееся покрытие."""
    out = []
    for start, end in sorted((int(s), int(e)) for s, e in intervals if e is not None):
        if out and start <= out[-1][1] + 1:
            out[-1] = (out[-1][0], max(out[-1][1], end))
        else:
            out.append((start, end))
    return out


def subtract(span, intervals):
    """span=(lo,hi) минус merged-интервалы → список дыр."""
    lo, hi = int(span[0]), int(span[1])
    out, cursor = [], lo
    for start, end in merge(intervals):
        if end < lo or start > hi:
            continue
        start = max(start, lo)
        if start > cursor:
            out.append((cursor, start - 1))
        cursor = max(cursor, min(end, hi) + 1)
        if cursor > hi:
            break
    if cursor <= hi:
        out.append((cursor, hi))
    return out


def main(argv=None):
    """CLI: разборка/анализ диапазона для ручной проверки адаптера."""
    parser = argparse.ArgumentParser(prog="analyze.disassembly",
                                     description="Статика ROM через v06c-mcp")
    parser.add_argument("--rom", required=True)
    parser.add_argument("--org", type=lambda s: int(s, 0), default=0x0100)
    parser.add_argument("--entry", action="append", default=[],
                        help="точка входа (адрес, повторяемо); по умолчанию --org")
    parser.add_argument("--disassemble", metavar="ADDR:LEN",
                        help="линейная разборка диапазона, например 0100:40")
    parser.add_argument("--json", action="store_true", help="вывести JSON")
    parser.add_argument("--cache", default=None)
    parser.add_argument("--server", default=None)
    args = parser.parse_args(argv)

    session, cache = open_session(rom=args.rom, org=args.org,
                                  server=args.server, cache_dir=args.cache)
    try:
        static = StaticAnalysis(session, cache)
        if args.disassemble:
            addr_s, _, len_s = args.disassemble.partition(":")
            instructions = static.disassemble_image(to_addr(addr_s) or args.org,
                                                    int(len_s or 0x40, 0))
            data = [i.to_dict() for i in instructions]
        else:
            entries = [to_addr(a) for a in args.entry] or [args.org]
            data = static.analyze_code(entries).summary()
        print(json.dumps(data, ensure_ascii=False, indent=2 if args.json else None))
        if not args.json:
            stats = cache.stats() if cache else {}
            print("# вызовов MCP: %d, промахов кэша: %s, попаданий: %s"
                  % (session.total_calls, stats.get("misses"), stats.get("hits")))
    finally:
        session.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
