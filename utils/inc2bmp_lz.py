#!/usr/bin/env python3
"""
inc2bmp_lz.py — обратная конвертация .inc (LZ-сжатый) → BMP.

Использование:
    python3 inc2bmp_lz.py path/to/image_bmp.inc [output.bmp]

Если output.bmp не указан, создаётся файл рядом с исходным:
    image_bmp.inc -> image_reconstructed.bmp

Тест: round-trip BMP → inc → BMP должен дать идентичное изображение.
"""

import os
import re
import struct
import sys


def die(msg):
    print(f"inc2bmp_lz: {msg}", file=sys.stderr)
    sys.exit(1)


def parse_inc(path):
    """Парсит .inc файл, возвращает (width, height, palette, data).
    palette — список из 16 байт.
    data — bytearray всех LZ-данных (заголовок + словарь + 4 LZ-потока)."""
    with open(path, "r") as f:
        text = f.read()

    # Ширина и высота из #define
    m = re.search(r'#define\s+\w+_width\s+(\d+)', text)
    if not m:
        die("не найден _width")
    width = int(m.group(1))

    m = re.search(r'#define\s+\w+_height\s+(\d+)', text)
    if not m:
        die("не найден _height")
    height = int(m.group(1))

    # Палитра: const unsigned char xxx_palette[16] = { ... };
    m = re.search(r'const\s+unsigned\s+char\s+\w+_palette\[\d+\]\s*=\s*\{([^}]+)\}', text)
    if not m:
        die("не найден массив палитры")
    palette = [int(x.strip(), 16) for x in m.group(1).split(',') if x.strip()]
    if len(palette) != 16:
        die(f"палитра содержит {len(palette)} байт, нужно 16")

    # Данные: const unsigned char xxx_screen_lz[...] = { ... };
    m = re.search(r'const\s+unsigned\s+char\s+\w+_screen_lz\[\d+\]\s*=\s*\{([^}]+)\}', text)
    if not m:
        die("не найден массив данных")
    data = bytearray(int(x.strip(), 16) for x in m.group(1).split(',') if x.strip())

    return width, height, palette, data


def lz_decode(stream, tiles_per_plane):
    """LZ-распаковка потока байтов. Возвращает (indices, consumed).
    tiles_per_plane — ожидаемое количество тайлов."""
    indices = []
    pos = 0

    while len(indices) < tiles_per_plane:
        if pos >= len(stream):
            die(f"LZ-поток закончился раньше времени (decoded {len(indices)}/{tiles_per_plane})")

        flag_byte = stream[pos]
        pos += 1
        group_start = pos  # начало данных группы (16 байт)

        for bit in range(8):
            if len(indices) >= tiles_per_plane:
                break

            if flag_byte & (1 << bit):
                # Literal: 2 байта (9-битный индекс)
                hi = stream[pos] & 0x01
                lo = stream[pos + 1]
                pos += 2
                indices.append((hi << 8) | lo)
            else:
                # Reference: 2 байта
                ref0 = stream[pos]
                ref1 = stream[pos + 1]
                pos += 2
                offset = ((ref0 & 0x0F) << 8) | ref1
                length = (ref0 >> 4) + 3
                if offset > len(indices) or offset < 1:
                    die(f"invalid offset {offset} at pos {len(indices)}, stream pos {pos}")
                for j in range(length):
                    if len(indices) >= tiles_per_plane:
                        break
                    indices.append(indices[-offset])

        # Всегда пропускаем полные 16 байт данных группы,
        # даже если достигли tiles_per_plane в середине
        pos = group_start + 16

    return indices, pos


def reconstruct_plane(indices, tile_dict, height):
    """Восстанавливает данные плоскости из индексов тайлов и словаря.
    Возвращает bytearray размером w8 * height."""
    tiles_per_row = len(indices) // (height // 8)
    plane_data = bytearray()

    for block_idx in range(tiles_per_row):
        for y in range(0, height, 8):
            row_tile = block_idx * (height // 8) + y // 8
            tile_idx = indices[row_tile]
            tile = tile_dict[tile_idx]
            plane_data.extend(tile)

    return plane_data


def reconstruct_pixels(planes_data, width, height):
    """Восстанавливает пиксели из 4 плоскостей.
    planes_data — список из 4 bytearray (плоскости 3,2,1,0).
    Возвращает pixels — список строк сверху вниз, каждая — список индексов цвета.
    В Векторе-06Ц байт с индексом i хранит строку y = (height - 1 - i) & 0xFF."""
    w8 = (width + 7) // 8
    pixels = []

    for screen_y in range(height):
        row = []
        for x in range(width):
            color = 0
            xb = x // 8
            bit_in_byte = 7 - (x % 8)

            for bit, plane_idx in enumerate([3, 2, 1, 0]):
                plane = planes_data[plane_idx]
                # VRAM: байт i хранит строку y = (height - 1 - i)
                # Значит строке screen_y соответствует байт i = height - 1 - screen_y
                byte_idx = (height - 1 - screen_y) & 0xFF
                byte_offset = xb * height + byte_idx
                byte_val = plane[byte_offset]
                if (byte_val >> bit_in_byte) & 1:
                    color |= (1 << bit)
            row.append(color)
        pixels.append(row)

    return pixels


def write_bmp(path, width, height, pixels, palette):
    """Записывает 4-битный BMP (top-down, BI_RGB)."""
    ncolors = 16
    stride = ((4 * width + 31) // 32) * 4

    # BMP header
    file_header_size = 14
    info_header_size = 40
    palette_size = ncolors * 4
    pixel_data_size = stride * height
    file_size = file_header_size + info_header_size + palette_size + pixel_data_size
    bits_offset = file_header_size + info_header_size + palette_size

    data = bytearray()

    # File header (14 bytes)
    data.extend(b'BM')
    data.extend(struct.pack('<I', file_size))
    data.extend(struct.pack('<HH', 0, 0))  # reserved
    data.extend(struct.pack('<I', bits_offset))

    # Info header (40 bytes) — BITMAPINFOHEADER
    data.extend(struct.pack('<I', info_header_size))
    data.extend(struct.pack('<ii', width, height))  # positive = top-down
    data.extend(struct.pack('<HH', 1, 4))  # planes=1, bpp=4
    data.extend(struct.pack('<I', 0))  # compression = BI_RGB
    data.extend(struct.pack('<I', pixel_data_size))
    data.extend(struct.pack('<ii', 2835, 2835))  # 72 DPI
    data.extend(struct.pack('<II', ncolors, 0))  # colors used, important

    # Palette (BGRX format)
    for rgb_byte in palette:
        r = (rgb_byte >> 0) & 0x07
        g = (rgb_byte >> 3) & 0x07
        b = (rgb_byte >> 6) & 0x03
        # Reverse the Vector-06C color encoding
        r_out = r << 5
        g_out = g << 5
        b_out = b << 6
        data.extend(bytes([b_out, g_out, r_out, 0]))

    # Pixel data (top-down, 4 bpp)
    for y in range(height):
        row_data = bytearray(stride)
        row = pixels[y]
        for x in range(width):
            v = row[x] & 0x0F
            byte_idx = x // 2
            if x % 2 == 0:
                row_data[byte_idx] |= (v << 4)
            else:
                row_data[byte_idx] |= v
        data.extend(row_data)

    with open(path, 'wb') as f:
        f.write(data)


def main():
    if len(sys.argv) < 2:
        print(f"Использование: {sys.argv[0]} <файл.inc> [output.bmp]",
              file=sys.stderr)
        sys.exit(1)

    inc_path = sys.argv[1]
    if not os.path.isfile(inc_path):
        die(f"файл не найден: {inc_path}")

    # Выходной BMP
    if len(sys.argv) >= 3:
        bmp_path = sys.argv[2]
    else:
        stem = os.path.splitext(os.path.basename(inc_path))[0]
        # image_bmp -> image_reconstructed.bmp
        base = stem.replace('_bmp', '')
        bmp_path = os.path.join(os.path.dirname(inc_path),
                                f"{base}_reconstructed.bmp")

    # Парсинг .inc
    width, height, palette, data = parse_inc(inc_path)
    print(f"{inc_path} → {bmp_path}")
    print(f"  размер: {width}x{height}")
    print(f"  палитра: {' '.join(f'{v:02X}' for v in palette)}")
    print(f"  данных: {len(data)} байт")

    # Заголовок: w8, h, n_tiles (16-bit LE)
    if len(data) < 4:
        die("данные слишком короткие")
    w8 = data[0]
    h_byte = data[1]
    h = 256 if h_byte == 0 else h_byte
    n_tiles = data[2] | (data[3] << 8)

    print(f"  w8={w8}, h={h}, n_tiles={n_tiles}")

    # Словарь
    dict_size = n_tiles * 8
    if len(data) < 4 + dict_size:
        die("данные слишком короткие для словаря")

    tile_dict = []
    for i in range(n_tiles):
        start = 4 + i * 8
        tile_dict.append(bytes(data[start:start + 8]))

    print(f"  словарь: {n_tiles} тайлов ({dict_size} байт)")

    # LZ-потоки для 4 плоскостей
    tiles_per_plane = w8 * (h // 8)
    offset = 4 + dict_size

    planes_data = []
    for p in range(4):
        stream = data[offset:]
        indices, consumed = lz_decode(stream, tiles_per_plane)

        print(f"  плоскость {p}: {len(indices)} тайлов, {consumed} байт LZ")

        # Восстановление данных плоскости
        plane = reconstruct_plane(indices, tile_dict, h)
        planes_data.append(plane)

        offset += consumed

    # Восстановление пикселей
    pixels = reconstruct_pixels(planes_data, width, height)

    # Запись BMP
    write_bmp(bmp_path, width, height, pixels, palette)
    print(f"  файл создан: {bmp_path}")


if __name__ == "__main__":
    main()
