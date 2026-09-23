"""Детерминированный первичный посев RDB из reachable code (ТЗ §3—§27, §44).

Схема (ТЗ §1, §50):

    ROM + entry points
        │
        ▼
    StaticAnalysis.analyze_code   ← debug_analyze_code (единственный источник)
        │  references: CALL/JMP/JCC/RST
        ▼
    build_plan                    ← ЧИСТАЯ функция: candidates против RDB
        │  functions / labels / links / skipped / conflicts
        ▼
    apply_plan (RdbWriter)        ← debug_add_rdb_object / link / property
        │
        ▼
    CoverageEngine.report + candidates  ← слепые цели переходов → labels
        │
        ▼  (повтор, пока есть новые seeds или coverage==100)
       RDB

Архитектурные запреты (ТЗ §4, §48): этот модуль НЕ декодирует 8080, НЕ знает
размеров инструкций, НЕ строит свой CFG и НЕ читает мнемоники из текста
дизассемблирования. Единственные входные данные о control flow — ответ
`debug_analyze_code` (через `CodeAnalysis.references`) и `CoverageReport`
из `coverage.py`. Здесь только арифметика множеств адресов и детерминированный
отбор кандидатов.

Правила отбора (ТЗ §6—§13, §19, §25—§27):

* CALL/RST  → кандидат `function`; JMP/JCC/branch → кандидат `label`;
* один адрес — один объект; `function > label` при конфликте ролей;
* существующий объект авторитетнее кандидата (не перезаписывается);
* цель внутри чужого объекта не порождает новый объект — это conflict;
* размер первичного seed = неизвестен (0), не выдумывается;
* техническое имя детерминировано по адресу (`func_XXXX` / `lbl_XXXX`);
* семантическое имя — только candidate/alias, никогда автоматический факт.

`build_plan` не трогает MCP и не меняет RDB — её можно тестировать на
подставном `CodeAnalysis` и `Rdb` (ТЗ §40).
"""
from __future__ import annotations

import argparse
import json
import os
import sys

from analyze import naming, pipeline_state
from analyze.coverage import CoverageEngine, rdb_after
from analyze.disassembly import StaticAnalysis
from analyze.mcp_session import addr_hex, envelope, open_session, to_addr
from analyze.rdb import Rdb, RdbWriter

# Приоритет ролей одного адреса: function сильнее label (ТЗ §13).
_ROLE_PRIORITY = {"function": 2, "label": 1}

# Классификация reference по типу, который вернул Debugger (ТЗ §6—§9, §17).
_FUNCTION_REF_TYPES = ("call", "rst")
_LABEL_REF_TYPES = ("jump", "conditional_jump", "branch", "jcc")

# Разумные пределы: за ними — защита от бесконечного цикла (ТЗ §24).
DEFAULT_MAX_INSTRUCTIONS = 40000
DEFAULT_MAX_DEPTH = 6


class SeedOptions(object):
    """Переключатели поведения посева (ТЗ §19, §39).

    По умолчанию создаются и функции, и метки, и ссылки; существующие объекты
    не трогаются (`force`/`update_existing` = False).
    """

    def __init__(self, functions=True, labels=True, links=True,
                 force=False, update_existing=False):
        self.functions = functions
        self.labels = labels
        self.links = links
        self.force = force
        self.update_existing = update_existing


def classify_reference(ref_type):
    """Тип reference из `debug_analyze_code` → роль кандидата или None.

    CALL/RST — вызываемый объект (function); JMP/JCC/branch — точка перехода
    (label). Ничего не угадываем по mnemonic: тип даёт Debugger.
    """
    key = (ref_type or "").strip().lower()
    if key in _FUNCTION_REF_TYPES:
        return "function"
    if key in _LABEL_REF_TYPES:
        return "label"
    return None


def _skip(address, reason, obj=None):
    out = {"address": addr_hex(address), "reason": reason}
    if obj is not None:
        out["object"] = obj.name
        out["type"] = obj.type
    return out


def build_plan(entries, analysis, rdb, opts=None):
    """Детерминированный план посева из `analysis` против текущего `rdb`.

    Чистая функция (без MCP, без записи): возвращает dict с ключами
    `entry_points`, `functions`, `labels`, `links`, `skipped`, `conflicts`,
    `existing_objects`. Все списки отсортированы по адресу → идемпотентно и
    независимо от порядка ответов (ТЗ §32).
    """
    opts = opts or SeedOptions()
    entry_addrs = sorted({to_addr(a) for a in entries if to_addr(a) is not None})

    # candidates[addr] = {"kind", "evidence_type", "from"} — роль с наивысшим
    # приоритетом выигрывает; seed_from берётся от раннего (минимального) source.
    candidates = {}

    def offer(address, kind, evidence_type, src):
        rec = candidates.get(address)
        if rec is None or _ROLE_PRIORITY[kind] > _ROLE_PRIORITY[rec["kind"]]:
            candidates[address] = {"kind": kind,
                                   "evidence_type": evidence_type,
                                   "from": src}
        elif (_ROLE_PRIORITY[kind] == _ROLE_PRIORITY[rec["kind"]]
              and src is not None
              and (rec["from"] is None or src < rec["from"])):
            rec["from"] = src

    # 1. Явные точки входа — структурный evidence (ТЗ §5, §11).
    for address in entry_addrs:
        offer(address, "function", "entry", address)

    # 2. References анализатора: обходим детерминированно (по to, затем from).
    refs = sorted(analysis.references,
                  key=lambda r: (r["to"] if r["to"] is not None else -1,
                                 r["from"] if r["from"] is not None else -1))
    for ref in refs:
        kind = classify_reference(ref["type"])
        if kind is None or ref["to"] is None:
            continue
        offer(ref["to"], kind, (ref["type"] or "").strip().lower(), ref["from"])

    functions, labels, skipped, conflicts = [], [], [], []
    existing_objects = 0
    claimed = set()

    for address in sorted(candidates):
        cand = candidates[address]
        kind = cand["kind"]
        if kind == "function" and not opts.functions:
            skipped.append(_skip(address, "functions disabled"))
            continue
        if kind == "label" and not opts.labels:
            skipped.append(_skip(address, "labels disabled"))
            continue

        exact = rdb.by_addr(address)
        if exact is not None:
            # Существующий объект авторитетнее кандидата (ТЗ §19, §38).
            existing_objects += 1
            skipped.append(_skip(address, "existing object", exact))
            continue

        cover = rdb.at(address)
        if cover is not None and cover.address != address:
            # Внутренний переход: не плодим объект внутри чужого (ТЗ §26, §27).
            conflicts.append({"address": addr_hex(address),
                              "reason": "target inside existing object",
                              "wanted": kind, "object": cover.name,
                              "object_type": cover.type})
            continue

        if kind == "function":
            name = naming.technical_function_name(address)
            rtype = "function"
        else:
            name = naming.technical_label_name(address)
            rtype = "label"
        record = {
            "address": address,
            "name": name,
            "type": rtype,
            "size": 0,  # первичный seed размера не знает (ТЗ §25)
            "evidence": {
                "seed_source": "debug_analyze_code",
                "seed_evidence": cand["evidence_type"],
                "seed_from": addr_hex(cand["from"]) if cand["from"] is not None
                else None,
            },
        }
        (functions if kind == "function" else labels).append(record)
        claimed.add(address)

    links = _build_links(analysis, rdb, claimed, entry_addrs, opts)
    return {
        "entry_points": [addr_hex(a) for a in entry_addrs],
        "functions": functions,
        "labels": labels,
        "links": links,
        "skipped": skipped,
        "conflicts": conflicts,
        "existing_objects": existing_objects,
    }


def _build_links(analysis, rdb, claimed, entry_addrs, opts):
    """RDB links строго из references Debugger (ТЗ §17, §18).

    Источник ссылки — объект, им владеющий: сам адрес `from`, если он объект,
    иначе объект, накрывающий `from`. Если владельца нет — ссылку не строим
    (нечего вешать). Дубликаты и self-link отбрасываются, порядок детерминирован.
    """
    if not opts.links:
        return []
    object_addrs = set(claimed) | set(entry_addrs) | {o.address for o in rdb.objects}
    seen = set()
    links = []
    for ref in sorted(analysis.references,
                      key=lambda r: (r["from"] if r["from"] is not None else -1,
                                     r["to"] if r["to"] is not None else -1)):
        src, dst = ref["from"], ref["to"]
        if classify_reference(ref["type"]) is None or src is None or dst is None:
            continue
        source = src
        if source not in object_addrs:
            cover = rdb.at(src)
            source = cover.address if cover is not None else None
        if source is None or source == dst:
            continue
        if (source, dst) in seen:
            continue
        seen.add((source, dst))
        links.append({"source": source, "target": dst})
    links.sort(key=lambda l: (l["source"], l["target"]))
    return links


class BatchSaver(object):
    """Каждые `every` внесённых изменений — save и checkpoint (ТЗ-§4.2, §4.4).

    Pipeline обязан гарантировать `max_unsaved_objects <= 10`, а посев — один
    из самых «толстых» mutating-этапов. Saver ничего не знает о MCP: он только
    дёргает `writer.save()` (debug_save_rdb) и просит pipeline подтвердить
    состояние checkpoint_active(). Без --save-every (every=0) — выключен.
    """

    def __init__(self, writer, every, log=None):
        self.writer = writer
        self.every = max(0, int(every))
        self.log = log
        self.applied = 0        # всего изменений с начала посева
        self.since_save = 0     # изменений с последнего save
        self.batches = 0
        self.saves = 0

    def note(self, changes=1, pending=0):
        """Зарегистрировать внесённое изменение; при достижении лимита — flush."""
        if not self.every:
            return False
        self.applied += changes
        self.since_save += changes
        if self.since_save >= self.every:
            return self.flush(pending)
        return False

    def flush(self, pending=0):
        """save → checkpoint; True, если что-то сохранили."""
        if not self.every or not self.since_save:
            return False
        self.batches += 1
        self.writer.save()
        self.saves += 1
        self.since_save = 0
        pipeline_state.checkpoint_active(
            current_stage="seed_rdb", current_batch=self.batches,
            processed_objects=self.applied,
            pending_objects=int(pending or 0), status="checkpoint")
        if self.log:
            self.log("batch %d: сохранено после %d изменений (%d в ожидании)" % (
                self.batches, self.applied, int(pending or 0)))
        return True


def apply_plan(writer, plan, opts=None, saver=None):
    """Выполнить план через `RdbWriter` (идемпотентно). Возвращает счётчики.

    Сухой прогон (`writer.dry_run`) считает то же самое, ничего не меняя:
    `ensure_object` читает состояние, но `_do` не шлёт запись.
    `saver` (BatchSaver) отмечает каждое внесённое изменение, чтобы делать
    save+checkpoint пачками не больше `max_unsaved_objects` (ТЗ-§4.2).
    """
    opts = opts or SeedOptions()
    counts = {"functions_added": 0, "labels_added": 0, "links_added": 0,
              "aliases_added": 0}
    items = (["function"] * len(plan.get("functions", []))
             + ["label"] * len(plan.get("labels", []))
             + ["link"] * len(plan.get("links", [])))
    left = {"pending": len(items)}

    def note(changed):
        left["pending"] -= 1
        if saver is not None:
            saver.note(1 if changed else 0, left["pending"])

    for rec in plan.get("functions", []):
        result = writer.ensure_object(rec["address"], rec["name"], rec["type"],
                                      size=rec.get("size") or None,
                                      properties=rec.get("evidence"))
        if result.get("created"):
            counts["functions_added"] += 1
        note(True)
    for rec in plan.get("labels", []):
        result = writer.ensure_object(rec["address"], rec["name"], rec["type"],
                                      size=rec.get("size") or None,
                                      properties=rec.get("evidence"))
        if result.get("created"):
            counts["labels_added"] += 1
        note(True)
    for link in plan.get("links", []):
        writer.add_link(link["source"], link["target"])
        counts["links_added"] += 1
        note(True)
    return counts


class SeedRdb(object):
    """Оркестратор fixpoint: analyze_code → plan → apply → coverage → повтор.

    Единственный потребитель MCP в этом модуле. `StaticAnalysis` даёт references,
    `CoverageEngine` — слепые цели переходов; собственных расчётов CFG нет.
    """

    def __init__(self, session, static=None, coverage=None, opts=None,
                 max_instructions=DEFAULT_MAX_INSTRUCTIONS, saver=None):
        self.session = session
        self.static = static or StaticAnalysis(session)
        self.coverage = coverage or CoverageEngine(session, static=self.static)
        self.opts = opts or SeedOptions()
        self.max_instructions = int(max_instructions)
        self.saver = saver

    def run(self, entries, image_lo, image_hi, rdb, writer,
            max_depth=DEFAULT_MAX_DEPTH, log=None):
        entries = sorted({to_addr(a) for a in entries if to_addr(a) is not None})
        existing_objects = len(rdb.objects)
        active = list(entries)
        rdb_model = rdb
        totals = {"functions_added": 0, "labels_added": 0, "links_added": 0,
                  "aliases_added": 0}
        seen_functions, seen_labels, seen_links = set(), set(), set()
        conflicts, skipped = [], []
        iterations = 0
        fixpoint = False
        report = None

        for index in range(1, max(1, int(max_depth)) + 1):
            iterations = index
            analysis = self.static.analyze_code(active, self.max_instructions)
            plan = build_plan(active, analysis, rdb_model, self.opts)
            counts = apply_plan(writer, plan, self.opts, saver=self.saver)
            for key in totals:
                totals[key] += counts[key]
            for rec in plan["functions"]:
                seen_functions.add(rec["address"])
            for rec in plan["labels"]:
                seen_labels.add(rec["address"])
            for link in plan["links"]:
                seen_links.add((link["source"], link["target"]))
            skipped.extend(plan["skipped"])
            conflicts.extend(plan["conflicts"])
            rdb_model = rdb_after(rdb_model, writer)

            # Слепые цели переходов, которые анализатор не заочерил, закрываем
            # Label-затравкой через общий API coverage (ТЗ §8, §23, §35).
            report = self.coverage.report(active, image_lo, image_hi)
            blind = self.coverage.candidates(report, rdb_model)
            blind_seeded = []
            for address in blind:
                if address in active or rdb_model.by_addr(address) is not None:
                    continue
                name = naming.technical_label_name(address)
                result = writer.ensure_object(
                    address, name, "label",
                    properties={"seed_source": "coverage",
                                "seed_evidence": "blind_branch_target"})
                if result.get("created"):
                    totals["labels_added"] += 1
                    seen_labels.add(address)
                    blind_seeded.append(address)
                if self.saver is not None:
                    self.saver.note(1, len(blind) - blind.index(address) - 1)
            rdb_model = rdb_after(rdb_model, writer)

            discovered = (set(seen_functions) | set(seen_labels)
                          | set(blind_seeded))
            new_active = sorted(discovered - set(active))
            if log:
                log("итер %d: функций +%d, меток +%d, ссылок %d, новых входов %d, "
                    "покрытие %.2f %%" % (
                        index, len(seen_functions), len(seen_labels),
                        len(seen_links), len(new_active), report.percent()))
            active = sorted(set(active) | set(new_active))
            if not new_active:
                fixpoint = True
                break
            if report.percent() >= 100.0:
                fixpoint = True
                break

        percent = report.percent() if report else 0.0
        return {
            "entry_points": [addr_hex(a) for a in entries],
            "functions_added": totals["functions_added"],
            "labels_added": totals["labels_added"],
            "links_added": totals["links_added"],
            "aliases_added": totals["aliases_added"],
            "existing_objects": existing_objects,
            "iterations": iterations,
            "fixpoint": fixpoint,
            "coverage_percent": percent,
            "blind_targets": ([addr_hex(a) for a in report.blind_targets]
                              if report else []),
            "conflicts": _dedupe_dicts(conflicts),
            "skipped": _dedupe_dicts(skipped),
        }


def _dedupe_dicts(items, key_fields=("address", "reason")):
    seen, out = set(), []
    for item in sorted(items, key=lambda d: tuple(str(d.get(k)) for k in key_fields)):
        marker = tuple(str(item.get(k)) for k in key_fields)
        if marker in seen:
            continue
        seen.add(marker)
        out.append(item)
    return out


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="analyze.seed_rdb",
        description="Детерминированный первичный посев RDB из reachable code")
    parser.add_argument("--rom", required=True)
    parser.add_argument("--rdb", default=None, help="путь к .rdb (иначе — из сессии)")
    parser.add_argument("--org", type=lambda s: int(s, 0), default=0x0100)
    parser.add_argument("--entry", action="append", default=[],
                        help="точка входа (адрес, повторяемо); по умолчанию --org")
    parser.add_argument("--hi", type=lambda s: int(s, 0), default=None,
                        help="конец образа ROM (по умолчанию org+size-1)")
    parser.add_argument("--max-instructions", type=int,
                        default=DEFAULT_MAX_INSTRUCTIONS)
    parser.add_argument("--max-depth", type=int, default=DEFAULT_MAX_DEPTH,
                        help="предел итераций fixpoint")
    parser.add_argument("--apply", action="store_true",
                        help="записать изменения (по умолчанию только dry-run)")
    parser.add_argument("--dry-run", action="store_true",
                        help="только показать план (это и так режим по умолчанию)")
    parser.add_argument("--save-every", type=int, default=0,
                        help="при --apply: каждые N внесённых изменений делать "
                             "debug_save_rdb и подтверждать checkpoint (0 — один "
                             "итоговый save; так просит pipeline, ТЗ-§4.2)")
    parser.add_argument("--no-functions", action="store_true")
    parser.add_argument("--no-labels", action="store_true")
    parser.add_argument("--no-links", action="store_true")
    parser.add_argument("--force", action="store_true",
                        help="разрешить технические правки существующих объектов")
    parser.add_argument("--update-existing", action="store_true",
                        help="обновлять size/links/props у существующих объектов")
    parser.add_argument("--cache", default=None)
    parser.add_argument("--server", default=None)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    dry_run = not args.apply          # режим по умолчанию — сухой прогон (§20)
    size = os.path.getsize(args.rom) if os.path.exists(args.rom) else 0
    lo = args.org
    hi = args.hi if args.hi is not None else lo + size - 1
    entries = [to_addr(a) for a in args.entry] or [args.org]

    session, cache = open_session(rom=args.rom, org=args.org, server=args.server,
                                  cache_dir=args.cache)
    try:
        static = StaticAnalysis(session, cache)
        coverage = CoverageEngine(session, cache, static=static)
        if args.rdb and os.path.isfile(args.rdb):
            rdb = Rdb.load(args.rdb)
        else:
            # Файла ещё нет (свежий ROM без .rdb — riseout-сценарий) или путь
            # не задан: состояние даёт сам отладчик, он же при save создаст файл.
            rdb = Rdb.from_session(session)
        writer = RdbWriter(session, dry_run=dry_run)
        opts = SeedOptions(functions=not args.no_functions,
                           labels=not args.no_labels,
                           links=not args.no_links,
                           force=args.force,
                           update_existing=args.update_existing)
        saver = None if dry_run else BatchSaver(
            writer, args.save_every,
            log=lambda m: print("# " + m, file=sys.stderr))
        engine = SeedRdb(session, static=static, coverage=coverage, opts=opts,
                         max_instructions=args.max_instructions, saver=saver)
        result = engine.run(entries, lo, hi, rdb, writer, max_depth=args.max_depth,
                            log=lambda m: print("# " + m, file=sys.stderr))
        if not dry_run:
            writer.save()
            # Итоговый save оставил RDB полностью сохранённым. Если посев шёл
            # пачками (--save-every), доливаем незакрытую пачку и подтверждаем
            # состояние checkpoint-ом: хэш перечитывается с диска (ТЗ-§6—§8).
            if saver is not None:
                saver.flush(0)
                pipeline_state.checkpoint_active(
                    current_stage="seed_rdb", current_batch=saver.batches,
                    processed_objects=saver.applied, pending_objects=0,
                    status="checkpoint")
            result["batches"] = saver.batches if saver else 0
            result["saves"] = (saver.saves if saver else 0) + 1
        status = "PASS" if result["fixpoint"] else "CANDIDATE"
        verdict = ("dry-run: functions %d, labels %d, links %d, существующих %d, "
                   "итераций %d" % (result["functions_added"],
                                    result["labels_added"], result["links_added"],
                                    result["existing_objects"],
                                    result["iterations"]))
        if not dry_run:
            verdict = "применено: " + verdict
        if result["conflicts"]:
            verdict += ", конфликтов %d" % len(result["conflicts"])
        data = envelope(
            result, module="seed_rdb", session=session, cache=cache,
            status=status, verdict=verdict,
            note="кандидаты только из debug_analyze_code/coverage; sizes и "
                 "семантические имена не выдумываются; существующие объекты "
                 "не перезаписаны (ТЗ §19, §25, §34)")
        print(json.dumps(data, ensure_ascii=False,
                         indent=2 if args.json else None))
    except Exception as error:                     # noqa: BLE001 — сбой посева не роняет прогон
        data = envelope({"module": "seed_rdb", "error": "%s: %s"
                         % (type(error).__name__, error), "fixpoint": False},
                        module="seed_rdb", session=session, status="FAILED",
                        verdict="посев завершился ошибкой: %s" % error)
        print(json.dumps(data, ensure_ascii=False,
                         indent=2 if args.json else None))
        return 1
    finally:
        session.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
