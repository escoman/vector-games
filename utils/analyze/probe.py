"""Канонический чистый запуск ROM и сбор runtime-доказательств (ТЗ §14, §15, §16).

Почему `debug_load_rom`, а не `debug_reset` (ТЗ §14):

    debug_reset != clean ROM boot

Сброс в отладчике не переносит ROM в 0x0100 и не инициализирует плату с нуля:
после `debug_reset` процессор попадает в тот же образ, что уже лежит в памяти,
`sp` остаётся от предыдущего запуска (у putup — 0xDCEC), и первые кадры
проваливаются в busy-wait опрос клавиатуры (`OUT 1C` / `IN 1B`). Прогон после
reset даёт доказательства, которые нельзя приравнять к старту игры.

Поэтому единственный канонический вход в рантайм — `RomRun.boot()`:

    debug_load_rom → (запись снапшота «до») → debug_run → ожидание →
    debug_pause → сбор доказательств

Runtime-наблюдения — это ЕЩЁ НЕ RDB-объекты и не факты (ТЗ §15): они
складируются в кэш как evidence, а семантику назначает AI.
"""
from __future__ import annotations

import argparse
import json
import sys
import time

from analyze.capabilities import CapabilityProfile
from analyze.mcp_session import addr_hex, envelope, open_session, to_addr

# 50 Гц → кадр ~20 мс. Кадровый счётчик в состоянии CPU не отдаётся, поэтому
# ожидание считается в стенд-тайме (эмулятор идёт в реальном времени).
FRAME_SECONDS = 1.0 / 50.0

EVIDENCE_TOOLS = (
    ("cpu", "debug_get_cpu_state"),
    ("state", "debug_get_state"),
    ("memory_access_map", "debug_get_memory_access_map"),
    ("memory_access_log", "debug_get_memory_access_log"),
    ("io_trace", "debug_get_io_trace"),
    ("screen", "debug_get_screen_info"),
    ("vram", "debug_get_vram_info"),
    ("symbols", "debug_get_symbols"),
)


class RomRun:
    """Один прогон ROM в долгоживущей сессии."""

    def __init__(self, session, cache=None, rom=None, org=0x0100, caps=None):
        self.session = session
        self.cache = cache
        self.rom = rom
        self.org = to_addr(org)
        self.caps = caps or CapabilityProfile.from_session(session)
        self.events = []
        self.key_names = None

    # -- загрузка и старт --------------------------------------------------

    def boot(self, snapshot_before=True, note=None):
        """Чистая загрузка ROM (ТЗ §14). Возвращает словарь доказательств старта."""
        if not self.rom:
            raise ValueError("RomRun: не указан путь к ROM")
        loaded = self.session.load_rom(self.rom, org=self.org)
        before = self.snapshot("pre_run") if snapshot_before else None
        out = {
            "loaded": loaded,
            "org": addr_hex(self.org),
            "state_at_entry": self._evidence("debug_get_state", {}, tag="boot_state"),
            "pre_boot_snapshot": before,
        }
        if note:
            out["note"] = note
        self.events.append({"event": "boot", "at": round(time.time(), 3)})
        return out

    def run(self):
        self.session.call("debug_run")
        self.events.append({"event": "run", "at": round(time.time(), 3)})

    def pause(self):
        self.session.call("debug_pause")
        state = self._evidence("debug_get_state", {}, tag="pause_state")
        self.events.append({"event": "pause", "at": round(time.time(), 3),
                            "pc": (state.get("cpu") or {}).get("pc")})
        return state

    def step(self, count=1):
        for _ in range(int(count)):
            self.session.call("debug_step")
        return self._evidence("debug_get_state", {}, tag="step")

    def wait(self, seconds=None, frames=None):
        """Ожидание в стенд-тайме; кадр = 20 мс (50 Гц)."""
        if frames is not None:
            seconds = frames * FRAME_SECONDS
        seconds = float(seconds or 0)
        if seconds > 0:
            time.sleep(seconds)
        self.events.append({"event": "wait", "seconds": round(seconds, 3)})
        return seconds

    def keys(self, sequence):
        """Клавиатурные события: [(задержка, имя_клавиши), …].

        Имена берёт `debug_list_keys` — своих кодов клавиш модуль не изобретает.
        """
        if self.key_names is None:
            listed = self._evidence("debug_list_keys", {}, tag="keys")
            self.key_names = sorted(available_keys(listed))
        played = []
        for delay, key in sequence or []:
            if delay:
                self.wait(delay)
            if key not in self.key_names:
                raise ValueError("клавиша %r есть? нет. Доступно: %s"
                                 % (key, ", ".join(self.key_names[:12]) + "…"))
            self.session.call("debug_type_key", {"key": key})
            played.append(key)
        return played

    def scenario(self, seconds=1.0, key_sequence=None, pause_after=True):
        """Полный канон: boot → run → (клавиши по таймингу) → пауза."""
        self.boot()
        self.run()
        if key_sequence:
            self.keys(key_sequence)
        self.wait(seconds)
        return self.pause() if pause_after else {}

    # -- доказательства ----------------------------------------------------

    def snapshot(self, name, address=0x0000, size=0x8000):
        """Снапшот памяти; id возвращает сервер, имя — для человека.

        Снапшоты — часть доказательств (ТЗ §15), сравнивает их `memory_diff`.
        """
        payload = self.session.call("debug_create_memory_snapshot",
                                    {"address": to_addr(address), "size": int(size)})
        payload["name"] = name
        return payload

    def evidence(self, label="runtime", trace_entries=2000, log_entries=2000):
        """Собрать полный runtime-набор (ТЗ §15).

        Всё идёт через кэш, но с обязательным пересъёмом отпечатка рантайма:
        после pause() состояние изменилось, и кэшировать его под старым
        ключом нельзя.
        """
        out = {"label": label, "events": list(self.events)}
        for key, tool in EVIDENCE_TOOLS:
            if not self.caps.has(tool):
                out[key] = {"missing_capability": tool}
                continue
            args = {}
            if tool in ("debug_get_execution_trace", "debug_get_memory_access_log",
                        "debug_get_io_trace"):
                args["max_entries"] = trace_entries
            if tool == "debug_get_symbols":
                args["limit"] = 400
            result, envelope = self._raw(tool, args)
            out[key] = result
            out.setdefault("evidence_ids", {})[key] = envelope.get("evidence_id")
        out["cpu"] = out.get("cpu") or out.get("state")
        return out

    def hit_profile(self, addresses, rounds=1, note=None):
        """Профиль попаданий в точки останова: адрес → регистры (ТЗ §19 dynamic).

        Для каждой точки: поставить → пустить CPU → на попадании снять регистры
        и трассу → снять точку. Интерпретации нет: это наблюдения, из которых
        `abi_scan` соберёт кандидатов параметров.
        """
        profile = []
        for addr in [to_addr(a) for a in addresses]:
            for _round in range(int(rounds) or 1):
                self.session.call("debug_set_breakpoint", {"address": addr})
                try:
                    self.session.call("debug_run")
                    state = self.session.call("debug_get_state")
                    cpu = state.get("cpu") or {}
                    hit = {
                        "breakpoint": addr_hex(addr),
                        "pc": cpu.get("pc"),
                        "sp": cpu.get("sp"),
                        "registers": {k: cpu.get(k) for k in
                                      ("a", "b", "c", "d", "e", "h", "l", "flags")},
                        "running": state.get("running"),
                        "current_function": state.get("current_function"),
                        "round": _round,
                    }
                    trace = self.session.call("debug_get_execution_trace",
                                              {"max_entries": 8})
                    hit["trace"] = trace.get("events") or trace.get("entries") or []
                    if note:
                        hit["note"] = note
                    profile.append(hit)
                finally:
                    self.session.call("debug_remove_breakpoint", {"address": addr})
                if self.stopped_after_hit(state):
                    break
        return profile

    @staticmethod
    def stopped_after_hit(state):
        """CPU после снятия точки не идёт — повторного замера не нужно."""
        return not (state or {}).get("running", False)

    # -- внутреннее --------------------------------------------------------

    def _raw(self, tool, args, tag=None):
        if self.cache is None:
            return self.session.call(tool, args), {"evidence_id": None}
        result, envelope = self.cache.get_or_call(self.session, tool, args,
                                                 stamp="auto", source="RUNTIME")
        return result, envelope

    def _evidence(self, tool, args, tag=None):
        result, _ = self._raw(tool, args, tag)
        return result


def available_keys(listed):
    """Имена клавиш из ответа `debug_list_keys`.

    Сервер отдаёт список словарей {name, scancode, description, modifier};
    голая строка тоже допускается, чтобы не развалиться на другом сервере.
    """
    if isinstance(listed, dict):
        listed = listed.get("keys") or listed.get("list") or []
    names = []
    for item in listed or []:
        if isinstance(item, dict):
            name = item.get("name")
            if name:
                names.append(str(name))
        elif item is not None:
            names.append(str(item))
    return names


def key_table(listed):
    """Имя → Полная запись клавиши (scancode/modifier) для отчётов."""
    if isinstance(listed, dict):
        listed = listed.get("keys") or []
    out = {}
    for item in listed or []:
        if isinstance(item, dict) and item.get("name"):
            out[str(item["name"])] = item
    return out


def run_for(session, cache=None, rom=None, org=0x0100, seconds=1.0, keys=None,
            caps=None, pause=True):
    """Хелпер CLI: канонический прогон и готовый RomRun.

    Нужен всем модулям, которые читают RUNTIME: без запуска ROM RAM пуста,
    и наивный `--runtime` вернул бы нули вместо глифов и таблиц.
    """
    run = RomRun(session, cache, rom=rom, org=org, caps=caps)
    run.scenario(seconds=seconds, key_sequence=keys, pause_after=pause)
    return run


def parse_key_specs(specs):
    """'0.5:SPACE' → (0.5, 'SPACE')."""
    out = []
    for item in specs or []:
        delay, _, key = str(item).partition(":")
        out.append((float(delay) if delay else 0.0, key))
    return out


def main(argv=None):
    parser = argparse.ArgumentParser(prog="analyze.probe",
                                     description="Чистый запуск ROM и runtime-доказательства")
    parser.add_argument("--rom", required=True)
    parser.add_argument("--org", type=lambda s: int(s, 0), default=0x0100)
    parser.add_argument("--seconds", type=float, default=1.0,
                        help="время работы эмулятора (50 Гц ⇒ 1 с = 50 кадров)")
    parser.add_argument("--key", action="append", default=[],
                        help="клавиша через задержку: '0.5:SPACE' (повторяемо)")
    parser.add_argument("--snapshot", action="store_true",
                        help="снять снапшоты памяти до/после прогона")
    parser.add_argument("--list-keys", action="store_true", help="показать имена клавиш")
    parser.add_argument("--cache", default=None)
    parser.add_argument("--server", default=None)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    session, cache = open_session(rom=args.rom, org=args.org, server=args.server,
                                  cache_dir=args.cache)
    try:
        run = RomRun(session, cache, rom=args.rom, org=args.org)
        if args.list_keys:
            listed = session.call("debug_list_keys")
            print(json.dumps({"count": len(available_keys(listed)),
                              "keys": key_table(listed)}, ensure_ascii=False,
                             indent=2 if args.json else None))
            return 0
        sequence = parse_key_specs(args.key)
        boot = run.boot(snapshot_before=args.snapshot)
        session.call("debug_run")
        if sequence:
            run.keys(sequence)
        run.wait(args.seconds)
        paused = run.pause()
        evidence = run.evidence("probe")
        if args.snapshot:
            evidence["snapshot_after"] = run.snapshot("post_run")
        out = {
            "boot": boot,
            "paused_at": (paused.get("cpu") or {}).get("pc"),
            "current_function": paused.get("current_function"),
            "evidence": evidence,
        }
        # Статус OK — это факт о рантайме: эмулятор так себя и повёл.
        # Про образ ROM из этого ничего не следует (ТЗ §17).
        out = envelope(out, module="probe", session=session, cache=cache,
                       status="OK",
                       verdict="чистый старт: пауза на %s через %.1f с (%s)"
                               % (out["paused_at"], args.seconds,
                                  out["current_function"] or "вне функции"),
                       note="наблюдение рантайма; факты о образе — из "
                            "ROM-изображения и RDB")
        print(json.dumps(out, ensure_ascii=False, indent=2 if args.json else None,
                         default=str))
    finally:
        session.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
