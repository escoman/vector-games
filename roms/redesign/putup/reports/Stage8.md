# Stage 8. Выгрузка функций в asm-файлы

## Goal

Экспорт всех функций/меток из RDB ROM `putup.rom` в отдельные asm-файлы формата
z88dk в каталог `./asm`, с заменой hex-адресов в операндах на символические имена
объектов RDB и локальные метки.

## ROM

- Файл: `putup.rom`
- Размер: 17664 байт
- SHA256: `8486442efc390b15860ec7f69c32db93b0884908565fa11fec57d5c551b4e9a6`
- RDB: `src/putup.rdb` (153 объекта)
- Загрузка: `debug_load_rom` **без запуска** (эмуляция не стартовала, PC=0x042A)

## Метод (MCP-first)

Дизассемблирование получено исключительно через MCP `vector-debugger`
(`debug_disassemble_range`). Самостоятельное дизассемблирование ROM не выполнялось.

Для гарантии правильного выравнивания инструкций код дизассемблировался
**непрерывными прогонами** (code runs), а не по одной функции: последовательное
дизассемблирование с произвольного адреса может «съезжать» на данных/gap-байтах.
Границы прогонов совмещались с началами объектов RDB.

Регионы выгрузки:

| Регион | Диапазон | Прогон (address/size, dec) |
|--------|----------|----------------------------|
| Region 1 | 0x0100-0x08C2 | стартовый код, звук, графика, глифы |
| Region 2 | 0x0800-0x08C2 | func_put_char / func_render_glyph |
| Region 3 | 0x0E85-0x1BF9 | игровой цикл, HUD, состояния сущностей, загрузчик уровня |
| Region 4 | 0x3858-0x3DE7 | музыкальный движок (12 функций) |

Region 4 дизассемблирован двумя выровненными частями с разделением на границе
объекта данных `var_music_voice2_flag` (0x3BC8):
- Part1: address=14424 (0x3858), size=880 → 0x3858-0x3BC7
- Part2: address=15306 (0x3BCA), size=542 → 0x3BCA-0x3DE7

## Правила замены операндов (по TZ)

1. Адрес совпадает с **началом объекта RDB** → подставляется имя объекта
   (например `LHLD 3854` → `LHLD var_music_track_ptr`,
   `CALL 3902` → `CALL func_music_load_voice_params`).
2. Адрес указывает **внутрь текущей функции** (локальный переход) → генерируется
   локальная метка `loc_XXXX` и размещается перед инструкцией-целью.
3. Адрес **не найден** ни в RDB, ни внутри функции → оставляется как hex
   (например `LXI H, 421Ah`, `LDA 3BC9h`, `JMP 3DC5h`).

Дополнительные соглашения:

- Немедленные константы, загружаемые в BC/DE/SP, и арифметические immediates
  **остаются hex**, даже если численно равны адресу функции
  (`LXI B, 0100h`, `LXI D, 03F8h`, `LXI E, 14h` — не заменяются).
- Символическая замена применяется только к реальным ссылкам на адреса:
  CALL / JMP / условные переходы / LDA / STA / LHLD / SHLD / LXI H,ptr.
- Формат локальных меток: `loc_XXXX:` (hex в верхнем регистре). В TZ приведён
  пример `.loc_0357` с точкой; принят формат без точки как совместимый с
  ассемблером z88dk и последовательный для всех файлов.
- Каждая инструкция снабжена комментарием с её адресом `; 0xXXXX`.

## Результат экспорта

Создано **82 asm-файла** — по одному на каждый объект RDB типа `function` (80)
и `label` (2). Проверка соответствия (RDB ↔ файловая система) дала точное
совпадение 1:1: нет ни одного объекта без файла и ни одного лишнего файла.

```
RDB func/label count: 82
ASM file count:       82
In RDB but NO asm file:   (нет)
asm file but NOT in RDB:  (нет)
```

### Экспортированные функции/метки (82)

**Region 1 — стартовый код, звук, графика (0x0100-0x04CD):**
func_entry (0x0100), func_draw_tile_at_ptr (0x0104), func_sound_init (0x0121),
func_draw_char_at_hl (0x0145), func_set_text_ptr (0x014F), func_decode_key (0x0153),
func_check_start_key (0x017C), func_read_keybuf (0x0197), func_print_char_at_ptr (0x01A1),
func_restore_cursor (0x01AE), func_sound_op (0x01BC), func_snd_out_ch0 (0x0201),
func_snd_calc_period (0x020E), func_snd_out_ch1 (0x022D), func_snd_out_ch2 (0x024E),
func_snd_toggle (0x026E), func_snd_enable_ch0 (0x0290), func_snd_enable_ch1 (0x029E),
func_snd_enable_ch2 (0x02AC), func_snd_enable_ch01 (0x02BA), func_snd_enable_ch02 (0x02C0),
func_snd_enable_ch12 (0x02C6), func_snd_enable_ch012 (0x02CC), func_snd_gate_ch0 (0x02D2),
func_snd_gate_ch1 (0x02EA), func_snd_gate_ch2 (0x0302), func_print_string (0x0321),
func_hl_add_a (0x032C), func_print_uint16 (0x0331), func_divmod_u16 (0x0355),
func_hw_init (0x0383), func_vblank_isr (0x03A4), func_load_glyph_block (0x0401),
func_blit_plane_mask80 (0x0439), func_blit_plane_mask40 (0x045E),
func_blit_plane_mask20 (0x0483), func_blit_plane_mask10 (0x04A8), func_load_gfx_2761 (0x04CD).

**Region 2 — вывод символа/глифа (0x0800-0x0803):**
func_put_char (0x0800), func_render_glyph (0x0803).

**Region 3 — игровой цикл, HUD, сущности, уровень (0x0B57-0x1BE5):**
func_main_init (0x0B57), lbl_title_key_poll (0x0C65), func_erase_char_08E9 (0x0CA3),
func_game_update (0x0CE0), lbl_main_game_loop (0x0E85), func_delay (0x0EF7),
func_score_and_redraw (0x0F09), func_prng (0x1123), func_draw_score_hud (0x1197),
func_play_sfx (0x11E9), func_draw_level_hud (0x11EE), func_draw_status_hud (0x121A),
func_draw_game_objects (0x130A), func_delay_long (0x1477), func_entity_state1 (0x1489),
func_entity_state2 (0x14F9), func_entity_state3 (0x1568), func_entity_state4 (0x15DF),
func_entity_state5 (0x164F), func_entity_state6 (0x16FC), func_entity_state7 (0x17A8),
func_entity_state8 (0x1851), func_entity_state9 (0x18FE), func_entity_state10 (0x191B),
func_level_loader (0x197C), func_draw_tile_to_buf (0x1B87), func_render_tile_vram (0x1BA8),
func_memcpy (0x1BC9), func_coords_to_textbuf (0x1BD4), func_clear_textbuf (0x1BE5).

**Region 4 — музыкальный движок (0x3858-0x3DCD):**
func_music_tick (0x3858), func_music_load_voice_params (0x3902), func_snd_op_keep_a (0x3940),
func_music_process_voice (0x3946), func_music_set_note_params (0x3B0F),
func_music_play_note_ch0 (0x3BCA), func_snd_op_keep_a2 (0x3C77), func_music_play_note_ch1 (0x3C7D),
func_snd_op_keep_a3 (0x3D48), func_music_init (0x3D4E), func_memcpy_keep_psw (0x3DB8),
func_music_start_track (0x3DCD).

## Коррекции размеров объектов RDB

В ходе выгрузки выявлены три объекта, размер которых в RDB перекрывал соседние
объекты. Размеры исправлены через `debug_update_rdb_object` так, чтобы объект
заканчивался ровно перед началом следующего:

| Объект | Адрес | Было | Стало | Обоснование |
|--------|-------|------|-------|-------------|
| func_snd_toggle | 0x026E | 16 | 18 | конец = 0x0280 (data_snd_toggle_table) |
| func_memcpy | 0x1BC9 | 12 | 11 | RET на 0x1BD3; след. func_coords_to_textbuf 0x1BD4 |
| func_music_load_voice_params | 0x3902 | 75 | 62 | RET на 0x393F; след. func_snd_op_keep_a 0x3940 |

## Gap-области (не функции RDB)

Обнаружены участки кода, на которые есть переходы, но которые не являются
объектами RDB типа `function`. Они **не выгружались** как отдельные функции
(соответствуют правилу 3 — ссылки на них оставлены как hex). Будут учтены на
Stage 10 (сборка ROM):

- **Region 3:** 0x0F39-0x1122, 0x1155-0x1196, 0x1253-0x1309, 0x13AA-0x1476.
- **Region 4:**
  - 0x388C-0x3901 — обёртка `CALL 3DCD`/`RET` (0x388C) + подпрограмма голоса,
    вызываемая `CZ 3890` из func_music_tick.
  - 0x3DC5-0x3DCC — 0x3DC5: `CALL 3DB8 / EI / RET` (цель `JMP 3DC5` из
    func_music_init); 0x3DCA: `CALL 3858` (вектор, загружаемый `LXI H,3DCA`).

## Verified Facts

- ROM загружен без запуска; PC=0x042A, running=false (подтверждено `debug_get_state`).
- В RDB 153 объекта: 80 function, 33 variable, 20 data, 12 string, 6 table, 2 label.
- Все 82 объекта кода (function+label) выгружены в `./asm` (соответствие 1:1).
- Три размера объектов исправлены и сохранены.
- RDB сохранён: `debug_save_rdb` → success, `dirty=false` (подтверждено
  `debug_get_rdb_info`).

## Inferences

- Музыкальный движок (Region 4) использует таблицу частот канала 0 (0x445D),
  таблицу нот канала 1 (0x42F9), таблицу параметров нот (0x43F9) и буфер
  параметров голоса (0x3845); выдача звука идёт через обёртки
  func_snd_op_keep_a{,2,3} → func_sound_op (0x01BC).
- func_music_init устанавливает в RAM 0x03F8 3-байтный вектор `CALL func_music_tick`
  (копируется из 0x3DCA), что указывает на использование хука таймера/ISR для
  музыкального тика.

## Unknowns / Limitations

- Назначение gap-байтов 0x383B/0x383C/0x383D (индексы нот) и 0x383F-0x3843
  (указатели голосов) подтверждено косвенно (использование в func_music_init /
  func_music_process_voice), но они не являются отдельными объектами RDB.
- Байт 0x3BC9 (смежный с var_music_voice2_flag 0x3BC8) используется
  func_music_play_note_ch1 как флаг третьего голоса; отдельного объекта RDB нет.
- Точная семантика аппаратных записей в порт 08h (36h/76h/B6h) в
  func_music_start_track не верифицирована аппаратно (статус: UNVERIFIED).

## RDB save

```
Mapping entry point: 0x0000
Objects: 153
RDB: src/putup.rdb
RDB save: success (dirty=false)
```

## Recommended Next Steps

- Stage 9: исследование карт уровней (15 карт 16×11 тайлов), создание объектов
  data_level_01..data_level_15.
- Stage 10: сборка PUTUP_NEW.ROM из `./asm`; потребуется добавить в RDB и
  выгрузить блоки данных (таблицы нот/частот, графика, шрифт, карты уровней) и
  gap-обёртки, перечисленные выше.
