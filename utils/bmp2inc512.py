#!/usr/bin/env python3
"""
bmp2inc512.py — конвертация 2-цветного BMP в .inc для режима 512x256 Вектора-06Ц.

Использование:
    python3 bmp2inc512.py path/to/image.bmp

Скрипт создаёт файл inc рядом с исходным: image.bmp -> image_bmp.inc.

Формат Вектора-06Ц (512x256, 2 цвета, расширенная плоскость B):
  - экранное ОЗУ 16 КБ: 0xC000-0xFFFF, по 8 КБ на плоскость:
      0xC000 — плоскость 1 (вес цвета 2, бит 1)
      0xE000 — плоскость 0 (вес цвета 1, бит 0)
  - режим 512x256: порт 02h, бит 4 = 1
  - чётные X (0,2,4,...) → плоскость 0 (E000h), бит 0
  - нечётные X (1,3,5,...) → плоскость 1 (C000h), бит 1
  - внутри плоскости: 32 блока по 256 байт, номер блока = x/16;
    байт с индексом i в блоке хранит строку экрана y = (256 - i) & 0xFF;
  - внутри байта: пиксель — бит (7 - ((x/2) & 7));
  - один байт содержит 8 пикселей через один (чётные или нечётные X).

Inc-файл содержит RLE-сжатый массив *_screen_rle — прямоугольник
картинки: заголовок из двух байт (ширина в 16-пиксельных блоках,
высота; 0 означает 256) и пары (количество, байт), количество 1-255,
конец потока — количество 0. Порядок байт: плоскости с весами цвета
2, 1; в плоскости блоки слева направо; в блоке строки сверху вниз.
Выводит graph_rle_expand_512(src) (lib/graphrle512.asm):
область вне картинки не меняется. Ширина картинки дополняется до
кратной 16 цветом 0.

Палитровые индексы перераспределяются: пиксель с индексом 0 (фон)
даёт цвет 0, пиксель с индексом 1 (передний план) даёт цвет 1.
"""

import os
import struct
import sys

SCREEN_W = 512
SCREEN_H = 256


def die(msg):
    print(f"bmp2inc512: {msg}", file=sys.stderr)
    sys.exit(1)


def parse_bmp(path):
    """Возвращает (width, height, pixels, palette).
    pixels — список строк сверху вниз, каждая строка — список индексов цвета (0 или 1).
    palette — 2 кортежа (r, g, b), значения 0-255."""
    with open(path, "rb") as f:
        data = f.read()

    if len(data) < 54 or data[0:2] != b"BM":
        die(f"{path}: не BMP-файл")

    bits_offset = struct.unpack_from("<I", data, 10)[0]
    ihdr_size = struct.unpack_from("<I", data, 14)[0]
    if ihdr_size < 40:
        die(f"{path}: unsupported BMP header (OS/2 format)")

    width, height = struct.unpack_from("<ii", data, 18)
    bpp = struct.unpack_from("<H", data, 28)[0]
    compression = struct.unpack_from("<I", data, 30)[0]
    clr_used = struct.unpack_from("<I", data, 46)[0]

    if bpp not in (1, 4, 8):
        die(f"{path}: нужен BMP с 1-8 битами/пиксель, а здесь {bpp} бит")
    if compression != 0:
        die(f"{path}: сжатые BMP (BI_RLE) не поддерживаются")
    if width <= 0 or width > SCREEN_W or abs(height) > SCREEN_H:
        die(f"{path}: размер {width}x{abs(height)} не помещается в экран {SCREEN_W}x{SCREEN_H}")

    ncolors = clr_used if clr_used else (1 << bpp)
    if ncolors > 2:
        die(f"{path}: в палитре {ncolors} цветов, нужно ровно 2")

    pal_off = 14 + ihdr_size
    palette = []
    for i in range(ncolors):
        b, g, r, _ = data[pal_off + i * 4: pal_off + i * 4 + 4]
        palette.append((r, g, b))

    stride = ((bpp * width + 31) // 32) * 4
    bottom_up = height > 0
    height = abs(height)

    pixels = []
    for y in range(height):
        row_idx = (height - 1 - y) if bottom_up else y
        row_off = bits_offset + row_idx * stride
        row = []
        for x in range(width):
            if bpp == 1:
                byte = data[row_off + x // 8]
                v = (byte >> (7 - (x % 8))) & 1
            elif bpp == 4:
                byte = data[row_off + x // 2]
                v = (byte >> 4) if (x & 1) == 0 else (byte & 0x0F)
                if v > 1:
                    v = 1  # приводим к 2 цветам
            else:  # bpp == 8
                v = data[row_off + x]
                if v > 1:
                    v = 1  # приводим к 2 цветам
            row.append(v)
        pixels.append(row)

    return width, height, pixels, palette


def build_plane(width, height, pixels, plane):
    """Поток данных для одной плоскости (32 блока × 256 байт = 8192 байт).
    plane=1 — нечётные X (плоскость 1, C000h),
    plane=0 — чётные X (плоскость 0, E000h).
    Один байт содержит 8 пикселей через один.
    """
    w16 = (width + 15) // 16
    out = bytearray()
    
    for xb in range(w16):
        for y in range(height):
            row = pixels[y]
            byte = 0
            for b in range(8):
                x = xb * 16 + b * 2 + plane
                if x < width and row[x]:
                    byte |= 0x80 >> b
            out.append(byte)
    
    return out


def rle_compress(data):
    """RLE парами (количество, байт); количество 1-255; терминатор 0."""
    import itertools
    out = bytearray()
    for v, g in itertools.groupby(data):
        run = sum(1 for _ in g)
        while run > 0:
            n = run if run < 256 else 255
            out.append(n)
            out.append(v)
            run -= n
    out.append(0)
    return out


def to_vector_color(r, g, b):
    """24-битный RGB -> байт палитры Вектора-06Ц.
    D0-D2 красный (1,2,4), D3-D5 зелёный (1,2,4), D6-D7 синий (2,4)."""
    return (r >> 5) | ((g >> 5) << 3) | ((b >> 6) << 6)


def format_array(f, name, data, per_line=16):
    f.write(f"const unsigned char {name}[{len(data)}] = {{\n")
    for i in range(0, len(data), per_line):
        chunk = data[i:i + per_line]
        f.write("    " + ", ".join(f"0x{v:02X}" for v in chunk) + ",\n")
    f.write("};\n")


def main():
    if len(sys.argv) < 2:
        print(f"Использование: {sys.argv[0]} <файл.bmp>",
              file=sys.stderr)
        sys.exit(1)

    args = [a for a in sys.argv[1:]]
    if len(args) != 1:
        print(f"Использование: {sys.argv[0]} <файл.bmp>",
              file=sys.stderr)
        sys.exit(1)

    bmp_path = args[0]
    if not os.path.isfile(bmp_path):
        die(f"файл не найден: {bmp_path}")

    stem = os.path.splitext(os.path.basename(bmp_path))[0]
    prefix = f"{stem}_bmp"
    inc_path = os.path.join(os.path.dirname(bmp_path), f"{prefix}.inc")

    width, height, pixels, palette = parse_bmp(bmp_path)
    
    # Для 2-цветного режима палитра всегда 2 цвета
    if len(palette) < 2:
        palette = [(0, 0, 0), (255, 255, 255)]
    
    pal_bytes = [to_vector_color(*c) for c in palette]

    print(f"{bmp_path} ({width}x{height}) -> {inc_path}")
    print(f"  цвета: фон 0x{pal_bytes[0]:02X}, передний план 0x{pal_bytes[1]:02X}")

    # Генерируем данные для обеих плоскостей:
    # сначала плоскость 1 (нечётные X, C000h), потом плоскость 0 (чётные X, E000h).
    w16 = (width + 15) // 16
    plane1_data = build_plane(width, height, pixels, plane=1)
    plane0_data = build_plane(width, height, pixels, plane=0)
    rle1 = rle_compress(plane1_data)
    rle0 = rle_compress(plane0_data)
    # Убираем терминатор из rle1, чтобы распаковщик не остановился
    # на середине потока. Терминатор только у rle0 (в конце).
    rle1_no_term = rle1[:-1]  # убираем последний байт (0x00)
    # Объединённый поток: header(64, height) + rle1 + rle0 + term
    # 64 блока: 32 для плоскости 1 (C000h) + 32 для плоскости 0 (E000h)
    total_blocks = w16 * 2  # 64 блока
    rle = bytes([total_blocks & 0xFF, height & 0xFF]) + rle1_no_term + rle0

    with open(inc_path, "w") as f:
        f.write(f"/* Автоматически сгенерировано bmp2inc512.py из {os.path.basename(bmp_path)} */\n")
        f.write(f"/* {width}x{height}, 2 цвета, режим 512x256 */\n")
        f.write(f"/* Обе плоскости: plane 1 (C000h) + plane 0 (E000h) */\n\n")
        f.write(f"#define {prefix}_width {width}\n")
        f.write(f"#define {prefix}_height {height}\n\n")
        f.write(f"/* 2 байта палитры для режима 512x256 (математические цвета 0,1) */\n")
        format_array(f, f"{prefix}_palette", pal_bytes[:2])
        f.write("\n/* RLE: плоскость 1 (32 блока) + плоскость 0 (32 блока), общий терминатор */\n")
        format_array(f, f"{prefix}_screen_rle", rle)

    print(f"  плоскость 1: {len(plane1_data)} байт -> RLE {len(rle1)} байт")
    print(f"  плоскость 0: {len(plane0_data)} байт -> RLE {len(rle0)} байт")
    print(f"  всего RLE: {len(rle)} байт (с заголовком)")
    print(f"  палитра: {' '.join(f'{v:02X}' for v in pal_bytes[:2])}")


if __name__ == "__main__":
    main()
