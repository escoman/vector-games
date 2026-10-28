#!/usr/bin/env python3
"""
measure_fire3.py — тактный профиль fire.asm в модели Вектора-06Ц.

v06_emu считает ШАГИ (число инструкций), а не такты. Здесь по трассе
(pc + opcode + снимки до/после) считаются такты Intel 8080, а затем
пересчитаны в такты Вектора таблицей wait-state из EMU80 (docs/VECTOR_VERIFIED.md):

    waits[19] = {0,0,0,0,0,3,0,1,0,0,2,5,0,3,0,0,4,7,6}   # индекс = базовых тактов
    MOV r,r: 5 → 8,  MVI: 7 → 8,  LXI: 10 → 12,  LDA/STA: 13 → 16,
    PUSH/POP: 11 → 16,  LHLD/SHLD: 16 → 20,  CALL: 17 → 24,  XTHL: 18 → 24

Кадр 50 Гц = 59 904 такт Вектора ⇒ fps = 50 / (T_кадра / 59904).

Запуск:  python3 tools/measure_fire3.py [КАДРОВ]
"""
import importlib.util
import os
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..'))
EMU = os.path.join(PROJ, 'utils', 'emulator', 'v06_emu.py')

spec = importlib.util.spec_from_file_location('v06_emu', EMU)
emu_mod = importlib.util.module_from_spec(spec)
sys.modules['v06_emu'] = emu_mod
spec.loader.exec_module(emu_mod)
Emulator8080 = emu_mod.Emulator8080
SENTINEL = emu_mod.SENTINEL

SP = 0x7FF0
POWER = 153
FRAME_T = 59904                     # тактов Вектора на кадр 50 Гц
WAITS = (0, 0, 0, 0, 0, 3, 0, 1, 0, 0, 2, 5, 0, 3, 0, 0, 4, 7, 6)

_3BYTE = {0x01, 0x11, 0x21, 0x31,
          0x22, 0x2A, 0x32, 0x3A,
          0xCD, 0xC3,
          0xC2, 0xCA, 0xD2, 0xDA, 0xE2, 0xEA, 0xF2, 0xFA,
          0xC4, 0xCC, 0xD4, 0xDC}
_2BYTE = {0x06, 0x0E, 0x16, 0x1E, 0x26, 0x2E, 0x36, 0x3E,
          0xC6, 0xCE, 0xD6, 0xDE, 0xE6, 0xEE, 0xF6, 0xFE}


def ilen(op):
    if op in _3BYTE:
        return 3
    if op in _2BYTE:
        return 2
    return 1


def cycles(op, taken):
    """Базовые такты Intel 8080 (без wait-state Вектора)."""
    hi, lo = op >> 6, op & 7
    if op in (0x3A, 0x32):            # LDA abs / STA abs
        return 13
    if op in (0x2A, 0x22):            # LHLD abs / SHLD abs
        return 16
    if op == 0xE3:                    # XTHL
        return 18
    if op == 0xEB:                    # XCHG
        return 4
    if op == 0xF9:                    # SPHL
        return 5
    if op == 0x00:
        return 4
    if op == 0x76:
        return 7
    if 0x40 <= op <= 0x7F:
        if lo == 6:
            return 7                  # MOV r,M
        if (op >> 3) & 7 == 6:
            return 7                  # MOV M,r
        return 5                      # MOV r,r'
    if 0x80 <= op <= 0xBF:
        return 7 if lo == 6 else 4    # ALU M : ALU r
    if hi == 0:
        return {1: 10, 2: 7, 3: 5,
                4: 10 if (op >> 3) & 7 == 6 else 5,
                5: 10 if (op >> 3) & 7 == 6 else 5,
                6: 10 if (op >> 3) & 7 == 6 else 7,
                9: 10}.get(lo, 4)
    if hi == 3:
        return {0: 11 if taken else 5,
                1: 10,                 # POP
                2: 10 if taken else 7,  # J cond
                3: 10 if op == 0xC3 else 17,   # JMP : CALL
                4: 17 if taken else 11,  # CALL cond
                5: 11,                 # PUSH
                6: 7,                  # ALU imm
                7: 11}.get(lo, 4)      # RST
    return 4


def vcycles(base):
    """Такты Вектора-06Ц: базовые + wait-state по таблице EMU80."""
    return base + (WAITS[base] if base < len(WAITS) else 0)


def category(op):
    hi, lo = op >> 6, op & 7
    if op in (0x22, 0x2A, 0x32, 0x3A):
        return "память-абс (LDA/STA 13→16, LHLD/SHLD 16→20)"
    if op in (0x02, 0x12, 0x0A, 0x1A) or op == 0xE3:
        return "косвенные (STAX/LDAX 7→8, XTHL 18→24)"
    if 0x40 <= op <= 0x7F and (lo == 6 or (op >> 3) & 7 == 6):
        return "косвенные (STAX/LDAX 7→8, XTHL 18→24)"
    if op in (0x09, 0x19, 0x29, 0x39):
        return "DAD (10→12)"
    if hi == 3 and lo in (0, 2, 3) and op != 0xC9:
        return "переходы (JMP/Jc)"
    if op == 0xC9:
        return "переходы (JMP/Jc)"
    if op == 0xCD or (hi == 3 and lo == 4):
        return "вызовы (CALL/CALLc)"
    if hi == 3 and lo in (1, 5):
        return "стек (PUSH/POP 11→16)"
    if 0x80 <= op <= 0xBF or (op in _2BYTE and lo == 6):
        return "ALU (cmp/add/sub/ani 4→4, 7→8)"
    if 0x40 <= op <= 0x7F:
        return "MOV r,r (5→8)"
    if lo in (4, 5) and hi != 3:
        return "INR/DCR (5→8)"
    if lo == 3:
        return "INX/DCX (5→8)"
    if lo == 1:
        return "LXI (10→12)"
    if lo == 6 and hi != 3:
        return "MVI (7→8)"
    return "прочее"


def profile_call(emu, entry, args=()):
    cpu = emu.setup_call(entry, args=args, sp=SP)
    cpu.trace_enabled = True
    cpu.run_until(max_steps=5_000_000, stop_pc=SENTINEL)
    cpu.trace_enabled = False
    n = intel = vec = 0
    cat_v = Counter()
    cat_n = Counter()
    op_v = Counter()
    op_n = Counter()
    for e in cpu.trace:
        op = e['opcode']
        pre, post = e['pre'], e['post']
        L = ilen(op)
        taken = post['pc'] != pre['pc'] + L
        base = cycles(op, taken)
        v = vcycles(base)
        n += 1
        intel += base
        vec += v
        k = category(op)
        cat_v[k] += v
        cat_n[k] += 1
        op_v[op] += v
        op_n[op] += 1
    return n, intel, vec, cat_v, cat_n, op_v, op_n


def report(title, n, intel, vec, cat_v, cat_n, op_v, op_n, frames):
    print("\n=== %s ===" % title)
    print("инструкций: %s   Intel T: %s   Вектор T: %s   T/инстр: %.2f"
          % (format(n // frames, ','), format(intel // frames, ','),
             format(vec // frames, ','), vec / n))
    print("доля кадра (Вектор T / 59904): %.2f" % (vec / frames / FRAME_T))
    print("разбивка по категориям:")
    for k, v in sorted(cat_v.items(), key=lambda kv: -kv[1]):
        print("  %10s  %5.1f%%  x%-8s %s"
              % (format(v // frames, ','), 100.0 * v / vec,
                 format(cat_n[k] // frames, ','), k))
    print("top-10 опкодов по тактам Вектора:")
    for op, v in sorted(op_v.items(), key=lambda kv: -kv[1])[:10]:
        print("  %10s  %5.1f%%  x%-8s %02X len=%d base=%dT vec=%dT"
              % (format(v // frames, ','), 100.0 * v / vec,
                 format(op_n[op] // frames, ','), op, ilen(op),
                 cycles(op, True), vcycles(cycles(op, True))))


def main():
    frames = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    emu = Emulator8080()
    emu.load_asm(os.path.join(HERE, '..', 'fire.asm'))
    emu.call('_rnd_init', sp=SP, max_steps=5_000_000)

    tot = {'n': 0, 'i': 0, 'v': 0}
    store = {}
    for name, args in (('_fire_generate', (POWER,)), ('_fire_paint', (0,)),
                       ('_fire_paint', (1,))):
        key = name + ('/A' if args[0] == 0 else ('/B' if name == '_fire_paint' else ''))
        acc = [Counter(), Counter(), Counter(), Counter()]
        n = i = v = 0
        for _ in range(frames):
            r = profile_call(emu, name, args=args)
            n += r[0]; i += r[1]; v += r[2]
            acc[0] += r[3]; acc[1] += r[4]; acc[2] += r[5]; acc[3] += r[6]
        store[key] = (n, i, v, acc[0], acc[1], acc[2], acc[3])
        report('%s  (%d кадр.)' % (key, frames), n, i, v,
               acc[0], acc[1], acc[2], acc[3], frames)

    g = store['_fire_generate']
    p = store['_fire_paint/A']
    frame_v = (g[2] + p[2]) / frames
    print("\n--- ИТОГ на кадр (один flip: generate + paint) ---")
    print("generate: %s Вектор T   paint: %s Вектор T   кадр: %s Вектор T"
          % (format(int(g[2] / frames), ','), format(int(p[2] / frames), ','),
             format(int(frame_v), ',')))
    print("кадров 50 Гц на один flip: %.2f     скорость: %.1f fps"
          % (frame_v / FRAME_T, 50.0 / (frame_v / FRAME_T)))
    print("справка: fire2 — ~2.4M T / flip ⇒ ~1.2 fps")


if __name__ == '__main__':
    main()
