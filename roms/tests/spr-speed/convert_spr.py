#!/usr/bin/env python3
"""
Конвертер mario_old.inc (тайл-префаб) → mario_new.inc (SPR_FORMAT)

Старый формат:
  Заголовок: [wcells, hcells, hpix, nTiles]
  nTiles записей: [pos] + 8×(op, b0, b1)
  pos = (col << 2) | row
  
  Каждый тайл 8x8: 8 строк, каждая строка = (op, b0, b1)
  op — маска (какие пиксели активны)
  b0 — биты плоскостей П3,П2 (старший бит пикселя)
  b1 — биты плоскостей П1,П0 (младший бит пикселя)
  
  Композиция: res = cur ^ ((cur ^ bit) & op)
  Если op бит = 1: result = bit (из b0/b1)
  Если op бит = 0: result = 0 (фон)

Новый формат (SPR_FORMAT.MD + SHIFT/LEN):
  Заголовок: [FLAGS, COLS, DEPTH]
  DATA: по плоскостям (П3, П2, П1, П0), в каждой — по COLS столбцов:
    [SHIFT, LEN] + LEN байт (строки с первой по последнюю ненулевую)
  SHIFT — сдвиг от верхней строки спрайта до первой выводимой строки
  LEN   — кол-во выводимых байтов в столбце (0 = столбец пуст)
  FLAGS: bit0=П3, bit1=П2, bit2=П1, bit3=П0, bit6=OR-композит

Вариант с маской (mario_new_mask.inc, SPR_FORMAT.MD §3/§4.6/§5):
  Заголовок: [FLAGS, COLS, DEPTH] + TABLE + DATA
  TABLE: COLS пар [SHIFT, LEN] — ОДНА на все блоки (sparse, bit5)
  DATA:  БЛОК МАСКИ (Σ LEN байт) первым — она применяется первой, поэтому
         mask_base = DATA без вычислений; за ней прогоны цветных
         плоскостей (П3,П2,П1,П0) подряд по COLS прогонов, без префиксов:
         указатель данных идёт линейно через все блоки.
  МАСКА = ~(П1 | П0) построчно — «¬S», маска сохранения фона (§5).
  Прогоны — ОБЩИЙ (union) span всех цветных плоскостей столбца, иначе
  курсоры цвета и маски разойдутся.
  Композиция: dst = (dst AND mask) OR color — фон сохраняется в строках,
  где спрайт прозрачен, поэтому отдельный erase не нужен.
  FLAGS: bit2=П1, bit3=П0, bit4=есть маска, bit5=sparse(TABLE), bit6=OR
"""

import sys
import re
from pathlib import Path

def parse_old_format(data):
    """Парсит тайл-префаб данные."""
    wcells = data[0]
    hcells = data[1]
    hpix = data[2]
    nTiles = data[3]
    
    tiles = []
    idx = 4
    for _ in range(nTiles):
        pos = data[idx]
        col = pos >> 2
        row = pos & 3
        idx += 1
        
        rows = []
        for _ in range(8):
            op = data[idx]
            b0 = data[idx + 1]
            b1 = data[idx + 2]
            idx += 3
            rows.append((op, b0, b1))
        
        tiles.append((col, row, rows))
    
    return wcells, hcells, hpix, tiles

def extract_planes_from_tile(rows):
    """
    Извлекает данные плоскостей из тайла (8 строк по 3 байта).
    
    По spr_old.asm (dr_p0/dr_p1):
    - b0 = данные плоскости П0 (VRAM E000)
    - b1 = данные плоскости П1 (VRAM C000)
    - op = маска прозрачности (бит=0 => пиксель прозрачный)
    
    Композиция старого алгоритма: res = cur ^ ((cur ^ bit) & op)
    Для нового flat-алгоритма с erase-фоном: color = bit & op
    (прозрачные пиксели = 0, фон зачищается отдельно).
    
    Возвращает: 4 списка по 8 байт (по одному на плоскость)
    """
    planes = {3: [], 2: [], 1: [], 0: []}
    
    for op, b0, b1 in rows:
        # П0 (E000) = b0, маскировано op
        # П1 (C000) = b1, маскировано op
        # П2, П3 не используются Марио
        planes[0].append(b0 & op)
        planes[1].append(b1 & op)
        planes[2].append(0)
        planes[3].append(0)
    
    return planes

def build_columns(wcells, hcells, tiles):
    """
    Строит плотные колонки из тайлов.
    Возвращает: columns[col][plane_id] = список байт
    """
    # Инициализируем пустые колонки
    columns = {c: {p: [] for p in range(4)} for c in range(wcells)}
    
    # Для каждой колонки собираем тайлы сверху вниз
    for col in range(wcells):
        for row in range(hcells):
            # Находим тайл для этой позиции
            tile_data = None
            for t_col, t_row, rows in tiles:
                if t_col == col and t_row == row:
                    tile_data = rows
                    break
            
            if tile_data:
                planes = extract_planes_from_tile(tile_data)
                for plane_id in range(4):
                    columns[col][plane_id].extend(planes[plane_id])
            else:
                # Пустой тайл — добавляем нули
                for plane_id in range(4):
                    columns[col][plane_id].extend([0] * 8)
    
    return columns

def compact_column(col_bytes):
    """
    Упаковывает плотную колонку в [SHIFT, LEN] + данные.
    SHIFT — индекс первой ненулевой строки (сдвиг от верха спрайта),
    LEN — число строк с первой по последнюю ненулевую (включая
    внутренние нули). Полностью пустая колонка -> [0, 0].
    """
    first = None
    last = None
    for i, b in enumerate(col_bytes):
        if b != 0:
            if first is None:
                first = i
            last = i
    if first is None:
        return [0, 0]
    return [first, last - first + 1] + col_bytes[first:last + 1]

def build_descriptor(columns, wcells, hcells, use_or=True):
    """
    Строит дескриптор в новом формате.
    """
    # Проверяем какие плоскости непустые
    plane_present = {3: False, 2: False, 1: False, 0: False}
    
    for col in range(wcells):
        for plane_id in range(4):
            if any(b != 0 for b in columns[col][plane_id]):
                plane_present[plane_id] = True
    
    # Строим FLAGS
    # Марио использует П1 (C000) и П0 (E000), flat-режим (без OR)
    flags = 0
    if plane_present[3]: flags |= 0x01
    if plane_present[2]: flags |= 0x02
    if plane_present[1]: flags |= 0x04
    if plane_present[0]: flags |= 0x08
    
    cols = wcells
    depth = hcells  # в тайл-рядах
    
    # Собираем DATA: для каждой плоскости (П3, П2, П1, П0) подряд по COLS
    # столбцов; каждый столбец — [SHIFT, LEN] + LEN байт (без хвостовых
    # и головных нулей).
    data = []
    for plane_id in [3, 2, 1, 0]:
        if not plane_present[plane_id]:
            continue

        for col in range(wcells):
            data.extend(compact_column(columns[col][plane_id]))

    return flags, cols, depth, data

# --- вариант с маской (SPR_FORMAT.MD §3/§4.6/§5) -------------------------
FLAG_MASK   = 0x10   # bit4: есть блок маски
FLAG_SPARSE = 0x20   # bit5: per-column таблица (SHIFT,LEN), общая для блоков
FLAG_OR     = 0x40   # bit6: композиция dst = (dst AND msk) OR color

def union_span(col_planes):
    """Общий (union) прогон столбца по всем цветным плоскостям: первая..
    последняя строка, где хоть одна плоскость ненулевая. Возвращает
    (SHIFT, LEN); пустой столбец -> (0, 0)."""
    n = len(col_planes[0])
    first = last = None
    for i in range(n):
        if any(p[i] for p in col_planes):
            if first is None:
                first = i
            last = i
    if first is None:
        return 0, 0
    return first, last - first + 1

def build_descriptor_mask(columns, wcells, hcells):
    """Дескриптор с маской: общая TABLE + прогоны цветных плоскостей +
    блок маски после них (§4.6). Прогоны всех блоков синхронны (одни и те
    же SHIFT/LEN из TABLE), поэтому ядро читает цвет и маску в замке
    двумя курсорами: DE=цвет, BC=маска (§4.4 sbf_plane_or)."""
    present = [p for p in (3, 2, 1, 0)
               if any(any(columns[c][p]) for c in range(wcells))]
    flags = 0
    for p in present:
        flags |= 1 << (3 - p)          # bit0=П3, bit1=П2, bit2=П1, bit3=П0
    flags |= FLAG_MASK | FLAG_SPARSE | FLAG_OR

    # Общий span: маска и цветные прогоны обязаны идти в замке, иначе
    # курсоры разойдутся; строки вне span во всех плоскостях нулевые.
    table = []
    spans = []
    for c in range(wcells):
        s, l = union_span([columns[c][p] for p in present])
        spans.append((s, l))
        table += [s, l]

    data = []

    # Маска — ПЕРВЫМ блоком DATA: она применяется первой, поэтому
    # mask_base = DATA (никакой арифметики в setup). Затем плоские
    # прогоны цветных плоскостей — курсор данных идёт линейно.
    mask_len = 0
    for c in range(wcells):
        s, l = spans[c]
        for i in range(s, s + l):
            acc = 0
            for p in present:
                acc |= columns[c][p][i]
            data.append((~acc) & 0xFF)
        mask_len += l

    for p in present:
        for c in range(wcells):
            s, l = spans[c]
            data += columns[c][p][s:s + l]

    return flags, wcells, hcells, table, data, mask_len

def format_c_array(name, data, indent=4):
    """Форматирует данные как C-массив."""
    lines = []
    prefix = ' ' * indent
    line = prefix
    for i, b in enumerate(data):
        line += f'0x{b:02X}, '
        if (i + 1) % 16 == 0:
            lines.append(line)
            line = prefix
    if line != prefix:
        lines.append(line)
    return '\n'.join(lines)

def convert_sprite(name, old_data, use_or=True):
    """Конвертирует один спрайт."""
    wcells, hcells, hpix, tiles = parse_old_format(old_data)
    columns = build_columns(wcells, hcells, tiles)
    flags, cols, depth, data = build_descriptor(columns, wcells, hcells, use_or)
    
    return {
        'name': name,
        'flags': flags,
        'cols': cols,
        'depth': depth,
        'data': data,
        'wcells': wcells,
        'hcells': hcells,
        'hpix': hpix,
        'columns': columns
    }

def main():
    # Читаем mario_old.inc
    old_file = Path('/home/alexey/Projects/vector-games/roms/tests/spr-speed/mario_old.inc')
    old_content = old_file.read_text()
    
    # Парсим массивы mario1_l, mario2_l, mario3_l
    sprites = {}
    for match in re.finditer(r'static const unsigned char (mario\d_l)\[\] = \{([^}]+)\}', old_content):
        name = match.group(1)
        data_str = match.group(2)
        data = [int(x, 16) for x in re.findall(r'0x[0-9A-Fa-f]+', data_str)]
        sprites[name] = data
    
    print(f"Найдено спрайтов: {list(sprites.keys())}")
    
    # Конвертируем каждый спрайт
    converted = []
    converted_mask = []
    for name in ['mario1_l', 'mario2_l', 'mario3_l']:
        if name in sprites:
            desc = convert_sprite(name, sprites[name], use_or=True)
            converted.append(desc)
            print(f"{name}: FLAGS=0x{desc['flags']:02X}, COLS={desc['cols']}, DEPTH={desc['depth']}, DATA={len(desc['data'])} байт")
            fl, co, de, tab, dat, mlen = build_descriptor_mask(
                desc['columns'], desc['wcells'], desc['hcells'])
            converted_mask.append({
                'name': name, 'flags': fl, 'cols': co, 'depth': de,
                'table': tab, 'data': dat
            })
            print(f"  +маска: FLAGS=0x{fl:02X}, TABLE={len(tab)}, DATA={len(dat)} байт (из них маска {mlen})")
    
    # Генерируем mario_new.inc
    output = []
    output.append('/*')
    output.append(' * mario_new.inc — спрайты идущего влево Марио в новом формате SPR_FORMAT.')
    output.append(' * Формат: [FLAGS, COLS, DEPTH] + DATA (по плоскостям)')
    output.append(' * DATA на столбец: [SHIFT, LEN] + LEN байт (первая..последняя ненулевая строка)')
    output.append(' * FLAGS: bit0=П3, bit1=П2, bit2=П1, bit3=П0, bit6=OR-композит')
    output.append(' *')
    output.append(' * Используются только 3 фазы ходьбы (walk_seq = {0,1,2,1} из mario-dbl):')
    output.append(' *   mario1_new — фаза 0 (ноги вместе)')
    output.append(' *   mario2_new — фаза 1 (шаг вперёд)')
    output.append(' *   mario3_new — фаза 2 (широкий шаг)')
    output.append(' */')
    output.append('')
    output.append('#define MARIO_NPOSE   3')
    output.append('#define MARIO_HCELLS  4')
    output.append('#define MARIO_HPIX    32')
    output.append('')
    
    for desc in converted:
        name_new = desc['name'].replace('_l', '_new')
        output.append(f'static const unsigned char {name_new}[] = {{')
        output.append(f'    0x{desc["flags"]:02X}, 0x{desc["cols"]:02X}, 0x{desc["depth"]:02X},')
        output.append(format_c_array('', desc['data'], 4))
        output.append('};')
        output.append('')
    
    output.append('/* таблица указателей: [фаза] 0..2 — только ходьба (walk_seq из mario-dbl) */')
    output.append('static const unsigned char * const mario_frames_new[MARIO_NPOSE] = {')
    output.append('    mario1_new, mario2_new, mario3_new')
    output.append('};')
    output.append('')
    
    # Записываем файл
    new_file = Path('/home/alexey/Projects/vector-games/roms/tests/spr-speed/mario_new.inc')
    new_file.write_text('\n'.join(output))
    print(f"\nСоздан {new_file}")

    # --- вариант с маской: mario_new_mask.inc ------------------------------
    mask_out = []
    mask_out.append('/*')
    mask_out.append(' * mario_new_mask.inc — те же спрайты с маской и OR-композитом')
    mask_out.append(' * (SPR_FORMAT.MD §3/§4.6/§5): [FLAGS, COLS, DEPTH] + TABLE + DATA.')
    mask_out.append(' * TABLE: COLS пар [SHIFT, LEN] — общая для всех блоков (sparse, bit5).')
    mask_out.append(' * DATA: блок МАСКИ первым (mask_base = DATA), затем прогоны П1, П0')
    mask_out.append(' * — указатель данных идёт линейно через все блоки.')
    mask_out.append(' * Маска = ~(П1|П0) построчно: композиция dst = (dst AND msk) OR color')
    mask_out.append(' * сохраняет фон вне силуэта — отдельный erase не нужен.')
    mask_out.append(' * FLAGS: bit2=П1, bit3=П0, bit4=маска, bit5=sparse, bit6=OR')
    mask_out.append(' */')
    mask_out.append('')
    mask_out.append('#ifndef MARIO_NPOSE')
    mask_out.append('#define MARIO_NPOSE   3')
    mask_out.append('#endif')
    mask_out.append('')

    for desc_m in converted_mask:
        name_m = desc_m['name'].replace('_l', '_new_mask')
        mask_out.append(f'static const unsigned char {name_m}[] = {{')
        mask_out.append(f'    0x{desc_m["flags"]:02X}, 0x{desc_m["cols"]:02X}, 0x{desc_m["depth"]:02X},')
        mask_out.append('    /* TABLE: пары [SHIFT, LEN] на столбец (общая для всех блоков) */')
        mask_out.append(format_c_array('', desc_m['table'], 4))
        mask_out.append('    /* DATA: блок маски, затем прогоны П1, П0 — все по TABLE */')
        mask_out.append(format_c_array('', desc_m['data'], 4))
        mask_out.append('};')
        mask_out.append('')

    mask_out.append('/* таблица указателей: [фаза] 0..2 — только ходьба (walk_seq из mario-dbl) */')
    mask_out.append('static const unsigned char * const mario_frames_new_mask[MARIO_NPOSE] = {')
    mask_out.append('    mario1_new_mask, mario2_new_mask, mario3_new_mask')
    mask_out.append('};')
    mask_out.append('')

    mask_file = Path('/home/alexey/Projects/vector-games/roms/tests/spr-speed/mario_new_mask.inc')
    mask_file.write_text('\n'.join(mask_out))
    print(f"Создан {mask_file}")

if __name__ == '__main__':
    main()
