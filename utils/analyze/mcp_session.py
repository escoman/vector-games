"""Единственная точка доступа к отладчику Vector-06C (ТЗ §3, §4, §33, §34).

Модуль реализует ОДНУ долгоживущую MCP-сессию: запуск `v06c-mcp`, JSON-RPC
«одна строка — одно сообщение» через stdin/stdout, `initialize`, `tools/list`,
`tools/call` и сбор статистики вызовов (ТЗ §30).

Никакому другому скрипту пакета нельзя открывать процесс сервера или писать
JSON-RPC самостоятельно — только через `McpSession` (ТЗ §3).

Python здесь НЕ является ни эмулятором, ни дизассемблером: он перевозит
байты и ответы отладчика (ТЗ §34).

Запуск сервера:
    V06C_MCP=/path/to/v06c-mcp            (по умолчанию DEFAULT_SERVER)

Пример:
    with McpSession() as s:
        s.load_rom("roms/redesign/putup/src/putup.rom", org=0x0100)
        state = s.call("debug_get_state")
        print(s.stats())
"""
from __future__ import annotations

import contextlib
import hashlib
import json
import os
import queue
import re
import subprocess
import sys
import threading
import time

DEFAULT_SERVER = os.environ.get(
    "V06C_MCP",
    "/home/alexey/Projects/vector-debugger/debugger/build/v06c-mcp",
)
PROTOCOL_VERSION = "2024-11-05"
CLIENT_INFO = {"name": "v06c-analyze", "version": "1"}

# Вызовы, меняющие состояние эмулятора/RDB: после них нельзя использовать
# кэш runtime-evidence и «отпечаток» рантайма должен быть переснят (ТЗ §16).
MUTATING_TOOLS = {
    "debug_load_rom",
    "debug_run",
    "debug_step",
    "debug_pause",
    "debug_reset",
    "debug_write_memory",
    "debug_write_io",
    "debug_press_key",
    "debug_release_key",
    "debug_type_key",
    "debug_set_register",
    "debug_set_breakpoint",
    "debug_remove_breakpoint",
    "debug_set_breakpoint_enabled",
    "debug_clear_breakpoints",
    "debug_clear_memory_access_map",
    "debug_create_memory_snapshot",
    "debug_add_rdb_object",
    "debug_update_rdb_object",
    "debug_remove_rdb_object",
    "debug_set_rdb_comment",
    "debug_set_rdb_property",
    "debug_add_rdb_link",
    "debug_remove_rdb_link",
    "debug_add_label",
    "debug_create_function",
    "debug_delete_function",
    "debug_rename_function",
    "debug_set_comment",
    "debug_set_function_comment",
    "debug_save_rdb",
    "debug_reload_rdb",
}


class McpError(RuntimeError):
    """Ошибка транспорта или ошибка, возвращённая инструментом сервера."""

    def __init__(self, tool, message, kind="tool_error", payload=None):
        super().__init__("%s: %s" % (tool, message))
        self.tool = tool
        self.kind = kind
        self.payload = payload or {}


class McpTimeout(McpError):
    """Сервер не ответил за отведённое время."""

    def __init__(self, tool, seconds):
        super().__init__(tool, "нет ответа за %.1f с" % seconds, kind="timeout")
        self.seconds = seconds


# ---------------------------------------------------------------------------
# Адреса.
#
# Все ответы v06c-mcp отдают адреса строками ("0x0100"), а параметры принимают
# числами. Хелперы ниже — единственное место в пакете, где это различие
# переводится (ТЗ §9: ограничения MCP не должны расползаться по вызывающему
# коду).
# ---------------------------------------------------------------------------


def to_addr(value):
    """"0x0100" | "FF" | 256 | None -> int | None.

    Соглашение: числа и строки с префиксом 0x — адреса как их отдаёт/принимает
    MCP; строка без префикса шестнадцатеричное основание только если содержит
    буквы (иначе это десятичное число). Неадресуемое значение (путь к файлу,
    например) — ValueError, а не тихая подмена.
    """
    if value is None:
        return None
    if isinstance(value, bool):
        raise ValueError("адрес не может быть булевым")
    if isinstance(value, int):
        return value
    text = str(value).strip()
    if not text:
        return None
    if text.lower().startswith("0x"):
        body, base = text[2:], 16
    else:
        body, base = text, 16 if re.search(r"[a-fA-F]", text) else 10
    try:
        return int(body, base)
    except ValueError:
        raise ValueError("не удалось прочитать адрес из %r" % (value,)) from None



def bytes_of(payload):
    """Байты из ответа сервера: разные инструменты называют поле по-разному.

    debug_read_memory_range отдаёт "data", debug_read_memory — "bytes",
    debug_get_vram_bytes — список чисел. Всегда возвращается `bytes`, чтобы
    вызывающий мог резать, сравнивать и звать .hex() без проверок на тип.
    """
    if isinstance(payload, (bytes, bytearray)):
        return bytes(payload)
    if isinstance(payload, str):
        return bytes.fromhex(payload.replace(" ", ""))
    if isinstance(payload, dict):
        payload = next((payload[key] for key in ("data", "bytes", "values")
                        if payload.get(key) is not None), None)
    if payload is None:
        return b""
    if isinstance(payload, str):
        return bytes.fromhex(payload.replace(" ", ""))
    out = bytearray()
    for item in payload:
        out.append(int(item, 16) & 0xFF if isinstance(item, str)
                   else int(item) & 0xFF)
    return bytes(out)


def addr_hex(value, width=4):
    """int | str -> "0x0100" (для вывода и ключей)."""
    if value is None:
        return "None"
    return "0x%0*X" % (width, to_addr(value) & ((1 << (4 * width)) - 1))


def sha256_file(path, block=1 << 20):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(block), b""):
            h.update(chunk)
    return h.hexdigest()


class ToolStat:
    """Однострочная метрика по одному инструменту (ТЗ §30)."""

    __slots__ = ("calls", "total_ms", "max_ms", "total_bytes", "max_bytes")

    def __init__(self):
        self.calls = 0
        self.total_ms = 0.0
        self.max_ms = 0.0
        self.total_bytes = 0
        self.max_bytes = 0

    def observe(self, ms, nbytes):
        self.calls += 1
        self.total_ms += ms
        if ms > self.max_ms:
            self.max_ms = ms
        self.total_bytes += nbytes
        if nbytes > self.max_bytes:
            self.max_bytes = nbytes

    def as_dict(self):
        return {
            "calls": self.calls,
            "total_ms": round(self.total_ms, 1),
            "max_ms": round(self.max_ms, 1),
            "total_bytes": self.total_bytes,
            "max_bytes": self.max_bytes,
        }


class McpSession:
    """Долгоживущая сессия к `v06c-mcp` (ТЗ §4).

    Один процесс сервера на весь прогон: ROM, память, RDB, снапшоты и трассы
    живут в нём, поэтому повторный запуск процесса на каждый анализ запрещён.
    """

    def __init__(self, server=None, timeout=120.0, verbose=False, cwd=None):
        self.server = server or DEFAULT_SERVER
        self.timeout = float(timeout)
        self.verbose = verbose
        self.cwd = cwd
        self._proc = None
        self._next_id = 0
        self._lines = None
        self._stderr_tail_lines = []
        self._tools = None
        self._server_info = None
        self._protocol_version = None
        self._stamp = None
        self._stamp_at = None
        self.per_tool = {}
        self.total_calls = 0
        self.total_ms = 0.0
        self.total_bytes = 0
        self.retries = 0
        self.started_at = None
        self.org = None
        self.rom = None            # dict identity после load_rom
        self.log = []              # [(t, tool, args, ms, bytes)]
        self.pinned = False        # общий сеанс: close() обязан быть пустым

    # -- жизненный цикл ---------------------------------------------------

    def __enter__(self):
        return self.start()

    def __exit__(self, *_exc):
        self.close()
        return False

    def start(self):
        """spawn v06c-mcp → initialize → tools/list."""
        if self._proc is not None:
            return self
        if not os.path.exists(self.server):
            raise McpError(
                "<spawn>",
                "сервер не найден: %s (переменная окружения V06C_MCP)" % self.server,
                kind="spawn",
            )
        self._proc = subprocess.Popen(
            [self.server],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            cwd=self.cwd,
        )
        # Чтение обязательно отдельным потоком: select()/poll() на TextIOWrapper
        # не видят строки, уже попавшие во внутренний буфер Python, и клиент
        # «засыпает» даже когда сервер отвечает мгновенно (проверено экспериментом).
        self._lines = queue.Queue()
        self._stderr_tail_lines = []
        threading.Thread(target=self._pump_stdout, daemon=True).start()
        threading.Thread(target=self._pump_stderr, daemon=True).start()
        self.started_at = time.time()
        init = self._request(
            "initialize",
            {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": CLIENT_INFO,
            },
        )
        self._server_info = init.get("serverInfo", {})
        self._protocol_version = init.get("protocolVersion")
        self._notify("notifications/initialized")
        listed = self._request("tools/list")
        self._tools = {}
        for tool in listed.get("tools", []):
            self._tools[tool["name"]] = {
                "schema": tool.get("inputSchema", {}) or {},
                "description": tool.get("description", ""),
            }
        if self.verbose:
            self._log("сервер %s, протокол %s, инструментов %d"
                      % (self._server_info.get("version"), self._protocol_version,
                         len(self._tools)))
        return self

    def pin(self):
        """Сделать сеанс общим: `close()` больше не убивает сервер (ТЗ §4).

        Ставит `pipeline.py` один раз на весь прогон; модули по-прежнему пишут
        `with open_session(...) as (s, c): ...`, но по выходе сервер живёт.
        """
        self.pinned = True
        return self

    def close(self):
        """Завершение процесса сервера (инструмента останова нет — см. скилл)."""
        if self.pinned:
            # Общий сеанс пайплайна: модуль обязан закрыть его без остатка для
            # остальных шагов, поэтому останов сервера откладывается до конца.
            return
        if self._proc is None:
            return
        try:
            if self._proc.stdin:
                self._proc.stdin.close()
        except OSError:
            pass
        try:
            self._proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self._proc.terminate()
            try:
                self._proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._proc.kill()
        self._proc = None

    @property
    def running(self):
        return self._proc is not None and self._proc.poll() is None

    # -- транспорт ---------------------------------------------------------

    def _send(self, msg):
        if self._proc is None or self._proc.stdin is None:
            raise McpError("<transport>", "сессия не запущена", kind="spawn")
        self._proc.stdin.write(json.dumps(msg, separators=(",", ":")) + "\n")
        self._proc.stdin.flush()

    def _pump_stdout(self):
        stream = self._proc.stdout
        try:
            for line in stream:
                self._lines.put(line)
        except (OSError, ValueError):
            pass
        self._lines.put(None)          # sentinel: сервер закрыл stdout

    def _pump_stderr(self):
        # Логи сервера копятся в кольцевом буфере: не читать stderr — значит
        # поймать блокировку на заполнении pipe (64 КБ) посреди запроса.
        try:
            for line in self._proc.stderr:
                self._stderr_tail_lines.append(line.rstrip())
                if len(self._stderr_tail_lines) > 400:
                    del self._stderr_tail_lines[:200]
        except (OSError, ValueError):
            pass

    def _recv_line(self, deadline):
        while True:
            left = deadline - time.time()
            if left <= 0:
                raise McpTimeout("<recv>", self.timeout)
            try:
                line = self._lines.get(timeout=min(left, 0.5))
            except queue.Empty:
                if self._proc is None or self._proc.poll() is not None:
                    raise McpError("<transport>",
                                   "сервер завершился: %s" % self._stderr_tail(),
                                   kind="spawn")
                continue
            if line is None:
                raise McpError("<transport>",
                               "сервер закрыл stdout: %s" % self._stderr_tail(),
                               kind="spawn")
            line = line.strip()
            if line:
                return line

    def _stderr_tail(self, limit=400):
        return " | ".join(self._stderr_tail_lines[-4:])[-limit:]

    def _request(self, method, params=None, timeout=None):
        self._next_id += 1
        mid = self._next_id
        msg = {"jsonrpc": "2.0", "id": mid, "method": method}
        if params is not None:
            msg["params"] = params
        self._send(msg)
        deadline = time.time() + (timeout or self.timeout)
        while True:
            line = self._recv_line(deadline)
            try:
                resp = json.loads(line)
            except json.JSONDecodeError:
                continue  # сервер может писать служебные строки в stdout
            if resp.get("id") != mid:
                continue
            if "error" in resp:
                err = resp["error"]
                raise McpError(
                    method,
                    err.get("message", str(err)),
                    kind="jsonrpc",
                    payload=err,
                )
            return resp.get("result", {})

    def _notify(self, method, params=None):
        msg = {"jsonrpc": "2.0", "method": method}
        if params is not None:
            msg["params"] = params
        self._send(msg)

    # -- инструменты -------------------------------------------------------

    @property
    def tools(self):
        """{имя: {"schema":…, "description":…}} после tools/list."""
        if self._tools is None:
            self.start()
        return self._tools

    def tool_names(self):
        return set(self.tools)

    def has(self, name):
        return name in self.tools

    def call(self, tool, arguments=None, timeout=None, retries=1, **kwargs):
        """tools/call → разобранный JSON из content[0].text.

        `retries` — повтор только для идемпотентных (не изменяющих состояние)
        инструментов и только по таймауту; mutating-инструмент никогда не
        повторяется, чтобы не запустить ROM дважды.
        """
        if self._tools is None:
            self.start()
        args = dict(arguments or {})
        args.update(kwargs)
        args = {k: v for k, v in args.items() if v is not None}
        attempts = 1 + (retries if tool not in MUTATING_TOOLS else 0)
        last = None
        for attempt in range(attempts):
            try:
                return self._call_once(tool, args, timeout)
            except McpTimeout as exc:
                last = exc
                self.retries += 1
                if attempt + 1 < attempts and self.verbose:
                    self._log("%s: таймаут, повтор %d/%d" % (tool, attempt + 1, attempts - 1))
        raise last

    def _call_once(self, tool, args, timeout=None):
        started = time.time()
        result = self._request(
            "tools/call", {"name": tool, "arguments": args}, timeout=timeout
        )
        elapsed_ms = (time.time() - started) * 1000.0
        text = ""
        content = result.get("content") or []
        if content:
            text = content[0].get("text", "")
        if result.get("isError"):
            raise McpError(tool, " ".join(text.split())[:400] or "без сообщения",
                           kind="tool_error", payload=args)
        payload = None
        if text.strip():
            try:
                payload = json.loads(text)
            except json.JSONDecodeError:
                payload = {"text": text}
        if payload is None:
            payload = {}
        if isinstance(payload, dict) and payload.get("error_code"):
            # Сервер умеет отвечать ошибкой в теле, не выставляя isError.
            raise McpError(tool, payload.get("message") or payload["error_code"],
                           kind=payload["error_code"], payload=args)
        if tool in MUTATING_TOOLS:
            self._stamp = None
        nbytes = len(text)
        self.total_calls += 1
        self.total_ms += elapsed_ms
        self.total_bytes += nbytes
        self.per_tool.setdefault(tool, ToolStat()).observe(elapsed_ms, nbytes)
        self.log.append((round(started - (self.started_at or started), 3), tool,
                         _shrink(args), round(elapsed_ms, 1), nbytes))
        if self.verbose:
            self._log("%s(%s) → %.0f мс, %d Б"
                      % (tool, _fmt_args(args), elapsed_ms, nbytes))
        return payload

    def _log(self, message):
        print("[mcp] " + message, file=sys.stderr)

    # -- идентичность ROM и отпечаток рантайма (ТЗ §6, §7, §16) ------------

    def load_rom(self, path, org=None):
        """Каноническая загрузка ROM (ТЗ §14). НЕ использует debug_reset."""
        path = os.path.abspath(path)
        args = {"path": path}
        if org is not None:
            args["org"] = to_addr(org)
        out = self.call("debug_load_rom", args)
        self.org = to_addr(out.get("origin"))
        self.rom = self.rom_identity(path)
        self.rom["org"] = self.org if self.rom.get("org") is None else self.rom["org"]
        self._stamp = None
        return out

    def rom_identity(self, path=None):
        """{filename,size,sha256,org} — ключ кэша и поле provenance.

        `debug_get_rdb_info` отдаёт rom_file/rom_size/rom_sha256; org берётся
        из ответа загрузки ROM (`debug_load_rom.origin`), потому что в info
        поле `path` — это путь к .rdb, а не начало образа.
        """
        info = self.call("debug_get_rdb_info")
        target = path or info.get("rom_file")
        identity = {
            "filename": os.path.basename(target) if target else info.get("rom_file"),
            "path": os.path.abspath(target) if target else None,
            "size": info.get("rom_size"),
            "sha256": info.get("rom_sha256"),
            "org": getattr(self, "org", None),
        }
        if target and os.path.exists(target):
            identity["size"] = identity["size"] or os.path.getsize(target)
            if not identity["sha256"]:
                identity["sha256"] = sha256_file(target)
        return identity

    def runtime_stamp(self, force=False):
        """Дешёвый «момент рантайма» для ключа кэша: pc/running/cycles/sp.

        Кэшируется до ближайшего mutating-вызова (он сбрасывает `_stamp`),
        поэтому не удваивает число обращений к серверу.
        """
        if self._stamp is not None and not force:
            return self._stamp
        state = self.call("debug_get_state")
        cpu = state.get("cpu") or {}
        self._stamp = {
            "pc": cpu.get("pc"),
            "sp": cpu.get("sp"),
            "running": state.get("running"),
            "cycles": cpu.get("cycles"),
            "frames": state.get("frame_count"),
        }
        self._stamp_at = time.time()
        return self._stamp

    # -- статистика (ТЗ §30) ------------------------------------------------

    def snapshot(self):
        """Мгновенный слепок счётчиков — для дельты одного шага пайплайна."""
        return {"total_calls": self.total_calls, "total_ms": self.total_ms,
                "total_bytes": self.total_bytes, "retries": self.retries}

    @staticmethod
    def since(before, after):
        """Разница двух съёмков `snapshot()`."""
        return {key: round(after[key] - before[key], 1)
                for key in ("total_calls", "total_ms", "total_bytes", "retries")}

    def stats(self):
        """Обязательная часть каждого прогона: вызовы, время, байты, кэш."""
        largest = sorted(
            (
                (name, st.as_dict())
                for name, st in self.per_tool.items()
            ),
            key=lambda kv: kv[1]["total_ms"],
            reverse=True,
        )
        return {
            "server": os.path.basename(self.server),
            "server_version": (self._server_info or {}).get("version"),
            "protocol_version": self._protocol_version,
            "tools_exposed": len(self.tools) if self._tools else 0,
            "total_calls": self.total_calls,
            "total_ms": round(self.total_ms, 1),
            "total_bytes": self.total_bytes,
            "retries": self.retries,
            "wall_ms": round((time.time() - (self.started_at or time.time())) * 1000.0, 1),
            "by_tool": dict(largest),
            "largest_by_time": [
                {"tool": n, **d} for n, d in largest[:5]
            ],
        }


def _fmt_args(args, limit=90):
    text = json.dumps(args, separators=(",", ":"), ensure_ascii=False)
    return text if len(text) <= limit else text[:limit] + "…"


def _shrink(args, max_list=8):
    """Версия args для журнала: длинные списки сворачиваем."""
    out = {}
    for key, value in args.items():
        if isinstance(value, list) and len(value) > max_list:
            out[key] = value[:max_list] + ["… +%d" % (len(value) - max_list)]
        elif isinstance(value, str) and len(value) > 120:
            out[key] = value[:120] + "…"
        else:
            out[key] = value
    return out


def open_session(rom=None, org=0x0100, server=None, cache_dir=None,
                 verbose=False, timeout=120.0, cache=True):
    """Общая точка входа для всех CLI пакета: сессия + кэш доказательств.

    Один вызов = одна долгоживущая сессия (ТЗ §4). Если пайплайн уже
    выставил общий сеанс (`share()`), возвращается ОН: сервер на весь прогон
    один, а `close()` запиненного сеанса — пустое действие. ROM перезагружается
    только когда запрошен другой образ.

    Импорт `evidence_cache` отложен, чтобы модули ядра не зависели друг от
    друга при импорте.
    """
    global _CACHE_DIR
    if _SHARED["session"] is not None:
        session = _SHARED["session"]
        if session._proc is None:
            session.start()
        want = os.path.abspath(rom) if rom else None
        if want and (session.rom or {}).get("path") != want:
            session.load_rom(want, org=org)
        if cache and _SHARED["cache"] is not None:
            return session, _SHARED["cache"]
        if cache and session.rom:
            from analyze.evidence_cache import EvidenceCache

            _SHARED["cache"] = EvidenceCache.for_rom(
                want or session.rom["path"], root=_CACHE_DIR,
                identity=session.rom, verbose=verbose)
        return session, _SHARED["cache"]

    session = McpSession(server=server, verbose=verbose, timeout=timeout)
    session.start()
    cache_obj = None
    if rom:
        session.load_rom(rom, org=org)
        if cache:
            from analyze.evidence_cache import EvidenceCache

            cache_obj = EvidenceCache.for_rom(rom, root=cache_dir,
                                              identity=session.rom,
                                              verbose=verbose)
    return session, cache_obj


# Общий сеанс прогона (ТЗ §4): один процесс сервера на все модули.
_SHARED = {"session": None, "cache": None}
_CACHE_DIR = None


def get_shared():
    return _SHARED["session"]


@contextlib.contextmanager
def share(rom=None, org=0x0100, server=None, cache_dir=None, verbose=False,
          timeout=120.0, cache=True):
    """Установить общий сеанс на время прогона пайплайна.

    Модули продолжают звать `open_session()` как раньше и получают этот же
    сеанс; статистика вызовов при этом общая, поэтому `pipeline.py` снимает
    дельту вокруг каждого шага (`session.snapshot()`).
    """
    global _CACHE_DIR
    if _SHARED["session"] is not None:
        yield _SHARED["session"]
        return
    _CACHE_DIR = cache_dir
    session = McpSession(server=server, verbose=verbose, timeout=timeout)
    session.start()
    session.pin()
    cache_obj = None
    if rom:
        session.load_rom(rom, org=org)
        if cache:
            from analyze.evidence_cache import EvidenceCache

            cache_obj = EvidenceCache.for_rom(rom, root=cache_dir,
                                              identity=session.rom,
                                              verbose=verbose)
    _SHARED["session"] = session
    _SHARED["cache"] = cache_obj
    try:
        yield session
    finally:
        _SHARED["session"] = None
        _SHARED["cache"] = None
        _CACHE_DIR = None
        session.pinned = False
        session.close()


# ---------------------------------------------------------------------------
# Общий конверт результата модуля
# ---------------------------------------------------------------------------

STATUS_FACT = ("OK", "FACT", "MATCHED", "CLEAN")
STATUS_CANDIDATE = ("CANDIDATE", "PARTIAL", "DERIVED")


def session_fields(session):
    """Два обязательных поля статистики: счётчик вызовов и вся сводка сеанса.

    Нужны модулям, которые собирают результат вручную, без `envelope`.
    """
    stats = session.stats()
    return {"mcp_calls": stats.get("total_calls", 0), "session_stats": stats}


def envelope(result, module=None, session=None, status=None, verdict=None,
             note=None, candidates=None, cache=None):
    """Доводит вывод модуля до общего конверта (ТЗ §29, §30).

    `report_gen.py` раскладывает результаты по разделам отчёта только по полям
    `status`/`verdict`, а `pipeline.py` складывает `mcp_calls` — поэтому эти
    поля обязаны быть у каждого модуля, даже у того, который сидит на файлах.

    Ничего не придумывает: если модуль не назвал статус, статус остаётся
    неназванным (в отчёте такой результат попадёт в «никогда не отнесённое»).
    """
    if not isinstance(result, dict):
        raise SystemExit("конверт строится над dict, а не над %s"
                         % type(result).__name__)
    out = dict(result)
    if module and not out.get("module"):
        out["module"] = module
    if status:
        out["status"] = status
    elif not out.get("status"):
        print("%s: модуль не назвал статус — отчёт не сможет отнести его "
              "между фактами и выводами" % (module or "модуль"),
              file=sys.stderr)
    if verdict:
        out["verdict"] = verdict
    if note and not out.get("note"):
        out["note"] = note
    if candidates is not None and "candidates" not in out:
        # Компактные кандидаты для отчёта: свои, полные списки остаются в
        # специфичных для модуля полях (`signatures`, `image_runs`, …).
        out["candidates"] = candidates
    if session is not None:
        # Полная статистика сеанса нужна не для чтения, а для `pipeline.py`: он
        # сливает её в сводку §30 по всем модулям сразу.
        out.update(session_fields(session))
    else:
        out.setdefault("mcp_calls", 0)
    if cache is not None and not out.get("cache"):
        out["cache"] = cache.stats()
    return out

