#!/usr/bin/env python3
"""
bmp2inc_lz.py — конвертация 16-цветного BMP в .inc для ROM Вектора-06Ц
с LZ-сжатием на основе тайлового словаря.

Использование:
    python3 bmp2inc_lz.py path/to/image.bmp

Скрипт создаёт файл inc рядом с исходным: image.bmp -> image_bmp.inc.

Формат Вектора-06Ц (256x256, 16 цветов, 4 битовые плоскости):
  - экранное ОЗУ 32 КБ: 0x8000-0xFFFF, по 8 КБ на плоскость:
      0x8000 — плоскость 3 (вес цвета 8)
      0xA000 — плоскость 2 (вес цвета 4)
      0xC000 — плоскость 1 (вес цвета 2)
      0xE000 — плоскость 0 (вес цвета 1)
  - внутри плоскости: 32 блока по 256 байт, номер блока = x/8;
    байт с индексом i в блоке хранит строку экрана y = (256 - i) & 0xFF;
  - внутри байта: левый пиксель — старший бит (7 - (x & 7)).

Алгоритм сжатия:
  1. Извлечение тайлов 8x8 (8 байт) из каждой плоскости.
  2. Построение словаря уникальных тайлов (один на все плоскости).
  3. Замена тайлов их индексами в словаре.
  4. LZ-сжатие потока индексов для каждой плоскости.

Формат данных:
  Заголовок: tpp (тайлов на плоскость, 16 бит LE), ntiles (16 бит LE),
             h_div8 (высота в тайлах, 1 байт).
  Словарь: n_tiles тайлов по 8 байт каждый.
  Для каждой из 4 плоскостей: LZ-поток.

  Тайлы в потоке идут в порядке VRAM постолбцово:
  сначала все тайлы столбца 0 (снизу вверх), затем столбца 1 и т.д.

LZ-формат (на тайлах):
  - flag_byte: 8 бит, каждый бит = literal(1) или reference(0).
  - literal: 2 байта (индекс тайла 0-511).
  - reference: 2 байта (offset 12 бит, length 4 бита).
    offset = ((flag_byte & 0x0F) << 8) | next_byte (1-4095).
    length = (flag_byte >> 4) + 3 (3-18 тайлов).

Распаковщик: lib/graphlz.asm (graph_lz_expand).
"""

import os
import struct
import sys

SCREEN_W = 256
SCREEN_H = 256


def die(msg):
    print(f"bmp2inc_lz: {msg}", file=sys.stderr)
    sys.exit(1)


def parse_bmp(path):
    """Возвращает (width, height, pixels, palette).
    pixels — список строк сверху вниз, каждая строка — список индексов цвета.
    palette — 16 кортежей (r, g, b), значения 0-255."""
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

    if bpp not in (4, 8):
        die(f"{path}: нужен 16-цветный BMP (4 бита), а здесь {bpp} бит/пиксель")
    if compression != 0:
        die(f"{path}: сжатые BMP (BI_RLE) не поддерживаются")
    if width <= 0 or width > SCREEN_W or abs(height) > SCREEN_H:
        die(f"{path}: размер {width}x{abs(height)} не помещается в экран {SCREEN_W}x{SCREEN_H}")

    ncolors = clr_used if clr_used else (1 << bpp)
    if ncolors > 16:
        die(f"{path}: в палитре {ncolors} цветов, нужно не больше 16")

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
            if bpp == 4:
                byte = data[row_off + x // 2]
                v = (byte >> 4) if (x & 1) == 0 else (byte & 0x0F)
            else:
                v = data[row_off + x]
            if v >= ncolors:
                die(f"{path}: пиксель x={x},y={y} ссылается на цвет {v}, "
                    f"а в палитре только {ncolors}")
            row.append(v)
        pixels.append(row)

    return width, height, pixels, palette


def build_rect(width, height, pixels):
    """Поток прямоугольника width×height в порядке записи распаковщиком:
    плоскости с весами цвета 8, 4, 2, 1; в плоскости — блоки слева направо;
    в блоке — строки сверху вниз. Ширина дополняется до кратной 8 цветом 0."""
    w8 = (width + 7) // 8
    out = bytearray()
    for bit in (3, 2, 1, 0):
        for xb in range(w8):
            for y in range(height):
                row = pixels[y]
                byte = 0
                for b in range(8):
                    x = xb * 8 + b
                    if x < width and (row[x] >> bit) & 1:
                        byte |= 0x80 >> b
                out.append(byte)
    return out


def extract_tiles(planes_data, height):
    """Извлекает тайлы (по 8 байт) из данных плоскостей в порядке VRAM:
    каждые 8 байт = один тайл, последовательно от начала плоскости."""
    all_tiles = []
    for plane in planes_data:
        for i in range(0, len(plane), 8):
            tile = plane[i:i+8]
            if len(tile) == 8:
                all_tiles.append(bytes(tile))
    return all_tiles


def lz_encode(indices, max_offset=4095, max_length=18):
    """LZ-сжатие потока индексов тайлов (список чисел 0-255).
    Возвращает (encoded_data, stats).
    encoded_data — список байт (flag_byte + данные).
    stats — словарь со статистикой.

    Важно: считаем cur (номер тайла) так же, как декодер,
    чтобы остановиться на том же месте и не написать лишних байт."""
    # Позиции каждого значения индекса для быстрого поиска
    value_positions = {}
    for i, idx in enumerate(indices):
        if idx not in value_positions:
            value_positions[idx] = []
        value_positions[idx].append(i)

    encoded = []
    i = 0
    cur = 0          # номер текущего тайла (как в декодере)
    n = len(indices)
    literals = 0
    references = 0

    while cur < n:
        flag_byte = 0
        group_data = []

        for bit in range(8):
            if cur >= n:
                # Декодер уже остановился. Пишем dummy literal,
                # чтобы декодер мог прочитать полную группу.
                flag_byte |= (1 << bit)
                group_data.extend([0, 0])
                continue

            # Ищем самое длинное совпадение
            best_offset = 0
            best_length = 0

            cur_val = indices[i]
            if cur_val in value_positions:
                for pos in value_positions[cur_val]:
                    if pos >= i:
                        break
                    offset = i - pos
                    if offset > max_offset:
                        continue

                    # Считаем длину совпадения
                    length = 0
                    while (i + length < n and
                           length < max_length and
                           indices[i + length] == indices[pos + length]):
                        length += 1

                    if length > best_length:
                        best_length = length
                        best_offset = offset

            if best_length >= 3:
                # Reference: 2 байта
                references += best_length
                length_byte = ((best_length - 3) << 4) | ((best_offset >> 8) & 0x0F)
                offset_byte = best_offset & 0xFF
                group_data.extend([length_byte, offset_byte])
                i += best_length
                cur += best_length
            else:
                # Literal: 2 байта (индекс тайла)
                literals += 1
                flag_byte |= (1 << bit)
                idx = indices[i]
                group_data.append((idx >> 8) & 0x01)  # старший бит
                group_data.append(idx & 0xFF)          # младшие 8 бит
                i += 1
                cur += 1

        encoded.append(flag_byte)
        encoded.extend(group_data)

    stats = {
        'literals': literals,
        'references': references,
        'total_tiles': literals + references,
        'encoded_size': len(encoded)
    }
    return encoded, stats


def to_vector_color(r, g, b):
    """24-битный RGB -> байт палитры Вектора-06Ц.
    D0-D2 красный (1,2,4), D3-D5 зелёный (1,2,4), D6-D7 синий (2,4)."""
    return (r >> 5) | ((g >> 5) << 3) | ((b >> 6) << 6)


def popcount(v):
    return bin(v).count("1")


INDEX_ORDER = [0,
               1, 2, 4, 8,
               3, 5, 6, 9, 10, 12,
               7, 11, 13, 14,
               15]


def color_groups(width, height, pixels, palette):
    """Группы цветов, совпадающих после квантования до байта Вектора."""
    pal_bytes = [to_vector_color(*c) for c in palette]
    counts = {}
    for row in pixels:
        for v in row:
            counts[v] = counts.get(v, 0) + 1
    groups = {}
    for idx, vb in enumerate(pal_bytes):
        groups.setdefault(vb, []).append(idx)
    grouped = []
    for vb, idxs in groups.items():
        total = sum(counts.get(i, 0) for i in idxs)
        grouped.append((total, idxs, vb))
    grouped.sort(key=lambda g: (-g[0], min(g[1])))
    return grouped, pal_bytes


def greedy_perm(grouped):
    """Жадное назначение: частым группам — малобитовые индексы."""
    perm = [0] * 16
    n_groups = 0
    assigned = set()
    for (total, idxs, vb), new_idx in zip(grouped, INDEX_ORDER):
        for i in idxs:
            perm[i] = new_idx
            assigned.add(i)
        n_groups += 1
    leftovers = INDEX_ORDER[n_groups:]
    free = [i for i in range(16) if i not in assigned]
    for i, v in zip(free, leftovers):
        perm[i] = v
    return perm


def make_masks(width, height, pixels):
    """Битовые маски положений пикселей каждого старого индекса."""
    w8 = (width + 7) // 8
    pat = [bytearray(w8 * height) for _ in range(16)]
    for xb in range(w8):
        for y in range(height):
            row = pixels[y]
            off = xb * height + y
            for b in range(8):
                x = xb * 8 + b
                if x < width:
                    pat[row[x] & 0x0F][off] |= 0x80 >> b
    return [int.from_bytes(p, "little") for p in pat]


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


def rle_size_of_perm(perm, masks, plane_len, cache={}):
    """Размер RLE прямоугольника при назначении perm."""
    data = bytearray()
    for p in (3, 2, 1, 0):
        subset = tuple(i for i in range(16) if (perm[i] >> p) & 1)
        acc = cache.get(subset)
        if acc is None:
            acc = 0
            for i in subset:
                acc |= masks[i]
            cache[subset] = acc
        data += acc.to_bytes(plane_len, "little")
    return 2 + len(rle_compress(data))


def local_search(perm, masks, plane_len):
    """Покоординатный спуск парными перестановками индексов."""
    perm = list(perm)
    cur = rle_size_of_perm(perm, masks, plane_len)
    while True:
        best_pair, best_size = None, cur
        for a in range(16):
            for b in range(a + 1, 16):
                if popcount(perm[a]) != popcount(perm[b]):
                    continue
                perm[a], perm[b] = perm[b], perm[a]
                size = rle_size_of_perm(perm, masks, plane_len)
                perm[a], perm[b] = perm[b], perm[a]
                if size < best_size:
                    best_size, best_pair = size, (a, b)
        if best_pair is None:
            return perm, cur
        a, b = best_pair
        perm[a], perm[b] = perm[b], perm[a]
        cur = best_size


def format_array(f, name, data, per_line=16):
    f.write(f"const unsigned char {name}[{len(data)}] = {{\n")
    for i in range(0, len(data), per_line):
        chunk = data[i:i + per_line]
        f.write("    " + ", ".join(f"0x{v:02X}" for v in chunk) + ",\n")
    f.write("};\n")


def main():
    if len(sys.argv) < 2:
        print(f"Использование: {sys.argv[0]} <файл.bmp>", file=sys.stderr)
        sys.exit(1)

    bmp_path = sys.argv[1]
    if not os.path.isfile(bmp_path):
        die(f"файл не найден: {bmp_path}")

    stem = os.path.splitext(os.path.basename(bmp_path))[0]
    prefix = f"{stem}_bmp"
    inc_path = os.path.join(os.path.dirname(bmp_path), f"{prefix}.inc")

    width, height, pixels, palette = parse_bmp(bmp_path)

    # Оптимизация палитры (как в bmp2inc.py)
    grouped, old_pal_bytes = color_groups(width, height, pixels, palette)
    masks = make_masks(width, height, pixels)
    plane_len = ((width + 7) // 8) * height

    print(f"{bmp_path} ({width}x{height}) -> {inc_path}")
    print("  частоты цветов:")
    for total, idxs, vb in grouped:
        old = ",".join(str(i) for i in idxs)
        print(f"    точек {total:6d}: индексы [{old}], цвет 0x{vb:02X}")

    greedy = greedy_perm(grouped)
    candidates = [
        ("жадное по частоте, перестановки внутри классов", greedy, True),
        ("жадное по частоте, свободные перестановки", greedy, False),
    ]
    best_perm, best_size, best_name = None, None, None
    for name, seed, cls in candidates:
        print(f"  поиск: {name}")
        perm, size = local_search(seed, masks, plane_len)
        if best_size is None or size < best_size:
            best_perm, best_size, best_name = perm, size, name

    perm = best_perm
    print(f"  лучший вариант: {best_name}, RLE {best_size} байт")

    # Применяем перестановку к пикселям
    new_pixels = [[perm[v] for v in row] for row in pixels]
    pixels = new_pixels

    # Новая палитра
    new_pal = [0] * 16
    for old_idx in range(16):
        new_idx = perm[old_idx]
        if old_idx < len(old_pal_bytes):
            new_pal[new_idx] = old_pal_bytes[old_idx]
    pal_bytes = new_pal

    print(f"{bmp_path} ({width}x{height}) -> {inc_path}")
    print(f"  палитра: {' '.join(f'{v:02X}' for v in pal_bytes)}")

    # Построение данных плоскостей
    w8 = (width + 7) // 8
    rect_data = build_rect(width, height, pixels)

    # Разбиение на плоскости
    plane_size = w8 * height
    planes = []
    for p in range(4):
        plane = rect_data[p * plane_size: (p + 1) * plane_size]
        planes.append(plane)

    # Извлечение тайлов из всех плоскостей (в порядке VRAM)
    all_tiles = extract_tiles(planes, height)

    print(f"  всего тайлов: {len(all_tiles)}")

    # Построение словаря уникальных тайлов
    tile_dict = []
    tile_to_idx = {}
    for tile in all_tiles:
        if tile not in tile_to_idx:
            tile_to_idx[tile] = len(tile_dict)
            tile_dict.append(tile)

    print(f"  уникальных тайлов: {len(tile_dict)}")

    if len(tile_dict) > 512:
        die(f"слишком много уникальных тайлов: {len(tile_dict)} (максимум 512)")

    # Замена тайлов их индексами
    tile_indices = [tile_to_idx[tile] for tile in all_tiles]

    # Разбиение индексов по плоскостям
    tiles_per_plane = w8 * (height // 8)
    plane_indices = []
    for p in range(4):
        start = p * tiles_per_plane
        end = start + tiles_per_plane
        plane_indices.append(tile_indices[start:end])

    # LZ-сжатие каждой плоскости
    lz_streams = []
    total_literals = 0
    total_refs = 0
    for p, indices in enumerate(plane_indices):
        encoded, stats = lz_encode(indices)
        lz_streams.append(encoded)
        total_literals += stats['literals']
        total_refs += stats['references']
        print(f"  плоскость {p}: {len(indices)} тайлов -> {len(encoded)} байт "
              f"({stats['literals']} literal, {stats['references']} ref)")

    # Сборка финальных данных
    # Заголовок: tpp (2 байта LE), ntiles (2 байта LE), h_div8 (1 байт)
    n_tiles = len(tile_dict)
    tiles_per_plane = w8 * (height // 8)
    h_div8 = height // 8
    header = bytes([tiles_per_plane & 0xFF, (tiles_per_plane >> 8) & 0xFF,
                    n_tiles & 0xFF, (n_tiles >> 8) & 0xFF,
                    h_div8])

    # Словарь тайлов
    dict_data = bytearray()
    for tile in tile_dict:
        dict_data.extend(tile)

    # Объединение всех данных
    output = bytearray()
    output.extend(header)
    output.extend(dict_data)
    for stream in lz_streams:
        output.extend(stream)

    print(f"  итого: {len(output)} байт "
          f"(заголовок 5 + словарь {len(dict_data)} + LZ {sum(len(s) for s in lz_streams)})")

    # Запись .inc файла
    with open(inc_path, "w") as f:
        f.write(f"/* Автоматически сгенерировано bmp2inc_lz.py из {os.path.basename(bmp_path)} */\n")
        f.write(f"/* {width}x{height}, 16 цветов, LZ-сжатие (тайлы + LZ77) */\n\n")
        f.write(f"#define {prefix}_width {width}\n")
        f.write(f"#define {prefix}_height {height}\n")
        f.write(f"#define {prefix}_n_tiles {len(tile_dict)}\n\n")
        f.write(f"/* 16 байт палитры для порта 0C */\n")
        format_array(f, f"{prefix}_palette", pal_bytes)
        f.write(f"\n/* LZ-сжатые данные: заголовок + словарь + 4 LZ-потока */\n")
        format_array(f, f"{prefix}_screen_lz", output)

    print(f"  файл создан: {inc_path}")


if __name__ == "__main__":
    main()
