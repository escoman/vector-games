"""Стандартный исполнитель анализа ROM Vector-06C (ТЗ Standard Pipeline, §1—§60).

Pipeline — инфраструктурный уровень: он управляет последовательностью stages,
их зависимостями (DAG, §14), одним MCP-сеансом (§57), persisten-политикой
(§3—§6: SAVE → VERIFY → CHECKPOINT после каждого изменяющего RDB stage),
checkpoint/resume (§7—§11, §23), dry-run/apply (§24—§25), ошибками (§30—§32)
и стандартными отчётами выполнения (§36—§41).

Главный принцип (§3): RDB на диске — persistent state анализа. Ничего не
считается завершённым, пока не сохранено официальные API (`debug_save_rdb`),
проверено и не подтверждено атомарным checkpoint (`pipeline_state.py`).

Режимы (решение по ТЗ §24—§25):

    без флагов   — реальный apply: seed_rdb и apply_annotations мутируют RDB,
                   pipeline сохраняет, проверяет, чекпоинтит;
    --dry-run    — строго read-only: ни одного object/link/alias/save (guard
                   на session.call останавливает прогон с DRY_RUN_VIOLATION);
    --resume     — продолжение с последнего подтверждённого checkpoint после
                   валидации ROM sha256 / RDB sha256 / capabilities (§9—§11);
    --clean      — удалить только checkpoint (RDB/ROM/отчёты не трогаются).

ROM-специфика сюда не попадает (§46): только TZ.md/config выбирают stages и
адреса; сам исполнитель про них ничего не знает.

    python3 utils/analyze/cli.py pipeline \
        --rom roms/redesign/putup/src/putup.rom \
        --rdb roms/redesign/putup/src/putup.rdb \
        --results .scratch/results/putup --out .scratch/Stage.md
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

from analyze import pipeline_state
from analyze import report_gen
from analyze.capabilities import CapabilityProfile
from analyze.mcp_session import (
    McpError, McpTimeout, share, to_addr,
)
from analyze.pipeline_state import PipelineFatal

# Каталог, где лежат z80asm и v06c-asm-export (можно перекрыть флагами).
REPO = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))
DEFAULT_Z80ASM = os.path.join(REPO, "z88dk", "bin", "z88dk-z80asm")
DEFAULT_EXPORTER = ("/home/alexey/Projects/vector-debugger/debugger/build/"
                    "v06c-asm-export")

# Статусы stage (ТЗ §13).
SUCCESS, SKIPPED, PARTIAL, FAILED, BLOCKED = (
    "SUCCESS", "SKIPPED", "PARTIAL", "FAILED", "BLOCKED")

# Повтор recoverable-ошибок: 3 попытки, backoff 1/2/4 с (ТЗ §31).
MAX_RETRIES = 3
RETRY_BACKOFF = (1.0, 2.0, 4.0)


class StageResult(object):
    """Стандартный результат stage (ТЗ §13)."""

    def __init__(self, status, changed=False, objects_added=0,
                 objects_updated=0, links_added=0, warnings=None, errors=None,
                 note=None):
        self.status = status
        self.changed = bool(changed)
        self.objects_added = int(objects_added or 0)
        self.objects_updated = int(objects_updated or 0)
        self.links_added = int(links_added or 0)
        self.warnings = list(warnings or [])
        self.errors = list(errors or [])
        self.note = note
        self.duration_ms = 0.0
        self.mcp = {}
        self.checkpoint = None
        # STEP_EXCEPTION/MCP_TIMEOUT — recoverable (ТЗ §30—§31); «FAILED» из
        # конверта модуля — семантический отказ, его не повторяем.
        self.retryable = False

    @property
    def ok(self):
        """Stage не является отказом прогона (ТЗ: PARTIAL — не FAILED)."""
        return self.status in (SUCCESS, PARTIAL, SKIPPED)

    def to_dict(self):
        out = {"status": self.status, "changed": self.changed,
               "objects_added": self.objects_added,
               "objects_updated": self.objects_updated,
               "links_added": self.links_added,
               "warnings": self.warnings, "errors": self.errors,
               "duration_ms": self.duration_ms, "mcp": self.mcp}
        if self.note:
            out["note"] = self.note
        if self.checkpoint:
            out["checkpoint"] = self.checkpoint
        return out


class Step(object):
    """Один stage: модуль пакета + аргументы его CLI + зависимости (ТЗ §14—§18).

    Историческое имя сохранено: `Step` и есть Stage. `depends_on` — edges DAG;
    `mutates_rdb` включает для него persistence-обвязку SAVE→VERIFY→CHECKPOINT
    и режимные флаги (--apply/--dry-run + --save-every) из контекста прогона.
    """

    def __init__(self, module, args=None, key=None, depends_on=(),
                 mutates_rdb=False):
        self.module = module
        self.args = list(args or [])
        self.key = key or module
        self.depends_on = tuple(depends_on)
        self.mutates_rdb = mutates_rdb

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

    def effective_argv(self, ctx):
        """argv + режимные флаги для mutating-stage (ТЗ §24—§25, §4.2)."""
        argv = self.argv(ctx)
        if self.mutates_rdb:
            if ctx.dry_run:
                argv += ["--dry-run"]
            else:
                argv += ["--apply", "--save-every",
                         str(ctx.persistence["max_unsaved_objects"])]
        return argv

    def can_run(self, ctx):
        """Может ли stage идти в этом прогоне (опции вроде --glyph-address)."""
        return True

    def run(self, ctx, session, stats):
        return StageResult(SKIPPED, note="не реализован")


def build_steps(ctx):
    """DAG stages. Порядок внутри — канонический (§36—§37 прошлой итерации),
    связи — минимально необходимые (ТЗ §18: независимые ветки не связываем)."""
    steps = [
        # 1—2: канонический старт и покрытие — без них остальное слепое.
        Step("probe", ["--rom", "{rom}", "--org", "{org}", "--seconds", "1"]),
        Step("coverage", ["--rom", "{rom}", "--org", "{org}", "--rdb", "{rdb}",
                          "--hi", "{hi}", "--entry", "{entry}"],
             depends_on=("probe",)),
        # 3—4: статика и детерминированный посев RDB. seed_rdb — mutating:
        # в обычном режиме реально пишет RDB (решение по ТЗ §24—§25), в
        # --dry-run получает --dry-run и остаётся планом.
        Step("disassembly", ["--rom", "{rom}", "--org", "{org}",
                             "--entry", "{entry}"], depends_on=("probe",)),
        Step("seed_rdb", ["--rom", "{rom}", "--rdb", "{rdb}", "--org", "{org}",
                          "--hi", "{hi}", "--entry", "{entry}"],
             depends_on=("coverage", "disassembly"), mutates_rdb=True),
        # 5—6: целостность RDB и проверка «рантайм не подменил образ» (§13, §16).
        Step("rdb_lint", ["--rdb", "{rdb}", "--rom", "{rom}"],
             depends_on=("seed_rdb",)),
        Step("memory_diff", ["--rom", "{rom}", "--org", "{org}",
                             "--lo", "{org}", "--hi", "{hi}"],
             depends_on=("probe",)),
        # 7—11: кандидаты семантики (все — CANDIDATE, не Facts: ТЗ §34).
        Step("io_signature", ["--rom", "{rom}", "--org", "{org}",
                              "--entry", "{entry}", "--hi", "{hi}",
                              "--rdb", "{rdb}", "--seconds", "1"],
             depends_on=("seed_rdb",)),
        Step("abi_scan", ["--rom", "{rom}", "--org", "{org}", "--rdb", "{rdb}",
                          "--all", "--limit", str(ctx.abi_limit)],
             depends_on=("seed_rdb",)),
        Step("strings_scan", ["--rom", "{rom}", "--org", "{org}",
                              "--hi", "{hi}", "--rdb", "{rdb}"],
             depends_on=("seed_rdb",)),
        Step("table_shape", ["--rom", "{rom}", "--org", "{org}",
                             "--rdb", "{rdb}"], depends_on=("seed_rdb",)),
        Step("glyph_scan", ["--rom", "{rom}", "--org", "{org}", "--rdb", "{rdb}",
                            "--address", ctx.glyph_address,
                            "--count", str(ctx.glyph_count),
                            "--out", "{results}"],
             depends_on=("seed_rdb",)) if ctx.glyph_address else None,
        # 10: предсказание VRAM против реальности (§23) — единственный способ
        # получить MATCHED без участия человека.
        Step("vram_credits", ["--rom", "{rom}", "--org", "{org}",
                              "--rdb", "{rdb}", "--string", ctx.credits],
             depends_on=("strings_scan",)),
        # 11—15: производные артефакты и их проверка (§24—§27).
        Step("export_asm", ["--rom", "{rom}", "--org", "{org}", "--rdb", "{rdb}",
                            "--out", "{export}", "--assemble",
                            "--z80asm", "{z80asm}", "--exporter", "{exporter}"],
             key="export_asm", depends_on=("rdb_lint",)),
        Step("toolchain_lint", ["--dir", "{export}", "--org", "{org}",
                                "--entry", "{asm_entry}"],
             depends_on=("export_asm",)),
        Step("symbolic_operand_lint", ["--dir", "{export}", "--rom", "{rom}",
                                       "--rdb", "{rdb}", "--org", "{org}"],
             depends_on=("export_asm",)),
        Step("syntax_check", ["--dir", "{export}", "--entry", "{asm_entry}",
                              "--z80asm", "{z80asm}",
                              "--out", "{export}/syntax_check.bin"],
             depends_on=("export_asm",)),
        Step("roundtrip_verify", ["--rom", "{rom}", "--org", "{org}",
                                  "--rdb", "{rdb}", "--dir", "{export}",
                                  "--exporter", "{exporter}",
                                  "--z80asm", "{z80asm}"],
             depends_on=("syntax_check",)),
        # 16—17: размеры объектов и музыка.
        Step("measure_sizes", ["--rom", "{rom}", "--org", "{org}",
                               "--rdb", "{rdb}"], depends_on=("seed_rdb",)),
    ]
    if ctx.spec:
        steps.append(
            Step("music2midi", ["--spec", "{spec}",
                                "-o", "{results}/pipeline.mid",
                                "--rom", "{rom}"]
                 + (["--runtime"] if ctx.runtime else []),
                 key="music2midi", depends_on=("probe",)))
    if getattr(ctx, "annotations", None):
        steps.append(
            Step("apply_annotations", ["--in", "{annotations}", "--rom", "{rom}",
                                       "--rdb", "{rdb}", "--org", "{org}"],
                 depends_on=("seed_rdb",), mutates_rdb=True))
        # Экспорт обязан уходить после нанесённых аннотаций, иначе артефакты
        # соберутся по половинам.
        for stage in steps:
            if stage is not None and stage.key == "export_asm":
                stage.depends_on = tuple(list(stage.depends_on) +
                                         ["apply_annotations"])
    return [step for step in steps if step]


def toposort(stages):
    """Стабильная топологическая сортировка DAG (ТЗ §14—§19).

    Тай-брейк — объявленный порядок `build_steps`, поэтому результат
    детерминирован и совпадает с прежним линейным порядком. Неизвестная
    зависимость игнорируется (она могла быть исключена --from/can_run).
    """
    by_key = {stage.key: stage for stage in stages}
    order = []
    visited = {}          # key -> 0 visiting / 1 done

    def visit(key):
        state = visited.get(key)
        if state == 1:
            return
        if state == 0:        # цикл: обрываем, DAG обязан быть ацикличным
            return
        visited[key] = 0
        for dep in by_key[key].depends_on:
            if dep in by_key:
                visit(dep)
        visited[key] = 1
        order.append(key)

    for stage in stages:
        visit(stage.key)
    return [by_key[key] for key in order]


def expand_only(stages, selected_keys):
    """--only: добавить транзитивные предков (ТЗ §22: deps проверяются
    автоматически, предок либо догоняется, либо потомок получает BLOCKED)."""
    by_key = {stage.key: stage for stage in stages}
    wanted = set()

    def take(key):
        if key in wanted or key not in by_key:
            return
        wanted.add(key)
        for dep in by_key[key].depends_on:
            take(dep)

    for key in selected_keys:
        if key not in by_key:
            raise SystemExit("нет stage %r (известны: %s)"
                             % (key, ", ".join(sorted(by_key))))
        take(key)
    return [stage for stage in stages if stage.key in wanted]


class Ctx(object):
    """Параметры прогона, подставляемые в шаги (он же PipelineContext, ТЗ §33)."""

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
        if getattr(self, "annotations", None):
            expand["annotations"] = self.annotations
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
    except pipeline_state.DryRunViolation:
        raise                        # guard dry-run — не «падение модуля»
    except BaseException as exc:      # падение модуля — не падение прогона
        raise StepError(exc)
    finally:
        sys.stdout = saved
    return code, buffer.getvalue(), message


def _classify_module_status(payload):
    """Статус конверта модуля → статус stage (ТЗ §13)."""
    status = str((payload or {}).get("status") or "").upper()
    if status in report_gen.FAILED_STATUSES:
        return FAILED
    if status == "SKIPPED":
        return SKIPPED
    if status in report_gen.CANDIDATE_STATUSES:
        return PARTIAL
    return SUCCESS


def _collect_counts(payload, module):
    """Извлечение объектов/ссылок из конверта mutator-модуля (ТЗ §35)."""
    payload = payload or {}
    out = {"changed": False, "objects_added": 0, "objects_updated": 0,
           "links_added": 0}
    if module == "seed_rdb":
        out["objects_added"] = int(payload.get("functions_added") or 0) + \
            int(payload.get("labels_added") or 0)
        out["links_added"] = int(payload.get("links_added") or 0)
    elif module == "apply_annotations":
        out["objects_added"] = int(payload.get("objects_added") or 0)
        out["objects_updated"] = int(payload.get("objects_updated") or 0)
        out["links_added"] = int(payload.get("links_added") or 0)
    out["changed"] = bool(out["objects_added"] or out["objects_updated"]
                          or out["links_added"])
    return out


def run_step(step, ctx, session, stats, retries=0):
    """Один шаг: дельта сеанса вокруг вызова + JSON в results + StageResult.

    Возвращает StageResult; бросает PipelineFatal только если модуль
    «проткнул» dry-run guard (DRY_RUN_VIOLATION — фатально, ТЗ §24).
    """
    argv = step.effective_argv(ctx)
    before = session.snapshot()
    started = time.time()
    error = None
    retryable = False
    code = 0
    payload = None
    text = ""
    try:
        code, text, message = capture_stdout(module_main(step.module), argv)
    except pipeline_state.DryRunViolation as violation:
        raise PipelineFatal("DRY_RUN_VIOLATION", str(violation))
    except StepError as exc:
        message = None
        error = "%s: %s" % (type(exc.wrapped).__name__, exc.wrapped)
        code = 1
        retryable = True             # STEP_EXCEPTION — recoverable (ТЗ §31)
    else:
        error = message
    # Модуль мог проглотить нарушение dry-run в свой штатный except —
    # тогда сигнал остаётся только на guard-е сеанса.
    violation = getattr(session, "dry_run_violation", None)
    if violation:
        raise PipelineFatal("DRY_RUN_VIOLATION",
                            "модуль %s вызвал %s в --dry-run" % (step.key,
                                                                 violation))
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
        "retries": retries,
        "status": (result or {}).get("status") if isinstance(result, dict)
                  else ("FAILED" if error else "NO-JSON"),
        "verdict": (result or {}).get("verdict") if isinstance(result, dict)
                   else None,
        "json": path if isinstance(result, dict) else None,
        "error": error,
    }

    # → StageResult (ТЗ §13)
    if error:
        status = FAILED
    elif not isinstance(result, dict):
        status = FAILED
    else:
        status = _classify_module_status(result)
        # code != 0 у линтеров — норма: «найдены блокирующие замечания», а не
        # «шаг упал». Отказом прогона считается только `error` и не-JSON.
    warnings = []
    if status == SUCCESS and code:
        warnings.append("ненулевой код выхода %d (находки линтера)" % code)
    if not isinstance(result, dict) and text.strip():
        warnings.append("stdout не JSON, см. %s.log" % path)
    counts = _collect_counts(result, step.module) if step.mutates_rdb else \
        {"changed": False, "objects_added": 0, "objects_updated": 0,
         "links_added": 0}
    outcome = StageResult(
        status, changed=counts["changed"],
        objects_added=counts["objects_added"],
        objects_updated=counts["objects_updated"],
        links_added=counts["links_added"],
        warnings=warnings, errors=[error] if error else [],
        note=(result or {}).get("verdict") if isinstance(result, dict) else None)
    outcome.duration_ms = elapsed_ms
    outcome.retryable = retryable
    outcome.mcp = {"calls": delta["total_calls"], "ms": delta["total_ms"],
                   "bytes": delta["total_bytes"], "retries": retries}
    outcome.payload = result if isinstance(result, dict) else None
    return outcome


# ---------------------------------------------------------------------------
# Persistence: SAVE → VERIFY → CHECKPOINT (ТЗ §3—§8, §41)
# ---------------------------------------------------------------------------

def persist_stage(ctx, session, stage, outcome):
    """Подтверждение stage на диске. Возвращает dict checkpoint-сводки.

    Для mutating-stage обязателен полный цикл: save (официальным API),
    verify (существование/читаемость/счёт объектов, ТЗ §6), checkpoint.
    Read-only stage получает только checkpoint: изменять на диске нечего,
    но «stage завершён» без записи в pipeline_state.json не считается (§35).
    """
    policy = ctx.persistence
    stats_before = pipeline_state.rdb_stats(session)
    if stage.mutates_rdb and not ctx.dry_run and policy["save_after_stage"]:
        session.call("debug_save_rdb")
        if policy["verify_after_save"]:
            expected = (pipeline_state.rdb_stats(session).get("objects"))
            minimum = stats_before.get("objects")
            ok, detail = pipeline_state.verify_saved_rdb(
                ctx.rdb,
                expected=expected if expected is not None else None,
                minimum=minimum if minimum is not None else None)
            if not ok:
                code, _, text = str(detail.get("error") or "").partition(": ")
                raise PipelineFatal(code if code in pipeline_state.FATAL_CODES
                                    else "SAVE_VERIFY_FAILED", text)
    if not policy["checkpoint_after_save"] and not stage.mutates_rdb:
        return None
    pipeline_state.update_active(current_stage=None, current_batch=None,
                                 processed_objects=None, pending_objects=None,
                                 status="checkpoint")
    path = pipeline_state.checkpoint_active()
    snapshot = pipeline_state.read_checkpoint(path) or {}
    ctx.checkpoint_log.append({
        "after_stage": stage.key,
        "time": snapshot.get("checkpoint_time"),
        "rdb_sha256": snapshot.get("rdb_sha256"),
        "rdb_objects": snapshot.get("rdb_objects"),
        "rdb_links": snapshot.get("rdb_links"),
    })
    outcome.checkpoint = ctx.checkpoint_log[-1]
    return outcome.checkpoint


def mark_completed(ctx, stage):
    """Stage подтверждён: в completed_stages checkpoint-а."""
    state = pipeline_state.update_active()
    done = list(state.get("completed_stages") or [])
    if stage.key not in done:
        done.append(stage.key)
    pipeline_state.update_active(completed_stages=done,
                                 last_completed_stage=stage.key)


# ---------------------------------------------------------------------------
# Guard --dry-run (ТЗ §24): ни одной RDB-мутации и debug_save_rdb
# ---------------------------------------------------------------------------

def install_dry_run_guard(session):
    original = session.call

    def guarded(tool, arguments=None, **kwargs):
        if tool in pipeline_state.RDB_MUTATING_TOOLS:
            # Отметку носим на сеансе: модуль может проглотить исключение в
            # свой except Exception — pipeline обязан увидеть нарушение.
            session.dry_run_violation = tool
            raise pipeline_state.DryRunViolation(tool)
        return original(tool, arguments, **kwargs)

    session.call = guarded
    return original


def _is_recoverable(exc):
    """MCP_TIMEOUT / обрыв транспорта — повторять; всё остальное — нет (ТЗ §31)."""
    return isinstance(exc, (McpTimeout, ConnectionError, OSError))


def _session_alive(session):
    proc = getattr(session, "_proc", None)
    return proc is None or proc.poll() is None


# ---------------------------------------------------------------------------
# Отчёты выполнения (ТЗ §36—§41)
# ---------------------------------------------------------------------------

def render_pipeline_md(meta, stages_summary, overall):
    """reports/pipeline.md — человекочитаемый отчёт прогона (ТЗ §36)."""
    lines = ["# Pipeline run report", ""]
    lines += ["| | |", "|---|---|",
              "| ROM | `%s` |" % meta.get("rom"),
              "| ROM SHA256 | `%s` |" % str(meta.get("rom_sha256") or "")[:16],
              "| RDB | `%s` |" % meta.get("rdb"),
              "| Режим | %s |" % ("dry-run (чтение)" if meta.get("dry_run")
                                   else "apply (мутации разрешены)"),
              "| Resume | %s |" % ("да" if meta.get("resumed") else "нет"),
              "| Старт | %s |" % meta.get("started_iso"),
              "| Финиш | %s |" % meta.get("finished_iso"),
              "| Итог | **%s** |" % overall, ""]
    lines += ["## Stages", "",
              "| Stage | Status | Duration | +objects | ~objects | +links "
              "| Warn | Err | Checkpoint |",
              "|---|---|---|---|---|---|---|---|---|"]
    for name in stages_summary:
        row = stages_summary[name]
        checkpoint = row.get("checkpoint") or {}
        lines.append("| %s | %s | %s | %s | %s | %s | %s | %s | %s |" % (
            name, row["status"],
            "%.1fs" % (row["duration_ms"] / 1000.0),
            row.get("objects_added", 0), row.get("objects_updated", 0),
            row.get("links_added", 0), len(row.get("warnings") or []),
            len(row.get("errors") or []),
            (checkpoint.get("time") or "—")[:19]))
    notes = [name for name in stages_summary
             if stages_summary[name].get("note")]
    if notes:
        lines += ["", "## Примечания", ""]
        for name in notes:
            lines.append("- **%s**: %s" % (name, stages_summary[name]["note"]))
    errors = [(name, err) for name in stages_summary
              for err in (stages_summary[name].get("errors") or [])]
    if errors:
        lines += ["", "## Ошибки", ""]
        for name, err in errors:
            lines.append("- **%s**: %s" % (name, err))
    lines.append("")
    return "\n".join(lines)


def write_reports(ctx, meta, stages_summary, overall, stats_merged):
    """pipeline.md + pipeline.json (ТЗ §36—§41)."""
    md_path = os.path.join(ctx.reports, "pipeline.md")
    with open(md_path, "w", encoding="utf-8") as handle:
        handle.write(render_pipeline_md(meta, stages_summary, overall))
    payload = {
        "version": 1,
        "status": overall,
        "rom": ctx.rom, "rom_sha256": meta.get("rom_sha256"),
        "rdb": ctx.rdb, "rdb_sha256": pipeline_state.file_sha256(ctx.rdb),
        "dry_run": ctx.dry_run, "resumed": meta.get("resumed", False),
        "started": meta.get("started_iso"), "finished": meta.get("finished_iso"),
        "wall_ms": stats_merged.get("wall_ms"),
        "checkpoint": ctx.state_path,
        "stages": stages_summary,
        "checkpoint_log": ctx.checkpoint_log,
        "mcp": {"total_calls": stats_merged.get("total_mcp_calls"),
                "total_ms": stats_merged.get("total_mcp_ms"),
                "retries": stats_merged.get("retries"),
                "restarts": stats_merged.get("session_restarts")},
        "rdb_stats": stats_merged.get("rdb_stats"),
        "fatal": meta.get("fatal"),
    }
    json_path = os.path.join(ctx.reports, "pipeline.json")
    with open(json_path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=1,
                  sort_keys=True)
        handle.write("\n")
    return md_path, json_path


# ---------------------------------------------------------------------------
# Прогон
# ---------------------------------------------------------------------------

def load_config(path):
    """--config: JSON (stdlib-only; YAML не поддерживаем — см. README, ТЗ §47)."""
    try:
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
    except ValueError as exc:
        raise SystemExit("конфиг не разобран (%s): %s" % (path, exc))
    if not isinstance(data, dict):
        raise SystemExit("конфиг — не объект JSON: %s" % path)
    return data


DEFAULT_PERSISTENCE = {
    # ТЗ §4.2, §4.3, §48: не больше 10 несохранённых объектов, checkpoint
    # не реже 5 минут, save/verify/checkpoint после каждого mutator-stage.
    "max_unsaved_objects": 10,
    "max_checkpoint_seconds": 300,
    "save_after_stage": True,
    "verify_after_save": True,
    "checkpoint_after_save": True,
}


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="analyze.pipeline",
        description="Стандартный прогон анализа ROM: stages, RDB persistence, "
                    "checkpoint/resume, dry-run/apply")
    parser.add_argument("--rom", required=True)
    parser.add_argument("--rdb", default=None,
                        help="путь .rdb; по умолчанию — сосед .rom (как делает "
                             "сам отладчик)")
    parser.add_argument("--org", default="0x0100")
    parser.add_argument("--entry", default=None,
                        help="точка входа для линтеров (по умолчанию org)")
    parser.add_argument("--hi", default=None,
                        help="верх анализа; по умолчанию конец образа")
    parser.add_argument("--spec", default=None,
                        help="music_spec.json для шага music2midi")
    parser.add_argument("--annotations", default=None,
                        help="JSON-файл аннотаций для stage apply_annotations")
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
    parser.add_argument("--reports", default=None,
                        help="каталог отчётов прогона (pipeline.md/json, "
                             "checkpoint); по умолчанию = --results")
    parser.add_argument("--export", default=".scratch/export/pipeline")
    parser.add_argument("--statistics", default=None,
                        help="куда писать JSON статистики §30")
    parser.add_argument("--out", default=None, help="куда писать отчёт")
    parser.add_argument("--config", default=None,
                        help="JSON-конфиг прогона: stages + persistence (ТЗ §47)")
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
    # Режимы выполнения (ТЗ §20—§25).
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--apply", action="store_true",
                      help="явный apply (он же режим по умолчанию): мутации "
                           "RDB разрешены")
    mode.add_argument("--dry-run", action="store_true",
                      help="строго read-only: ни мутаций RDB, ни save (ТЗ §24)")
    parser.add_argument("--resume", action="store_true",
                        help="продолжить с последнего подтверждённого "
                             "checkpoint (ТЗ §9—§11, §23)")
    parser.add_argument("--clean", action="store_true",
                        help="удалить checkpoint перед прогоном (RDB/ROM/отчёты "
                             "не трогаются, ТЗ §23)")
    parser.add_argument("--only", action="append", default=[],
                        help="повторяемо: прогнать только эти stages "
                             "(зависимости добавляются автоматически, §22)")
    parser.add_argument("--from", dest="from_stage", default=None,
                        help="начать с этого stage (предки считаются "
                             "уже сделанными, §21)")
    parser.add_argument("--until", dest="until_stage", default=None,
                        help="закончить на этом stage (включительно)")
    parser.add_argument("--list", action="store_true",
                        help="показать stages и выйти")
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--json", action="store_true",
                        help="итоговую сводку прогона в stdout")
    args = parser.parse_args(argv)

    ctx = Ctx()
    ctx.rom = args.rom
    ctx.rdb = args.rdb or re.sub(r"\.(rom|ROM|bin)$", ".rdb", args.rom)
    ctx.org = args.org
    ctx.server = args.server
    ctx.z80asm = args.z80asm
    ctx.exporter = args.exporter
    ctx.abi_limit = args.abi_limit
    ctx.credits = args.credits
    ctx.glyph_address = args.glyph_address
    ctx.glyph_count = args.glyph_count
    ctx.spec = args.spec or ""
    ctx.annotations = args.annotations
    ctx.entry = args.entry or args.org
    ctx.asm_entry = "main.asm"
    ctx.hi = args.hi or None
    ctx.cache = None if args.no_cache else args.cache
    ctx.runtime = args.runtime
    ctx.results = os.path.abspath(args.results)
    ctx.export = os.path.abspath(args.export)
    ctx.reports = os.path.abspath(args.reports or args.results)
    ctx.statistics = args.statistics
    ctx.dry_run = bool(args.dry_run)          # дефолт — apply (решение по §25)
    ctx.resume = bool(args.resume)
    ctx.verbose = args.verbose
    cache_root = ctx.cache or os.path.join(ctx.results, ".analyze")
    ctx.cache = cache_root if not args.no_cache else None

    ctx.persistence = dict(DEFAULT_PERSISTENCE)
    cfg = load_config(args.config) if args.config else {}
    cfg_persist = cfg.get("persistence") or {}
    unknown_keys = set(cfg_persist) - set(ctx.persistence)
    if unknown_keys:
        raise SystemExit("конфиг: неизвестные ключи persistence: %s"
                         % ", ".join(sorted(unknown_keys)))
    ctx.persistence.update(cfg_persist)

    size = os.path.getsize(args.rom) if os.path.exists(args.rom) else 0
    if not ctx.hi:
        ctx.hi = "0x%04X" % (to_addr(args.org) + size - 1)

    steps = toposort(build_steps(ctx))
    cfg_stages = cfg.get("stages")
    if cfg_stages:
        allowed = set(cfg_stages)
        steps = [s for s in steps if s.key in allowed]
    if args.only:
        wanted = set()
        for chunk in args.only:
            wanted.update(name.strip() for name in chunk.split(",") if name.strip())
        steps = expand_only(steps, sorted(wanted))
    elif args.from_stage or args.until_stage:
        keys = [s.key for s in steps]
        try:
            lo = keys.index(args.from_stage) if args.from_stage else 0
            hi = keys.index(args.until_stage) if args.until_stage else len(keys) - 1
        except ValueError as exc:
            raise SystemExit("нет stage %r (известны: %s)" % (exc.args[0],
                                                              ", ".join(keys)))
        if lo > hi:
            raise SystemExit("--from идёт после --until: %s > %s"
                             % (args.from_stage, args.until_stage))
        steps = steps[lo:hi + 1]
    if args.list:
        for step in steps:
            print(step.key)
        return 0

    for directory in (ctx.results, ctx.export, ctx.reports):
        if not os.path.isdir(directory):
            os.makedirs(directory)

    ctx.state_path = os.path.join(ctx.reports, pipeline_state.STATE_FILENAME)

    # --clean — до любых проверок: удаляется ТОЛЬКО checkpoint (ТЗ §23).
    if args.clean:
        removed = pipeline_state.remove_checkpoint(ctx.state_path)
        print("checkpoint %s" % ("удалён" if removed else "не существовал"),
              file=sys.stderr)

    # Resume валидируется ДО любого анализа (ТЗ §23): ROM/RDB по sha256 —
    # без сервера; capabilities — сразу после подъёма сеанса, до первого stage.
    checkpoint = None
    try:
        if ctx.resume:
            checkpoint = pipeline_state.read_checkpoint(ctx.state_path)
            pipeline_state.validate_resume(checkpoint, ctx.rom, ctx.rdb,
                                           required=("debug_save_rdb",))
    except PipelineFatal as exc:
        print("STOP %s: %s" % (exc.code, exc.message), file=sys.stderr)
        return 1

    stats = {"by_module": {}, "session_restarts": 0}
    started = time.time()
    ctx.checkpoint_log = []
    results = {}                    # key -> StageResult
    fatal = None
    if checkpoint is None:
        checkpoint = pipeline_state.make_state(
            rom=os.path.basename(ctx.rom), rdb=os.path.basename(ctx.rdb))
    checkpoint.update({
        "rom": os.path.basename(ctx.rom), "rom_path": os.path.abspath(ctx.rom),
        "rom_sha256": pipeline_state.file_sha256(ctx.rom),
        "rdb": os.path.basename(ctx.rdb), "rdb_path": os.path.abspath(ctx.rdb),
        "dry_run": ctx.dry_run, "status": "running",
    })
    if not pipeline_state.file_sha256(ctx.rdb):
        checkpoint["rdb_sha256"] = None   # RDB ещё не рождался (riseout-сценарий)
    pipeline_state.set_active(ctx.state_path, checkpoint)

    rdb_sha_before = pipeline_state.file_sha256(ctx.rdb)

    share_kwargs = dict(rom=args.rom, org=to_addr(args.org), server=args.server,
                        cache_dir=ctx.cache, cache=not args.no_cache,
                        verbose=args.verbose)
    holder = {"cm": share(**share_kwargs), "session": None}
    session = None
    try:
        session = holder["cm"].__enter__()
        holder["session"] = session
        session.close = lambda: None      # общий сеанс: сервер умирать нельзя
        if ctx.dry_run:
            install_dry_run_guard(session)
        caps = CapabilityProfile.from_session(session)
        ctx.caps = caps
        missing = caps.missing_core()
        if missing:
            raise PipelineFatal("REQUIRED_CAPABILITY_MISSING",
                                "сервер не даёт: %s" % ", ".join(missing))
        try:
            from analyze.mcp_session import _SHARED
            ctx.cache_obj = _SHARED.get("cache")
        except Exception:                            # noqa: BLE001
            ctx.cache_obj = None
        completed = set((checkpoint or {}).get("completed_stages") or [])
        completed = verified_completed(ctx, completed)
        last_checkpoint_ts = time.time()
        for step in steps:
            if step.key in completed and ctx.resume:
                outcome = StageResult(SKIPPED,
                                      note="уже завершён (resume)")
                outcome.mcp = {"calls": 0}
                results[step.key] = outcome
                print("→ %s (уже готов, resume)" % step.key, file=sys.stderr)
                continue
            blocked = [dep for dep in step.depends_on
                       if results.get(dep) and results[dep].status in
                       (FAILED, BLOCKED)]
            if blocked:
                results[step.key] = StageResult(
                    BLOCKED, note="предок %s в отказе (ТЗ §22)"
                    % ", ".join(blocked))
                print("→ %s BLOCKED (%s)" % (step.key, ", ".join(blocked)),
                      file=sys.stderr)
                continue
            pipeline_state.update_active(current_stage=step.key,
                                         current_batch=None,
                                         processed_objects=None,
                                         pending_objects=None)
            print("→ %s%s" % (step.key, " [dry-run]" if ctx.dry_run else ""),
                  file=sys.stderr)
            outcome = run_guarded(step, ctx, session, stats)
            results[step.key] = outcome
            if "MCP_UNAVAILABLE" in " ".join(outcome.errors) and \
                    stats["session_restarts"] == 0 and not fatal:
                # Один переподним сеанса на прогон (ТЗ §57): сервер умер —
                # сохраняем подтверждённое, поднимаем новый сеанс, повторяем
                # stage (идемпотентный apply переставляет всё сам).
                try:
                    holder["cm"].__exit__(None, None, None)
                except Exception:                    # noqa: BLE001 — мёртвый сервер
                    pass
                holder["cm"] = share(**share_kwargs)
                session = holder["cm"].__enter__()
                session.close = lambda: None
                if ctx.dry_run:
                    install_dry_run_guard(session)
                stats["session_restarts"] += 1
                print("→ %s после переподключения MCP" % step.key,
                      file=sys.stderr)
                outcome = run_guarded(step, ctx, session, stats)
                results[step.key] = outcome
            if outcome.status in (SUCCESS, PARTIAL):
                try:
                    persist_stage(ctx, session, step, outcome)
                    mark_completed(ctx, step)
                    last_checkpoint_ts = time.time()
                except PipelineFatal as exc:
                    if exc.code == "DRY_RUN_VIOLATION":
                        fatal = exc
                        break
                    raise
            elif outcome.status == FAILED and not ctx.dry_run:
                # recoverable-исчерпан: подтвердить на диске всё, что уже
                # применено, и остановиться — resume продолжит (ТЗ §31).
                try:
                    persist_stage(ctx, session, step, outcome)
                except PipelineFatal as exc:
                    fatal = exc
                    break
            # Принудительный checkpoint по таймеру (ТЗ §4.3): mutating-stage
            # сам дробит пачки (--save-every), здесь граница между stages.
            if time.time() - last_checkpoint_ts > \
                    ctx.persistence["max_checkpoint_seconds"]:
                pipeline_state.checkpoint_active(status="checkpoint")
                last_checkpoint_ts = time.time()
            if fatal:
                break
        if not _session_alive(session) and not fatal:
            fatal = PipelineFatal("MCP_UNAVAILABLE",
                                  "сервер умер; несохранённое потеряно, "
                                  "сохранённое подтверждено checkpoint")
        ctx.session_stats = session.stats()
    except PipelineFatal as exc:
        fatal = exc
    finally:
        try:
            holder["cm"].__exit__(None, None, None)
        except Exception:                            # noqa: BLE001 — уходим в любом случае
            pass
        final_state = pipeline_state.update_active() or {}
        pipeline_state.checkpoint_active(
            status="finished" if not fatal else "stopped",
            current_stage=None,
            completed_stages=sorted(set(final_state.get("completed_stages") or
                                        [])))
        pipeline_state.clear_active()

    # --dry-run обязан оставить RDB байт в байт тем же (ТЗ §24).
    dry_run_intact = True
    if ctx.dry_run:
        dry_run_intact = (pipeline_state.file_sha256(ctx.rdb) == rdb_sha_before)

    merged, stats_path = write_statistics(ctx, stats, started, results)
    overall, stages_summary = summarize(results, steps, fatal)
    meta = {
        "rom": ctx.rom, "rom_sha256": checkpoint.get("rom_sha256"),
        "rdb": ctx.rdb, "dry_run": ctx.dry_run, "resumed": ctx.resume,
        "started_iso": time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                     time.gmtime(started)),
        "finished_iso": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "fatal": "%s: %s" % (fatal.code, fatal.message) if fatal else None,
    }
    if ctx.dry_run and not dry_run_intact:
        overall = "FAILED"
        meta["fatal"] = "DRY_RUN_VIOLATION: RDB изменился в dry-run"
    md_path, json_path = write_reports(ctx, meta, stages_summary, overall,
                                       merged)

    results_payload = {}
    for step in steps:
        entry = stats["by_module"].get(step.key) or {}
        path = entry.get("json")
        if not path or not os.path.isfile(path):
            continue
        with open(path, "r", encoding="utf-8") as handle:
            results_payload[step.key] = json.load(handle)

    report_path = args.out or os.path.join(ctx.results, "report.md")
    text = report_gen.render(
        results_payload, goal=args.goal, stage=args.stage,
        stats_file=stats_path,
        limitations=list(report_gen.DEFAULT_LIMITATIONS) + [
            "Прогон выполнен `pipeline.py` в одном общем MCP-сеансе; поле "
            "`mcp_calls` у модуля — дельта этого сеанса на момент его шага"])
    with open(report_path, "w", encoding="utf-8") as handle:
        handle.write(text)

    ok = sum(1 for r in results.values() if r.ok)
    failed = sum(1 for r in results.values()
                 if r.status in (FAILED, BLOCKED))
    skipped = sum(1 for r in results.values() if r.status == SKIPPED)
    flagged = sum(1 for step, r in ((s, results.get(s.key)) for s in steps)
                  if r and r.warnings)
    summary = {
        "steps": len(steps), "succeeded": ok, "failed": failed,
        "skipped": skipped, "exit_nonzero": flagged,
        "status": overall,
        "mode": "dry-run" if ctx.dry_run else "apply",
        "total_mcp_calls": merged.get("total_mcp_calls"),
        "wall_ms": merged.get("wall_ms"),
        "cache": merged.get("cache"),
        "statistics": stats_path,
        "report": report_path,
        "results": ctx.results,
        "checkpoint": ctx.state_path,
        "pipeline_report": md_path,
        "pipeline_json": json_path,
    }
    if fatal:
        summary["fatal"] = "%s: %s" % (fatal.code, fatal.message)
        print("STOP %s" % summary["fatal"], file=sys.stderr)
    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=1,
                         sort_keys=True))
    else:
        print("stages %d, успешных %d, отказов %d, пропущено %d; режим %s; "
              "вызовов MCP %s за %s мс; отчёт: %s%s"
              % (summary["steps"], ok, failed, skipped, summary["mode"],
                 summary["total_mcp_calls"], summary["wall_ms"], md_path,
                 "" if not fatal else "; STOP: %s" % fatal.code))
    return 0 if (not failed and not fatal) else 1


def verified_completed(ctx, completed):
    """Resume не верит checkpoint на слово (ТЗ §9): сверяем артефакты.

    Stage считается завершённым, только если его `results/<key>.json` на месте,
    а RDB содержит не меньше объектов, чем подтверждал последний checkpoint.
    Не прошедшие сверку исключаются — они будут перезапускаются идемпотентно.
    """
    state = pipeline_state.read_checkpoint(ctx.state_path) or {}
    expected_objects = state.get("rdb_objects")
    rdb_count = None
    if expected_objects is not None:
        try:
            rdb_count = pipeline_state.rdb_file_stats(ctx.rdb).get("objects")
        except ValueError:
            rdb_count = None
        if rdb_count is None or rdb_count < expected_objects:
            print("resume: RDB (%s) беднее checkpoint (%s) — completed_stages "
                  "не подтверждены" % (rdb_count, expected_objects),
                  file=sys.stderr)
            return set()
    out = set()
    for key in completed:
        artifact = os.path.join(ctx.results, "%s.json" % key)
        if os.path.isfile(artifact):
            out.add(key)
    return out


def run_guarded(step, ctx, session, stats):
    """Stage c retry recoverable-ошибок (ТЗ §31—§32).

    Read-only stage повторяется до MAX_RETRIES с backoff; mutating-stage —
    нет: его повтор равен перезапуску с нуля при --resume (идемпотентность
    applyPlan), а inline-retry мог бы дважды посчитать аддитивные поля.
    Смерть сервера — отдельная ветка: MCP_UNAVAILABLE (fatal для прогона,
    --resume поднимет новый сеанс и догонит по checkpoint).
    """
    attempts = 1 if step.mutates_rdb and not ctx.dry_run else MAX_RETRIES + 1
    last_error = None
    for attempt in range(attempts):
        if attempt:
            delay = RETRY_BACKOFF[min(attempt - 1, len(RETRY_BACKOFF) - 1)]
            print("  repeat %s через %.0f с (attempt %d/%d)"
                  % (step.key, delay, attempt + 1, attempts), file=sys.stderr)
            time.sleep(delay)
        try:
            outcome = run_step(step, ctx, session, stats, retries=attempt)
            retryable = getattr(outcome, "retryable", False)
            if outcome.status != FAILED or attempt == attempts - 1 \
                    or not retryable:
                if not _session_alive(session) and outcome.status == FAILED:
                    outcome.errors.append("MCP_UNAVAILABLE: сеанс умер")
                return outcome
            last_error = outcome.errors[0] if outcome.errors else "FAILED"
        except (McpTimeout, ConnectionError, OSError) as exc:
            last_error = "%s: %s" % (type(exc).__name__, exc)
            if attempt == attempts - 1 or not _session_alive(session):
                outcome = StageResult(
                    FAILED, errors=[
                        ("MCP_UNAVAILABLE: " if not _session_alive(session)
                         else "MCP_TIMEOUT: ") + str(last_error)])
                outcome.duration_ms = 0.0
                return outcome
    outcome = StageResult(FAILED, errors=["retries исчерпаны: %s" % last_error])
    return outcome


def summarize(results, steps, fatal):
    """Итоговый статус прогона + табличное представление stages (ТЗ §36—§37)."""
    stages_summary = {}
    statuses = []
    for step in steps:
        outcome = results.get(step.key)
        if outcome is None:
            continue
        stages_summary[step.key] = outcome.to_dict()
        statuses.append(outcome.status)
    if fatal:
        overall = "STOPPED"
    elif FAILED in statuses or BLOCKED in statuses:
        overall = "FAILED"
    elif PARTIAL in statuses or SKIPPED in statuses:
        overall = "PARTIAL"
    else:
        overall = "SUCCESS"
    return overall, stages_summary


def merge_cache(stats, cache):
    if cache is None:
        return
    try:
        data = cache.stats()
    except Exception:                            # noqa: BLE001 — статистика не роняет прогон
        return
    stats["cache"] = {key: data.get(key) for key in
                      ("hits", "misses", "stores", "bypasses", "hit_rate",
                       "entries", "root")
                      if data.get(key) is not None}


def write_statistics(ctx, stats, started, results):
    """Обязательная сводка вызовов (ТЗ прошлой итерации §30) + rdb_stats.

    Сеанс к этому моменту уже закрыт, поэтому берётся `ctx.session_stats`,
    снятый main() перед выходом из `share()`; итог по вызовам — сумма
    честных дельт по stages (при общем сеансе счётчик сеанса накопительный).
    """
    final = getattr(ctx, "session_stats", None) or {}
    merged = {
        "total_mcp_calls": final.get("total_calls") or sum(
            entry.get("mcp_calls", 0)
            for entry in stats["by_module"].values() if isinstance(entry, dict)),
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
        "session_restarts": stats.get("session_restarts", 0),
        "session": "shared (ТЗ §4)",
    }
    try:
        merged["rdb_stats"] = pipeline_state.rdb_file_stats(ctx.rdb)
    except ValueError:
        merged["rdb_stats"] = {"objects": None, "links": None}
    merge_cache(merged, getattr(ctx, "cache_obj", None))
    path = ctx.statistics or os.path.join(ctx.results, "statistics.json")
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(merged, handle, ensure_ascii=False, indent=1, sort_keys=True)
        handle.write("\n")
    return merged, path


if __name__ == "__main__":
    sys.exit(main())
