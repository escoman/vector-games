#!/usr/bin/env python3
"""Регрессия: блиттер плоскости сегментов (lib/gfx/plane.asm).

Сверяет 8080-код с независимой Python-моделью того же формата битмап.
Данные берутся из настоящих игровых ассетов (roms/games/nu_pogodi/src/
sprites.inc), которые генерирует tools/gen_assets.py, так что тест заодно
ловит расхождение между генератором и блиттером.

Проверяются три свойства:
  * OR выставляет ровно биты маски в прямоугольнике;
  * AND-NOT снимает ровно их же;
  * на обнулённой плоскости (так в игре: фон занимает только чётные слоты
    палитры, поэтому плоскость веса 1 пуста) OR и затем AND-NOT возвращают
    побайтно нулевое содержимое — то есть стирание восстанавливает фон.

Запуск: python3 utils/emulator/test_plane.py
"""
import random
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(HERE))

from v06_emu import Emulator8080          # noqa: E402

ASM = str(ROOT / 'lib' / 'gfx' / 'plane.asm')
SPRITES_INC = ROOT / 'roms' / 'games' / 'nu_pogodi' / 'src' / 'sprites.inc'

INK_PLANE = 0xE000         # плоскость веса 1
BASE = 0x0000              # код: метки ассемблера 0-базовые
BLOB = 0x4000              # битмап в памяти — за концом кода
SP = 0x7FF0                # стек
SCR_W, SCR_H = 256, 176

ARRAY_RE = re.compile(
    r'static const unsigned char (\w+)\[(\d+)\] = \{(.*?)\};', re.S)


def load_blobs(path):
    """{имя: bytes} из сгенерированного sprites.inc."""
    out = {}
    for name, size, body in ARRAY_RE.findall(Path(path).read_text()):
        data = bytes(int(t, 16) for t in re.findall(r'0x[0-9A-Fa-f]{2}', body))
        assert len(data) == int(size), f'{name}: {len(data)} != {size}'
        out[name] = data
    return out


def rect_of(blob):
    x0, y0, wb, h = blob[:4]
    return x0, y0, wb, h, blob[4:]


def addr_of(x0, y0, c, r):
    """Адрес байта (колонка c, строка r) в плоскости сегментов."""
    return INK_PLANE + ((x0 >> 3) + c) * 256 + (255 - (y0 + r))


def plane_bytes(cpu):
    return bytes(cpu.mem[INK_PLANE + i] for i in range(0x2000))


def apply_model(before, blob, op):
    """Эталон: копия плоскости после операции над прямоугольником битмапа."""
    x0, y0, wb, h, data = rect_of(blob)
    after = bytearray(before)
    for c in range(wb):
        for r in range(h):
            m = data[c * h + r]
            a = addr_of(x0, y0, c, r) - INK_PLANE
            if op == 'or':
                after[a] |= m
            else:
                after[a] &= ~m & 0xFF
    return bytes(after)


def run_case_with(emu, plane, blob, op):
    """Гоняет одну операцию на заданном содержимом плоскости."""
    assert len(plane) == 0x2000, f'плоскость {len(plane)} байт, нужно 0x2000'
    emu.reset()
    emu.cpu.mem[INK_PLANE:INK_PLANE + 0x2000] = plane
    emu.load_bytes(blob, BLOB)
    entry = '_gfx_plane_or' if op == 'or' else '_gfx_plane_andn'
    emu.call(entry, args=(BLOB,), sp=SP, max_steps=4_000_000)
    return plane_bytes(emu.cpu)


def main():
    if not SPRITES_INC.exists():
        print(f'FAIL: нет ассетов {SPRITES_INC} — запусти tools/gen_assets.py')
        return 1
    blobs = load_blobs(str(SPRITES_INC))
    emu = Emulator8080()
    emu.load_asm(ASM, base=BASE)
    for label in ('_gfx_plane_or', '_gfx_plane_andn'):
        if label.lower() not in emu.asm.labels:
            print(f'FAIL: метка {label} не найдена')
            return 1
    # Данные не должны накладываться на код: иначе загрузка битмапа затирает
    # инструкции, и тест падает на ровном месте.
    assert BLOB >= len(emu.asm.data), \
        f'BLOB=0x{BLOB:04X} внутри кода (длина 0x{len(emu.asm.data):04X})'

    rnd = random.Random(20261004)
    # Случайное содержимое плоскости нужно, чтобы ловить лишние изменения
    # битов вне маски. Индекс фона при этом не важен: побитовая операция над
    # произвольными битами — самый строгий тест.
    base_plane = bytes(rnd.getrandbits(8) for _ in range(0x2000))
    zero_plane = bytes(0x2000)          # 8192 байт нуля — «фон» в плоскости

    names = sorted(blobs)
    print(f'plane.asm: {len(names)} битмапов, по три проверки на каждый')
    failed = 0
    for name in names:
        blob = blobs[name]
        x0, y0, wb, h, data = rect_of(blob)
        assert x0 % 8 == 0, f'{name}: x0={x0} не кратно 8'
        assert y0 + h <= 256, f'{name}: y0+h={y0 + h} > 256'
        assert x0 + wb * 8 <= 256, f'{name}: x0+wb*8={x0 + wb * 8} > 256'
        assert len(data) == wb * h, f'{name}: данных {len(data)} != {wb * h}'

        # 1-2. Операции над случайным содержимым: побитовая точность.
        after_or = run_case_with(emu, base_plane, blob, 'or')
        want_or = apply_model(base_plane, blob, 'or')
        after_andn = run_case_with(emu, base_plane, blob, 'andn')
        want_andn = apply_model(base_plane, blob, 'andn')

        # 3. Раунд-трип на чистой плоскости: стирание возвращает фон.
        shown = run_case_with(emu, zero_plane, blob, 'or')
        erased = run_case_with(emu, shown, blob, 'andn')

        errs = []
        for what, got, want in (('OR', after_or, want_or),
                                ('AND-NOT', after_andn, want_andn),
                                ('стирание фона', erased, zero_plane)):
            if got != want:
                j = next(k for k in range(0x2000) if got[k] != want[k])
                errs.append(f'{what}: @0x{INK_PLANE + j:04X} '
                            f'получено 0x{got[j]:02X}, эталон 0x{want[j]:02X}')
        if errs:
            failed += 1
            print(f'  FAIL {name} rect {wb}B x {h}r @({x0},{y0}):')
            for e in errs:
                print(f'        {e}')

    if failed:
        print(f'ПРОВАЛЕНО: {failed} из {len(names)}')
        return 1
    print(f'Все битмапы совпали: ассемблер == Python-эталон, '
          f'AND-NOT восстанавливает фон.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
