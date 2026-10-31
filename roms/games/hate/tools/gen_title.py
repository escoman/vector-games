#!/usr/bin/env python3
"""gen_title.py — титульная картинка H.A.T.E. для Вектора-06Ц: 256x256, 8 цветов.

Источник — `assets/hate.png`: экран 256x192 в семи ярких цветах ZX (так
он и выглядит на Спектруме). Вектор показывает его БЕЗ растяжения, в
обычном режиме 256x256 (GFX_MODE_256_16), прижатым к ВЕРХНЕМУ краю
экрана — как на ZX, где картинка занимает 256x192 из 256x192 видимых
растра, а нижние 64 строки Вектора остаются чёрными.

ЦВЕТ. Номер чернила ZX (0..7) — это и есть номер цвета Вектора:

    бит 0 (плоскость 0xE000, вес 1) — синий
    бит 1 (плоскость 0xC000, вес 2) — красный
    бит 2 (плоскость 0xA000, вес 4) — зелёный
    бит 3 (плоскость 0x8000, вес 8) — не используется (чёрный)

Поэтому палитра в main.c — ровно восемь ярких цветов ZX по номерам
чернил, и никакого выбора «какой слот за какой цвет» больше нет:
одна картинка — одна таблица цветов, менять нечего.

РАСКЛАДКА В ПАМЯТИ. Плоскости идут в образе в порядке АДРЕСОВ
распаковки: [0x8000 вес 8][0xA000 вес 4][0xC000 вес 2][0xE000 вес 1],
по 8 КБ, то есть 32 КБ. Поэтому вызывающий делает ОДИН
zx0_decompress(title_zx0, 0x8000) и получает весь экран, включая
обнулённые строки под картинкой (в образе они нули, сжимаются в ничто).
Адрес байта внутри плоскости — `колонка * 256 + (255 - строка)`:
младший адрес — низ экрана, поэтому строка ZX y ложится в 255-y.

Использование:
    python3 tools/gen_title.py            # assets/hate.png -> include/title.inc
    python3 tools/gen_title.py --preview  # + assets/title_preview.png (сверка)
"""

import argparse
import struct
import sys
import zlib
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT.parents[2]
sys.path.insert(0, str(PROJECT / 'utils'))
from zx0 import compress, decompress  # noqa: E402

SCR_W, SCR_H = 256, 192       # картинка ZX
PLANE = 0x2000                # 32 колонки * 256 строк = 8 КБ на плоскость
Y_TOP = 255                   # строка картинки y -> строка экрана y -> адрес 255-y

# Яркие чернила ZX по номерам: номер = номер цвета Вектора (см. шапку).
ZX_INKS = [
    (0x00, 0x00, 0x00),       # 0 чёрный
    (0x00, 0x00, 0xD7),       # 1 синий
    (0xD7, 0x00, 0x00),       # 2 красный
    (0xD7, 0x00, 0xD7),       # 3 пурпурный
    (0x00, 0xD7, 0x00),       # 4 зелёный
    (0x00, 0xD7, 0xD7),       # 5 голубой
    (0xD7, 0xD7, 0x00),       # 6 жёлтый
    (0xD7, 0xD7, 0xD7),       # 7 белый
]
MAX_MISS = 3000               # допуск суммой квадратов: 0xCD против 0xD7 = 300,
                              # то есть допускается ±30 на канал — картинка
                              # того же рисунка, отрендеренная другим ZX-эмулятором


def ink_of(color):
    """RGB -> номер чернила ZX и квадрат расстояния до него."""
    best, best_d = 0, None
    for i, ink in enumerate(ZX_INKS):
        d = sum((a - b) ** 2 for a, b in zip(color, ink))
        if best_d is None or d < best_d:
            best, best_d = i, d
    return best, best_d


def load_inks(path):
    """PNG -> матрица чернил 192x256 (номер цвета Вектора в каждом пикселе)."""
    im = Image.open(path)
    if im.size != (SCR_W, SCR_H):
        raise SystemExit('%s: ожидалось %dx%d, в файле %dx%d'
                         % (path, SCR_W, SCR_H, im.size[0], im.size[1]))
    im = im.convert('RGB')
    px = im.load()
    rows = []
    miss = 0
    seen = {}
    for y in range(SCR_H):
        row = bytearray(SCR_W)
        for x in range(SCR_W):
            ink, d = ink_of(px[x, y])
            if d:
                miss = max(miss, d)
            seen[ink] = seen.get(ink, 0) + 1
            row[x] = ink
        rows.append(row)
    if miss > MAX_MISS:
        raise SystemExit('%s: цвет не из палитры ZX (расхождение %d)'
                         % (path, miss))
    return rows, seen, miss


def convert(rows):
    """Чернила 192x256 -> 32 КБ плоскостей в порядке распаковки с 0x8000."""
    buf = bytearray(4 * PLANE)
    green = memoryview(buf)[1 * PLANE:2 * PLANE]    # 0xA000, вес 4
    red = memoryview(buf)[2 * PLANE:3 * PLANE]      # 0xC000, вес 2
    blue = memoryview(buf)[3 * PLANE:4 * PLANE]     # 0xE000, вес 1
    for y, row in enumerate(rows):
        off_row = (Y_TOP - y) * 1                   # колонка прибавится ниже
        for bx in range(32):
            b_green = b_red = b_blue = 0
            for bit in range(8):
                ink = row[bx * 8 + bit]
                mask = 0x80 >> bit
                if ink & 4:
                    b_green |= mask
                if ink & 2:
                    b_red |= mask
                if ink & 1:
                    b_blue |= mask
            off = bx * 0x100 + off_row
            green[off] = b_green
            red[off] = b_red
            blue[off] = b_blue
    return bytes(buf)


def preview(buf, path):
    """Собрать экран 256x256 обратно из плоскостей и записать PNG."""
    raw = bytearray()
    for Y in range(256):
        raw.append(0)
        if Y >= 256 - SCR_H:
            y = 255 - Y
            for bx in range(32):
                off = bx * 0x100 + y
                b_g = buf[PLANE + off]
                b_r = buf[2 * PLANE + off]
                b_b = buf[3 * PLANE + off]
                for bit in range(8):
                    mask = 0x80 >> bit
                    ink = ((1 if b_b & mask else 0)
                           | (2 if b_r & mask else 0)
                           | (4 if b_g & mask else 0))
                    raw += bytes(ZX_INKS[ink])
        else:
            raw += b'\x00\x00\x00' * 256

    def chunk(tag, data):
        return (struct.pack('>I', len(data)) + tag + data
                + struct.pack('>I', zlib.crc32(tag + data) & 0xFFFFFFFF))

    png = (b'\x89PNG\r\n\x1a\n'
           + chunk(b'IHDR', struct.pack('>IIBBBBB', 256, 256, 8, 2, 0, 0, 0))
           + chunk(b'IDAT', zlib.compress(bytes(raw), 9))
           + chunk(b'IEND', b''))
    path.write_bytes(png)


def emit_inc(packed, path, raw_size):
    lines = [
        '/*',
        ' * title.inc — титульная картинка H.A.T.E.: 256x256, 8 цветов,',
        ' * картинка 256x192 прижата к ВЕРХНЕМУ краю экрана.',
        ' *',
        ' * СГЕНЕРИРОВАНО tools/gen_title.py из assets/hate.png —',
        ' * править здесь бессмысленно, правится исходник и пересобирается.',
        ' *',
        ' * Поток ZX0 распаковывается ОДНИМ вызовом в 0x8000 и заполняет все',
        ' * четыре плоскости по порядку адресов:',
        ' *   [0x0000..0x1FFF] -> 0x8000 — вес 8, нули (цвета ZX 0..7 его не',
        ' *                                используют);',
        ' *   [0x2000..0x3FFF] -> 0xA000 — вес 4, бит 2 цвета (зелёный);',
        ' *   [0x4000..0x5FFF] -> 0xC000 — вес 2, бит 1 цвета (красный);',
        ' *   [0x6000..0x7FFF] -> 0xE000 — вес 1, бит 0 цвета (синий).',
        ' * Байт внутри плоскости: колонка*256 + (255 - строка), младший',
        ' * адрес — низ экрана. Строки 192..255 экрана в образе нулевые.',
        ' * %d байт плоскостей -> %d байт ZX0.' % (raw_size, len(packed)),
        ' */',
        '',
        'static const unsigned char title_zx0[%d] = {' % len(packed),
    ]
    for i in range(0, len(packed), 12):
        chunk = ', '.join('0x%02X' % b for b in packed[i:i + 12])
        lines.append('    ' + chunk + ',')
    lines.append('};')
    lines.append('')
    path.write_text('\n'.join(lines), encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--src', default=str(ROOT / 'assets' / 'hate.png'))
    parser.add_argument('--out', default=str(ROOT / 'include' / 'title.inc'))
    parser.add_argument('--preview', action='store_true',
                        help='записать assets/title_preview.png для сверки')
    args = parser.parse_args()

    rows, seen, miss = load_inks(args.src)
    buf = convert(rows)
    packed = bytes(compress(buf))
    if decompress(packed) != buf:
        raise SystemExit('ZX0: round-trip не совпал')

    emit_inc(packed, Path(args.out), len(buf))
    print('%s -> %s: %d байт плоскостей, %d байт ZX0'
          % (args.src, args.out, len(buf), len(packed)))
    print('  чернила: '
          + ', '.join('%d:%d' % (k, seen[k]) for k in sorted(seen)))
    print('  расхождение с палитрой ZX: %d (допуск %d)' % (miss, MAX_MISS))

    if args.preview:
        out = ROOT / 'assets' / 'title_preview.png'
        preview(buf, out)
        print('превью: %s' % out)


if __name__ == '__main__':
    main()
