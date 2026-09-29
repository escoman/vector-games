#!/usr/bin/env python3
"""split_data.py — TZ2 Stage R0: вынос данных из address-ordered layout.asm в inc-файлы.

Читает оригинальный asm/layout.asm (экспорт v06c-asm-export, Stage 10), находит
блоки чистых данных (глифы, карты уровней, музыкальные партитуры), выносит каждый
блок в remake/inc/*.inc, а в layout.asm заменяет блок на include. Карта уровней
(data_level_maps, 5715 байт, 20 уровней без постоянного stride) режется на 20
отдельных файлов inc/level_NN.inc по таблице смещений data_level_map_offsets.

Байты не меняются: defb-строки переиздаются в том же формате (8 байт на строку,
NNh, ведущий 0 перед буквой). Контроль — побайтовая сверка собранного ROM
с src/riseout.rom (цель verify в Makefile).

Запуск (из remake/):
    python3 tools/split_data.py --src ../asm/layout.asm --dst layout.asm --inc inc
"""
import argparse
import os
import re
import sys

# Смещения упакованных карт уровней 1..20 относительно базы 0x3594
# (data_level_map_offsets @0x253D, Stage 7). Конец последней = 5715.
LEVEL_OFFSETS = [0, 278, 481, 800, 1053, 1401, 1713, 2049, 2355, 2675,
                 3051, 3230, 3584, 3788, 4140, 4345, 4678, 4898, 5119, 5480]
LEVEL_TOTAL = 5715

# Метка блока -> список inc-файлов (один; data_level_maps режется на 20).
EXTRACT = {
    'data_note_freq_table_title': ['music_note_freq.inc'],
    'data_music_track_level_03':  ['music_track_level_03.inc'],
    'data_glyph_block':           ['glyph_block.inc'],
    'data_glyph_mode_table':      ['glyph_mode_table.inc'],
    'data_level_maps':            ['level_%02d.inc' % (i + 1) for i in range(20)],
    'data_music_track_title_02':  ['music_track_title_02.inc'],
    'data_music_track_title_01':  ['music_track_title_01.inc'],
    'data_music_track_title_03':  ['music_track_title_03.inc'],
}

DEFB_RE = re.compile(r'^\s*defb\s+')

# Хвост layout.asm («Symbols at addresses owned by another unit») держит
# equ-алиасы data_level_02..20 на адреса внутри data_level_maps. После выноса
# карт эти метки становятся настоящими в inc/level_NN.inc — алиасы снимаем.
ALIAS_EQU_RE = re.compile(r'^(data_level_(?:0[2-9]|1[0-9]|20))\s+equ\b')

# Ожидаемые объёмы блоков (Stage 6/7/9): ранний контроль разбора defb.
EXPECT = {
    'data_glyph_block': 1024,
    'data_glyph_mode_table': 128,
    'data_note_freq_table_title': 182,
    'data_music_track_level_03': 65,
    'data_music_track_title_02': 351,
    'data_level_maps': LEVEL_TOTAL,
}
# Байт defb: 2–3 hex-цифры + 'h' (экспортёр пишет ведущий 0 перед буквой: 0F1h).
BYTE_RE = re.compile(r'(?<![0-9A-Za-z_])([0-9A-Fa-f]{2,3})h(?![0-9A-Za-z_])')


def fmt_byte(v):
    s = '%02X' % v
    return ('0' + s if s[0].isalpha() else s) + 'h'


def glyph_comment(code):
    """Комментарий справа от растра: код глифа = код символа (шрифт ASCII).
    Исключения по Stage 6/7: на позициях 2B..2F и 3C лежат блочные/штриховые
    глифы (не пунктуация), 60..6F — тайлы поля и спец-клетки (не буквы),
    70..7F — вариантные растры тайлов."""
    if code == 0x20:
        return '; space (20h)'
    if 0x21 <= code <= 0x7E and not (0x2B <= code <= 0x2F or code in (0x3C,)) \
            and not 0x60 <= code <= 0x7F:
        return "; '%s' (%02Xh)" % (chr(code), code)
    if code == 0x60:
        return '; tile 00 — маркер старта игрока (Stage 7)'
    if code == 0x64:
        return '; tile 04 — целевая клетка (Stage 7)'
    if 0x61 <= code <= 0x6E:
        return '; tile %02X (Stage 7)' % (code - 0x60)
    if code == 0x6F:
        return '; tile 0F — пусто (Stage 7)'
    return None


def emit_defb(bytes_, comments=None):
    lines = []
    for n, i in enumerate(range(0, len(bytes_), 8)):
        line = '        defb    ' + ','.join(fmt_byte(b) for b in bytes_[i:i + 8])
        if comments and comments[n]:
            # колонка комментария: максимум 16 + 8*5 - 1 = 55 символов
            line = line.ljust(57) + comments[n]
        lines.append(line)
    return lines


def parse_block(lines, idx):
    """idx — строка метки. Возвращает (комментарий-сверху, байты, индекс-за-блоком)."""
    # непрерывная цепочка ';' строк непосредственно над меткой
    c0 = idx
    while c0 > 0 and lines[c0 - 1].startswith(';'):
        c0 -= 1
    comment = lines[c0:idx]
    j = idx + 1
    data = []
    while j < len(lines) and DEFB_RE.match(lines[j]):
        vals = BYTE_RE.findall(lines[j])
        if not vals:
            break
        for v in vals:
            b = int(v, 16)
            if b > 0xFF:
                sys.exit('строка %d: значение %s не байт' % (j + 1, v))
            data.append(b)
        j += 1
    return comment, data, j


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--src', required=True, help='исходный layout.asm (asm/layout.asm)')
    ap.add_argument('--dst', required=True, help='новый layout.asm (remake/layout.asm)')
    ap.add_argument('--inc', required=True, help='каталог inc-файлов (remake/inc)')
    args = ap.parse_args()

    with open(args.src, encoding='utf-8') as f:
        lines = f.read().splitlines()

    os.makedirs(args.inc, exist_ok=True)
    out = []
    written = set()
    dropped = 0
    i = 0
    while i < len(lines):
        if ALIAS_EQU_RE.match(lines[i]):
            dropped += 1
            i += 1
            continue
        m = re.match(r'^([A-Za-z_][A-Za-z0-9_]*):\s*$', lines[i])
        label = m.group(1) if m else None
        if label not in EXTRACT or label in written:
            out.append(lines[i])
            i += 1
            continue
        comment, data, j = parse_block(lines, i)
        if not data:
            sys.exit('%s: блок defb не найден' % label)
        if label in EXPECT and len(data) != EXPECT[label]:
            sys.exit('%s: %d байт != %d (ожидалось)' % (label, len(data), EXPECT[label]))
        files = EXTRACT[label]
        if label == 'data_level_maps':
            if len(data) != LEVEL_TOTAL:
                sys.exit('data_level_maps: %d байт != %d' % (len(data), LEVEL_TOTAL))
            for n, off in enumerate(LEVEL_OFFSETS):
                end = LEVEL_OFFSETS[n + 1] if n + 1 < len(LEVEL_OFFSETS) else LEVEL_TOTAL
                chunk = data[off:end]
                body = []
                if n == 0:
                    body += comment
                    body += ['data_level_maps:', 'data_level_01:']
                else:
                    body += ['; Уровень %d из 20 — упакованная карта: RLE-пары' % (n + 1),
                             '; (мл. ниббл = длина повтора, 0 ⇒ 256; ст. ниббл = код тайла,',
                             '; 0x6F → пусто). База 0x3594, смещение %d, длина %d байт.' % (off, len(chunk)),
                             '; Формат и адресация — комментарий в level_01.inc (Stage 7).',
                             'data_level_%02d:' % (n + 1)]
                body += emit_defb(chunk)
                path = os.path.join(args.inc, files[n])
                with open(path, 'w', encoding='utf-8') as f:
                    f.write('\n'.join(body) + '\n')
                print('%s: %d байт' % (path, len(chunk)))
            out.append('; Карты уровней 1..20 вынесены в inc/level_01.inc .. inc/level_20.inc')
            out.append('; (база data_level_maps = уровень 1; формат — комментарий в level_01.inc)')
            out += ['        include "inc/%s"' % f for f in files]
        else:
            comments = None
            if label == 'data_glyph_block':
                comments = [glyph_comment(n) for n in range(len(data) // 8)]
            body = comment + ['%s:' % label] + emit_defb(data, comments)
            path = os.path.join(args.inc, files[0])
            with open(path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(body) + '\n')
            print('%s: %d байт' % (path, len(data)))
            out.append('; %s: данные вынесены в inc/%s (комментарий там)' % (label, files[0]))
            out.append('        include "inc/%s"' % files[0])
        written.add(label)
        i = j

    missing = set(EXTRACT) - written
    if missing:
        sys.exit('блоки не найдены в layout: %s' % ', '.join(sorted(missing)))
    if dropped != 19:
        sys.exit('снято %d equ-алиасов data_level_NN, ожидалось 19' % dropped)
    with open(args.dst, 'w', encoding='utf-8') as f:
        f.write('\n'.join(out) + '\n')
    print('%s: записан (%d строк)' % (args.dst, len(out)))


if __name__ == '__main__':
    main()
