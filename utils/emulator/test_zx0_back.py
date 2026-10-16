#!/usr/bin/env python3
"""Регрессия: 8080 BACKWARD-распаковщик ZX0 (lib/unpack/zx0_back.asm) против
компрессора utils/zx0.py::compress_backwards.

Ядро — голое (без C-обёртки): входит с HL = последний адрес источника,
DE = последний адрес назначения, адрес возврата лежит в стеке (как это
делает бутстрап unpack_boot.asm: push ret; jmp zx0_back). Здесь воспроизводим
тот же контракт вручную, чтобы проверить, что backward-декодер читает ровно
тот поток, что выдаёт compress_backwards, и распаковывает его в оригинал.

Запуск: python3 utils/emulator/test_zx0_back.py
"""
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / 'utils'))

from v06_emu import Emulator8080, SENTINEL   # noqa: E402
import zx0                                    # noqa: E402

ASM = str(ROOT / 'lib' / 'unpack' / 'zx0_back.asm')
BASE = 0x0000        # код ядра грузим в 0
SRC = 0x9000         # сжатый поток (его конец = HL на входе)
DST = 0x4000         # оригинал (его конец = DE на входе); растёт вниз от SRC
SP = 0xF000          # стек (выше потока, ниже SENTINEL 0xFF00)
ENTRY = 'zx0_back'


def _datasets():
    ds = []
    ds.append(b'A')
    ds.append(b'AB')
    ds.append(b'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA')
    ds.append(bytes(range(256)))
    ds.append(b'abcabcabcabcabcabcabcabcabcabc')
    period = bytes((i * 37 + 11) & 0xFF for i in range(200))
    ds.append(period * 20)
    rnd = random.Random(7)
    ds.append(bytes(rnd.getrandbits(8) for _ in range(900)))
    base = bytes(rnd.getrandbits(8) for _ in range(64))
    blob = bytearray()
    for _ in range(300):
        if rnd.random() < 0.5:
            blob += base[rnd.randrange(0, 40):rnd.randrange(40, 64)]
        else:
            blob.append(rnd.getrandbits(8))
    ds.append(bytes(blob))
    # длинный «pseudorom» с широкими back-reference (distance > 255)
    prog = bytearray(b'\xc3\x00\x01')
    for _ in range(1200):
        prog += bytes(rnd.choice([0x06, 0x3E, 0x32, 0xC3, 0x00]) for _ in range(3))
        prog += bytes(rnd.getrandbits(8) for _ in range(rnd.randrange(1, 9)))
    ds.append(bytes(prog))
    return ds


def main():
    emu = Emulator8080()
    emu.load_asm(ASM, base=BASE)
    if ENTRY.lower() not in emu.asm.labels:
        print(f'FAIL: метка {ENTRY} не найдена; есть: '
              f'{sorted(emu.asm.labels)[:20]}')
        return 1
    entry = emu.asm.labels[ENTRY.lower()]
    core_len = len(emu.asm.data)

    datasets = _datasets()
    print(f'zx0 backward asm-регрессия: {len(datasets)} наборов '
          f'(ядро {core_len} байт)')
    failed = 0
    for i, data in enumerate(datasets):
        packed = zx0.compress_backwards(data)
        if len(data) + DST >= SRC:
            # разнести области: поток должен лежать строго выше оригинала
            print(f'  [{i:2d}] SKIP (слишком большой для раскладки теста)')
            continue
        emu.reset()
        emu.load_bytes(packed, SRC)
        emu.load_bytes(b'\xa5' * len(data), DST)   # затрём приёмник
        cpu = emu.cpu
        cpu.halted = False
        cpu.steps = 0
        cpu.call_depth = 0
        cpu.sp = SP
        cpu.push(SENTINEL)                 # адрес возврата = 0xFF00
        cpu.pc = entry
        cpu.set_hl(SRC + len(packed) - 1)  # HL = последний байт потока
        cpu.set_de(DST + len(data) - 1)    # DE = последний байт оригинала
        try:
            steps = cpu.run_until(max_steps=40_000_000, stop_pc=SENTINEL)
        except (TimeoutError, RuntimeError) as e:
            failed += 1
            print(f'  [{i:2d}] FAIL run: {e}')
            continue
        got = bytes(cpu.mem[DST:DST + len(data)])
        ok = got == data
        if not ok:
            failed += 1
            # распаковка идёт снизу; найдём расхождение (справа, т.к. сходим вниз)
            j = next((k for k in range(len(data)) if got[k] != data[k]), len(data))
            print(f'  [{i:2d}] FAIL len={len(data)} packed={len(packed)} '
                  f'первое расхождение @{j}: got=0x{got[j]:02X} '
                  f'want=0x{data[j]:02X} (pc=0x{cpu.pc:04X})')
        else:
            print(f'  [{i:2d}] OK   len={len(data):5d} packed={len(packed):5d} '
                  f'({100.0 * len(packed) / max(1, len(data)):5.1f}%) '
                  f'{steps} шагов')

    if failed:
        print(f'ПРОВАЛЕНО: {failed} из {len(datasets)}')
        return 1
    print('Все наборы совпали: backward-ассемблер == compress_backwards.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
