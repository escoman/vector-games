#!/usr/bin/env python3
"""
Проб семантики флагов в эмуляторе отладки (vector-debugger). Вопрос возник на шаге
E3-6a: код «LDA flag -> MVI A,1 -> JZ» повёл себя не так, как на реальном 8080 (где
MVI флаги не меняет). Probe собирает в свободной RAM три программы и по PC на паузе
показывает, сработал ли JZ:

  C) ADI 01 ; LDA [0]=0 ; JZ good          -> LDA ставит Z?
  B) ADI 01 ; MVI A,00 ; JZ good           -> MVI сам ставит Z?
  A) ADI 01 ; LDA [0]=0 ; MVI A,01 ; JZ good -> переживёт ли Z от LDA инструкцию MVI?

good и bad — точки останова, поэтому выполнение не уезжает в мусор.
Запуск: python3 roms/games/putup/tools/probe_flags.py
"""
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.abspath(os.path.join(HERE, '..'))
ROOT = os.path.abspath(os.path.join(PROJECT, '..', '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'utils'))
from analyze.mcp_session import McpSession, to_addr  # noqa: E402

ROM = os.path.join(PROJECT, 'putup_new.rom')
CODE = 0x7F00                    # свободная RAM (ни списков, ни VRAM: 0x7F00 < 0x8000)
ZERO = 0x7F80                    # байт, который мы сами обнуляем перед прогоном
GOOD = CODE + 0x40
BAD = CODE + 0x41


def assemble(steps):
    """steps: список ('ADI'|'LDA'|'MVI'|'JZ'|'JMP'). Возвращает байты проги."""
    out = bytearray()
    for st in steps:
        op = st[0]
        if op == 'ADI':
            out += bytes([0xC6, st[1]])
        elif op == 'LDA':
            out += bytes([0x3A, st[1] & 0xFF, st[1] >> 8])
        elif op == 'MVI':
            out += bytes([0x3E, st[1]])
        elif op == 'JZ':                  # метка good: относительный переход
            rel = (GOOD - (CODE + len(out) + 2)) & 0xFF
            out += bytes([0xCA, rel])
        elif op == 'JMP':                 # метка bad: абсолютный переход
            out += bytes([0xC3, BAD & 0xFF, BAD >> 8])
        else:
            raise ValueError(op)
    return bytes(out)


def run_case(s, steps, name):
    prog = assemble(steps)
    s.call("debug_write_memory", {"address": ZERO, "data": [0x00]})
    s.call("debug_write_memory", {"address": CODE, "data": list(prog)})
    s.call("debug_clear_breakpoints", {})
    s.call("debug_set_breakpoint", {"address": GOOD})
    s.call("debug_set_breakpoint", {"address": BAD})
    s.call("debug_set_register", {"name": "PC", "value": CODE})
    s.call("debug_run")
    t0 = time.time()
    while time.time() - t0 < 15:
        if not s.call("debug_is_running").get("running"):
            break
        time.sleep(0.02)
    else:
        print(f"{name}: паузы нет за 15 с")
        return None
    pc = to_addr(s.call("debug_get_registers")['PC'])
    where = 'GOOD (переход был)' if pc == GOOD else ('BAD (условие не сработало)'
                                                     if pc == BAD else f'?? {pc:04X}')
    print(f"{name}: {where}")
    return pc == GOOD


def main():
    s = McpSession(cwd=ROOT)
    s.start()
    try:
        s.load_rom(ROM, org=0x0100)
        c = run_case(s, [('ADI', 1), ('LDA', ZERO), ('JZ',), ('JMP',)],
                     "C) ADI ; LDA 0 ;        JZ")
        b = run_case(s, [('ADI', 1), ('MVI', 0), ('JZ',), ('JMP',)],
                     "B) ADI ; MVI A,0 ;      JZ")
        a = run_case(s, [('ADI', 1), ('LDA', ZERO), ('MVI', 1), ('JZ',), ('JMP',)],
                     "A) ADI ; LDA 0 ; MVI A,1 ; JZ")
        print("\nвывод:")
        print(f"  LDA ставит Z: {c};  MVI A,00 ставит Z: {b};  "
              f"Z от LDA переживает MVI A,01: {a}")
        if c and a is False:
            print("  -> MVI в этой модели ЗАТИРАЕТ флаги (на реальном 8080 не трогает)")
    finally:
        s.close()
    return 0


if __name__ == '__main__':
    sys.exit(main())
