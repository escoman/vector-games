#!/usr/bin/env python3
"""split_data.py — TZ2 Stage R0: вынос данных из address-ordered layout.asm в inc-файлы.

Читает оригинальный asm/layout.asm (экспорт v06c-asm-export, Stage 10), находит
блоки чистых данных (глифы, карты уровней, музыкальные партитуры), выносит каждый
блок в remake/inc/*.inc, а в layout.asm заменяет блок на include. Карта уровней
(data_level_maps, 5715 байт, 20 уровней без постоянного stride) режется на 20
отдельных файлов inc/level_NN.inc по таблице смещений data_level_map_offsets.

Байты не меняются: defb-строки переиздаются в том же формате (8 байт на строку,
NNh, ведущий 0 перед буквой). Второй проход — адресные immediate в командах
(LXI с базами ROM-блоков и RAM-областей) заменяются на метки/выражения:
метки разрешаются в те же адреса, поэтому байты обязаны совпасть. Контроль —
побайтовая сверка собранного ROM с src/riseout.rom (цель verify в Makefile).

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
    'gap_1E9C':                   ['level_names.inc'],
    'data_level_keywords':        ['level_keywords.inc'],
}

# Текстовые регионы: непрерывные цепочки «строки + таблицы записей» (только
# метки/defb/комментарии, без кода) переносятся в inc дословно — адреса
# сохраняются. Границы: (стартовая метка, метка-конец, файл). Комментарий
# над меткой-концом остаётся в layout.asm.
REGIONS = [
    ('data_msg_records',          'func_draw_counter_value',     'strings_msg.inc'),
    ('data_records_keyword',      'func_draw_text_record',       'strings_keyword.inc'),
    ('data_records_player_color', 'func_find_player_start',      'strings_player_color.inc'),
    ('str_ready',                 'func_clear_cells_and_text',   'strings_ready.inc'),
    ('str_game_over',             'func_draw_player_speed_text', 'strings_game_over.inc'),
    ('str_player_label',          'func_count_player_cells',     'strings_player_label.inc'),
    ('str_hud_status',            'func_level_loader',           'strings_hud_status.inc'),
    ('data_title_records',        'lbl_2c22',                    'strings_title.inc'),
    ('data_records_players_count','lbl_2ca4',                    'strings_menu_players.inc'),
    ('data_records_speed_menu',   'func_draw_text_records',      'strings_menu_speed.inc'),
]
LABEL_RE = re.compile(r'^([A-Za-z_][A-Za-z0-9_]*):\s*$')

# Одиночные строки без терминатора: копируются func_memcpy_bc, длина зашита
# в коде. Метка _end после N-го байта позволяет выразить её разностью меток.
TEXT_ENDS = {
    'str_player_label': 7,    # PLAYER^ → 0x718C
    'str_ready': 9,           # ^ READY ^ → 0x71CB
    'str_game_over': 13,      # ^ GAME OVER ^ → 0x714A
    'str_high_score': 17,     # «HIGH SCORE: 00» → 0x71C8 целиком; «:» из Stage-комментария вне блока
}
# Регионы, которые собираются через build_strings_text (остальные — дословно).
TEXT_REGIONS = {'strings_player_label.inc', 'strings_ready.inc', 'strings_game_over.inc'}

DEFB_RE = re.compile(r'^\s*defb\s+')

# Шапка RAM-меток: области, куда игра копирует данные (Stage 6/7). Добавляется
# в начало генерируемого layout.asm до первого использования.
RAM_EQU_HEADER = [
    '; === RAM-области аппаратного слоя (Stage 6/7). Адресные immediate в коде ===',
    '; === заменены на эти метки; адреса как в оригинале, байты идентичны (verify).',
    'ram_mode_table      equ     5800h   ; режимы вывода глифов: mode(code) = +07h+8*code (65..6F: +8*code)',
    'ram_font            equ     6000h   ; растры шрифта: растр(code) = 8*code; коды 80..FF — зеркало в +400h',
    'ram_credit_glyphs   equ     6700h   ; растры кредит-полосы, коды E0..FF (копия data_credits_logo_strip)',
    'ram_field_area      equ     7000h   ; область клеток поля с краями: ряды stride 20h, карта идёт с +40h',
    'ram_field_buffer    equ     ram_field_area+040h   ; развёрнутая карта уровня, 22×32 = 704 байта (до 72FFh)',
    'ram_hud_buffer      equ     7300h   ; буфер HUD/рамки (0x7300..0x75FE); он же граница выхода развёртки карты',
    'ram_text_page       equ     5400h   ; текстовая страница-зеркало клеток поля (те же смещения, что ram_field_area)',
    'ram_service_row     equ     5700h   ; служебная строка текстовой страницы (чистится пробелом при выходе из аттракта)',
    '; === VRAM: 4 бит-плоскости по 8 КБ (Stage 6) ===',
    'vram_plane_0        equ     8000h   ; плоскость 0: база VRAM и текста/точек',
    'vram_plane_size     equ     2000h   ; размер/шаг плоскости (8 КБ)',
    'vram_plane_1        equ     vram_plane_0+2000h   ; плоскость 1: текст и точки (имmediate не адресуется: рендер шагает base+size)',
    'vram_plane_2        equ     vram_plane_1+2000h   ; плоскость 2: оверлей точек RISEOUT (аттракт чистит с неё до FFFF)',
    'vram_plane_3        equ     vram_plane_1+4000h   ; плоскость 3: звёзды (единственный скроллер)',
    '; === Константы игры (Stage 7/9): прежде магические числа в коде ===',
    'level_count         equ     20      ; число уровней: CPI level_count+1 — обёртка var_level; CPI level_count — финал (intro); таблица смещений = level_count слов',
    'lives_start         equ     5       ; начальные жизни игрока (заливка слотов [0x7DAF..] и var_lives)',
    '',
]

# (regex, замена, ожидаемое число вхождений) — immediate→метка. Только lowercase:
# комментарии экспорта пишут мнемоники капсом и не задеваются. data_level_maps_addr_ptr
# хранит базу карт defb 94h,35h — заменяется выражением от data_level_maps.
REWRITES = [
    (r'lxi(\s+)h,3114h',  r'lxi\1h,data_glyph_block', 2),
    (r'lxi(\s+)h,3514h',  r'lxi\1h,data_glyph_mode_table', 1),
    (r'lxi(\s+)h,0721h',  r'lxi\1h,data_credits_logo_strip', 1),
    (r'lxi(\s+)h,301ch',  r'lxi\1h,data_note_freq_table_title', 3),
    (r'lxi(\s+)h,4e23h',  r'lxi\1h,data_music_track_title_01', 1),
    (r'lxi(\s+)b,4cc4h',  r'lxi\1b,data_music_track_title_02', 1),
    (r'lxi(\s+)d,4fb4h',  r'lxi\1d,data_music_track_title_03', 1),
    (r'lxi(\s+)h,3112h',  r'lxi\1h,data_music_track_level_01', 1),
    (r'lxi(\s+)b,3112h',  r'lxi\1b,data_music_track_level_01', 1),
    (r'lxi(\s+)d,30d2h',  r'lxi\1d,data_music_track_level_03', 1),
    (r'lxi(\s+)h,253dh',  r'lxi\1h,data_level_map_offsets', 1),
    (r'lxi(\s+)d,6000h',  r'lxi\1d,ram_font', 2),
    (r'lxi(\s+)d,5b00h',  r'lxi\1d,ram_mode_table+300h', 1),
    (r'lxi(\s+)d,6700h',  r'lxi\1d,ram_credit_glyphs', 1),
    (r'lxi(\s+)h,7040h',  r'lxi\1h,ram_field_buffer', 3),
    (r'lxi(\s+)h,7000h',  r'lxi\1h,ram_field_area', 12),
    (r'lxi(\s+)d,7000h',  r'lxi\1d,ram_field_area', 3),
    (r'lxi(\s+)h,7300h',  r'lxi\1h,ram_hud_buffer', 1),
    (r'lxi(\s+)d,7301h',  r'lxi\1d,ram_hud_buffer+1', 1),
    (r'lxi(\s+)d,7302h',  r'lxi\1d,ram_hud_buffer+2', 1),
    (r'lxi(\s+)h,7320h',  r'lxi\1h,ram_hud_buffer+20h', 1),
    (r'lxi(\s+)d,7442h',  r'lxi\1d,ram_hud_buffer+142h', 1),
    (r'lxi(\s+)h,7440h',  r'lxi\1h,ram_hud_buffer+140h', 1),
    (r'sta(\s+)7300h',    r'sta\1ram_hud_buffer', 1),
    (r'sta(\s+)7311h',    r'sta\1ram_hud_buffer+11h', 1),
    (r'sta(\s+)7440h',    r'sta\1ram_hud_buffer+140h', 1),
    (r'sta(\s+)7451h',    r'sta\1ram_hud_buffer+151h', 1),
    (r'lxi(\s+)h,5400h',  r'lxi\1h,ram_text_page', 6),
    (r'lxi(\s+)d,5400h',  r'lxi\1d,ram_text_page', 4),
    (r'lxi(\s+)h,5700h',  r'lxi\1h,ram_service_row', 1),
    (r'lxi(\s+)([hbd]),8000h',  r'lxi\1\2,vram_plane_0', 3),
    (r'lxi(\s+)d,2000h',  r'lxi\1d,vram_plane_size', 1),
    (r'lxi(\s+)([hbd]),0c000h', r'lxi\1\2,vram_plane_2', 2),
    (r'lxi(\s+)([hbd]),0e000h', r'lxi\1\2,vram_plane_3', 3),
    (r'cpi(\s+)15h',      r'cpi\1level_count+1', 1),
    (r'lxi(\s+)b,0405h',  r'lxi\1b,0400h+lives_start', 1),
    (r'mvi(\s+)a,05h(\n\s*sta\s+var_lives)', r'mvi\1a,lives_start\2', 1),
    (r'lxi(\s+)b,5807h',  r'lxi\1b,ram_mode_table+07h', 1),
    (r'lxi(\s+)b,5800h',  r'lxi\1b,ram_mode_table', 1),
    (r'lxi(\s+)h,5800h',  r'lxi\1h,ram_mode_table', 2),
    (r'lxi(\s+)d,0800h',  r'lxi\1d,ram_font-ram_mode_table', 2),
    (r'(data_level_maps_addr_ptr:\n\s+defb\s+)94h,35h',
     r'\1data_level_maps&0ffh,data_level_maps>>8', 1),
    # === Имена уровней и уточнение констант (Stage 7, блок gap_1E9C) ===
    (r'lxi(\s+)h,1e9ch', r'lxi\1h,data_level_names', 1),
    (r'lxi(\s+)h,1f49h', r'lxi\1h,data_level_keywords', 1),
    # === Таблица сообщений: код берёт записи по адресам (immediates → метки записей) ===
    (r'lxi(\s+)h,1ce2h', r'lxi\1h,data_msg_records', 1),
    (r'lxi(\s+)h,1d13h', r'lxi\1h,data_msg_rec_keyword_label', 1),
    (r'lxi(\s+)h,1d1fh', r'lxi\1h,data_msg_rec_good_luck', 1),
    (r'lxi(\s+)h,1d30h', r'lxi\1h,data_msg_rec_all_patterns', 1),
    # === Одиночные строки: база и длина копирования через метки (данные без терминатора) ===
    (r'(lxi\s+h,)2356h(\n\s+lxi\s+d,714ah\n\s+lxi\s+b,)000dh',
     r'\1str_game_over\2str_game_over_end-str_game_over', 1),
    (r'(lxi\s+h,)2363h(\n\s+lxi\s+d,71c8h\n\s+lxi\s+b,)0011h',
     r'\1str_high_score\2str_high_score_end-str_high_score', 1),
    (r'(lxi\s+h,)233ah(\n\s+lxi\s+d,71cbh\n\s+lxi\s+b,)0009h',
     r'\1str_ready\2str_ready_end-str_ready', 1),
    (r'(lxi\s+d,718ch\n\s+lxi\s+h,)2388h(\n\s+lxi\s+b,)0007h',
     r'\1str_player_label\2str_player_label_end-str_player_label', 1),
    (r'(lxi\s+h,)24b2h', r'\1str_hud_status', 1),
    (r'cpi(\s+)14h', r'cpi\1level_count', 2),
    (r'func_find_free_record_slot', r'func_level_name_ptr', 2),
    (r'(?m)^; Поиск свободного слота в таблице записей.*$',
     '; Указатель на имя уровня A (NUL-строка в data_level_names): LXI H,data_level_names; '
     'цикл A-1 раз — пропуск HL до ближайшего 00h (перебор не более 0x1E байт = ограничение '
     'длины имени); на выходе HL = начало имени уровня A. Единственный вызов — '
     'func_init_playfield_buffers (0x1C18, A=var_level): имя копируется циклом 0x1C2E в строку '
     'HUD 0x73E3 в кавычках-глифах 0x22/0x24 (строка NEXT SCENE IS). Имя find_free_record_slot '
     '(Stage 5) было ошибочным — слоты записей здесь не ищутся. Портов не трогает.', 1),
]

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
    'gap_1E9C': 173,
    'data_level_keywords': 80,
    'data_level_maps': LEVEL_TOTAL,
}
# Имена 20 уровней (декодированы из data_level_names); порядок = порядок ключей.
LEVEL_NAMES = ['UNDERGROUND', 'SNAKE', 'BEGIN', 'GRASP', 'LADDER',
               'TWIN TOWERS', 'ASCII', 'LOOPS', 'ROOMS', 'AMIDA',
               'FIFTH TOWER', 'IN THE LAKE', 'GRAVEYARD', 'PYRAMID^2',
               'PYRAMID^3', 'PERVERSE', 'PYRAMID^1', 'PYRAMID^4',
               'TRAPS', 'WATER TANK']
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


def parse_region_blocks(region_lines, tag):
    """Блоки региона: [(строки комментария сверху, метка, байты)].
    Комментарий после defb — уже следующий блок."""
    blocks = []
    cmt, label, data = [], None, []
    for ln in region_lines:
        if ln.startswith(';'):
            if label is not None:
                blocks.append((cmt, label, bytes(data)))
                label, data, cmt = None, [], []
            cmt.append(ln)
            continue
        m = LABEL_RE.match(ln)
        if m:
            if label is not None:
                blocks.append((cmt, label, bytes(data)))
                cmt = []
            label, data = m.group(1), []
            continue
        if DEFB_RE.match(ln):
            vals = BYTE_RE.findall(ln)
            if not vals:
                sys.exit('%s: строка без байтов: %r' % (tag, ln))
            for v in vals:
                b = int(v, 16)
                if b > 0xFF:
                    sys.exit('%s: значение %s не байт' % (tag, v))
                data.append(b)
            continue
        if ln.strip():
            sys.exit('%s: неожиданная строка %r' % (tag, ln))
    if label is not None:
        blocks.append((cmt, label, bytes(data)))
    return blocks


def build_strings_text(region_lines, tag):
    """Регион одиночных строк: блоки + метки _end после копируемых N байт —
    длина копирования в коде выражается разностью меток (терминатора в данных нет)."""
    blocks = parse_region_blocks(region_lines, tag)
    body = ['; Текстовый регион вынесен из layout.asm (адреса сохранены): строки без терминатора —',
            '; длину копирования держит код (func_memcpy_bc); метки _end позволяют',
            '; выразить её разностью меток (в коде — str_*_end-str_*).']
    for cmt, label, data in blocks:
        body += cmt
        body.append('%s:' % label)
        n = TEXT_ENDS.get(label)
        if n is None:
            body += emit_defb(data)
            continue
        if n > len(data):
            sys.exit('%s: %s: длина %d больше блока %d байт' % (tag, label, n, len(data)))
        body += emit_defb(data[:n])
        body.append('%s_end:' % label)
        if n < len(data):
            body.append('        defb    ' + ','.join(fmt_byte(b) for b in data[n:])
                        + '      ; не копируется (длина в коде — %d)' % n)
    return body


def build_strings_msg(region_lines):
    """Таблица сообщений: 12 записей [dst_lo,dst_hi,len]+строка → самосогласованный inc.
    dst символизируется через ram_hud_buffer, len = метка_end-метка (пересчитывается
    ассемблером); каждое значение сверяется с оригинальными байтами."""
    blocks = parse_region_blocks(region_lines, 'strings_msg')
    if len(blocks) != 24:
        sys.exit('strings_msg: %d блоков вместо 24 (12 записей)' % len(blocks))
    body = ['; Таблица сообщений 0x1CE2..0x1DA5: 12 записей [dst_lo,dst_hi,len] + строка len байт.',
            '; dst = ram_hud_buffer+смещение (строка HUD, шаг 0x20); len = метка_end-метка —',
            '; пересчитывается ассемблером: при правке строки длина записи обновляется сама.',
            '; Читатель — func_copy_record_entries @0x1E5D (код берёт записи через data_msg_rec_*).']
    for n in range(12):
        hcmt, hlabel, hb = blocks[2 * n]
        scmt, slabel, sb = blocks[2 * n + 1]
        if len(hb) != 3:
            sys.exit('strings_msg: заголовок %s — %d байт вместо 3' % (hlabel, len(hb)))
        if not slabel.startswith('str_msg_'):
            sys.exit('strings_msg: после %s идёт %s вместо str_msg_*' % (hlabel, slabel))
        dst = hb[1] * 256 + hb[0]
        if hb[2] != len(sb):
            sys.exit('strings_msg: запись %s: len %d != %d байт строки' % (hlabel, hb[2], len(sb)))
        if not 0x7300 <= dst < 0x7600:
            sys.exit('strings_msg: запись %s: dst 0x%04X вне HUD-буфера' % (hlabel, dst))
        off = dst - 0x7300
        rlabel = hlabel if n == 0 else 'data_msg_rec_' + slabel[len('str_msg_'):]
        if n == 0:
            body += hcmt   # исходный комментарий таблицы — у первой записи
        body.append('; Запись %d: dst = ram_hud_buffer+%03Xh' % (n, off))
        body.append('%s:' % rlabel)
        body.append('        defb    (ram_hud_buffer+%03Xh)&0ffh,(ram_hud_buffer+%03Xh)>>8,%s_end-%s'
                    % (off, off, slabel, slabel))
        body += scmt
        body.append('%s:' % slabel)
        body += emit_defb(sb)
        body.append('%s_end:' % slabel)
        body.append('')
    return body


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--src', required=True, help='исходный layout.asm (asm/layout.asm)')
    ap.add_argument('--dst', required=True, help='новый layout.asm (remake/layout.asm)')
    ap.add_argument('--inc', required=True, help='каталог inc-файлов (remake/inc)')
    args = ap.parse_args()

    with open(args.src, encoding='utf-8') as f:
        lines = f.read().splitlines()

    os.makedirs(args.inc, exist_ok=True)
    region_by_start = {s: (e, f) for s, e, f in REGIONS}
    regions_done = set()
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
        if label in region_by_start and label not in regions_done:
            end_lbl, fname = region_by_start[label]
            e = None
            for k in range(i + 1, len(lines)):
                if lines[k] == end_lbl + ':':
                    e = k
                    break
            if e is None:
                sys.exit('регион %s: конечная метка %s: не найдена' % (label, end_lbl))
            k = e
            while k > i and (lines[k - 1].startswith(';') or not lines[k - 1].strip()):
                k -= 1
            for ln in lines[i:k]:
                if not (not ln.strip() or ln.startswith(';')
                        or DEFB_RE.match(ln) or LABEL_RE.match(ln)):
                    sys.exit('регион %s: не-данные в регионе: %r' % (label, ln))
            c0 = i
            while c0 > 0 and lines[c0 - 1].startswith(';'):
                c0 -= 1
            if fname == 'strings_msg.inc':
                block = build_strings_msg(lines[c0:k])
            elif fname in TEXT_REGIONS:
                block = build_strings_text(lines[c0:k], fname)
            else:
                block = ['; Текстовый регион вынесен из layout.asm дословно (адреса сохранены):',
                         '; строки + таблицы записей func_copy_record_entries/func_draw_text_records.'] \
                    + lines[c0:k]
            path = os.path.join(args.inc, fname)
            with open(path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(block) + '\n')
            print('%s: %d строк' % (path, len(block)))
            out.append('; %s: текстовый регион вынесен в inc/%s' % (label, fname))
            out.append('        include "inc/%s"' % fname)
            out += lines[k:e]   # комментарий над меткой-концом остаётся в layout
            regions_done.add(label)
            i = e
            continue
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
        elif label == 'gap_1E9C':
            strings = bytes(data).split(b'\0')
            if strings[-1] != b'' or len(strings) - 1 != 20:
                sys.exit('gap_1E9C: ожидалось 20 NUL-строк, получено %d' % (len(strings) - 1))
            decoded = [s.decode() for s in strings[:-1]]
            if decoded != LEVEL_NAMES:
                sys.exit('gap_1E9C: имена не совпали с LEVEL_NAMES: %r' % decoded)
            body = ['; Имена 20 уровней — строка NEXT SCENE IS (NUL-терминированный ASCII).',
                    '; Читатель: func_level_name_ptr (A = номер уровня) пропускает A-1 строк',
                    '; от начала (лимит 0x1E байт на имя) и возвращает HL на имя;',
                    '; порядок имён = порядок data_level_keywords (UNDR→UNDERGROUND, ...).',
                    'data_level_names:']
            for n, s in enumerate(strings[:-1], 1):
                line = '        defb    ' + ','.join(fmt_byte(b) for b in s + b'\0')
                body.append(line.ljust(66) + '; уровень %d: %s' % (n, s.decode()))
            path = os.path.join(args.inc, files[0])
            with open(path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(body) + '\n')
            print('%s: %d байт (%d имён)' % (path, len(data), len(strings) - 1))
            out.append('; gap_1E9C: имена уровней вынесены в inc/level_names.inc (data_level_names)')
            out.append('        include "inc/level_names.inc"')
        elif label == 'data_level_keywords':
            body = ['; 4-символьные ключи-читы 20 уровней (уровень N — имя N в data_level_names).',
                    '; Сравнивает рутина ввода @0x1277 (сырой код внутри gap_125C: LXI H,1F49h /',
                    '; MVI B,14h / при совпадении уровень = 0x15-B-1 → 0x7C66); копирует',
                    '; func_init_playfield_buffers (0x1C52) по индексу 4*level в RAM 0x742B для показа.',
                    'data_level_keywords:']
            for n in range(20):
                chunk = data[n * 4:n * 4 + 4]
                key = ''.join(chr(b) for b in chunk)
                line = '        defb    ' + ','.join(fmt_byte(b) for b in chunk)
                body.append(line.ljust(66) + '; уровень %d: %s (%s)' % (n + 1, key, LEVEL_NAMES[n]))
            path = os.path.join(args.inc, files[0])
            with open(path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(body) + '\n')
            print('%s: %d байт (20 ключей)' % (path, len(data)))
            out.append('; data_level_keywords: ключи вынесены в inc/level_keywords.inc (комментарий там)')
            out.append('        include "inc/level_keywords.inc"')
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
    if regions_done != set(region_by_start):
        sys.exit('регионы не найдены: %s' % ', '.join(sorted(set(region_by_start) - regions_done)))
    if dropped != 19:
        sys.exit('снято %d equ-алиасов data_level_NN, ожидалось 19' % dropped)
    text = '\n'.join(RAM_EQU_HEADER + out)
    for pat, repl, want in REWRITES:
        text, n = re.subn(pat, repl, text)
        if n != want:
            sys.exit('rewrite %s: %d вхождений, ожидалось %d' % (pat, n, want))
        print('rewrite %s -> %s (%d)' % (pat, repl, n))
    with open(args.dst, 'w', encoding='utf-8') as f:
        f.write(text + '\n')
    print('%s: записан (%d строк)' % (args.dst, text.count('\n') + 1))


if __name__ == '__main__':
    main()
