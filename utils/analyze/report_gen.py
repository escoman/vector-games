"""Отчёт StageN.md из результатов модулей (ТЗ §29, §30, §34).

Модули считают и находят; этот файл раскладывает их JSON по обязательным
разделам отчёта и подставляет статистику прогона. Собственных выводов здесь
никто не делает:

* `Verified Facts` — только то, что модуль выдал со статусом `OK`/`FACT`
  (например побайтовый round-trip или совпавший VRAM);
* `Inferences` / `Hypotheses` — всё, у чего статус `CANDIDATE`: высокая и
  средняя уверенность идёт в Inferences, низкая и неизвестная — в Hypotheses.
  Кандидат никогда не повышается до Fact автоматикой (ТЗ §34);
* `Goal` и текст `Method` приходят параметрами командной строки: цель анализа
  назначает человек или AI, генератор её не изобретает.

Принимает либо каталог с `*.json` (каждый — вывод одного модуля), либо один
объединённый файл прогона от `pipeline.py`.
"""
from __future__ import annotations

import argparse
import datetime
import glob
import json
import os
import sys

from analyze import naming

SECTIONS = ("Goal", "ROM", "Method", "Findings", "Verified Facts", "Inferences",
            "Hypotheses", "Unknowns", "Limitations", "Recommended Next Steps")

FACT_STATUSES = ("OK", "FACT", "MATCHED", "CLEAN")
CANDIDATE_STATUSES = ("CANDIDATE", "PARTIAL", "DERIVED")
FAILED_STATUSES = ("MISMATCH", "FAIL", "FAILED", "ERROR", "BLOCKED")
HIGH_CONFIDENCE = ("high", "medium")
SEVERITY_ORDER = {"error": 0, "warn": 1, "warning": 1, "info": 2}

# Что модули отдают как «доказательство» — пути в кэше доказательств.
EVIDENCE_KEYS = ("evidence", "evidence_files", "cache_root", "out_dir",
                 "provenance", "output", "rdb")

# У находок два наречия: линты пишут `rule`/`detail`, rdb_lint — `code`/`message`.
FINDING_ALIASES = (("rule", ("rule", "code")),
                   ("detail", ("detail", "message")),
                   ("severity", ("severity", "level")))


def normalize_finding(item, module):
    """Один вид находки для всех модулей; исходные поля остаются на месте."""
    out = dict(item)
    out.setdefault("module", module)
    for key, sources in FINDING_ALIASES:
        for source in sources:
            if out.get(source) is not None:
                out[key] = out[source]
                break
    if out.get("severity") == "warning":
        out["severity"] = "warn"
    return out


def load_results(source):
    """Каталог *.json или один объединённый файл → {имя_модуля: результат}."""
    results = {}
    if os.path.isdir(source):
        paths = sorted(glob.glob(os.path.join(source, "*.json")))
    else:
        paths = [source]
    for path in paths:
        try:
            with open(path, "r", encoding="utf-8") as handle:
                payload = json.load(handle)
        except (OSError, ValueError) as error:
            print("пропущен %s: %s" % (path, error), file=sys.stderr)
            continue
        name = os.path.splitext(os.path.basename(path))[0]
        if isinstance(payload, dict) and set(payload) - {"module", "results",
                                                         "statistics", "goal",
                                                         "method", "rom"}:
            results[name] = payload
        if isinstance(payload, dict) and isinstance(payload.get("results"), dict):
            # объединённый прогон pipeline.py
            for key, value in payload["results"].items():
                results[key] = value
    return results


def status_of(result):
    return str(result.get("status") or "").upper()


def confidence_of(finding, result):
    return str(finding.get("confidence")
               or result.get("confidence") or "low").lower()


def classify(result):
    """Куда положить результат модуля: Fact-секция или кандидатная.

    Модуль без статуса в отчёте не становится ни фактом, ни выводом: он
    попадает в `unclassified`, и это видно читателю.
    """
    status = status_of(result)
    if status in FACT_STATUSES:
        return "facts"
    if status in CANDIDATE_STATUSES:
        return "candidates"
    if status in FAILED_STATUSES:
        return "blocked"
    return "unknowns" if status else "unclassified"


def collect(results):
    buckets = {"facts": [], "candidates": [], "hypotheses": [], "unknowns": [],
               "findings": [], "blocked": [], "unclassified": []}
    for name, result in sorted(results.items()):
        if not isinstance(result, dict):
            continue
        verdict = result.get("verdict")
        bucket = classify(result)
        summary = {"module": name, "verdict": verdict, "kind": "module",
                   "status": result.get("status"),
                   "mcp_calls": result.get("mcp_calls"),
                   "note": result.get("note")}
        if str(verdict or "").lower().startswith("blocked"):
            bucket = "blocked"
        buckets[bucket].append(summary)
        for finding in result.get("findings") or []:
            if not isinstance(finding, dict):
                continue
            item = normalize_finding(finding, name)
            buckets["findings"].append(item)
            if "unknown" in str(item.get("rule", "")):
                buckets["unknowns"].append({"module": name, "detail": item})
        for candidate in result.get("candidates") or []:
            if not isinstance(candidate, dict):
                continue
            target = ("candidates" if confidence_of(candidate, result)
                      in HIGH_CONFIDENCE else "hypotheses")
            entry = dict(candidate)
            entry.setdefault("module", name)
            buckets[target].append(entry)
        if result.get("blind_spots"):
            buckets["unknowns"].append({"module": name,
                                        "detail": "%d слепых зон покрытия"
                                                  % len(result["blind_spots"])})
    return buckets


def rom_identity(results):
    """Данные о ROM из любого модуля, где они есть."""
    merged = {}
    for name in ("probe", "export_asm", "memory_diff", "rdb_lint", "coverage"):
        result = results.get(name)
        if not isinstance(result, dict):
            continue
        for key in ("rom", "rom_path", "origin", "org", "rom_size", "size",
                    "sha256", "image", "rdb", "entry", "mapping_entry"):
            value = result.get(key)
            if value is not None and key not in merged:
                merged[key] = value
        for key in ("identity", "rom_identity", "export_json"):
            block = result.get(key)
            if isinstance(block, dict):
                for sub in ("sha256", "rom_size", "origin", "rom"):
                    if block.get(sub) is not None and sub not in merged:
                        merged[sub] = block[sub]
    return merged


def statistics(results, stats_file=None):
    """Сводка прогона (ТЗ §30): вызовы, кэш, время, самые дорогие инструменты.

    Файл статистики от `pipeline.py` важнее полевой суммы: поле `mcp_calls`
    модуля — это счётчик на момент его запуска, а один общий сеанс (§4) к тому
    моменту уже наживал вызовы предыдущих модулей, поэтому слагаемые
    перекрываются. `total_mcp_calls` берётся из файла, когда он есть.
    """
    stats = {"total_mcp_calls": 0, "by_module": {}}
    calls_from_modules = True
    for name, result in sorted((results or {}).items()):
        if not isinstance(result, dict):
            continue
        calls = result.get("mcp_calls")
        if isinstance(calls, int):
            stats["total_mcp_calls"] += calls
            stats["by_module"][name] = calls
    if stats_file and os.path.isfile(stats_file):
        with open(stats_file, "r", encoding="utf-8") as handle:
            extra = json.load(handle)
        # `by_module` остаётся от результатов: он говорит, кто сколько съел.
        merged = {key: value for key, value in extra.items()
                  if key not in stats["by_module"]}
        if isinstance(extra.get("total_mcp_calls"), int):
            merged["total_mcp_calls"] = extra["total_mcp_calls"]
            merged.setdefault("mcp_calls_field_sum", stats["total_mcp_calls"])
            calls_from_modules = False
        stats.update(merged)
        stats["statistics_source"] = stats_file
    elif stats_file:
        stats["statistics_file_missing"] = stats_file
    if calls_from_modules and stats["by_module"]:
        stats["mcp_calls_meaning"] = ("сумма mcp_calls по модулям; при общем "
                                     "сеансе слагаемые перекрываются")
    return stats


def rdb_summary(results):
    """Result summary блоком из rdb_lint/coverage: объекты, связи, _unknown."""
    for name in ("rdb_lint", "seed_rdb", "rdb", "coverage", "probe"):
        result = results.get(name)
        if not isinstance(result, dict):
            continue
        summary = result.get("summary") or result.get("rdb") or {}
        if isinstance(summary, dict) and any(
                key in summary for key in ("objects", "total_objects", "links",
                                           "unknown")):
            merged = dict(summary)
            merged.setdefault("source_module", name)
            for key in ("objects", "links", "unknown", "unknown_count",
                        "rdb_path", "dirty", "coverage_percent", "verdict"):
                if result.get(key) is not None and key not in merged:
                    merged[key] = result[key]
            return merged
    return {}


def suggestions(buckets, limit=12):
    """Next steps механически из подсказок находок; приоритет — за человеком."""
    seen, out = set(), []
    for item in buckets["findings"]:
        text = (item.get("suggestion") or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        out.append({"module": item.get("module"), "rule": item.get("rule"),
                    "severity": item.get("severity"), "text": text})
    for item in buckets["blocked"]:
        out.append({"module": item["module"], "rule": "blocked",
                    "severity": "error",
                    "text": "разобрать отказ модуля: %s" % item["verdict"]})
    return out[:limit]


def evidence_refs(results):
    refs = []
    for name, result in sorted((results or {}).items()):
        if not isinstance(result, dict):
            continue
        for key in EVIDENCE_KEYS:
            value = result.get(key)
            if isinstance(value, str) and ("/" in value or value.endswith(".json")):
                refs.append({"module": name, "key": key, "path": value})
    return refs


def _scalar(value, limit=200):
    """Значение любой формы — в одну строку таблицы."""
    if isinstance(value, dict):
        return ", ".join("%s=%s" % (key, _scalar(item, 40))
                         for key, item in sorted(value.items(), key=str))
    if isinstance(value, list):
        head = " ".join(_scalar(item, 30) for item in value[:6])
        return head + (" …" if len(value) > 6 else "")
    return str(value).replace("\n", " ").replace("|", "\\|")[:limit]


def _table(pairs):
    lines = ["| ключ | значение |", "|---|---|"]
    for key, value in pairs:
        if value is None:
            continue
        lines.append("| `%s` | %s |" % (key, _scalar(value)))
    return lines


def render_statistics(stats):
    """§30: скаляры — таблицей, списки вызовов — списком, а не обрезанной ячейкой."""
    scalars = [(key, value) for key, value in sorted(stats.items())
               if not isinstance(value, (dict, list))]
    lines = _table(scalars) or ["_статистики прогона нет_"]
    by_tool = stats.get("by_tool")
    if isinstance(by_tool, dict) and by_tool:
        lines += ["", "Вызовы по инструментам:", ""]
        for name, item in sorted(by_tool.items(),
                                 key=lambda kv: -(_calls(kv[1]))):
            if isinstance(item, dict):
                lines.append("* `%s` — %s вызов(ов), %s мс, %s байт"
                             % (name, item.get("calls"), item.get("total_ms"),
                                item.get("total_bytes")))
            else:
                lines.append("* `%s` — %s" % (name, item))
    largest = stats.get("largest_by_time")
    if isinstance(largest, list) and largest:
        lines += ["", "Самые дорогие инструменты по времени:", ""]
        for item in largest:
            if isinstance(item, dict):
                lines.append("* `%s` — %s мс всего, %s мс максимум, %s байт "
                             "максимум на вызов"
                             % (item.get("tool"), item.get("total_ms"),
                                item.get("max_ms"), item.get("max_bytes")))
    cache = stats.get("cache")
    if isinstance(cache, dict) and cache:
        lines += ["", "Кэш доказательств: %s"
                  % ", ".join("%s=%s" % (key, _scalar(cache[key], 40))
                              for key in ("hits", "misses", "stores",
                                          "bypasses", "hit_rate")
                              if cache.get(key) is not None)]
    by_module = stats.get("by_module")
    if isinstance(by_module, dict) and by_module:
        lines += ["", "Вызовы по модулям:", ""]
        for name, item in sorted(by_module.items()):
            if isinstance(item, dict):
                lines.append("* `%s` — %s вызов(ов), %s мс, статус `%s`"
                             % (name, item.get("mcp_calls"),
                                item.get("mcp_ms"), item.get("status")))
            else:
                lines.append("* `%s` — %s вызов(ов)" % (name, item))
    return lines


def _calls(value):
    return value.get("calls", 0) if isinstance(value, dict) else (value or 0)


def severity_rank(item):
    return SEVERITY_ORDER.get(str(item.get("severity") or "").lower(), 3)


def render(results, goal=None, method=None, stage=None, title=None,
           limitations=None, stats_file=None):
    buckets = collect(results)
    stats = statistics(results, stats_file=stats_file)
    lines = ["# %s" % (title or ("Stage %s. Анализ ROM" % stage if stage
                                 else "Анализ ROM")),
             "",
             "> Сгенерировано `report_gen.py` из JSON-результатов модулей "
             "`utils/analyze/`. Дата прогона: %s."
             % datetime.date.today().isoformat(),
             "",
             "## Goal", ""]
    lines.append(goal or "_цель анализа назначает человек или AI; здесь её нет — "
                         "передайте `--goal`._")
    lines += ["", "## ROM", ""]
    ident = rom_identity(results)
    lines += _table(sorted(ident.items())) or ["_нет данных о ROM_"]
    lines += ["", "## Method", ""]
    lines.append(method or "Один долгий MCP-сеанс, кэш доказательств, "
                           "пакетные инструменты отладчика; Python читает и "
                           "сравнивает байты и не декодирует коды (ТЗ §8, §33).")
    lines += ["", "Модули прогона:", ""]
    for name, result in sorted(results.items()):
        if not isinstance(result, dict):
            continue
        lines.append("* `%s` — вердикт `%s`, статус `%s`, вызовов MCP: %s"
                     % (name, result.get("verdict"), result.get("status"),
                        result.get("mcp_calls")))
    lines += ["", "## Result summary", ""]
    summary = rdb_summary(results)
    lines += _table(sorted(summary.items())) or ["_нет RDB-статистики_"]
    lines += ["", "### Статистика прогона (ТЗ §30)", ""]
    lines += render_statistics(stats)
    refs = evidence_refs(results)
    lines += ["", "### Ссылки на доказательства", ""]
    if refs:
        for ref in refs:
            lines.append("* `%s` → `%s` (%s)" % (ref["module"], ref["path"],
                                                 ref["key"]))
    else:
        lines.append("_модули не оставили путей к доказательствам_")
    lines += ["", "## Findings", ""]
    if buckets["findings"]:
        by_module = {}
        for item in buckets["findings"]:
            by_module.setdefault(item["module"], []).append(item)
        for name in sorted(by_module):
            items = sorted(by_module[name], key=severity_rank)
            counts = {}
            for item in items:
                counts[item.get("rule")] = counts.get(item.get("rule"), 0) + 1
            lines.append("### `%s` (%d: %s)\n"
                         % (name, len(items),
                            ", ".join("%s×%d" % (rule, count)
                                       for rule, count in
                                       sorted(counts.items(),
                                              key=lambda kv: -kv[1]))))
            for item in items[:20]:
                where = "`%s`" % item["object"] if item.get("object") else ""
                if item.get("file"):
                    where = (where + " " if where else "") + \
                        "%s:%s" % (item["file"], item["line"])
                lines.append("* **%s** `%s`%s — %s"
                             % (item.get("severity"), item.get("rule"),
                                " " + where if where else "",
                                item.get("detail")))
            if len(items) > 20:
                lines.append("* _… ещё %d в исходном JSON_"
                             % (len(items) - 20))
            lines.append("")
    else:
        lines.append("_находок нет_")
    lines += ["", "## Verified Facts", ""]
    if buckets["facts"]:
        for item in buckets["facts"]:
            lines.append("* `%s` — %s (`%s`)"
                         % (item["module"], item["verdict"] or "вердикта нет",
                            item["status"]))
        lines.append("")
        lines.append("_Фактом результат считается только потому, что модуль "
                     "выдал статус OK/FACT: совпадение байтов, совпадение "
                     "предсказания с реальностью, нулевая разница. Сюда не "
                     "попадают CANDIDATE (ТЗ §34)._")
    else:
        lines.append("_модули с статусом OK/FACT не найдены_")
    for header, key in (("## Inferences", "candidates"),
                        ("## Hypotheses", "hypotheses")):
        lines += ["", header, ""]
        items = buckets[key]
        if not items:
            lines.append("_пусто_")
            continue
        for item in items[:40]:
            if item.get("kind") == "module":
                # Это не отдельный вывод, а итог модуля целиком: у него есть
                # статус, но нет собственной уверенности.
                lines.append("* `%s` — %s (статус модуля: %s)"
                             % (item["module"],
                                item.get("verdict") or "вердикта нет",
                                item.get("status")))
                continue
            lines.append("* `%s` %s — %s (уверенность: %s)"
                         % (item.get("module"), item.get("name")
                            or item.get("rule") or "",
                            item.get("detail") or item.get("verdict")
                            or json.dumps(item, ensure_ascii=False)[:160],
                            confidence_of(item, {})))
        if len(items) > 40:
            lines.append("_… ещё %d в исходном JSON_" % (len(items) - 40))
    lines += ["", "## Unknowns", ""]
    if buckets["unknowns"]:
        # Одно и то же «неизвестно» по всем объектам показывать построчно —
        # способ утопить отчёт: группируем по модулю и правилу.
        groups = {}
        for item in buckets["unknowns"]:
            detail = item.get("detail") or {}
            rule = (detail.get("rule") if isinstance(detail, dict)
                    else None) or "(без правила)"
            groups.setdefault((item.get("module"), rule), []).append(detail)
        for (module, rule), items in sorted(groups.items()):
            example = items[0] if isinstance(items[0], dict) else {}
            lines.append("* `%s` `%s` ×%d — %s"
                         % (module, rule, len(items),
                            _scalar(example.get("detail") or example, 140)))
    else:
        lines.append("_модули не вернули «неизвестного»_")
    unknown_names = sorted({str(item.get("object"))
                            for item in buckets["findings"]
                            if naming.is_unknown(str(item.get("object") or ""))})
    if unknown_names:
        lines.append("* имён с `_unknown` в находках: %d, например %s"
                     % (len(unknown_names), ", ".join("`%s`" % n
                                                      for n in unknown_names[:5])))
    for item in buckets["unclassified"]:
        lines.append("* модуль `%s` не вернул статус — его результат `%s` "
                     "никуда не отнесён, проверьте формат вывода модуля"
                     % (item["module"], item["verdict"]))
    lines += ["", "## Limitations", ""]
    for text in (limitations or DEFAULT_LIMITATIONS):
        lines.append("* %s" % text)
    for item in buckets["blocked"]:
        lines.append("* модуль `%s` завершился отказом: %s"
                     % (item["module"], item["verdict"]))
    lines += ["", "## Recommended Next Steps", ""]
    steps = sorted(suggestions(buckets),
                   key=lambda step: (severity_rank(step), step["module"]))
    if steps:
        for step in steps:
            lines.append("* [%s] `%s` %s → %s" % (step["severity"],
                                                  step["module"],
                                                  "`%s`" % step["rule"],
                                                  step["text"]))
        lines.append("")
        lines.append("_Порядок этих шагов выбирает человек: генератор только "
                     "собирает подсказки модулей без дублей._")
    else:
        lines.append("_подсказок от модулей нет_")
    return "\n".join(lines) + "\n"


DEFAULT_LIMITATIONS = (
    "Python не декодирует 8080-коды и не строит CFG: всё это отдаёт отладчик "
    "(ТЗ §8, §34)",
    "Имена и семантика — кандидаты; окончательное значение назначает AI по "
    "доказательствам",
    "RUNTIME-наблюдения не подменяют Facts из ROM-образа (ТЗ §17)",
    "Модули, не вошедшие в прогон, в отчёте не участвуют",
)


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="analyze.report_gen",
        description="Сборка StageN.md из JSON-результатов модулей")
    parser.add_argument("--results", required=True,
                        help="каталог *.json или один объединённый файл прогона")
    parser.add_argument("--out", default=None, help="куда писать markdown")
    parser.add_argument("--stage", default=None, help="номер раздела отчёта")
    parser.add_argument("--title", default=None)
    parser.add_argument("--goal", default=None)
    parser.add_argument("--goal-file", default=None)
    parser.add_argument("--method", default=None)
    parser.add_argument("--statistics", default=None,
                        help="JSON со статистикой сеанса от pipeline.py")
    parser.add_argument("--markdown", action="store_true",
                        help="печатать markdown в stdout (по умолчанию и так)")
    args = parser.parse_args(argv)
    results = load_results(args.results)
    if not results:
        print("в %s нет читаемых JSON-результатов" % args.results,
              file=sys.stderr)
        return 1
    goal = args.goal
    if args.goal_file:
        with open(args.goal_file, "r", encoding="utf-8") as handle:
            goal = handle.read().strip()
    text = render(results, goal=goal, method=args.method, stage=args.stage,
                  title=args.title, stats_file=args.statistics)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as handle:
            handle.write(text)
        print("записан %s (%d байт, разделов %d)"
              % (args.out, len(text.encode("utf-8")), len(SECTIONS)))
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
