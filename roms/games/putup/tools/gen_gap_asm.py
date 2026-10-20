#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Генератор asm из авторитетного декода отладчика для гэпов движка putup.
# Вход — компактные triples (addr, mnem, oper). Переименование операндов по
# таблицам SYM (RAM/data), FUNC (адрес->имя), ENTRY (точки входа->func_),
# и авто-расстановка локальных меток loc_%04X по всем целям переходов.
import re, os

OUT = os.path.join(os.path.dirname(__file__), '..', 'asm')

# --- RAM/data EQU (уже объявлены в var_ram_symbols.asm) -> оставляем имя как есть
# Значение-адрес -> символическое имя для подстановки в операнды.
DATA_SYM = {
    0x26DE: 'data_tile_table_26DE',
    0x2706: 'data_tile_2706',
    0x270A: 'data_tile_empty',
    0x2716: 'data_tile_2716',
    0x272A: 'data_tile_272A',
    0x1BFA: 'data_egg_speed_table', 0x0B3C: 'data_game_object_init',
    0x031A: 'data_snd_init',
    0x3E1A: 'data_music_scores',
    # Курсоры текстового буфера: base 0x6600 + исходное смещение (релокация +0x1600)
    0x500A: 'data_text_buffer+000Ah', 0x516A: 'data_text_buffer+016Ah',
}
FUNC = {
    0x01AE: 'func_restore_cursor', 0x01A1: 'func_print_char_at_ptr',
    0x0104: 'func_draw_tile_at_ptr', 0x0121: 'func_sound_init',
    0x032C: 'func_hl_add_a', 0x1BA8: 'func_render_tile_vram',
    0x1BD4: 'func_coords_to_textbuf', 0x0EF7: 'func_delay',
    0x0CA3: 'func_erase_char_08E9', 0x1B87: 'func_draw_tile_to_buf',
    0x11E9: 'func_play_sfx', 0x1197: 'func_draw_score_hud',
    0x1123: 'func_prng', 0x197C: 'func_level_loader',
    0x121A: 'func_draw_status_hud', 0x014F: 'func_set_text_ptr',
    0x0321: 'func_print_string', 0x130A: 'func_draw_game_objects',
    0x1BE5: 'func_clear_textbuf', 0x1477: 'func_delay_long',
}
# Точки входа -> имена функций (внутри файла меток)
ENTRY = {
    0x0F39: 'func_item_bonus_collect', 0x0F63: 'func_item_bonus_timer',
    0x0F6D: 'func_player_move_a', 0x0FD4: 'func_player_move_b',
    0x1017: 'func_player_move_c', 0x1042: 'func_player_move_d',
    0x1157: 'func_spawn_egg',
    0x1252: 'func_egg_caught', 0x12B3: 'func_gamestate_catch',
    0x12F6: 'func_gamestate_evade', 0x13AA: 'func_collision_death',
    0x0364: 'func_print_digit_tail',
    0x3DEB: 'func_music_load_score',
}
# Метки, определённые в ДРУГИХ файлах (нужно, чтобы они там существовали)
EXTERNAL = {0x0D68: 'loc_0D68', 0x0D6D: 'loc_0D6D',
            0x0F25: 'loc_0F25', 0x0F28: 'loc_0F28',
            0x0D41: 'loc_0D41', 0x0E4A: 'loc_0E4A',
            0x0BC2: 'loc_0BC2', 0x19A0: 'loc_19A0'}

# Мнемоники, чей 16-битный операнд — это адрес памяти (всегда резолвим):
MEM16 = {'LDA', 'STA', 'LHLD', 'SHLD'}
# Условные/безусловные переходы: операнд = адрес перехода
BR = {'JMP', 'JZ', 'JNZ', 'JC', 'JNC', 'JP', 'JM', 'CALL'}

# RAM-символы для подстановки (адрес -> EQU-имя), зеркало var_ram_symbols
RAM = {
    0x08E3: 'var_enemy_rc', 0x08E5: 'var_bonus_rc', 0x08E7: 'var_egg_rc',
    0x08E9: 'var_blink_cell', 0x08EA: 'var_blink_type',
    0x08ED: 'var_item_cost_table', 0x08F3: 'var_score', 0x08F5: 'var_level',
    0x08F7: 'var_egg_hist_prev', 0x08F8: 'var_egg_hist_cur',
    0x08F9: 'var_page_flip', 0x08FA: 'var_page_flip_hi',
    0x08FB: 'var_bonus_counter', 0x08FE: 'var_draw_row', 0x08FF: 'var_draw_col',
    0x0901: 'var_player_row', 0x0902: 'var_player_col',
    0x0903: 'var_player_bufaddr', 0x0905: 'var_collision_flag',
    0x0907: 'var_work_const', 0x090C: 'var_obj_type_idx',
    0x090D: 'var_move_dir', 0x090F: 'var_egg_counter',
    0x0910: 'var_egg_seq', 0x0911: 'data_level_param_buf',
    0x0912: 'data_level_param_buf+1', 0x091C: 'var_egg_slot',
    0x1155: 'var_prng_seed',
    0x08E2: 'var_num_leading_zero_flag', 0x08EB: 'var_score_delta',
    0x091A: 'var_entity1_state', 0x091B: 'var_entity2_state',
    0x091E: 'var_lives_icons', 0x0920: 'data_entity_xcoords+1',
    0x0921: 'data_entity_xcoords+2', 0x0923: 'data_entity_ycoords+1',
    0x0924: 'data_entity_ycoords+2', 0x0B3D: 'var_score_scratch',
    0x3854: 'var_music_track_ptr', 0x3856: 'var_music_track_base',
}
ALLSYM = {}
ALLSYM.update(RAM); ALLSYM.update(DATA_SYM)


def fmt_word(v):
    """16-битный операнд (LXI/адрес): всегда 4 цифры, при необходимости с 0."""
    return f'{v:04X}h'


def fmt_byte(v):
    """8-битный операнд (MVI/acc-иммедиат/DEFB): 2 цифры, старший ноль обязателен
    если leading ниббл — буква (0BFh, а не BFh — иначе 8080_strict читает как символ)."""
    return f'{v:02X}h' if v <= 0x0F else f'0{v:02X}h'


def fmt_hex(v):
    return fmt_word(v) if v > 0xFF else fmt_byte(v)


def resolve_addr(v, is_branch):
    """Вернуть символическое имя для адресного операнда или None."""
    if v in ENTRY and not is_branch:
        return None  # ENTRY — только метки определения, не ссылки
    if v in EXTERNAL:
        return EXTERNAL[v]
    if v in FUNC:
        return FUNC[v]
    if v in DATA_SYM:
        return DATA_SYM[v]
    if v in RAM:
        return RAM[v]
    if is_branch:
        # внутренние цели переходов -> loc_ (или имя точки входа)
        if v in ENTRY:
            return ENTRY[v]
        return f'loc_{v:04X}'
    return None


def transform(mnem, oper, addr, targets):
    """Отдать строку операндов с подстановкой символов."""
    mn = mnem.upper()
    # Определяем числовые токены в операндах
    def repl_num(txt):
        # возвращаем (value) из hex-токена
        return int(txt, 16)

    if mn in BR:
        # операнд = один адрес
        v = int(oper, 16)
        sym = resolve_addr(v, True)
        return sym if sym else fmt_hex(v), v
    if mn in MEM16:
        v = int(oper, 16)
        sym = resolve_addr(v, False)
        return (sym if sym else fmt_hex(v)), v
    # LXI/MVI: "reg, imm16/imm8" — единственный случай числового операнда с запятой
    if mn in ('LXI', 'MVI'):
        m = re.match(r'^([A-Z]+),\s*([0-9A-Fa-f]+)$', oper)
        if m:
            reg, num = m.group(1), int(m.group(2), 16)
            if num in ALLSYM and reg in ('H', 'D', 'B'):
                return f'{reg}, {ALLSYM[num]}', num
            imm = fmt_word(num) if reg in ('H', 'D', 'B') else fmt_byte(num)
            return f'{reg}, {imm}', num
    # MOV/CMP/ADD/ORA и прочие регистровые — без изменений (2-й токен может быть
    # регистром-буквой A/B/C/D/E — не трогать!)
    # MOV/CMP/и прочие регистровые — без изменений
    # одиночный hex-токен только для acc-иммедиатов (ADI/CPI/ANI/...) -> с суффиксом h
    if mn in {'ADI', 'ACI', 'SUI', 'SBI', 'ANI', 'XRI', 'ORI', 'CPI'}:
        return fmt_hex(int(oper, 16)), None
    return oper, None


# --- Данные дизассемблирования (addr, mnem, oper) ---
HANDLERS = [
    (0x0F39,'LHLD','08F3'),(0x0F3C,'LXI','B, 0064'),(0x0F3F,'DAD','B'),
    (0x0F40,'SHLD','08F3'),(0x0F43,'LXI','H, 090F'),(0x0F46,'INR','M'),
    (0x0F47,'MOV','A, M'),(0x0F48,'RLC',''),(0x0F49,'ADI','17'),
    (0x0F4B,'STA','08FE'),(0x0F4E,'MVI','A, 18'),(0x0F50,'STA','08FF'),
    (0x0F53,'CALL','01AE'),(0x0F56,'MVI','A, 72'),(0x0F58,'CALL','01A1'),
    (0x0F5B,'MVI','A, 6D'),(0x0F5D,'CALL','01A1'),(0x0F60,'JMP','0F25'),
    (0x0F63,'LXI','H, 08FB'),(0x0F66,'INR','M'),(0x0F67,'CALL','11E9'),
    (0x0F6A,'JMP','0F28'),(0x0F6D,'MVI','A, 06'),(0x0F6F,'STA','090C'),
    (0x0F72,'LXI','H, 08E3'),(0x0F75,'LDA','0901'),(0x0F78,'CMP','M'),
    (0x0F79,'JNZ','0F85'),(0x0F7C,'INX','H'),(0x0F7D,'LDA','0902'),
    (0x0F80,'CMP','M'),(0x0F81,'DCX','H'),(0x0F82,'JZ','0F88'),
    (0x0F85,'CALL','0104'),(0x0F88,'LDA','0901'),(0x0F8B,'MOV','L, A'),
    (0x0F8C,'LDA','0902'),(0x0F8F,'MOV','H, A'),(0x0F90,'SHLD','08E3'),
    (0x0F93,'XCHG',''),(0x0F94,'LDA','090C'),(0x0F97,'ADD','A'),
    (0x0F98,'ADD','A'),(0x0F99,'LXI','H, 26DE'),(0x0F9C,'CALL','032C'),
    (0x0F9F,'CALL','1BA8'),(0x0FA2,'LHLD','08E9'),(0x0FA5,'INX','H'),
    (0x0FA6,'MOV','A, L'),(0x0FA7,'ANI','1F'),(0x0FA9,'SHLD','08E9'),
    (0x0FAC,'JNZ','0FD1'),(0x0FAF,'MVI','B, 02'),(0x0FB1,'CALL','0121'),
    (0x0FB4,'CALL','0CA3'),(0x0FB7,'MVI','B, 01'),(0x0FB9,'CALL','0EF7'),
    (0x0FBC,'LHLD','08F3'),(0x0FBF,'LXI','B, 000A'),(0x0FC2,'DAD','B'),
    (0x0FC3,'SHLD','08F3'),(0x0FC6,'CALL','1197'),(0x0FC9,'LDA','08EA'),
    (0x0FCC,'CPI','02'),(0x0FCE,'JZ','197C'),(0x0FD1,'JMP','0FA2'),
    (0x0FD4,'LXI','H, 0902'),(0x0FD7,'INR','M'),(0x0FD8,'XRA','A'),
    (0x0FD9,'STA','090D'),(0x0FDC,'MOV','D, M'),(0x0FDD,'LDA','0901'),
    (0x0FE0,'MOV','E, A'),(0x0FE1,'CALL','1BD4'),(0x0FE4,'SHLD','0903'),
    (0x0FE7,'INX','H'),(0x0FE8,'MOV','A, M'),(0x0FE9,'CPI','77'),
    (0x0FEB,'JNC','0FF8'),(0x0FEE,'LXI','B, 0020'),(0x0FF1,'DAD','B'),
    (0x0FF2,'MOV','A, M'),(0x0FF3,'CPI','77'),(0x0FF5,'JC','0FFC'),
    (0x0FF8,'LXI','H, 0902'),(0x0FFB,'DCR','M'),(0x0FFC,'LDA','08F8'),
    (0x0FFF,'MOV','B, A'),(0x1000,'LDA','08F7'),(0x1003,'STA','08F8'),
    (0x1006,'MOV','A, B'),(0x1007,'STA','08F7'),(0x100A,'ORA','A'),
    (0x100B,'JNZ','0D68'),(0x100E,'LDA','08F9'),(0x1011,'STA','0907'),
    (0x1014,'JMP','0D6D'),(0x1017,'LXI','H, 0902'),(0x101A,'DCR','M'),
    (0x101B,'MVI','A, 01'),(0x101D,'STA','090D'),(0x1020,'MOV','D, M'),
    (0x1021,'LDA','0901'),(0x1024,'MOV','E, A'),(0x1025,'CALL','1BD4'),
    (0x1028,'SHLD','0903'),(0x102B,'MOV','A, M'),(0x102C,'CPI','77'),
    (0x102E,'JNC','103B'),(0x1031,'LXI','B, 0020'),(0x1034,'DAD','B'),
    (0x1035,'MOV','A, M'),(0x1036,'CPI','77'),(0x1038,'JC','103F'),
    (0x103B,'LXI','H, 0902'),(0x103E,'INR','M'),(0x103F,'JMP','0FFC'),
    (0x1042,'LHLD','0901'),(0x1045,'XCHG',''),(0x1046,'CALL','1BD4'),
    (0x1049,'SHLD','0903'),(0x104C,'LXI','B, 0040'),(0x104F,'DAD','B'),
    (0x1050,'MOV','A, M'),(0x1051,'CPI','7E'),(0x1053,'JZ','111A'),
    (0x1056,'CPI','7D'),(0x1058,'JZ','1188'),(0x105B,'LDA','090F'),
    (0x105E,'CPI','01'),(0x1060,'JZ','106B'),(0x1063,'CPI','02'),
    (0x1065,'JZ','106B'),(0x1068,'JMP','0D68'),(0x106B,'LHLD','0903'),
    (0x106E,'LXI','B, 0040'),(0x1071,'DAD','B'),(0x1072,'MOV','A, M'),
    (0x1073,'CPI','79'),(0x1075,'JNZ','0D68'),(0x1078,'MVI','B, 05'),
    (0x107A,'CALL','0121'),(0x107D,'LDA','0902'),(0x1080,'STA','08FE'),
    (0x1083,'LDA','0901'),(0x1086,'ADI','02'),(0x1088,'STA','08FF'),
    (0x108B,'CALL','01AE'),(0x108E,'MVI','A, 7B'),(0x1090,'CALL','01A1'),
    (0x1093,'MVI','A, 7C'),(0x1095,'CALL','01A1'),(0x1098,'LDA','090F'),
    (0x109B,'DCR','A'),(0x109C,'STA','090F'),(0x109F,'RLC',''),
    (0x10A0,'ADI','19'),(0x10A2,'STA','08FE'),(0x10A5,'MVI','A, 18'),
    (0x10A7,'STA','08FF'),(0x10AA,'CALL','01AE'),(0x10AD,'MVI','A, 20'),
    (0x10AF,'CALL','01A1'),(0x10B2,'CALL','01A1'),(0x10B5,'LDA','0910'),
    (0x10B8,'INR','A'),(0x10B9,'STA','0910'),(0x10BC,'LDA','08F5'),
    (0x10BF,'CPI','0A'),(0x10C1,'MVI','B, 01'),(0x10C3,'JC','10C8'),
    (0x10C6,'MVI','B, 02'),(0x10C8,'LDA','0910'),(0x10CB,'CMP','B'),
    (0x10CC,'JNZ','0D68'),(0x10CF,'LDA','0911'),(0x10D2,'MOV','D, A'),
    (0x10D3,'LDA','0912'),(0x10D6,'MOV','E, A'),(0x10D7,'LXI','H, 272A'),
    (0x10DA,'CALL','1B87'),(0x10DD,'MVI','B, 05'),(0x10DF,'CALL','0121'),
    (0x10E2,'MVI','A, 07'),(0x10E4,'STA','090C'),(0x10E7,'LXI','H, 08E5'),
    (0x10EA,'LDA','0912'),(0x10ED,'CMP','M'),(0x10EE,'JNZ','10FA'),
    (0x10F1,'INX','H'),(0x10F2,'LDA','0911'),(0x10F5,'CMP','M'),
    (0x10F6,'DCX','H'),(0x10F7,'JZ','10FD'),(0x10FA,'CALL','0104'),
    (0x10FD,'LDA','0912'),(0x1100,'MOV','L, A'),(0x1101,'LDA','0911'),
    (0x1104,'MOV','H, A'),(0x1105,'SHLD','08E5'),(0x1108,'XCHG',''),
    (0x1109,'LDA','090C'),(0x110C,'ADD','A'),(0x110D,'ADD','A'),
    (0x110E,'LXI','H, 26DE'),(0x1111,'CALL','032C'),(0x1114,'CALL','1BA8'),
    (0x1117,'JMP','0D68'),(0x111A,'LHLD','0901'),(0x111D,'XCHG',''),
    (0x111E,'INR','E'),(0x111F,'INR','E'),(0x1120,'JMP','1157'),
]
SPAWN = [
    (0x1157,'CALL','1123'),(0x115A,'ANI','07'),(0x115C,'CPI','05'),
    (0x115E,'JNC','1120'),(0x1161,'STA','091C'),(0x1164,'LDA','091C'),
    (0x1167,'CPI','04'),(0x1169,'JNZ','1174'),(0x116C,'CALL','1123'),
    (0x116F,'ANI','01'),(0x1171,'JNZ','111A'),(0x1174,'LDA','091C'),
    (0x1177,'ADI','0A'),(0x1179,'MOV','L, A'),(0x117A,'MVI','H, 00'),
    (0x117C,'DAD','H'),(0x117D,'DAD','H'),(0x117E,'LXI','B, 2706'),
    (0x1181,'DAD','B'),(0x1182,'CALL','1B87'),(0x1185,'JMP','0D68'),
    (0x1188,'LHLD','0901'),(0x118B,'XCHG',''),(0x118C,'INR','E'),
    (0x118D,'INR','E'),(0x118E,'LXI','H, 2716'),(0x1191,'CALL','1B87'),
    (0x1194,'JMP','0D68'),
]


def targets_of(prog):
    ts = set()
    for a, mn, op in prog:
        if mn.upper() in BR:
            ts.add(int(op, 16))
    return ts


def emit(prog, base, size, header, path, all_targets):
    ts = all_targets
    lines = [header]
    for a, mn, op in prog:
        if a in ENTRY:
            lines.append(f'{ENTRY[a]}:')
        elif a in ts:
            lines.append(f'loc_{a:04X}:')
        nops, _ = transform(mn, op, a, ts)
        body = f'    {mn:<5} {nops}' if nops else f'    {mn}'
        lines.append(f'{body:<30}; 0x{a:04X}')
    open(path, 'w', encoding='utf-8').write('\n'.join(lines) + '\n')
    print(f'wrote {path}: {len(prog)} instrs')


ALLT = targets_of(HANDLERS) | targets_of(SPAWN)

h = ('; Функция: func_game_update_handlers\n'
     '; Адрес: 0x0F39\n'
     '; Размер: 490 байт (0x0F39-0x1122, непрерывное тело)\n'
     '; Описание: Обработчики событий кадра движка (6 точек входа из func_game_update:\n'
     ';   0x0F39 сбор бонуса, 0x0F63 таймер бонуса, 0x0F6D/0x0FD4/0x1017/0x1042\n'
     ';   движение игрока и коллизии). Возврат в func_score_and_redraw (0F25/0F28)\n'
     ';   и в общий перерисов loc_0D68 game_update.\n')
emit(HANDLERS, 0x0F39, 0x1123 - 0x0F39, h,
     os.path.join(OUT, 'funcs', 'func_game_update_handlers.asm'), ALLT)

s = ('; Функция: func_spawn_egg\n'
     '; Адрес: 0x1157\n'
     '; Размер: 64 байт (0x1157-0x1196, непрерывное тело)\n'
     '; Описание: Спавн яйца: CALL func_prng -> выбор колонки, отбор по чётности,\n'
     ';   расчёт тайла из data_tile_2706/2716, CALL func_draw_tile_to_buf,\n'
     ';   JMP loc_0D68 (перерис). Вход 0x1188 — вариант B. Retry via loc_1120.\n')
emit(SPAWN, 0x1157, 0x1197 - 0x1157, s,
     os.path.join(OUT, 'funcs', 'func_spawn_egg.asm'), ALLT)

# 2-байтовый сид PRNG @0x1155 (иниц. значение из ROM)
sd = ('; Данные: var_prng_seed_init\n'
      '; Адрес: 0x1155\n'
      '; Размер: 2 байта\n'
      '; Описание: Инициализация слова-сида PRNG (func_prng LHLD/SHLD var_prng_seed).\n'
      'var_prng_seed_init:\n'
      '    DEFB 01h, 00h\n')
open(os.path.join(OUT, 'data', 'var_prng_seed_init.asm'), 'w',
     encoding='utf-8').write(sd)
print('wrote var_prng_seed_init.asm')

# ---------------- CLUSTER B: обработчики игры (0x1252/0x12B3/0x12F6) ----------
CLUSTER_B = [
    (0x1252,'LXI','H, 00E0'),(0x1255,'SHLD','08E9'),(0x1258,'MVI','A, 07'),
    (0x125A,'STA','091E'),(0x125D,'CALL','121A'),(0x1260,'CALL','1123'),
    (0x1263,'ANI','03'),(0x1265,'ADI','0A'),(0x1267,'STA','091C'),
    (0x126A,'MOV','L, A'),(0x126B,'MVI','H, 00'),(0x126D,'DAD','H'),
    (0x126E,'DAD','H'),(0x126F,'LDA','0920'),(0x1272,'MOV','D, A'),
    (0x1273,'LDA','0923'),(0x1276,'MOV','E, A'),(0x1277,'LXI','B, 2706'),
    (0x127A,'DAD','B'),(0x127B,'PUSH','H'),(0x127C,'CALL','1B87'),
    (0x127F,'POP','H'),(0x1280,'LDA','0921'),(0x1283,'MOV','D, A'),
    (0x1284,'LDA','0924'),(0x1287,'MOV','E, A'),(0x1288,'CALL','1B87'),
    (0x128B,'LDA','0902'),(0x128E,'STA','0920'),(0x1291,'MVI','A, 23'),
    (0x1293,'STA','0923'),(0x1296,'LXI','H, 500A'),(0x1299,'CALL','014F'),
    (0x129C,'LXI','H, 0B01'),(0x129F,'CALL','0321'),(0x12A2,'MVI','B, 08'),
    (0x12A4,'CALL','0121'),(0x12A7,'MVI','A, 09'),(0x12A9,'STA','091A'),
    (0x12AC,'INR','A'),(0x12AD,'STA','091B'),(0x12B0,'JMP','0E4A'),
    (0x12B3,'LXI','H, 0901'),(0x12B6,'DCR','M'),(0x12B7,'MOV','E, M'),
    (0x12B8,'LDA','0902'),(0x12BB,'MOV','D, A'),(0x12BC,'CALL','1BD4'),
    (0x12BF,'SHLD','0903'),(0x12C2,'LHLD','0903'),(0x12C5,'MOV','A, M'),
    (0x12C6,'CPI','77'),(0x12C8,'JNC','12D2'),(0x12CB,'INX','H'),
    (0x12CC,'MOV','A, M'),(0x12CD,'CPI','77'),(0x12CF,'JC','12E0'),
    (0x12D2,'XRA','A'),(0x12D3,'STA','0900'),(0x12D6,'STA','0906'),
    (0x12D9,'LXI','H, 0901'),(0x12DC,'INR','M'),(0x12DD,'JMP','0D41'),
    (0x12E0,'LXI','H, 0906'),(0x12E3,'INR','M'),(0x12E4,'MOV','A, M'),
    (0x12E5,'CPI','04'),(0x12E7,'JC','12F3'),(0x12EA,'XRA','A'),
    (0x12EB,'STA','0906'),(0x12EE,'MVI','A, 02'),(0x12F0,'STA','0900'),
    (0x12F3,'JMP','0D41'),(0x12F6,'LXI','H, 0906'),(0x12F9,'INR','M'),
    (0x12FA,'MOV','A, M'),(0x12FB,'CPI','03'),(0x12FD,'JC','1307'),
    (0x1300,'XRA','A'),(0x1301,'STA','0906'),(0x1304,'STA','0900'),
    (0x1307,'JMP','0D41'),
]
COLLISION = [
    (0x13AA,'MVI','B, 02'),(0x13AC,'CALL','0121'),(0x13AF,'LDA','0901'),
    (0x13B2,'SUI','02'),(0x13B4,'STA','090E'),(0x13B7,'LDA','0902'),
    (0x13BA,'STA','0905'),(0x13BD,'LXI','B, 0000'),(0x13C0,'LXI','H, 1BFA'),
    (0x13C3,'DAD','B'),(0x13C4,'MOV','A, M'),(0x13C5,'CPI','FF'),
    (0x13C7,'JZ','1424'),(0x13CA,'RRC',''),(0x13CB,'RRC',''),
    (0x13CC,'RRC',''),(0x13CD,'ANI','1F'),(0x13CF,'MOV','E, A'),
    (0x13D0,'LDA','090E'),(0x13D3,'ADD','E'),(0x13D4,'CPI','18'),
    (0x13D6,'JNC','1424'),(0x13D9,'STA','090A'),(0x13DC,'LDA','0905'),
    (0x13DF,'STA','0909'),(0x13E2,'MVI','A, 06'),(0x13E4,'STA','090C'),
    (0x13E7,'PUSH','H'),(0x13E8,'PUSH','B'),(0x13E9,'LXI','H, 08E3'),
    (0x13EC,'LDA','090A'),(0x13EF,'CMP','M'),(0x13F0,'JNZ','13FC'),
    (0x13F3,'INX','H'),(0x13F4,'LDA','0909'),(0x13F7,'CMP','M'),
    (0x13F8,'DCX','H'),(0x13F9,'JZ','13FF'),(0x13FC,'CALL','0104'),
    (0x13FF,'LDA','090A'),(0x1402,'MOV','L, A'),(0x1403,'LDA','0909'),
    (0x1406,'MOV','H, A'),(0x1407,'SHLD','08E3'),(0x140A,'XCHG',''),
    (0x140B,'LDA','090C'),(0x140E,'ADD','A'),(0x140F,'ADD','A'),
    (0x1410,'LXI','H, 26DE'),(0x1413,'CALL','032C'),(0x1416,'CALL','1BA8'),
    (0x1419,'MVI','B, 01'),(0x141B,'CALL','0EF7'),(0x141E,'POP','B'),
    (0x141F,'POP','H'),(0x1420,'INR','C'),(0x1421,'JMP','13C0'),
    (0x1424,'CALL','130A'),(0x1427,'XRA','A'),(0x1428,'STA','090F'),
    (0x142B,'LXI','H, 08FB'),(0x142E,'DCR','M'),(0x142F,'MOV','A, M'),
    (0x1430,'CPI','FF'),(0x1432,'JZ','1438'),(0x1435,'JMP','19A0'),
    (0x1438,'CALL','1BE5'),(0x143B,'LXI','H, 516A'),(0x143E,'CALL','014F'),
    (0x1441,'LXI','H, 0B0E'),(0x1444,'CALL','0321'),(0x1447,'LHLD','08F3'),
    (0x144A,'XCHG',''),(0x144B,'LHLD','08EB'),(0x144E,'STA','0B3D'),
    (0x1451,'MOV','A, L'),(0x1452,'SBB','E'),(0x1453,'MOV','L, A'),
    (0x1454,'MOV','A, H'),(0x1455,'SBB','D'),(0x1456,'MOV','H, A'),
    (0x1457,'PUSH','H'),(0x1458,'PUSH','PSW'),(0x1459,'ORA','L'),
    (0x145A,'JZ','1463'),(0x145D,'POP','H'),(0x145E,'MVI','A, BF'),
    (0x1460,'ANA','L'),(0x1461,'MOV','L, A'),(0x1462,'PUSH','H'),
    (0x1463,'POP','PSW'),(0x1464,'POP','H'),(0x1465,'LDA','0B3D'),
    (0x1468,'JNC','146F'),(0x146B,'XCHG',''),(0x146C,'SHLD','08EB'),
    (0x146F,'MVI','B, 05'),(0x1471,'CALL','1477'),(0x1474,'JMP','0BC2'),
]
PRINT_TAIL = [
    (0x0364,'ORI','30'),(0x0366,'PUSH','PSW'),(0x0367,'CPI','30'),
    (0x0369,'JZ','0371'),(0x036C,'MVI','A, 01'),(0x036E,'STA','08E2'),
    (0x0371,'LDA','08E2'),(0x0374,'ORA','A'),(0x0375,'JNZ','037F'),
    (0x0378,'MVI','A, 20'),(0x037A,'CALL','01A1'),(0x037D,'POP','PSW'),
    (0x037E,'RET',''),(0x037F,'POP','PSW'),(0x0380,'JMP','01A1'),
]
ALLT_B = targets_of(CLUSTER_B) | targets_of(COLLISION) | targets_of(PRINT_TAIL)

emit(CLUSTER_B, 0x1252, 0x130A - 0x1252,
     ('; Функция: func_gamestate_handlers\n'
      '; Адрес: 0x1252\n'
      '; Размер: 184 байт (0x1252-0x1309, непрерывное тело)\n'
      '; Описание: Обработчики исходов кадра (3 входа из func_game_update):\n'
      ';   0x1252 пойманное яйцо (продвижение), 0x12B3 game_state==1 (ловушка),\n'
      ';   0x12F6 game_state==2 (уклонение). 0x1296 — site релокации textbuf (500Ah).\n'),
     os.path.join(OUT, 'funcs', 'func_gamestate_handlers.asm'), ALLT_B)
emit(COLLISION, 0x13AA, 0x1477 - 0x13AA,
     ('; Функция: func_collision_death\n'
      '; Адрес: 0x13AA\n'
      '; Размер: 205 байт (0x13AA-0x1476, непрерывное тело)\n'
      '; Описание: Коллизия/гибель: проход по data_egg_speed_table, сравнение с\n'
      ';   врагом (var_enemy_rc), перерис тайлов, подсчёт дельты счёта. 0x143B —\n'
      ';   site релокации textbuf (516Ah). Входы loc_ из func_game_update (JNZ 13AA).\n'),
     os.path.join(OUT, 'funcs', 'func_collision_death.asm'), ALLT_B)
emit(PRINT_TAIL, 0x0364, 0x0383 - 0x0364,
     ('; Функция: func_print_digit_tail\n'
      '; Адрес: 0x0364\n'
      '; Размер: 31 байт (0x0364-0x0382, непрерывное тело)\n'
      '; Описание: Хвост func_print_uint16: вывод цифры (A|=30h), подача ведущих\n'
      ';   нулей через var_num_leading_zero_flag, печать пробелом/func_print_char_at_ptr.\n'
      ';   Вход из func_print_uint16 (JMP 0x0364).\n'),
     os.path.join(OUT, 'funcs', 'func_print_digit_tail.asm'), ALLT_B)

# ---------------- func_music_load_score (0x3DEB, чистый decode) ---------------
MUSIC_LOAD = [
    (0x3DEB,'MVI','A, 01'),(0x3DED,'LXI','H, 3E1A'),(0x3DF0,'ANA','A'),
    (0x3DF1,'CPI','00'),(0x3DF3,'RZ',''),(0x3DF4,'CPI','06'),(0x3DF6,'RNC',''),
    (0x3DF7,'DCR','A'),(0x3DF8,'CPI','00'),(0x3DFA,'JZ','3E0C'),
    (0x3DFD,'MOV','B, A'),(0x3DFE,'LXI','D, 030F'),(0x3E01,'DAD','D'),
    (0x3E02,'PUSH','PSW'),(0x3E03,'DCR','B'),(0x3E04,'JZ','3E0B'),
    (0x3E07,'POP','PSW'),(0x3E08,'JMP','3E01'),(0x3E0B,'POP','PSW'),
    (0x3E0C,'SHLD','3854'),(0x3E0F,'LXI','B, 000F'),(0x3E12,'DAD','B'),
]
_mpath = os.path.join(OUT, 'funcs', 'func_music_load_score.asm')
emit(MUSIC_LOAD, 0x3DEB, 0x3E1A - 0x3DEB,
     ('; Функция: func_music_load_score\n'
      '; Адрес: 0x3DEB\n'
      '; Размер: 47 байт (0x3DEB-0x3E1A)\n'
      '; Описание: Загрузка текущего score: индекс дорожки -> выбор записи из\n'
      ';   data_music_scores (шаг 0x0F, цикл DCR B), установка var_music_track_ptr/\n'
      ';   var_music_track_base, CALL 3888h (возврат в func_music_tick). Хвост 0x3E13\n'
      ';   (SHLD/CALL/RET) — DEFB (пост-RET, в RDB не размечен).\n'),
     _mpath, targets_of(MUSIC_LOAD))
# 7-байтовый хвост 0x3E13..0x3E19 (SHLD/CALL/RET — не размечен как инстр.)
with open(_mpath, 'a', encoding='utf-8') as _f:
    _f.write('    ; --- хвост 0x3E13..0x3E19 (SHLD/CALL/RET) ---\n')
    _f.write('    DEFB 022h, 056h, 038h, 0CDh, 088h, 038h, 0C9h\n')
print('appended func_music_load_score tail (7B)')

# ---- data-блоки гэпов ----
rom = open(os.path.join(OUT, '..', '..', '..', 'redesign', 'putup', 'src',
                        'putup.rom'), 'rb').read()
def data_file(fn, addr, n, name, desc):
    b = rom[addr - 0x100: addr - 0x100 + n]
    body = ''.join('    DEFB ' + ', '.join(fmt_byte(x) for x in b[i:i+8]) + '\n'
                   for i in range(0, n, 8))
    txt = (f'; Данные: {name}\n; Адрес: 0x{addr:04X}\n; Размер: {n} байт\n'
           f'; Описание: {desc}\n{name}:\n' + body)
    open(os.path.join(OUT, 'data', fn), 'w', encoding='utf-8').write(txt)
    print(f'wrote data/{fn} ({n}B)')
data_file('data_egg_speed_table.asm', 0x1BFA, 20, 'data_egg_speed_table',
          'Кривая скорости/фаз яйца (FF-терминатор); читается func_collision_death.')
data_file('data_game_object_init.asm', 0x0B3C, 27, 'data_game_object_init',
          'Иниц. таблица игровых объектов (экран-буфер); читается func_draw_game_objects.')
data_file('data_snd_init.asm', 0x031A, 7, 'data_snd_init',
          'Иниц. значения состояния звука (var_snd_period_ch0..state).')
