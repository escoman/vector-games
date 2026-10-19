#!/usr/bin/env python3
"""Stage 17: явный `size` для всех функций (Phase C — размеры по CFG-границам).

Вход: CODE ∪ RDB = 100.00%, но **208 из 233 функций с `size=0`** (RDB-extents
покрытие мало, `measure_sizes` даёт сотни `size-unknown`). Цель — проставить
каждой функции честную длину тела, чтобы (а) сработал acceptance-критерий
«у каждой функции стоит size», (б) поднялось RDB-extents покрытие, (в) ушли
расхождения `measure_sizes`.

Метод границы (то же ядро, что `analyze.measure_sizes`, без правок RDB):
  * одна линейная разборка образа `disassemble_image` → карта `адрес → размер
    инструкции` (декодирует отладчик; Python лишь складывает длины);
  * граница функции = старт **следующего РЕАЛЬНЫЙ объект** (function/data/table/
    string/variable); `label`-объекты — внутренние цели переходов, границу НЕ
    задают (входят в тело функции);
  * `size` = сумма длин целых инструкций от entry до границы (`decode_extent`);
    остановка на разрыве карты (конец линейной разборки) — не переводим байты
    через границу данных.

Почему round-trip безопасен: `asm/code.asm` — линейный вывод экспортёра
(`v06c-asm-export`), по одному байту на адрес окна; классификация код↔DEFB
задают **data-объекты**, а не declared size функции. Мы НЕ меняем типы и НЕ
посягаем на чужие extent (ограничены следующим реальным объектом) → layout
неподвижен → `make verify` обязан остаться byte-for-byte (оракул).

Usage:
    PYTHONPATH=utils python3 roms/redesign/basic/tools/stage17_function_sizes.py --check
    PYTHONPATH=utils python3 roms/redesign/basic/tools/stage17_function_sizes.py --apply
"""
from __future__ import annotations

import argparse
import os
import sys

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

# Типы, задающие реальную границу региона (label — внутри тела, не граница).
BOUNDARY_TYPES = ("function", "data", "table", "string", "variable")
CODE_TYPES = ("function", "code")


def instruction_map(instructions):
    return {item.address: int(item.size or 1) for item in instructions}


def walk(instructions, limit):
    """Сумма длин целых инструкций, не пересекающих limit (start выровнен).

    instructions — разборка ОТ САМОГО entry (per-entry disassemble_range),
    поэтому 1-я инструкция начинается ровно по адресу функции. Кладём только
    те инструкции, чей конец <= limit: чужой объект (даже на 1 байт) не
    затрагивается — extent гарантированно без наложений.
    """
    total = 0
    reached = True
    for ins in instructions:
        nxt = total + int(ins.size or 1)
        if nxt > limit:
            reached = False
            break
        total = nxt
    return total, reached


def next_boundaries(rdb):
    """addr -> адрес следующего РЕАЛЬНОГО объекта (label — не граница)."""
    ordered = sorted(rdb.objects, key=lambda o: o.address)
    nb = {}
    carry = HI + 1
    for obj in reversed(ordered):
        nb[obj.address] = carry
        if obj.type in BOUNDARY_TYPES:
            carry = obj.address
    return nb


def compute_sizes(rdb, analysis):
    """[(addr, name, old_size, new_size, reached)] только для функций с size=0.

    Размер — per-entry линейная разборка от entry до следующего реального
    объекта (рекомендация ТЗ: точные длины по отдельному диапазону, а не по
    одному большому вызову — глобальная разборка может разойтись с entry).
    """
    nb = next_boundaries(rdb)
    out = []
    for obj in sorted(rdb.objects, key=lambda o: o.address):
        if obj.type not in CODE_TYPES or obj.size_known:
            continue                              # не функция или размер уже честный
        limit = min(nb.get(obj.address, HI + 1), HI + 1)
        window = limit - obj.address
        if window <= 0:
            out.append((obj.address, obj.name, obj.size, 0, False))
            continue
        ins = analysis.disassemble_range(obj.address, window)
        extent, reached = walk(ins, window)
        # Если целая инструкция в окно не влезла (тесный сосед/шум), берём
        # первую инструкцию РОВНО если она не пересекает limit — иначе overlap.
        if extent <= 0 and ins and int(ins[0].size or 1) <= window:
            extent, reached = int(ins[0].size or 1), False
        out.append((obj.address, obj.name, obj.size, extent, reached))
    return out


# ---- check / apply ------------------------------------------------------
def cmd_check(session, rdb, analysis):
    rows = compute_sizes(rdb, analysis)
    zero = [r for r in rows if r[3] == 0]
    reach = sum(1 for r in rows if r[4])
    tot_new = sum(r[3] for r in rows)
    print("Stage 17 plan — функции с size=0: %d" % len(rows))
    for addr, name, old, new, reached in rows:
        flag = "OK " if reached else "PART" if new else "ZERO"
        print("  %s %-32s [%s] size %2s -> %-4s (%s)"
              % (addr_hex(addr), name, flag, old, new,
                 "до границы" if reached else ("до разбора" if new else "нет входа в разборку")))
    print("\nитог: к записи %d, из них full-to-boundary %d; zero-extent(пропуск) %d; "
          "суммарно байт extent = %d" % (len(rows), reach, len(zero), tot_new))
    return rows


def cmd_apply(session, rdb, analysis, writer):
    rows = compute_sizes(rdb, analysis)
    log, skipped = [], []
    for addr, name, old, new, reached in rows:
        if new <= 0:
            skipped.append((addr, name, "entry не на границе линейной разборки"))
            continue
        obj = rdb.by_addr(addr)
        writer.ensure_object(addr, obj.name, obj.type, size=new)
        writer.set_property(addr, "size_source",
                            "stage17_linear_decode%s" % ("" if reached else "_partial"))
        log.append("%s: %s size %d -> %d (%s)" % (
            addr_hex(addr), obj.name, old, new,
            "full" if reached else "partial-to-disasm-end"))
    writer.save()
    for line in log:
        print("  " + line)
    for addr, name, why in skipped:
        print("  SKIP %s %s — %s" % (addr_hex(addr), name, why))
    print("summary: %s" % (writer.summary(),))
    info = session.call("debug_get_rdb_info")
    print("objects: %s, dirty: %s" % (info.get("object_count"), info.get("dirty")))
    return len(log), len(skipped)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--rom", default=DEFAULT_ROM)
    ap.add_argument("--rdb", default=DEFAULT_RDB)
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args(argv)
    if not (args.check or args.apply):
        args.check = True

    rdb_path = os.path.abspath(args.rdb)
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
        if args.check:
            cmd_check(session, rdb, analysis)
            return 0
        writer = RdbWriter(session)
        cmd_apply(session, rdb, analysis, writer)
        return 0
    finally:
        session.close()


if __name__ == "__main__":
    sys.exit(main())
