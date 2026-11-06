#!/usr/bin/env python3
"""
png2panel.py — конвертация 2-цветного PNG в данные панели загрузчика.

Панель — это картинка, которую stage-2 второго загрузчика рисует в угол
экрана 256x256 ПЕРЕД сеткой карты загрузки (docs/LOADER_TZ.MD §5.2). Данные
лежат в слоте high RAM (base + номер·stride), куда их РАЗПАКОВЫВАЕТ копир из
ROM заставки (стаб `boot/loader.asm` вызывает zx0_decompress), поэтому в ROM
панель лежит сжатой ZX0 (флаг --zx0), а в слоте — плоскость Вектора «как
есть»: байт = 8 ГОРИЗОНТАЛЬНЫХ пикселя, бит 7 = левый пиксель, строки сверху
вниз. Тогда рисование = копирование байтов в 0xC000 + (x/8)·100h + (255 − y)
без сдвигов и маскирования.

Использование:
    python3 utils/png2panel.py INPUT.png --name panel_top [опции]

    --name ИМЯ      метка/C-имя массива
    --emit inc|h    .inc для z80asm (по умолчанию) или C-заголовок
    -o ФАЙЛ         куда писать (по умолчанию рядом с PNG:
                    panel_top.png -> panel_top.inc / panel_top_png.h)
    --corner M      куда ставить панель: top-left (0,0),
                    bottom-right (256-w, 256-h) или none (только --x/--y)
    --x N --y N     явная позиция левого верхнего угла (N-й пиксель экрана)
    --slot N        бюджет РАЗУПАКОВАННЫХ данных, по умолчанию 3072 (слот)
    --zx0           cжать поток ZX0 (utils/zx0.py) — в ROM лежат сжатые
                    байты, стаб распаковывает их в слот перед stage-2

Позиция по X обязана быть кратна 8: байт плоскости накрывает ровно 8
пикселей по горизонтали, сдвиг потребовал бы побитовой сборки на каждом
байте. По Y кратность не нужна — строки экрана это соседние байты внутри
блока.

Фон — самый частый цвет PNG, светится всё, что ему не равно (поэтому
подойдёт и инверсная картинка). Выход содержит сами данные и геометрию:
ширину в байтах (wb), высоту в строках, x, y — из них складывается
дескриптор панели в конфиге загрузчика.
"""
import argparse
import os
import sys
from collections import Counter

from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import zx0                                                    # noqa: E402

SCREEN = 256
SLOT = 3072


def analyze(png_path):
    """(bg, lit-карта, w, h) по PNG: фон = самый частый цвет."""
    im = Image.open(png_path).convert('RGB')
    w, h = im.size
    px = im.load()
    freq = Counter(px[x, y] for y in range(h) for x in range(w))
    if len(freq) > 2:
        raise SystemExit('%s: цветов %d, а панель — 2-цветная (фон + линия)'
                         % (os.path.basename(png_path), len(freq)))
    bg = freq.most_common(1)[0][0]
    return bg, px, w, h


def pack_panel(png_path):
    """(данные, wb, h, w) — укладка панели в байты плоскости.

    wb — байт в строке (ширина, дополненная до кратной 8), h — строк.
    Позиция сюда не входит: она влияет только на адреса при рисовании, а
    сами байты от неё не зависят. Возвращает и геометрию, чтобы
    потребитель (тест раунд-трипа) не разматывал PNG сам: формат и ожидание
    должны сходиться на одной функции.
    """
    bg, px, w, h = analyze(png_path)
    wb = (w + 7) // 8
    out = bytearray()
    for y in range(h):
        for b in range(wb):
            v = 0
            for i in range(8):
                x = b * 8 + i
                if x < w and px[x, y] != bg:
                    v |= 0x80 >> i
            out.append(v)
    return bytes(out), wb, h, w


def place(args, w, h):
    """Позиция панели и проверка влезания."""
    if args.corner == 'top-left':
        x, y = 0, 0
    elif args.corner == 'bottom-right':
        x, y = SCREEN - w, SCREEN - h
    else:
        x, y = args.x, args.y
    if x % 8:
        raise SystemExit('x=%d не кратен 8: байт плоскости накрывает 8 '
                         'пикселей по горизонтали' % x)
    if x < 0 or y < 0 or y + h > SCREEN or x + ((w + 7) // 8) * 8 > SCREEN:
        raise SystemExit('панель %dx%d в (%d,%d) не влезает в %dx%d'
                         % (w, h, x, y, SCREEN, SCREEN))
    return x, y


def emit_inc(name, blob, wb, h, x, y, raw_len, comp):
    up = name.upper()
    out = [';',
           '; %s — сгенерировано из PNG (utils/png2panel.py), НЕ ПРАВИТЬ.' % name,
           '; Панель загрузчика: байт = 8 горизонтальных пикселей (бит 7 =',
           '; левый), строки сверху вниз.%s' % (
               ' ПОТОК СЖАТ ZX0 — стаб распаковывает в слот.' if comp else ''),
           '; docs/LOADER_TZ.MD §5.2.',
           ';']
    out.append('%s:' % name)
    for i in range(0, len(blob), 16):
        out.append('        db      ' + ', '.join('0%02Xh' % b
                                                  for b in blob[i:i + 16]))
    defs = ((up + '_WB', wb), (up + '_H', h),
            (up + '_X', x), (up + '_Y', y),
            (up + '_SIZE', raw_len))
    if comp:
        defs = defs + ((up + '_CSIZE', len(blob)), (up + '_ZX0', 1))
    for label, value in defs:
        out.append('%-14s equ     %d' % (label, value))
    out.append('')
    return '\n'.join(out)


def emit_h(name, blob, wb, h, x, y, raw_len, comp):
    up = name.upper()
    lines = ['/*',
             ' * %s — сгенерировано из PNG (utils/png2panel.py), НЕ ПРАВИТЬ.'
             % name,
             ' * Панель загрузчика: байт = 8 горизонтальных пикселя (бит 7 =',
             ' * левый), строки сверху вниз; позиция — левый верхний угол.%s'
             % ('\n * ПОТОК СЖАТ ZX0 (lib/unpack/zx0.asm) — стаб loader.asm'
                '\n * распаковывает его в слот high RAM перед stage-2.'
                if comp else ''),
             ' * docs/LOADER_TZ.MD §5.2.',
             ' */',
             '#ifndef PANELS_%s_H' % up,
             '#define PANELS_%s_H' % up,
             '',
             'static const unsigned char %s[] = {' % name]
    for i in range(0, len(blob), 12):
        lines.append('    ' + ', '.join('0x%02X' % b for b in blob[i:i + 12])
                     + ',')
    lines += ['};', '',
              '#define %s_WB %d   /* байт в строке */' % (up, wb),
              '#define %s_H  %d   /* строк */' % (up, h),
              '#define %s_X  %d   /* x левого верхнего угла, кратно 8 */'
              % (up, x),
              '#define %s_Y  %d   /* y левого верхнего угла */' % (up, y),
              '#define %s_SIZE %d   /* размер РАЗУПАКОВАННЫХ данных */'
              % (up, raw_len)]
    if comp:
        lines += ['/* %s[] — это сжатый поток, распаковать zx0_decompress. */'
                  % name,
                  '#define %s_CSIZE %d   /* байт сжатого потока в ROM */'
                  % (up, len(blob)),
                  '#define %s_ZX0  1' % up]
    lines += ['', '#endif', '']
    return '\n'.join(lines)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument('src')
    ap.add_argument('--name', required=True)
    ap.add_argument('--emit', choices=('inc', 'h'), default='inc')
    ap.add_argument('-o', '--out', default=None)
    ap.add_argument('--corner', choices=('top-left', 'bottom-right', 'none'),
                    default='top-left')
    ap.add_argument('--x', type=int, default=0)
    ap.add_argument('--y', type=int, default=0)
    ap.add_argument('--slot', type=int, default=SLOT,
                    help='бюджет РАЗУПАКОВАННЫХ данных панели, байт')
    ap.add_argument('--zx0', action='store_true',
                    help='сжать поток ZX0 (в ROM лежат сжатые байты, '
                         'стаб loader.asm распаковывает в слот)')
    a = ap.parse_args()

    data, wb, h, w = pack_panel(a.src)
    x, y = place(a, w, h)
    if len(data) > a.slot:
        raise SystemExit('%s: %d байт (разупаковано), слот панели %d — не помещается'
                         % (os.path.basename(a.src), len(data), a.slot))
    blob = zx0.compress(data) if a.zx0 else data
    text = (emit_inc(a.name, blob, wb, h, x, y, len(data), a.zx0)
            if a.emit == 'inc'
            else emit_h(a.name, blob, wb, h, x, y, len(data), a.zx0))
    dst = a.out or os.path.join(
        os.path.dirname(a.src) or '.',
        '%s%s' % (a.name, '.inc' if a.emit == 'inc' else '_png.h'))
    open(dst, 'w', encoding='utf-8').write(text)
    print('%s: %dx%d -> %s: %d байт%s, %d байт/строку, позиция (%d,%d)'
          % (os.path.basename(a.src), w, h, dst, len(data),
             (' -> ZX0 %d' % len(blob)) if a.zx0 else '', wb, x, y))
    return 0


if __name__ == '__main__':
    sys.exit(main())
