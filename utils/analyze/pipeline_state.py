"""Checkpoint, RDB persistence и валидация resume (ТЗ Standard Pipeline §5—§11, §23, §30).

Здесь живёт всё, что связано с фразой «RDB на диске — persistent state анализа»
(ТЗ §3):

* атомарная запись checkpoint (ТЗ §8): `.tmp` → fsync → rename, так что после
  crash файл либо старый корректный, либо новый корректный;
* проверка сохранения (ТЗ §6): файл существует, ненулевой, читается, содержит
  ожидаемое число объектов — читается ЧИСТО (правки `*.rdb` отсюда нет:
  save делает только отладчик через `debug_save_rdb`, ТЗ §5);
* вычисление sha256 ROM/RDB и валидация resume (ТЗ §9—§11, §23) — до первого
  аналитического вызова, с фатальными кодами ROM_MISMATCH /
  RDB_CHANGED_OUTSIDE_PIPELINE / CHECKPOINT_CORRUPTED / REQUIRED_CAPABILITY_MISSING;
* «активный checkpoint» — хук для долгих mutating-модулей (`seed_rdb`,
  `apply_annotations`): pipeline регистрирует файл состояния перед прогоном,
  модуль после каждого сохранённого батча зовёт `checkpoint_active(...)` и
  батч подтверждается посреди stage (ТЗ §4.4 «после batch RDB modifications»).

Модуль намеренно не знает ни про какие Stage/модули — только про состояние.
"""
from __future__ import annotations

import json
import os
import time

from analyze.mcp_session import sha256_file

STATE_VERSION = 1
STATE_FILENAME = "pipeline_state.json"

# Инструменты, меняющие RDB. В --dry-run pipeline ставит guard, который
# запрещает их полностью (ТЗ §24: «запрещены object/link/alias изменения и
# debug_save_rdb»). runtime-инструменты (breakpoint/ registers) сюда не входят:
# ROM в dry-run обязан анализироваться по-настоящему.
RDB_MUTATING_TOOLS = frozenset([
    "debug_add_rdb_object", "debug_update_rdb_object", "debug_remove_rdb_object",
    "debug_add_rdb_link", "debug_remove_rdb_link", "debug_set_rdb_comment",
    "debug_set_rdb_property", "debug_add_label", "debug_create_function",
    "debug_rename_function", "debug_delete_function", "debug_save_rdb",
])

# Таксономия ошибок (ТЗ §30). Остановить прогон немедленно.
FATAL_CODES = (
    "ROM_MISMATCH",              # checkpoint.rom_sha256 != факт (ТЗ §10)
    "RDB_MISSING",               # resume, а подтверждённого RDB нет на диске
    "RDB_CHANGED_OUTSIDE_PIPELINE",  # checkpoint.rdb_sha256 != факт (ТЗ §11)
    "RDB_CORRUPTED",             # сохранённый RDB не читается (ТЗ §6)
    "CHECKPOINT_CORRUPTED",      # pipeline_state.json битый/не-JSON
    "CHECKPOINT_MISSING",        # --resume без checkpoint
    "MCP_UNAVAILABLE",           # сервер не отвечает и не переподнимается
    "REQUIRED_CAPABILITY_MISSING",  # без нужного инструмента нечего делать
    "SAVE_VERIFY_FAILED",        # save отработал, но verify не прошёл
    "DRY_RUN_VIOLATION",         # модуль попытался мутировать RDB в --dry-run
)
# Повторить до 3 раз с backoff, потом — FAILED + checkpoint + --resume (ТЗ §31).
RECOVERABLE_CODES = ("MCP_TIMEOUT", "MCP_DISCONNECTED", "STEP_EXCEPTION")


class PipelineFatal(RuntimeError):
    """Фатальная остановка: продолжать нельзя, checkpoint уже записан."""

    def __init__(self, code, message=""):
        RuntimeError.__init__(self, "%s: %s" % (code, message) if message else code)
        self.code = code
        self.message = message or code


class CheckpointCorrupted(PipelineFatal):
    def __init__(self, message):
        PipelineFatal.__init__(self, "CHECKPOINT_CORRUPTED", message)


class DryRunViolation(RuntimeError):
    """Мутация RDB в --dry-run: прогон обязан остановиться с фатальным кодом."""

    def __init__(self, tool):
        RuntimeError.__init__(self, "dry-run: модуль попытался вызвать %s" % tool)
        self.tool = tool


def utc_now():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def file_sha256(path):
    """SHA256 файла или None, если файла нет (отсутствие — не исключение)."""
    if not path or not os.path.isfile(path):
        return None
    return sha256_file(path)


# ---------------------------------------------------------------------------
# Статистика RDB
# ---------------------------------------------------------------------------

def rdb_file_stats(path):
    """Прочитать *.rdb и вернуть {"objects": n, "links": n} — ТОЛЬКО чтение.

    None по полю — файл есть, но поле по нему не читается. Битый JSON
    поднимает ValueError (вызывающий решает, RDB_CORRUPTED это или «нет данных»).
    """
    if not path or not os.path.isfile(path):
        return {"objects": None, "links": None}
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    objects = data.get("objects") or []
    links = sum(len(o.get("links") or []) for o in objects if isinstance(o, dict))
    return {"objects": len(objects), "links": links}


def rdb_stats(session):
    """{objects, links} из живого отладчика (debug_get_rdb_info).

    Поля в ответе сервера могут называться по-разному по версиям; берём
    первое имеющееся, отсутствие — None, а не 0: «не известно» != «нуль».
    """
    out = {"objects": None, "links": None}
    try:
        info = session.call("debug_get_rdb_info")
    except Exception:
        return out
    if not isinstance(info, dict):
        return out
    for key, names in (("objects", ("object_count", "objects", "total_objects")),
                       ("links", ("link_count", "links", "total_links"))):
        for name in names:
            if info.get(name) is not None:
                out[key] = info[name]
                break
    return out


# ---------------------------------------------------------------------------
# Чтение/атомарная запись checkpoint (ТЗ §7, §8)
# ---------------------------------------------------------------------------

def make_state(rom=None, rdb=None, **fields):
    """Скелет checkpoint формата version 1 (ТЗ §7)."""
    state = {
        "version": STATE_VERSION,
        "rom": rom,
        "rom_sha256": None,
        "rdb": rdb,
        "rdb_sha256": None,
        "last_completed_stage": None,
        "completed_stages": [],
        "current_stage": None,
        "current_batch": None,
        "processed_objects": None,
        "pending_objects": None,
        "checkpoint_time": utc_now(),
        "rdb_objects": None,
        "rdb_links": None,
        "status": "started",
        "dry_run": False,
    }
    state.update(fields)
    return state


def read_checkpoint(path):
    """Читаемый checkpoint или None (файла нет). Битый — CheckpointCorrupted."""
    if not path or not os.path.isfile(path):
        return None
    try:
        with open(path, encoding="utf-8") as handle:
            state = json.load(handle)
    except ValueError as exc:
        raise CheckpointCorrupted("pipeline_state.json не разобран: %s" % exc)
    if not isinstance(state, dict):
        raise CheckpointCorrupted("pipeline_state.json — не объект JSON")
    if int(state.get("version") or 0) != STATE_VERSION:
        raise CheckpointCorrupted("неизвестная версия checkpoint: %r"
                                  % state.get("version"))
    return state


def write_checkpoint(path, state):
    """Атомарно: tmp → flush+fsync → rename (ТЗ §8). Возвращает path."""
    state = dict(state)
    state["version"] = STATE_VERSION
    state["checkpoint_time"] = utc_now()
    directory = os.path.dirname(os.path.abspath(path))
    if not os.path.isdir(directory):
        os.makedirs(directory)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as handle:
        json.dump(state, handle, ensure_ascii=False, indent=1, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.rename(tmp, path)
    return path


# ---------------------------------------------------------------------------
# Проверка сохранения (ТЗ §6)
# ---------------------------------------------------------------------------

def verify_saved_rdb(rdb_path, expected=None, minimum=None):
    """Минимальная проверка: существует, не пустой, читается, счёт совпадает.

    (ok, detail). expected — точное число объектов (после нашего save),
    minimum — нижняя граница («не меньше, чем до save»). Только ЧТЕНИЕ файла:
    pipeline не имеет права править *.rdb сам (ТЗ §5).
    """
    detail = {"path": rdb_path, "exists": False, "size": 0, "objects": None,
              "links": None, "error": None}
    if not rdb_path or not os.path.isfile(rdb_path):
        detail["error"] = "RDB_CORRUPTED: файл не найден"
        return False, detail
    detail["exists"] = True
    detail["size"] = os.path.getsize(rdb_path)
    if detail["size"] <= 0:
        detail["error"] = "RDB_CORRUPTED: файл нулевой"
        return False, detail
    try:
        stats = rdb_file_stats(rdb_path)
    except (ValueError, KeyError) as exc:
        detail["error"] = "RDB_CORRUPTED: не читается: %s" % exc
        return False, detail
    detail["objects"] = stats["objects"]
    detail["links"] = stats["links"]
    if stats["objects"] is None:
        detail["error"] = "SAVE_VERIFY_FAILED: в RDB нет списка objects"
        return False, detail
    if expected is not None and stats["objects"] != expected:
        detail["error"] = "SAVE_VERIFY_FAILED: объектов %s, ожидалось %s" % (
            stats["objects"], expected)
        return False, detail
    if minimum is not None and stats["objects"] < minimum:
        detail["error"] = "SAVE_VERIFY_FAILED: объектов %s, минимум %s" % (
            stats["objects"], minimum)
        return False, detail
    return True, detail


# ---------------------------------------------------------------------------
# «Активный checkpoint»: батч-хук для долгих mutating-модулей (ТЗ §4.4, §7)
# ---------------------------------------------------------------------------

_ACTIVE = {"path": None, "state": None}


def set_active(path, state=None):
    """Зарегистрировать файл checkpoint для текущего прогона (или снять)."""
    if path is None:
        _ACTIVE["path"] = None
        _ACTIVE["state"] = None
        return None
    _ACTIVE["path"] = path
    _ACTIVE["state"] = dict(state or read_checkpoint(path) or
                            make_state(rom=None, rdb=None))
    return _ACTIVE["path"]


def clear_active():
    set_active(None)


def active_path():
    return _ACTIVE["path"]


def update_active(**changes):
    """Изменить базовый state без записи (текущий stage и прочее)."""
    if _ACTIVE["state"] is not None:
        _ACTIVE["state"].update(changes)
    return _ACTIVE["state"]


def checkpoint_active(**changes):
    """Подтвердить текущее состояние диска: перечитать sha256/счёта и записать.

    Вызывается изнутри mutating-модулей после каждого save-батча. Без
    регистрации (`set_active`) — no-op: модуль можно запускать и вне pipeline.
    """
    if not _ACTIVE["path"]:
        return None
    state = dict(_ACTIVE["state"] or {})
    state.update(changes)
    # Полный путь мог лежать в `rdb_path` (pipeline пишет и имя, и путь);
    # без этого sha256 считался бы от basename и был бы None.
    rdb_path = state.get("rdb_path") or state.get("rdb")
    state["rdb_sha256"] = file_sha256(rdb_path)
    try:
        stats = rdb_file_stats(rdb_path)
    except ValueError:
        stats = {"objects": None, "links": None}
    state["rdb_objects"] = stats["objects"]
    state["rdb_links"] = stats["links"]
    state.setdefault("status", "checkpoint")
    path = write_checkpoint(_ACTIVE["path"], state)
    _ACTIVE["state"].update(state)
    return path


# ---------------------------------------------------------------------------
# Валидация resume (ТЗ §9—§11, §23): порядок проверок до любого анализа
# ---------------------------------------------------------------------------

def validate_resume(state, rom_path, rdb_path, caps=None, required=()):
    """Проверить checkpoint против реальности. PipelineFatal при отказе.

    Порядок обязан быть именно такой (ТЗ §23): checkpoint читаем (сам вызывающий
    делает через read_checkpoint — сюда уже dict) → ROM sha256 → RDB sha256 →
    capabilities. Возвращает список завершённых stage.
    """
    if state is None:
        raise PipelineFatal("CHECKPOINT_MISSING",
                            "checkpoint не найден — нечего возобновлять")
    actual_rom = file_sha256(rom_path)
    if actual_rom is None:
        raise PipelineFatal("ROM_MISMATCH", "ROM-файл не найден: %s" % rom_path)
    if state.get("rom_sha256") and actual_rom != state["rom_sha256"]:
        raise PipelineFatal("ROM_MISMATCH",
                            "ROM изменён вне pipeline: %s != %s (начните новый "
                            "прогон без --resume)" % (actual_rom[:12],
                                                      str(state["rom_sha256"])[:12]))
    actual_rdb = file_sha256(rdb_path)
    if state.get("rdb_sha256") and actual_rdb is None:
        raise PipelineFatal("RDB_MISSING",
                            "checkpoint подтверждал RDB %s, но файла нет" % rdb_path)
    if state.get("rdb_sha256") and actual_rdb != state["rdb_sha256"]:
        raise PipelineFatal("RDB_CHANGED_OUTSIDE_PIPELINE",
                            "RDB изменён вне pipeline (%s != %s): молча "
                            "перезаписывать пользовательские изменения нельзя"
                            % (actual_rdb[:12], str(state["rdb_sha256"])[:12]))
    missing = [name for name in required if caps is not None and name not in caps]
    if missing:
        raise PipelineFatal("REQUIRED_CAPABILITY_MISSING",
                            "для resume нужны инструменты: %s" % ", ".join(missing))
    return list(state.get("completed_stages") or [])


def remove_checkpoint(path):
    """--clean (ТЗ §23): удаляет ТОЛЬКО checkpoint; RDB/ROM/отчёты не трогаем."""
    removed = False
    for candidate in (path, path + ".tmp"):
        if os.path.isfile(candidate):
            os.remove(candidate)
            removed = True
    return removed
