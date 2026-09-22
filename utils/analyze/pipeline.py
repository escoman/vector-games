#!/usr/bin/env python3
"""Полный прогон анализа: все модули в ОДНОМ MCP-сеансе (ТЗ §4, §29—§32, §35).

Модули пакета обычно запускают по одному. Этот бегун делает три вещи, которые
поодиночке невозможны:

* поднимает один процесс `v06c-mcp` на весь прогон (`mcp_session.share`) —
  запуск сервера и загрузка ROM дороже любого отдельного вызова;
* терпит отказ одного шага: шаг помечается `FAILED`, прогон продолжается, а
  `report_gen` относит его в Limitations;
* собирает обязательную статистику §30 в `statistics.json` и подаёт её в
  отчёт: всего вызовов, по инструментам, hits/misses кэша, wall time, самые
  дорогие вызовы. Именно по этим цифрам решается, что тащить в C++-пакеты.

    python3 utils/analyze/cli.py pipeline \
        --rom roms/redesign/putup/src/putup.rom \
        --rdb roms/redesign/putup/src/putup.rdb \
        --spec roms/redesign/putup/tools/music_spec.json \
        --results .scratch/results/putup --out .scratch/Stage13.md

Каждый шаг пишет `<results>/<module>.json`, поэтому отчёт можно пересобрать из
файлов, даже если бегун упал на середине.
"""
from __future__ import annotations

import argparse
import importlib
import json
import os
import re
import sys
import time
from io import StringIO

from analyze import report_gen
from analyze.mcp_session import share, to_addr

# Каталог, где лежат z80asm и v06c-asm-export (можно перекрыть флагами).
REPO = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))
DEFAULT_Z80ASM = os.path.join(REPO, "z88dk", "bin", "z88dk-z80asm")
DEFAULT_EXPORTER = ("/home/alexey/Projects/vector-debugger/debugger/build/"
                    "v06c-asm-export")


class Step(object):
    """Один шаг прогона: модуль пакета + аргументы его CLI."""

    def __init__(self, module, args=None, key=None):
        self.module = module
        self.args = list(args or [])
        self.key = key or module

    def argv(self, ctx):
        """Аргументы модуля с подстановкой путей, известных только в прогоне.

        `{name}` заменяется как целый токен (`{rom}`) и как часть строки
        (`{results}/pipeline.mid`); иначе составной путь уходит литералом.
        """
        expand = ctx.placeholders()
        argv = ["--json"] + list(self.args)
        out = []
        for token in argv:
            if "{" in token and "}" in token:
                def repl(match):
                    name = match.group(1)
                    if name not in expand:
                        raise SystemExit("шагу %s нечем подставить {%s}"
                                         % (self.module, name))
                    return str(expand[name])
                token = re.sub(r"\{(\w+)\}", repl, token)
            out.append(token)
        return out


def build_steps(ctx):
    """Порядок шагов. Сначала читающие ROM, потом рантайм, в конце экспорт."""
    steps = [
        # 1—2: канонический старт и покрытие — без них остальное слепое.
        Step("probe", ["--rom", "{rom}", "--org", "{org}", "--seconds", "1"]),
        Step("coverage", ["--rom", "{rom}", "--org", "{org}", "--rdb", "{rdb}",
                          "--hi", "{hi}", "--entry", "{entry}"]),
        # 3—4: статика и детерминированный посев RDB (ТЗ §36, §37). seed_rdb
        # идёт в режиме dry-run — план показывается, putup.rdb не меняется.
        Step("disassembly", ["--rom", "{rom}", "--org", "{org}",
                             "--entry", "{entry}"]),
        Step("seed_rdb", ["--rom", "{rom}", "--rdb", "{rdb}", "--org", "{org}",
                          "--hi", "{hi}", "--entry", "{entry}"]),
        # 5—6: целостность RDB и проверка «рантайм не подменил образ» (§13, §16).
        Step("rdb_lint", ["--rdb", "{rdb}", "--rom", "{rom}"]),
        Step("memory_diff", ["--rom", "{rom}", "--org", "{org}",
                             "--lo", "{org}", "--hi", "{hi}"]),
        # 7—11: кандидаты семантики (все — CANDIDATE, не Facts: ТЗ §34).
        Step("io_signature", ["--rom", "{rom}", "--org", "{org}",
                              "--entry", "{entry}", "--hi", "{hi}",
                              "--rdb", "{rdb}", "--seconds", "1"]),
        Step("abi_scan", ["--rom", "{rom}", "--org", "{org}", "--rdb", "{rdb}",
                          "--all", "--limit", str(ctx.abi_limit)]),
        Step("strings_scan", ["--rom", "{rom}", "--org", "{org}",
                              "--hi", "{hi}", "--rdb", "{rdb}"]),
        Step("table_shape", ["--rom", "{rom}", "--org", "{org}",
                             "--rdb", "{rdb}"]),
        Step("glyph_scan", ["--rom", "{rom}", "--org", "{org}", "--rdb", "{rdb}",
                            "--address", ctx.glyph_address,
                            "--count", str(ctx.glyph_count),
                            "--out", "{results}"]) if ctx.glyph_address else None,
        # 10: предсказание VRAM против реальности (§23) — единственный способ
        # получить MATCHED без участия человека.
        Step("vram_credits", ["--rom", "{rom}", "--org", "{org}",
                              "--rdb", "{rdb}", "--string", ctx.credits]),
        # 11—15: производные артефакты и их проверка (§24—§27).
        Step("export_asm", ["--rom", "{rom}", "--org", "{org}", "--rdb", "{rdb}",
                            "--out", "{export}", "--assemble",
                            "--z80asm", "{z80asm}", "--exporter", "{exporter}"],
             key="export_asm"),
        Step("toolchain_lint", ["--dir", "{export}", "--org", "{org}",
                                "--entry", "{asm_entry}"]),
        Step("symbolic_operand_lint", ["--dir", "{export}", "--rom", "{rom}",
                                       "--rdb", "{rdb}", "--org", "{org}"]),
        Step("syntax_check", ["--dir", "{export}", "--entry", "{asm_entry}",
                              "--z80asm", "{z80asm}",
                              "--out", "{export}/syntax_check.bin"]),
        Step("roundtrip_verify", ["--rom", "{rom}", "--org", "{org}",
                                  "--rdb", "{rdb}", "--dir", "{export}",
                                  "--exporter", "{exporter}",
                                  "--z80asm", "{z80asm}"]),
        # 16—17: размеры объектов и музыка.
        Step("measure_sizes", ["--rom", "{rom}", "--org", "{org}",
                               "--rdb", "{rdb}"]),
        Step("music2midi", ["--spec", "{spec}", "-o", "{results}/pipeline.mid",
                            "--rom", "{rom}"] + (["--runtime"] if ctx.runtime
                                                 else []),
             key="music2midi"),
    ]
    return [step for step in steps if step]


class Ctx(object):
    """Параметры прогона, подставляемые в шаги."""

    def placeholders(self):
        expand = {
            "rom": self.rom, "rdb": self.rdb, "org": self.org,
            "entry": self.entry, "hi": self.hi, "results": self.results,
            "export": self.export, "z80asm": self.z80asm,
            "exporter": self.exporter, "spec": self.spec,
            # `--entry` у syntax_check/toolchain_lint — это имя входного .asm,
            # а не адрес: без разделения линтеры считают, что не собрано ничего.
            "asm_entry": self.asm_entry,
        }
        if self.cache:
            expand["cache"] = self.cache
        if self.server:
            expand["server"] = self.server
        return expand


def module_main(module):
    name = "analyze.%s" % module
    if name in sys.modules:
        return importlib.reload(sys.modules[name]).main
    return importlib.import_module(name).main


class StepError(Exception):
    """Модуль упал внутри шага: прогон это переживает, шаг — нет."""

    def __init__(self, wrapped):
        Exception.__init__(self, "%s: %s" % (type(wrapped).__name__, wrapped))
        self.wrapped = wrapped


def capture_stdout(fn, argv):
    """Вызвать `fn(argv)` и вернуть (код, текст stdout, сообщение SystemExit).

    Модули печатают JSON в stdout — это их договор с CLI, менять его ради
    пайплайна нельзя, поэтому перехватываем поток, а не перепиливаем `main`.
    Текст `SystemExit("…")` — штатный способ модуля сказать «я не могу»: его
    нельзя терять, иначе отказ выглядит пустым молчанием.
    """
    saved = sys.stdout
    buffer = StringIO()
    sys.stdout = buffer
    message = None
    try:
        try:
            code = fn(argv) or 0
        except SystemExit as exc:
            if isinstance(exc.code, int):
                code = exc.code
            else:
                message = exc.code
                code = 1 if message else 0
    except BaseException as exc:       # падение модуля — не падение прогона
        raise StepError(exc)
    finally:
        sys.stdout = saved
    return code, buffer.getvalue(), message


def run_step(step, ctx, session, stats):
    """Один шаг: дельта сеанса вокруг вызова + JSON в results."""
    argv = step.argv(ctx)
    before = session.snapshot()
    started = time.time()
    error = None
    code = 0
    payload = None
    text = ""
    try:
        code, text, message = capture_stdout(module_main(step.module), argv)
    except StepError as exc:
        message = None
        error = "%s: %s" % (type(exc.wrapped).__name__, exc.wrapped)
        code = 1
    else:
        error = message
    delta = session.since(before, session.snapshot())
    elapsed_ms = round((time.time() - started) * 1000.0, 1)

    path = os.path.join(ctx.results, "%s.json" % step.key)
    result = None
    try:
        result = json.loads(text)
    except (TypeError, ValueError):
        result = None
    if isinstance(result, dict):
        # Поле `mcp_calls` модуля при общем сеансе — накопленный счётчик, а не
        # стоимость самого модуля: правим на честную дельту (§30).
        result["module"] = result.get("module") or step.module
        result["mcp_calls"] = delta["total_calls"]
        result["step_wall_ms"] = elapsed_ms
        result["step_ms"] = delta["total_ms"]
        if error or code:
            result.setdefault("status", "FAILED")
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(result, handle, ensure_ascii=False, indent=1,
                      sort_keys=True)
            handle.write("\n")
    elif text.strip():
        # Не JSON — сохраняем как есть, чтобы молчание не выглядело успехом.
        with open(path + ".log", "w", encoding="utf-8") as handle:
            handle.write(text)

    stats["by_module"][step.key] = {
        "argv": argv,
        "exit_code": code,
        "wall_ms": elapsed_ms,
        "mcp_calls": delta["total_calls"],
        "mcp_ms": delta["total_ms"],
        "mcp_bytes": delta["total_bytes"],
        "status": (result or {}).get("status") if isinstance(result, dict)
                  else ("FAILED" if error else "NO-JSON"),
        "verdict": (result or {}).get("verdict") if isinstance(result, dict)
                   else None,
        "json": path if isinstance(result, dict) else None,
        "error": error,
    }
    if error:
        return False
    if not isinstance(result, dict):
        print("шаг %s: stdout не JSON (см. %s.log)" % (step.key, path),
              file=sys.stderr)
        return False
    # code != 0 у линтеров — норма: «найдены блокирующие замечания», а не
    # «шаг упал». Отказом прогона считается только `error` и не-JSON.
    return True


def merge_cache(stats, cache):
    if cache is None:
        return
    try:
        data = cache.stats()
    except Exception:
        return
    stats["cache"] = {key: data.get(key) for key in
                      ("hits", "misses", "stores", "bypasses", "hit_rate",
                       "entries", "root")
                      if data.get(key) is not None}


def write_statistics(ctx, session, stats, started):
    final = session.stats()
    merged = {
        "total_mcp_calls": final.get("total_calls", 0),
        "total_mcp_ms": final.get("total_ms", 0),
        "total_mcp_bytes": final.get("total_bytes", 0),
        "retries": final.get("retries", 0),
        "wall_ms": round((time.time() - started) * 1000.0, 1),
        "server": final.get("server"),
        "server_version": final.get("server_version"),
        "protocol_version": final.get("protocol_version"),
        "tools_exposed": final.get("tools_exposed"),
        "by_tool": final.get("by_tool"),
        "largest_by_time": final.get("largest_by_time"),
        "by_module": stats["by_module"],
        "session": "shared (ТЗ §4)",
    }
    merge_cache(merged, ctx.cache_obj)
    path = ctx.statistics or os.path.join(ctx.results, "statistics.json")
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(merged, handle, ensure_ascii=False, indent=1, sort_keys=True)
        handle.write("\n")
    return merged, path


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="analyze.pipeline",
        description="Прогон всех модулей анализа в одном MCP-сеансе")
    parser.add_argument("--rom", required=True)
    parser.add_argument("--rdb", required=True)
    parser.add_argument("--org", default="0x0100")
    parser.add_argument("--entry", default=None,
                        help="точка входа для линтеров (по умолчанию org)")
    parser.add_argument("--hi", default=None,
                        help="верх анализа; по умолчанию конец образа")
    parser.add_argument("--spec", default=None,
                        help="music_spec.json для шага music2midi")
    parser.add_argument("--credits", default="str_credits_koi8",
                        help="имя строки-кредитов для vram_credits")
    parser.add_argument("--glyph-address", default=None,
                        help="адрес блока глифов для glyph_scan; без него шаг "
                             "пропускается — адрес ROM-специфичен")
    parser.add_argument("--glyph-count", type=int, default=6)
    parser.add_argument("--abi-limit", type=int, default=4,
                        help="сколько функций берёт abi_scan (у него сотни "
                             "вызовов на функцию)")
    parser.add_argument("--results", default=".scratch/results/pipeline")
    parser.add_argument("--export", default=".scratch/export/pipeline")
    parser.add_argument("--statistics", default=None,
                        help="куда писать JSON статистики §30")
    parser.add_argument("--out", default=None, help="куда писать отчёт")
    parser.add_argument("--stage", default=None)
    parser.add_argument("--goal", default=None)
    parser.add_argument("--server", default=None)
    parser.add_argument("--cache", default=None)
    parser.add_argument("--z80asm", default=DEFAULT_Z80ASM)
    parser.add_argument("--exporter", default=DEFAULT_EXPORTER)
    parser.add_argument("--no-cache", action="store_true")
    parser.add_argument("--runtime", action="store_true",
                        help="разрешить модулям читать RUNTIME-байты через MCP "
                             "(нужно для music2midi с runtime-источником)")
    parser.add_argument("--only", action="append",
                        help="повторяемо: прогнать только эти шаги")
    parser.add_argument("--list", action="store_true",
                        help="показать шаги и выйти")
    parser.add_argument("--json", action="store_true",
                        help="итоговую сводку прогона в stdout")
    args = parser.parse_args(argv)

    ctx = Ctx()
    ctx.rom = args.rom
    ctx.rdb = args.rdb
    ctx.org = args.org
    ctx.server = args.server
    ctx.z80asm = args.z80asm
    ctx.exporter = args.exporter
    ctx.abi_limit = args.abi_limit
    ctx.credits = args.credits
    ctx.glyph_address = args.glyph_address
    ctx.glyph_count = args.glyph_count
    ctx.spec = args.spec or ""
    ctx.entry = args.entry or args.org
    ctx.asm_entry = "main.asm"
    ctx.hi = args.hi or None
    ctx.cache = None if args.no_cache else args.cache
    ctx.runtime = args.runtime
    ctx.results = os.path.abspath(args.results)
    ctx.export = os.path.abspath(args.export)
    ctx.statistics = args.statistics
    cache_root = ctx.cache or os.path.join(ctx.results, ".analyze")
    ctx.cache = cache_root if not args.no_cache else None

    size = os.path.getsize(args.rom) if os.path.exists(args.rom) else 0
    if not ctx.hi:
        ctx.hi = "0x%04X" % (to_addr(args.org) + size - 1)

    steps = build_steps(ctx)
    if not ctx.spec:
        steps = [s for s in steps if s.module != "music2midi"]
    if args.only:
        wanted = set(args.only)
        steps = [s for s in steps if s.key in wanted]
    if args.list:
        for step in steps:
            print(step.key)
        return 0

    for directory in (ctx.results, ctx.export):
        if not os.path.isdir(directory):
            os.makedirs(directory)
    stats = {"by_module": {}}
    started = time.time()
    ok = failed = flagged = 0

    with share(rom=args.rom, org=to_addr(args.org), server=args.server,
               cache_dir=ctx.cache, cache=not args.no_cache) as session:
        ctx.cache_obj = None
        try:
            from analyze.mcp_session import _SHARED
            ctx.cache_obj = _SHARED["cache"]
        except Exception:
            pass
        # Общий сеанс: модули вызывают close() в finally, сервер умирать нельзя.
        session.close = lambda: None
        for step in steps:
            print("→ %s" % step.key, file=sys.stderr)
            good = run_step(step, ctx, session, stats)
            entry = stats["by_module"][step.key]
            ok += 1 if good else 0
            failed += 0 if good else 1
            if good and entry["exit_code"]:
                flagged += 1
        merged, stats_path = write_statistics(ctx, session, stats, started)

    results = {}
    for step in steps:
        entry = stats["by_module"].get(step.key) or {}
        path = entry.get("json")
        if not path or not os.path.isfile(path):
            continue
        with open(path, "r", encoding="utf-8") as handle:
            results[step.key] = json.load(handle)

    report_path = args.out or os.path.join(ctx.results, "report.md")
    text = report_gen.render(
        results, goal=args.goal, stage=args.stage,
        stats_file=stats_path,
        limitations=list(report_gen.DEFAULT_LIMITATIONS) + [
            "Прогон выполнен `pipeline.py` в одном общем MCP-сеансе; поле "
            "`mcp_calls` у модуля — дельта этого сеанса на момент его шага"])
    with open(report_path, "w", encoding="utf-8") as handle:
        handle.write(text)

    summary = {
        "steps": len(steps), "succeeded": ok, "failed": failed,
        "exit_nonzero": flagged,
        "total_mcp_calls": merged.get("total_mcp_calls"),
        "wall_ms": merged.get("wall_ms"),
        "cache": merged.get("cache"),
        "statistics": stats_path,
        "report": report_path,
        "results": ctx.results,
    }
    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=1,
                         sort_keys=True))
    else:
        print("шагов %d, успешных %d, отказов %d (из них с ненулевым кодом: %d); "
              "вызовов MCP %s за %s мс; отчёт: %s"
              % (summary["steps"], ok, failed, flagged,
                 summary["total_mcp_calls"], summary["wall_ms"],
                 report_path))
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
