"""Покрытие ROM и fixpoint «gaps ∩ branch targets» (ТЗ §10, §34).

Схема:

    диапазон ROM
      − разобранный код (из отладчика)
      − экстенты объектов RDB
      = gaps

    gaps ∩ branch targets (берутся ТОЛЬКО из дизассемблирования отладчика)
      = кандидаты недостающих точек входа

    для кандидата: Label в RDB → debug_analyze_code → пересчёт

пока покрытие не станет 100 % или пока не перестанут появляться новые цели.

Python здесь не трактует инструкции: чтобы понять, что в дыре лежит переход,
он спрашивает `debug_coverage_report` / `debug_analyze_code`. Если
пакетного инструмента нет, покрытие считается локально — но исключительно
как арифметика множеств адресов поверх готовых границ `ranges` (ТЗ §8).
"""
from __future__ import annotations

import argparse
import json
import os
import sys

from analyze import naming
from analyze.capabilities import CapabilityProfile
from analyze.disassembly import StaticAnalysis, merge, subtract
from analyze.mcp_session import addr_hex, envelope, open_session, to_addr
from analyze.rdb import Rdb, RdbWriter

# Практический предел итераций: за ним значит, что цели переходов упираются в
# данные или в ограничение анализатора, а не в отсутствие затравок.
MAX_ROUNDS = 12


class CoverageRound:
    __slots__ = ("index", "percent", "gap_bytes", "candidates", "seeded",
                 "blind_targets", "uncovered_ranges")

    def __init__(self, index, report, candidates, seeded):
        self.index = index
        self.percent = report.percent()
        self.gap_bytes = report.gap_bytes()
        self.candidates = list(candidates)
        self.seeded = list(seeded)
        self.blind_targets = len(report.blind_targets)
        self.uncovered_ranges = [addr_hex(a) for a, _ in report.uncovered_ranges]

    def to_dict(self):
        return {
            "round": self.index,
            "coverage_percent": self.percent,
            "uncovered_bytes": self.gap_bytes,
            "blind_branch_targets": self.blind_targets,
            "candidates": [addr_hex(a) for a in self.candidates],
            "seeded": [addr_hex(a) for a in self.seeded],
            "uncovered_starts": self.uncovered_ranges,
        }


class CoverageRun:
    """Итог fixpoint-процедуры."""

    def __init__(self, image_lo, image_hi, entries):
        self.image_lo = to_addr(image_lo)
        self.image_hi = to_addr(image_hi)
        self.entries = [to_addr(a) for a in entries]
        self.rounds = []
        self.final = None
        self.converged = False
        self.reason = None
        self.rdb_only_gaps = []

    def to_dict(self):
        # Машиночитаемый набор (ТЗ §35): seed_rdb читает именно эти ключи,
        # а не пересчитывает слепые цели самостоятельно.
        final = self.final
        return {
            "image": [addr_hex(self.image_lo), addr_hex(self.image_hi)],
            "entries": [addr_hex(a) for a in self.entries],
            "rounds": [r.to_dict() for r in self.rounds],
            "iterations": len(self.rounds),
            "converged": self.converged,
            "fixpoint": self.converged,
            "reason": self.reason,
            "blind_targets": ([addr_hex(a) for a in final.blind_targets]
                              if final else []),
            "reachable": ([[addr_hex(a), addr_hex(b)] for a, b in final.code_ranges]
                          if final else []),
            "gaps": ([[addr_hex(a), addr_hex(b)] for a, b in final.uncovered_ranges]
                     if final else []),
            "final": final.summary() if final else None,
            "gaps_without_rdb": [[addr_hex(a), addr_hex(b)]
                                 for a, b in self.rdb_only_gaps],
        }


class CoverageEngine:
    def __init__(self, session, cache=None, caps=None, static=None):
        self.session = session
        self.cache = cache
        self.caps = caps or CapabilityProfile.from_session(session)
        self.static = static or StaticAnalysis(session, cache, self.caps)

    # -- один шаг ----------------------------------------------------------

    def report(self, entries, image_lo, image_hi):
        return self.static.coverage_report(entries, image_lo, image_hi)

    def gaps_against_rdb(self, report, rdb):
        """Дыры покрытия, которые не накрыты НИ ОДНИМ объектом RDB."""
        covered = list(report.code_ranges) + [
            (o.address, o.end) for o in rdb.objects
        ]
        return subtract((report.image_lo, report.image_hi), covered)

    def candidates(self, report, rdb):
        """Цели переходов без разобранного кода, лежащие внутри дыр.

        Кандидат не должен попадать внутрь существующего RDB-объекта: если
        адрес уже описан, семантику правит AI, а не затравка.
        """
        out = []
        for target in report.blind_targets:
            if any(o.address == target for o in rdb.objects):
                continue
            if rdb.at(target) is not None:
                continue
            for start, end in report.uncovered_ranges:
                if start <= target <= end:
                    out.append(target)
                    break
        return sorted(set(out))

    # -- fixpoint ----------------------------------------------------------

    def fixpoint(self, entries, image_lo, image_hi, rdb_path=None, writer=None,
                 max_rounds=MAX_ROUNDS, save=True, dry_run=False, log=None):
        """add Label → analyze → пересчёт, пока покрытие не закроется."""
        # RDB-файл может ещё не родиться (свежий ROM без sidecar: riseout-
        # сценарий, решение §55) — тогда читаем живой RDB из отладчика,
        # как делает seed_rdb.
        rdb = (Rdb.load(rdb_path)
               if rdb_path and os.path.isfile(rdb_path)
               else Rdb.from_session(self.session))
        writer = writer or RdbWriter(self.session, dry_run=dry_run)
        run = CoverageRun(image_lo, image_hi, entries)
        seen = set()
        for index in range(1, int(max_rounds) + 1):
            report = self.report(entries, image_lo, image_hi)
            rdb = (Rdb.load(rdb_path)
                   if rdb_path and not dry_run and os.path.isfile(rdb_path)
                   else rdb_after(rdb, writer))
            cand = [a for a in self.candidates(report, rdb) if a not in seen]
            run.rdb_only_gaps = self.gaps_against_rdb(report, rdb)
            seeded = []
            if cand:
                for addr in cand:
                    seen.add(addr)
                    name = naming.unknown_for("label", addr)
                    writer.add_label(addr, name)
                    seeded.append(addr)
                if not dry_run:
                    # Затравки должны уйти в сервер до пересчёта покрытия.
                    writer.save() if save else None
            run.rounds.append(CoverageRound(index, report, cand, seeded))
            run.final = report
            if log:
                log("раунд %d: покрытие %.2f %%, дыр %d Б, кандидатов %d, "
                    "затравлено %d" % (index, report.percent(), report.gap_bytes(),
                                       len(cand), len(seeded)))
            if report.percent() >= 100.0:
                run.converged = True
                run.reason = "coverage 100%"
                break
            if not cand:
                run.converged = report.gap_bytes() == 0
                run.reason = ("нет новых целей переходов; остаток — данные"
                              if not run.converged else "покрытие закрыто")
                break
        else:
            run.reason = "достигнут предел итераций (%d)" % max_rounds
        if not dry_run and save:
            writer.save()
        run.writer_summary = writer.summary()
        return run


def rdb_after(rdb, writer):
    """Локальное отражение внесённых затравок (для следующего шага кандидатов)."""
    from analyze.rdb import RdbObject

    added = [a for a in writer.actions if a["kind"] == "add"]
    if not added:
        return rdb
    objects = list(rdb.objects)
    known = {o.address for o in objects}
    for action in added:
        args = action["arguments"]
        if args["address"] in known:
            continue
        objects.append(RdbObject(args["address"], args["name"], args["type"],
                                 args.get("size", 1)))
        known.add(args["address"])
    return Rdb(objects, meta=rdb.meta, path=rdb.path)


def coverage_table(report, rdb=None, rows=40):
    """Человекочитаемая таблица дыр (для отчёта)."""
    lines = ["%-11s %-11s %6s  %s" % ("старт", "конец", "байт", "кандидатов")]
    for start, end in report.uncovered_ranges[:rows]:
        hits = sum(1 for b in report.blind_targets if start <= b <= end)
        tag = ""
        if rdb is not None:
            obj = rdb.at(start)
            tag = " [%s]" % obj.name if obj else ""
        lines.append("%-11s %-11s %6d  %4d%s" % (addr_hex(start), addr_hex(end),
                                                 end - start + 1, hits, tag))
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(prog="analyze.coverage",
                                     description="Покрытие ROM и fixpoint затравок")
    parser.add_argument("--rom", required=True)
    parser.add_argument("--org", type=lambda s: int(s, 0), default=0x0100)
    parser.add_argument("--entry", action="append", default=[])
    parser.add_argument("--rdb", default=None, help="путь к .rdb (иначе — из сессии)")
    parser.add_argument("--hi", type=lambda s: int(s, 0), default=None,
                        help="конец образа ROM (по умолчанию org+size-1)")
    parser.add_argument("--seed", action="store_true",
                        help="реально добавлять Label-затравки в RDB")
    parser.add_argument("--rounds", type=int, default=MAX_ROUNDS)
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
        engine = CoverageEngine(session, cache)
        entries = [to_addr(a) for a in args.entry] or [args.org]
        if args.seed:
            run = engine.fixpoint(entries, lo, hi, rdb_path=args.rdb,
                                  max_rounds=args.rounds,
                                  log=lambda m: print("# " + m, file=sys.stderr))
            data = run.to_dict()
        else:
            report = engine.report(entries, lo, hi)
            rdb = (Rdb.load(args.rdb)
                   if args.rdb and os.path.isfile(args.rdb)
                   else Rdb.from_session(session))
            data = {
                "report": report.summary(),
                "gaps_without_rdb": [[addr_hex(a), addr_hex(b)]
                                     for a, b in engine.gaps_against_rdb(report, rdb)],
                "candidates": [addr_hex(a) for a in engine.candidates(report, rdb)],
            }
        report = data.get("report") or {}
        percent = report.get("coverage_percent", data.get("coverage_percent"))
        gaps = report.get("uncovered_ranges") or data.get("uncovered_starts") or []
        without_rdb = data.get("gaps_without_rdb") or []
        verdict = ("покрытие %s%%, незанятых промежутков %d, без покрытия RDB %d"
                   % (percent, len(gaps), len(without_rdb)))
        if "converged" in data:
            verdict += ", %s" % ("фиксированная точка достигнута"
                                 if data["converged"] else
                                 "фиксированная точка за %d раунда(ов) "
                                 "не достигнута: %s"
                                 % (len(data.get("rounds") or []),
                                    data.get("reason")))
        data = envelope(
            data, module="coverage", session=session, cache=cache,
            status="CANDIDATE", verdict=verdict,
            note="проценты и промежутки — арифметика по ответам отладчика; "
                 "что там код, а что данные, решает не этот модуль (ТЗ §8)")
        print(json.dumps(data, ensure_ascii=False, indent=2 if args.json else None))
    finally:
        session.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
