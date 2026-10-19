#!/usr/bin/env python3
"""Stage 18: семантика функций — params/calls/links + обоснованные rename (Phase C).

Вход: все функции имеют `size` (Stage17). Цель: у КАЖДОЙ функции — `params`
(регистровый ABI: вход/выход/сохраняемые), `calls` + RDB-связи (call-graph →
debug_add_rdb_link, чтобы диспетчер ↔ обработчики были сшиты), `reads`/`writes`
абсолютных ячеек; и снять `func_XXXX`-имя там, где семантика ДОКАЗАНА.

Источники доказательств (всё — от отладчика, не догадки):
  * `debug_get_function_context(addr)` → instructions[], callees, callers,
    memory_reads/writes, stack_behavior;
  * `analyze.abi_scan.static_signature(instructions)` → кандидаты входа/выхода
    (регистр читается до любой записи = вход; пишется в конце = выход; PUSH∩POP
    = сохраняемые; LDA/STA/LHLD/SHLD с abs-адресом = аргумент через память).
    Это CANDIDATE-статика по листингу — честный ABI-профиль тела функции.

Связи: для каждого callee резолвим покрывающий RDB-объект (`Rdb.at`) и вешаем
`debug_add_rdb_link(func → объект)`. Хвостовые `JMP`/`RST`-цели тоже берутся из
текста инструкций (call-graph отладчика ловит не всё).

Rename: только из `RENAME_MAP` (ниже) — адрес → имя, для функций, чья роль
подтверждена структурой вызовов/телом. Остальные `func_XXXX` остаются с
`size`+`params`+`calls` (ТЗ §61: нехватка доказательств ⇒ имя не снимаем, это
не блокирует атрибуцию).

Round-trip: имена/свойства/связи не двигают байты (`make verify` — оракул).

Usage:
    PYTHONPATH=utils python3 roms/redesign/basic/tools/stage18_function_semantics.py --check
    PYTHONPATH=utils python3 roms/redesign/basic/tools/stage18_function_semantics.py --apply
"""
from __future__ import annotations

import argparse
import os
import re
import sys

from analyze.abi_scan import static_signature
from analyze.capabilities import CapabilityProfile
from analyze.disassembly import StaticAnalysis
from analyze.mcp_session import addr_hex, open_session, to_addr
from analyze.rdb import Rdb, RdbWriter

HERE = os.path.dirname(os.path.abspath(__file__))
MODULE = os.path.dirname(HERE)
REPO = os.path.dirname(os.path.dirname(os.path.dirname(MODULE)))
DEFAULT_ROM = os.path.join(MODULE, "src", "basic.r0m")
DEFAULT_RDB = os.path.join(MODULE, "src", "basic.rdb")
LO, HI = 0x0000, 0x42FF

# Целевые rename (адрес → (новое_имя, доказательство)). Пополняется по мере
# вскрытия; пустой = чисто mechanical pass (params/calls/links для всех).
RENAME_MAP = {
    0x00A1: ("func_print_packed_string",
             "обход HL до байта с bit7=1; каждый символ -> ANI 7F -> CALL 1C95 "
             "(func_putchar); вызывается с LXI H,msg (напр. 0x2544) — печать "
             "упакованного строкового сообщения"),
    0x031F: ("func_is_delimiter",
             "CPI-веер на 20/3A/2C/3B/22 (SPC ':' ',' ';' '\"') -> RZ при "
             "совпадении: предикатор разделителя токенов/аргументов"),
}

# instr-text парсер целей переходов: CALL/JMP/RST + hex-операнд.
TARGET_RE = re.compile(r"\b(?:call|jmp)\s+([0-9A-Fa-f]{2,4})\b", re.I)
RST_VECTORS = {0: 0x0000, 1: 0x0008, 2: 0x0010, 3: 0x0018,
               4: 0x0020, 5: 0x0028, 6: 0x0030, 7: 0x0038}
RST_RE = re.compile(r"\brst\s+([0-7])\b", re.I)


def resolve_obj(rdb, addr):
    """Покрывающий объект; предпочитаем function/label на самом адресе."""
    exact = rdb.by_addr(addr)
    if exact:
        return exact
    return rdb.at(addr)


def collect_targets(instructions):
    """Множество адресов-целей из текстов инструкций (CALL/JMP/RST)."""
    out = set()
    for ins in instructions:
        text = (ins.get("text") or "").split(";")[0]
        for m in TARGET_RE.finditer(text):
            try:
                out.add(int(m.group(1), 16))
            except ValueError:
                pass
        for m in RST_RE.finditer(text):
            out.add(RST_VECTORS[int(m.group(1))])
    return out


def build_plan(session, rdb, analysis, writer_dry):
    """[(addr, name, params_str, reads, writes, [callee_objs], rename_or_None)]."""
    plan = []
    for obj in sorted(rdb.of_type("function", "code"), key=lambda o: o.address):
        addr = obj.address
        ctx = session.call("debug_get_function_context", {"address": addr})
        ins = ctx.get("instructions") or []
        static = static_signature(ins, LO, HI)
        ins_regs = sorted({i["register"] for i in static["inputs"]})
        out_regs = sorted({o["register"] for o in static["outputs"]})
        saved = static["saved_registers"]
        params = "in[%s] out[%s] saves[%s]" % (
            ",".join(ins_regs), ",".join(out_regs), ",".join(saved))
        reads = sorted({m["address"] for m in static["memory_arguments"]
                        if m["access"] == "read"})
        writes = sorted({m["address"] for m in static["memory_arguments"]
                         if m["access"] == "write"})
        # callee → объекты (из call-graph отладчика + текстов переходов)
        raw_targets = set()
        for callee in (ctx.get("callees") or []):
            try:
                raw_targets.add(to_addr(callee))
            except Exception:                                    # noqa: BLE001
                pass
        raw_targets |= collect_targets(ins)
        callees, seen = [], set()
        for t in raw_targets:
            if t == addr:
                continue
            tgt = resolve_obj(rdb, t)
            if tgt and tgt.address not in seen:
                seen.add(tgt.address)
                callees.append(tgt)
        newname = RENAME_MAP.get(addr, (None, None))[0]
        plan.append((addr, obj.name, params, reads, writes, callees, newname))
    return plan


def apply_plan(rdb, plan, writer):
    log = []
    n_params = n_links = n_renames = 0
    for addr, name, params, reads, writes, callees, newname in plan:
        obj = rdb.by_addr(addr)
        if newname:
            writer.ensure_object(addr, newname, obj.type, size=obj.size,
                                 rename=True)
            writer.set_property(addr, "semantic_evidence", RENAME_MAP[addr][1])
            n_renames += 1
        writer.set_property(addr, "params", params)
        writer.set_property(addr, "calls",
                            [addr_hex(c.address) for c in callees][:24])
        if reads:
            writer.set_property(addr, "reads", reads[:24])
        if writes:
            writer.set_property(addr, "writes", writes[:24])
        n_params += 1
        for tgt in callees:
            writer.add_link(addr, tgt.address)
            n_links += 1
    writer.save()
    log.append("params=%d links=%d renames=%d" % (n_params, n_links, n_renames))
    return log


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--rom", default=DEFAULT_ROM)
    ap.add_argument("--rdb", default=DEFAULT_RDB)
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args(argv)
    if not (args.check or args.apply):
        args.check = True

    rom_path = args.rom if os.path.isabs(args.rom) else os.path.join(REPO, args.rom)
    rdb_path = args.rdb if os.path.isabs(args.rdb) else os.path.join(REPO, args.rdb)

    session, cache = open_session(rom=rom_path, org=LO)
    try:
        info = session.call("debug_get_rdb_info")
        if os.path.abspath(info.get("path") or "") != rdb_path:
            raise SystemExit("RDB in session %r, expected %r"
                             % (info.get("path"), rdb_path))
        caps = CapabilityProfile.from_session(session)
        analysis = StaticAnalysis(session, cache=cache, caps=caps)
        rdb = Rdb.load(rdb_path)
        plan = build_plan(session, rdb, analysis, args.check)
        if args.limit:
            plan = plan[:args.limit]
        if args.check:
            tot_links = sum(len(p[5]) for p in plan)
            print("Stage 18 plan — функций: %d, связей (calls→links): %d, "
                  "rename: %d" % (len(plan), tot_links,
                                  sum(1 for p in plan if p[6])))
            for addr, name, params, reads, writes, callees, newname in plan:
                tag = " → %s" % newname if newname else ""
                print("  %s %s%s" % (addr_hex(addr), name, tag))
                print("        %s  callees=%s r/w=%d/%d"
                      % (params, len(callees), len(reads), len(writes)))
            return 0
        writer = RdbWriter(session)
        for line in apply_plan(rdb, plan, writer):
            print("  " + line)
        print("summary: %s" % (writer.summary(),))
        info = session.call("debug_get_rdb_info")
        print("objects: %s, links: %s, dirty: %s"
              % (info.get("object_count"), info.get("link_count"), info.get("dirty")))
        return 0
    finally:
        session.close()


if __name__ == "__main__":
    sys.exit(main())
