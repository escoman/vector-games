#!/usr/bin/env python3
"""measure_cycles.py — ТАКТОВЫЙ (T-state) профиль fire.asm, а не счётчик инструкций.

v06_emu.py считает ШАГИ (число инструкций, steps+=1), поэтому замена `lda abs`
(3 байта, 7 T) на `mov r,r` (1 байт, 5 T) в его метрике вообще не видна. Этот
скрипт прогоняет изолированные вызовы _fire_generate / _fire_render, снимает
трассу (pc + opcode + снимки регистров до/после) и суммирует настоящие такты
Intel 8080 по таблице длин и циклов для того набора опкодов, что реально
исполняется. Условные переходы/вызовы/возвраты корректируются по факту взятия
(post.pc != pre.pc + len).

Вывод: для каждой функции — полные такты/кадр, среднее T на инструкцию и
разбивка по категориям (прямой доступ к памяти / косвенный / рег. арифметика /
переходы / стек), плюс хистотопоп-20 опкодов для аудита.

Запуск:  python3 measure_cycles.py [КАДРОВ]
"""
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import verify_fire_asm as V  # noqa: E402  (патчит ассемблер + даёт константы/Ref)
from v06_emu import Emulator8080, SENTINEL  # noqa: E402


# ---------------- длина инструкции (8080) ----------------
_3BYTE = {0x01, 0x11, 0x21, 0x31,          # LXI rp,d16
          0x22, 0x2A, 0x32, 0x3A,          # SHLD/LHLD/STA/LDA abs
          0xCD, 0xC3,                       # CALL / JMP abs
          0xC2, 0xCA, 0xD2, 0xDA, 0xE2, 0xEA, 0xF2, 0xFA,   # J cond
          0xC4, 0xCC, 0xD4, 0xDC}           # CALL cond
_2BYTE = {0x06, 0x0E, 0x16, 0x1E, 0x26, 0x2E, 0x36, 0x3E,   # MVI r/M,d8
          0xC6, 0xCE, 0xD6, 0xDE, 0xE6, 0xEE, 0xF6, 0xFE}   # ALU imm


def ilen(op: int) -> int:
    if op in _3BYTE:
        return 3
    if op in _2BYTE:
        return 2
    return 1


# ---------------- такты (T-states), Intel 8080 ----------------
# taken — был ли взят условный переход/вызов/возврат.
def cycles(op: int, taken: bool) -> int:
    hi, lo = op >> 6, op & 7
    # Прямые memory-опкоды с lo==2 в блоке 0 (LDA/STA/LHLD/SHLD) НЕ равны STAX/LDAX.
    if op in (0x3A, 0x32):            # LDA abs / STA abs
        return 13
    if op in (0x2A, 0x22):            # LHLD abs / SHLD abs
        return 16
    if op == 0x00:
        return 4                     # NOP
    if op == 0x76:
        return 7                     # HLT
    if 0x40 <= op <= 0x7F:            # MOV-блок
        if op == 0x76:
            return 7
        if lo == 6:
            return 7                 # MOV r,M
        if (op >> 3) & 7 == 6:
            return 7                 # MOV M,r
        return 5                     # MOV r,r'
    if 0x80 <= op <= 0xBF:            # ALU-блок
        return 7 if lo == 6 else 4   # ALU M : ALU r
    if hi == 0:                       # блок 0
        return {0: 4,                 # (0x00 обработан) 8/10/..: NOP-подобные
                1: 10,                # LXI
                2: 7,                 # STAX (0x02/0x12); 0x22/0x32 в hi!=0
                3: 5,                 # INX
                4: 10 if (op >> 3) & 7 == 6 else 5,   # DCR M : DCR r
                5: 10 if (op >> 3) & 7 == 6 else 5,   # INR M : INR r
                6: 10 if (op >> 3) & 7 == 6 else 7,   # MVI M : MVI r
                9: 10,                # DAD (0x09/0x19/0x29/0x39)
                }.get(lo, 4)
    # hi == 3 (0xC0..0xFF) — точечно по lo
    return {
        0: 11 if taken else 5,       # RET cond
        1: 10,                        # POP
        2: 10 if taken else 7,        # J cond
        3: 10 if op == 0xC3 else 17,  # JMP : CALL
        4: 17 if taken else 11,       # CALL cond
        5: 11,                        # PUSH
        6: 7,                         # ALU imm
        7: 11,                        # RST
    }.get(lo, 4)


# ---------------- категории для разбивки ----------------
def category(op: int) -> str:
    hi, lo = op >> 6, op & 7
    if op in (0x22, 0x2A, 0x32, 0x3A):
        return "память-абс (LDA/STA/LHLD/SHLD 13/16T)"
    if op in (0x02, 0x12, 0x0A, 0x1A) or (0x40 <= op <= 0x7F and (lo == 6 or (op >> 3) & 7 == 6)):
        return "память-косв (STAX/LDAX/MOV r,M 7T)"
    if op in (0x09, 0x19, 0x29, 0x39):
        return "DAD (10T)"
    if hi == 3 and lo in (0, 2, 3, 4, 7) and op != 0xC9:
        return "переходы (JMP/Jc/CALLc/RST)"
    if op in (0xC9,):
        return "переходы (JMP/Jc/CALLc/RST)"
    if op in (0xCD,) or (hi == 3 and lo == 4):
        return "вызовы (CALL/CALLc)"
    if hi == 3 and lo in (1, 5):
        return "стек (PUSH/POP)"
    if 0x80 <= op <= 0xBF or op in _2BYTE and lo == 6:
        return "ALU (cmp/add/sub/ani/ori 4-7T)"
    if 0x40 <= op <= 0x7F:
        return "MOV r,r (5T)"
    if lo in (4, 5) and hi != 3:
        return "INR/DCR (5T)"
    if lo == 3:
        return "INX/DCX (5T)"
    if lo == 1:
        return "LXI (10T)"
    if lo == 6 and hi != 3:
        return "MVI (7T)"
    if op in (0x07, 0x0F, 0x17, 0x1F):
        return "сдвиги RLC/RRC/RAL/RAR (4T)"
    return "прочее"


def profile_call(emu, entry, args=()):
    """Возвращает (instr_count, total_cycles, Counter по категориям, Counter по опкодам).

    call() внутри делает setup_call(), который принудительно выключает трассировку
    и чистит трассу — поэтому готовим вызов через setup_call(), ВКЛЮЧАЕМ трассу после
    него и крутим run_until() до сентинела вручную.
    """
    cpu = emu.setup_call(entry, args=args, sp=V.SP)
    cpu.trace_enabled = True
    cpu.run_until(max_steps=3_000_000, stop_pc=SENTINEL)
    cpu.trace_enabled = False
    tr = cpu.trace
    n = 0
    cyc = 0
    cat_cyc = Counter()
    cat_n = Counter()
    op_hist = Counter()
    op_cyc = Counter()
    for e in tr:
        op = e["opcode"]
        pre_pc = e["pre"]["pc"]
        post_pc = e["post"]["pc"]
        L = ilen(op)
        taken = post_pc != pre_pc + L
        c = cycles(op, taken)
        n += 1
        cyc += c
        k = category(op)
        cat_cyc[k] += c
        cat_n[k] += 1
        op_hist[op] += 1
        op_cyc[op] += c
    return n, cyc, cat_cyc, cat_n, op_hist, op_cyc


def report(title, n, cyc, cat_cyc, cat_n, op_hist, op_cyc):
    print(f"\n=== {title} ===")
    print(f"инструкций: {n:,}   тактов: {cyc:,}   среднее T/инстр: {cyc / n:.2f}")
    print("разбивка по категориям (такты, доля):")
    for k, c in sorted(cat_cyc.items(), key=lambda kv: -kv[1]):
        print(f"  {c:>10,}  {100 * c / cyc:5.1f}%  x{cat_n[k]:<8,}  {k}")
    print("top-12 опкодов по суммарным тактам:")
    for op, c in sorted(op_cyc.items(), key=lambda kv: -kv[1])[:12]:
        print(f"  {c:>10,}  {100 * c / cyc:5.1f}%  x{op_hist[op]:<8,}  {op:02X}  "
              f"len={ilen(op)} cyc={cycles(op, True)}/{cycles(op, False)}")


def main():
    frames = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    emu = Emulator8080()
    emu.load_asm(str(HERE / "fire.asm"))
    emu.call("_rnd_init", sp=V.SP, max_steps=3_000_000)

    # аккумулируем по кадрам
    acc = {k: Counter() for k in ("gcatc", "gcatn", "gop", "gopc",
                                   "rcatc", "rcatn", "rop", "ropc")}
    g_n = g_c = r_n = r_c = 0
    for _ in range(frames):
        gn, gc, gcatc, gcatn, gop, gopc = profile_call(emu, "_fire_generate", args=(V.POWER,))
        rn, rc, rcatc, rcatn, rop, ropc = profile_call(emu, "_fire_render")
        g_n += gn; g_c += gc; r_n += rn; r_c += rc
        acc["gcatc"] += gcatc; acc["gcatn"] += gcatn; acc["gop"] += gop; acc["gopc"] += gopc
        acc["rcatc"] += rcatc; acc["rcatn"] += rcatn; acc["rop"] += rop; acc["ropc"] += ropc

    report(f"fire_generate  ({frames} кадр.)", g_n, g_c,
           acc["gcatc"], acc["gcatn"], acc["gop"], acc["gopc"])
    report(f"fire_render    ({frames} кадр.)", r_n, r_c,
           acc["rcatc"], acc["rcatn"], acc["rop"], acc["ropc"])

    print(f"\n--- ИТОГ на кадр ---")
    print(f"generate: {g_c / frames:>10,.0f} T     render: {r_c / frames:>10,.0f} T"
          f"     frame: {(g_c + r_c) / frames:>10,.0f} T"
          f"     render доля кадра: {100 * r_c / (g_c + r_c):.1f}%")


if __name__ == "__main__":
    main()
