#!/usr/bin/env python3
"""Регрессия: 8080-распаковщик ZX0 (lib/unpack/zx0.asm) против эталонного
Python-компрессора (utils/zx0.py).

Для каждого набора данных: сжимаем Python-компрессором, кладём поток в
память эмулятора, вызываем _zx0_decompress(src, dst) и сверяем распакованные
байты с оригиналом. Это проверяет, что целевой ассемблер читает ровно тот
поток, который выдаёт сборочный компрессор.

Запуск: python3 utils/emulator/test_zx0.py
"""
import os
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / 'utils'))

from v06_emu import Emulator8080            # noqa: E402
import zx0                                   # noqa: E402

ASM = str(ROOT / 'lib' / 'unpack' / 'zx0.asm')
BASE = 0x0000        # грузим код в 0: метки ассемблера 0-базовые
SRC = 0x0200         # сжатый поток (код+bss занимают ~0x0000..0x0090)
DST = 0x1000         # результат распаковки
SP = 0x7FF0          # стек (растёт вниз, далеко от DST)
ENTRY = '_zx0_decompress'


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
    # реальная партитура (если есть)
    inc = ROOT / 'roms' / 'musics' / 'ducktales2' / 'rom_data' / 'track_0_music.inc'
    if inc.exists():
        ds.append(inc.read_bytes()[:8000])
    return ds


def main():
    emu = Emulator8080()
    emu.load_asm(ASM, base=BASE)
    if ENTRY.lower() not in emu.asm.labels:
        print(f'FAIL: метка {ENTRY} не найдена; есть: '
              f'{sorted(emu.asm.labels)[:20]}')
        return 1

    datasets = _datasets()
    print(f'zx0 asm-регрессия: {len(datasets)} наборов')
    failed = 0
    for i, data in enumerate(datasets):
        packed = zx0.compress(data)
        # свежая память под каждый прогон
        emu.reset()
        emu.load_bytes(packed, SRC)
        # затрём область назначения, чтобы поймать недозапись
        emu.load_bytes(bytes(len(data)), DST)
        # setup_call: args[0]@sp+2, args[1]@sp+4. Обёртка читает dst@sp+2,
        # src@sp+4 (соглашение z88dk classic: правый аргумент ближе к SP).
        emu.call(ENTRY, args=(DST, SRC), sp=SP, max_steps=20_000_000)
        got = bytes(emu.cpu.rb(DST + k) for k in range(len(data)))
        ok = got == data
        extra = emu.cpu.rb(DST + len(data))
        if not ok:
            failed += 1
            # первый расходящийся байт
            j = next((k for k in range(len(data)) if got[k] != data[k]),
                     len(data))
            print(f'  [{i:2d}] FAIL len={len(data)} packed={len(packed)} '
                  f'первое расхождение @+{j}:_ASM={got[j] if j < len(got) else "-"} '
                  f'эталон={data[j] if j < len(data) else "-"}')
        else:
            print(f'  [{i:2d}] OK   len={len(data):5d} packed={len(packed):5d} '
                  f'({100.0 * len(packed) / max(1, len(data)):5.1f}%) '
                  f'next={extra:02x}')

    if failed:
        print(f'ПРОВАЛЕНО: {failed} из {len(datasets)}')
        return 1
    print('Все наборы совпали: ассемблер == Python-эталон.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
