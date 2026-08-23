#!/usr/bin/env python3
"""
bmp2inc.py — конвертация 16-цветного BMP в .inc для ROM Вектора-06Ц.

Использование:
    python3 bmp2inc.py path/to/image.bmp

Скрипт создаёт файл inc рядом с исходным: image.bmp -> image_bmp.inc.

Формат Вектора-06Ц (256x256, 16 цветов, 4 битовые плоскости):
  - экранное ОЗУ 32 КБ: 0x8000-0xFFFF, по 8 КБ на плоскость:
      0x8000 — плоскость 3 (вес цвета 8)
      0xA000 — плоскость 2 (вес цвета 4)
      0xC000 — плоскость 1 (вес цвета 2)
      0xE000 — плоскость 0 (вес цвета 1)
  - внутри плоскости: 32 блока по 256 байт, номер блока = x/8;
    байт с индексом i в блоке хранит строку экрана y = (256 - i) & 0xFF
    (при регистре верхней строки = 0, как ставит z88dk crt);
  - внутри байта: левый пиксель — старший бит (7 - (x & 7));
  - номер цвета 0-15 = палитровый индекс BMP (плоскость 0 — бит 0 и т.д.);
  - байт палитры (порт 0C): D0-D2 красный (веса 1,2,4),
    D3-D5 зелёный (1,2,4), D6-D7 синий (2,4) — 256 цветов из 512.

Inc-файл содержит RLE-сжатый массив *_screen_rle — прямоугольник
картинки: заголовок из двух байт (ширина в 8-пиксельных блоках,
высота; 0 означает 256) и пары (количество, байт), количество 1-255,
конец потока — количество 0. Порядок байт: плоскости с весами цвета
8, 4, 2, 1; в плоскости блоки слева направо; в блоке строки сверху
вниз. Выводит graph_rle_expand(src, x, y) (lib/graphrle.asm):
(x, y) — левый верхний угол, x кратно 8; область вне картинки
не меняется. Ширина картинки дополняется до кратной 8 цветом 0.

Палитровые индексы перераспределяются под содержимое картинки: пиксель
с индексом i рисуется popcount(i) плоскостями, поэтому жадное назначение
даёт самому частому цвету индекс 0 (ни одной плоскости), следующим четырём —
однобитовые 1,2,4,8 и т.д. Затем локальным поиском (парные перестановки
индексов) размер RLE-потока минимизируется напрямую. Цвета, совпадающие
после квантования до байта Вектора, объединяются.
"""

import os
import struct
import sys

SCREEN_W = 256
SCREEN_H = 256


def die(msg):
    print(f"bmp2inc: {msg}", file=sys.stderr)
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
    """Поток прямоугольника width×height в порядке записи распаковщиком
    (graphrle.asm): плоскости с весами цвета 8, 4, 2, 1; в плоскости —
    блоки по 8 пикселей слева направо; в блоке — строки сверху вниз.
    Ширина дополняется до кратной 8 цветом 0."""
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


# Индексы палитры в порядке возрастания «стоимости» (числа плоскостей):
# 0 бит, 1 бит, 2 бита, 3 бита, 4 бита.
INDEX_ORDER = [0,
               1, 2, 4, 8,
               3, 5, 6, 9, 10, 12,
               7, 11, 13, 14,
               15]


def popcount(v):
    return bin(v).count("1")


def color_groups(width, height, pixels, palette):
    """Группы цветов, совпадающих после квантования до байта Вектора.
    Возвращает список (число точек, старые индексы, байт Вектора),
    от частых к редким, и байты Вектора для старых индексов."""
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


def greedy_perm(grouped, pin_index0=False):
    """Жадное назначение: частым группам — малобитовые индексы.
    Возвращает perm: perm[старый индекс] = новый индекс. Неиспользуемым
    («мёртвым») старым индексам раздаются оставшиеся значения, чтобы
    perm оставался перестановкой 0-15 (иначе обмены в поиске могут
    слить два цвета в один).
    pin_index0: если True, старый индекс 0 всегда получает новый 0."""
    perm = [0] * 16
    n_groups = 0
    assigned = set()

    if pin_index0:
        # Найти группу, содержащую старый индекс 0
        for (total, idxs, vb), new_idx in zip(grouped, INDEX_ORDER):
            if 0 in idxs:
                for i in idxs:
                    perm[i] = 0
                    assigned.add(i)
                n_groups += 1
                break
        # Остальные группы назначаем, пропуская уже занятые
        order_idx = 1  # начинаем со второго элемента INDEX_ORDER
        for (total, idxs, vb) in grouped:
            if any(i in assigned for i in idxs):
                continue
            while order_idx < len(INDEX_ORDER) and INDEX_ORDER[order_idx] in assigned:
                order_idx += 1
            if order_idx >= len(INDEX_ORDER):
                break
            new_idx = INDEX_ORDER[order_idx]
            for i in idxs:
                perm[i] = new_idx
                assigned.add(i)
            n_groups += 1
            order_idx += 1
    else:
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
    """Битовые маски (int, длина = блоков×высота) положений пикселей
    каждого старого индекса в потоке прямоугольника: в байте потока
    установлены биты пикселей с этим индексом."""
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


def rle_size_of_perm(perm, masks, plane_len, cache={}):
    """Размер RLE прямоугольника (плюс 2 байта заголовка) при назначении
    perm[старый]=новый. Плоскость = ИЛИ масок цветов с соответствующим
    битом индекса; одинаковые наборы цветов кэшируются."""
    data = bytearray()
    for p in (3, 2, 1, 0):              # порядок в памяти: веса 8,4,2,1
        subset = tuple(i for i in range(16) if (perm[i] >> p) & 1)
        acc = cache.get(subset)
        if acc is None:
            acc = 0
            for i in subset:
                acc |= masks[i]
            cache[subset] = acc
        data += acc.to_bytes(plane_len, "little")
    return 2 + len(rle_compress(data))


def local_search(perm, masks, same_class_only, plane_len, pinned=frozenset()):
    """Покоординатный спуск парными перестановками индексов.
    Обмениваются любые старые индексы 0-15: через «мёртвые» слоты
    живые цвета могут получать любые из 16 новых индексов (perm —
    перестановка, слияния цветов не происходит).
    same_class_only: переставлять только индексы с тем же числом битов
    (частые цвета остаются на однобитовых индексах и т.д.).
    pinned: множество старых индексов, которые нельзя переставлять."""
    perm = list(perm)
    cur = rle_size_of_perm(perm, masks, plane_len)
    while True:
        best_pair, best_size = None, cur
        for a in range(16):
            if a in pinned:
                continue
            for b in range(a + 1, 16):
                if b in pinned:
                    continue
                if same_class_only and popcount(perm[a]) != popcount(perm[b]):
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
        print(f"    ... обмен индексов цветов {a}<->{b}: RLE {cur} байт")


def format_array(f, name, data, per_line=16):
    f.write(f"const unsigned char {name}[{len(data)}] = {{\n")
    for i in range(0, len(data), per_line):
        chunk = data[i:i + per_line]
        f.write("    " + ", ".join(f"0x{v:02X}" for v in chunk) + ",\n")
    f.write("};\n")


def main():
    if len(sys.argv) < 2:
        print(f"Использование: {sys.argv[0]} [--bg-black] <файл.bmp>",
              file=sys.stderr)
        sys.exit(1)

    bg_black = False
    args = [a for a in sys.argv[1:]]
    if '--bg-black' in args:
        bg_black = True
        args.remove('--bg-black')
    if len(args) != 1:
        print(f"Использование: {sys.argv[0]} [--bg-black] <файл.bmp>",
              file=sys.stderr)
        sys.exit(1)

    bmp_path = args[0]
    if not os.path.isfile(bmp_path):
        die(f"файл не найден: {bmp_path}")

    stem = os.path.splitext(os.path.basename(bmp_path))[0]
    prefix = f"{stem}_bmp"
    inc_path = os.path.join(os.path.dirname(bmp_path), f"{prefix}.inc")

    width, height, pixels, palette = parse_bmp(bmp_path)
    grouped, old_pal_bytes = color_groups(width, height, pixels, palette)
    masks = make_masks(width, height, pixels)
    plane_len = ((width + 7) // 8) * height
    active = sorted({v for row in pixels for v in row})

    print(f"{bmp_path} ({width}x{height}) -> {inc_path}")
    print("  частоты цветов:")
    for total, idxs, vb in grouped:
        old = ",".join(str(i) for i in idxs)
        print(f"    точек {total:6d}: индексы [{old}], цвет 0x{vb:02X}")

    identity = list(range(16))
    greedy = greedy_perm(grouped, pin_index0=bg_black)
    pinned = frozenset({0}) if bg_black else frozenset()
    candidates = [
        ("палитра BMP как есть", identity, False),
        ("жадное по частоте, перестановки внутри классов", greedy, True),
        ("жадное по частоте, свободные перестановки", greedy, False),
    ]
    best_perm, best_size, best_name = None, None, None
    for name, seed, cls in candidates:
        print(f"  поиск: {name}")
        perm, size = local_search(seed, masks, cls, plane_len, pinned=pinned)
        if best_size is None or size < best_size:
            best_perm, best_size, best_name = perm, size, name

    perm = best_perm
    print(f"  лучший вариант: {best_name}, RLE {best_size} байт")

    new_pal = [0] * 16
    for old in active:
        new_pal[perm[old]] = old_pal_bytes[old]

    if bg_black and 0 in active:
        # Сдвигаем палитру: цвет старого индекса 0 уходит на свободное
        # место, а позиция 0 освобождается под чёрный фон.
        saved_color = new_pal[perm[0]]
        if saved_color != 0:
            used_new = {perm[v] for v in active}
            spare = next(i for i in range(16) if i not in used_new)
            new_pal[spare] = saved_color
            perm[0] = spare
            # Если другие старые индексы указывали на позицию 0,
            # перенаправляем их на spare тоже.
            for old in range(16):
                if old != 0 and perm[old] == 0:
                    perm[old] = spare
        new_pal[0] = 0  # позиция 0 — чёрный (фон)

    new_pixels = [[perm[v] for v in row] for row in pixels]
    rect = build_rect(width, height, new_pixels)
    w8 = (width + 7) // 8
    rle = bytes([w8 & 0xFF, height & 0xFF]) + rle_compress(rect)

    with open(inc_path, "w") as f:
        f.write(f"/* Автоматически сгенерировано bmp2inc.py из {os.path.basename(bmp_path)} */\n")
        f.write(f"/* {width}x{height}, 16 цветов; прямоугольник выводится "
                f"graph_rle_expand(src, x, y), x кратно 8 */\n\n")
        f.write(f"#define {prefix}_width {width}\n")
        f.write(f"#define {prefix}_height {height}\n\n")
        f.write(f"/* 16 байт палитры для порта 0C (индексы оптимизированы под картинку) */\n")
        format_array(f, f"{prefix}_palette", new_pal)
        f.write("\n/* RLE-поток прямоугольника картинки: заголовок "
                "(ширина в блоках, высота; 0 = 256), пары (количество, "
                "байт), конец — 0 */\n")
        format_array(f, f"{prefix}_screen_rle", rle)

    counts = {}
    for row in pixels:
        for v in row:
            counts[v] = counts.get(v, 0) + 1
    print("  итоговое назначение (старый индекс -> новый):")
    for total, idxs, vb in grouped:
        old = ",".join(str(i) for i in idxs)
        new = perm[idxs[0]]
        print(f"    точек {total:6d}: [{old}] -> индекс {new:2d} "
              f"(0x{new:X}, плоскостей: {popcount(new)}) цвет 0x{vb:02X}")
    print(f"  прямоугольник: {len(rect)} байт -> RLE {len(rle)} байт "
          f"(с заголовком)")
    print(f"  палитра: {' '.join(f'{v:02X}' for v in new_pal)}")


if __name__ == "__main__":
    main()
