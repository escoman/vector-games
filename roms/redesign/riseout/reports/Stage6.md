# Stage 6. Вывод текста на экран (riseout.rom)

> Источник фактов — MCP `vector-debugger`: канонический `debug_load_rom` (org 0x0100, `roms/redesign/riseout/src/riseout.rom`), `debug_get_rdb_info`, `debug_disassemble_range`, `debug_analyze_code`, `debug_find_immediate_in_range`, `debug_read_memory_range`, `debug_read_memory`, `debug_get_vram_bytes`, правки только через `debug_add_rdb_object` / `debug_update_rdb_object` / `debug_set_rdb_comment` / `debug_set_rdb_property` / `debug_add_rdb_link` + `debug_save_rdb`. `debug_reset` не вызывался. Механизм вывода, найденный на Stage 2, не переисследовался — он уточнён и формализован в RDB.

## Goal (ТЗ, строки 162–173)

ТЗ: «Строки-кандидатов находит `strings_scan` … ИИ подтверждает, классифицирует, создаёт объекты `str_*` (комментарий = содержимое строки). Найти функцию вывода строк и её базовый адрес глифов (`data_glyph_block`); растровую сетку подтвердить `glyph_scan` (PNG на адресе блока), предсказание картинки сверить с реальностью `vram_credits` … Задача выполнена, когда найдены глифы всех строк. Отчёт `./reports/Stage6.md`.»

Разложенно на проверяемые пункты:

1. классифицировать прогоны `strings_scan` (терминатор / адресация / попадание в VRAM) и создать `str_*`;
2. отобразить таблицы текстовых записей как `data_*` и связать с `str_*`;
3. зафиксировать связи «функция вывода → таблица/строка»;
4. подтвердить базовый адрес глифов `data_glyph_block` и формулу адреса глифа;
5. прогнать `glyph_scan` (PNG) и `vram_credits` (вердикт);
6. показать, что глифы **всех** символов всех подтверждённых строк существуют.

Все адреса в отчёте — **адреса образа ROM** (ТЗ пишет смещение в файле; реальный адрес = смещение + 0x0100). Проверка: ТЗ `HIT BUTTON OR SPACE KEY @0x2A9D` → образ `0x2B9D` (подтверждено дампом).

## Method

1. **Предусловие.** `debug_get_rdb_info` на старте этапа: `loaded=true`, `object_count=403` (после Stage 5), sha256 ROM `c265014b…a6991`; `debug_reload_rdb` не потребовался. К концу этапа — **449 объектов**.
2. **Кандидаты.** 10 кандидатов `strings_scan` (`.scratch/pipeline/riseout/strings_scan.json`: 1576 прогонов, 120 прогонов длиной ≥10, charset ascii 309 / koi8 1267) разобраны по трём исходам: подтверждено как строка / переклассифицировано в `data_*` / отбраковано (раздел «Отбраковка»).
3. **Доказательная база строки.** Для каждого кандидата: `debug_read_memory_range` (байты + терминатор `00` или длина в заголовке), `debug_find_immediate_in_range(value=адрес, 256..20735)` (единственный адресный сайт `LXI H/D,<addr>`), `debug_disassemble_range` (как сайт связан с `CALL 16F3/2D1B/2D2F/12E0`), затем для титула — живое состояние RAM (знакостраница `0x5400`).
4. **Формат записей.** Два формата, оба подтверждены дизассемблированием: `[x, y, текст…, 00]` → `func_draw_text_records` (`0x2D1B`, B = число записей) / `func_draw_text_record_safe` (`0x2D2F`) / `func_draw_text_record` (`0x16F3`); и `[dst_lo, dst_hi, len, текст]` → `func_copy_record_entries` (`0x1E5D`) через `memcpy` (`0x12E0`) в RAM-буфер.
5. **Глифы.** `debug_analyze_code`/`debug_disassemble_range` по `0x0551`, `0x05B7`, `0x0124`, `0x0142`, сайты загрузки шрифта `0x2B32`/`0x2B3E`/`0x23CC`/`0x23F2`; затем `glyph_scan` (2 запуска, PNG просмотрены глазами) и `vram_credits`.
6. **Пересборка.** `PATH=$PWD/z88dk/bin:$PATH utils/analyze/run_pipeline.sh riseout --from export_asm` (без `--resume`), затем перегенерация `Stage1.md` через `analyze.report_gen`.

## 1. Механизм вывода: цепочка и две трассы

```
ROM: str_*  ─┬─ [x,y,текст..00] в таблице data_records_*  ── func_draw_text_records 0x2D1B (B=число записей)
             │                                                 └─ E=x=СТОЛБЕЦ, D=y=СТРОКА → func_draw_text_record 0x16F3
             └─ [dst_lo,dst_hi,len,текст] в data_msg_records ── func_copy_record_entries 0x1E5D → memcpy 0x12E0 → RAM-буфер
                                                                                                        │
                                    func_draw_text_record 0x16F3 ◄────────────────── коммит (0x21E4 и др.)┘
                                            │ подсчёт длины до 00; SHLD 7DEB; LXI H,5400
                                            ▼
                              знакостраница RAM 0x5400 (0x5400 + 256*(row>>3) + 32*(row&7) + col)
                                            ▼
        func_put_char_glyph 0x0124 / func_fill_char_glyph 0x0142 → func_render_glyph_vram 0x0551 → func_write_plane_run 0x05B7
                                            ▼
                    4 битплоскости VRAM 0x8000 / 0xA000 / 0xC000 / 0xE000 (шаг 0x2000)
```

**Ветвление рендерера** (`0x0551`, подтверждено дизассемблированием `0x0551..0x057A` и `0x05DD..0x061B`):

| участок | смысл |
|---|---|
| `LXI B,AC00; DAD B` | HL − 0x5400 → смещение в знакостранице |
| `MOV A,L; ANI 1F` | столбец = смещение & 0x1F |
| `MOV A,L; ANI E0; MOV A,H; ANI 03; ORA B; RRC; RRC` | группа строк (смещение & 0xE0 \| bank) / 4 |
| `LDA 081C; SUB E` | база знакоместа из переменной |
| `CPI 20` → `JZ 0645` | **пробел**: заполнение нулями, растр не читается |
| `CPI 65; JNC 05DD` / `CPI 70; JNC 0579` | коды `<0x65` и `≥0x70` — «шрифтовой» путь; `0x65..0x6F` — служебный путь |
| `LXI B,5807; DAD B; MOV A,M; RRC` (шрифтовой) / `0x5800` (служебный) | байт режима глифа, `ANI 088h` → 0 = пусто, `0x88` = solid `FF`, `0x80` = копия, `0x08` = инверсия |
| `LXI D,0800; DAD D` | растр = `0x6000 + 8*код` (0x6400 — зеркало для кодов ≥0x80, 0x6700 — кредит-полоса) |

**Семантика `^`.** ТЗ трактует `^` в цитатах (`^LEVEL COMPLETE^`, `RISE OUT^2!!`) как управляющий маркер координат/атрибута. Это **не подтвердилось**: код `0x5E` — печатный глиф «двойная горизонтальная линия», растр `00 00 00 7E 7E 00 00 00` (дамп `0x3404`). Он стоит **перед цифрой** в `PLAYER^1` (`str_player_label` + `ADI 30 / STAX D` на `0x2384..0x2386`), в `RISE OUT^2!!`, в `LEVEL INC:CTRL^`, т. е. это узкий визуальный разделитель/подложка, а не escape-код. Управляющих маркеров в строках riseout нет: позиция всегда берётся из заголовка записи (`x`,`y`) или из `LXI D,buf`/`LXI B,len` для in-code литералов.

**Уточнение к Stage 5.** В `Stage5.md` формат записи описан как `{строка, столбец, текст…00}` — порядок байт обратный: **первый байт = столбец (x), второй = строка (y)**. Доказательство: `func_draw_text_records` делает `MOV E,M` (первый байт) и `MOV D,M` (второй), а `func_draw_text_record` из `E` делает столбец (`ANI 1F`-подобная ветка), из `D` — строку; проверено на `data_records_keyword` (`0x16E3 = 0A 01` → «KEYWORD?» в столбце 10 строки 1, поле ответа `LXI H,5433` = строка 1, столбец 19 — примыкает вплотную) и на `str_title_copyright` (`0x2BE5 = 02 16` → знакостраница `0x56C2` = строка 22, столбец 2, дампом подтверждено). В комментариях RDB с Stage 2 порядок `[x, y, …]` корректен, правок не потребовалось.

## 2. Подтверждённые строки (34 объекта `str_*`)
| `str_*` | адрес | размер | содержимое (⟨XX⟩ = код < 0x20) | доказательство (адресный сайт / заголовок записи) |
|---|---|---|---|---|
| `str_prompt_keyword` | `0x16E5` | 14 | `KEYWORD?     ` | data_records_keyword rec0 header 0x16E3 = 0A 01 (x=10,y=1), text 0x16E5..0x16F2 (KEYWORD? + 5 spaces + 00) |
| `str_msg_level_complete` | `0x1CE5` | 16 | `^LEVEL COMPLETE^` | data_msg_records rec0, header 0x1CE2 = 21 73 10 (dst 0x7321, len 16) |
| `str_msg_bonus` | `0x1CF8` | 11 | `BONUS:  000` | data_msg_records rec1, header 0x1CF5 = 63 73 0B (dst 0x7363, len 11) |
| `str_msg_next_scene` | `0x1D06` | 13 | `NEXT SCENE IS` | data_msg_records rec2, header 0x1D03 = A2 73 0D (dst 0x73A2, len 13) |
| `str_msg_keyword_label` | `0x1D16` | 9 | `KEYWORD:"` | data_msg_records rec3, header 0x1D13 = 22 74 09 (dst 0x7422, len 9) |
| `str_msg_good_luck` | `0x1D22` | 14 | `^ GOOD  LUCK ^` | data_msg_records rec4, header 0x1D1F = 22 74 0E (dst 0x7422, len 14) |
| `str_msg_all_patterns` | `0x1D33` | 13 | `^ALL PATTERNS` | data_msg_records rec5, header 0x1D30 = 21 73 0D (dst 0x7321, len 13) |
| `str_msg_completed` | `0x1D43` | 10 | `COMPLETED^` | data_msg_records rec6, header 0x1D40 = 47 73 0A (dst 0x7347, len 10) |
| `str_msg_secret_keys` | `0x1D50` | 16 | `* SECRET KEYS  *` | data_msg_records rec7, header 0x1D4D = 81 73 10 (dst 0x7381, len 16) |
| `str_msg_level_inc` | `0x1D63` | 16 | `LEVEL INC:CTRL^#` | data_msg_records rec8, header 0x1D60 = A1 73 10 (dst 0x73A1, len 16) |
| `str_msg_men_inc` | `0x1D76` | 16 | `MEN   INC:CTRL^"` | data_msg_records rec9, header 0x1D73 = C1 73 10 (dst 0x73C1, len 16) |
| `str_msg_more_levels` | `0x1D89` | 14 | `MORE LEVELS IN` | data_msg_records rec10, header 0x1D86 = 02 74 0E (dst 0x7402, len 14) |
| `str_msg_rise_out` | `0x1D9A` | 12 | `RISE OUT^2!!` | data_msg_records rec11 (last), header 0x1D99 = 23 74 0C (dst 0x7423, len 12) |
| `str_color_player_one` | `0x202B` | 9 | `⟨D0⟩⟨CC⟩⟨C1⟩⟨D9⟩⟨C5⟩⟨D2⟩⟨DE⟩⟨B1⟩` | data_records_player_color rec0 header 0x2029 = 0D 01 (x=13,y=1), text 0x202B..0x203B (PLAYER 5E + high-bit codes D0 CC C1 D9 C5 D2 DE B1 + 00) |
| `str_ready` | `0x233A` | 9 | `^ READY ^` | LXI H,233A @0x231D |
| `str_game_over` | `0x2356` | 13 | `^ GAME OVER ^` | LXI H,2356 @0x2278 |
| `str_high_score` | `0x2363` | 18 | `HIGH SCORE:    00:` | LXI H,2363 @0x228A |
| `str_player_label` | `0x2388` | 7 | `PLAYER^` | LXI D,718C |
| `str_hud_status` | `0x24B2` | 29 | `SCORE:    00 MEN: 5 LEVEL: 1` | LXI H,24B2 @0x249B |
| `str_title_from_dungeons` | `0x2B8D` | 14 | `FROM DUNGEONS` | data_title_records rec0 header 0x2B8B = 0A 08 (x=10,y=8), text 0x2B8D..0x2B9A (13+00) |
| `str_title_hit_button` | `0x2B9D` | 24 | `HIT BUTTON OR SPACE KEY` | data_title_records rec1 header 0x2B9B = 05 0B (x=5,y=11), text 0x2B9D..0x2BB4 (23+00) |
| `str_title_up_to_players` | `0x2BB7` | 16 | `UP TO 4 PLAYERS` | data_title_records rec2 header 0x2BB5 = 09 0E (x=9,y=14), text 0x2BB7..0x2BC6 (15+00) |
| `str_title_and` | `0x2BC9` | 4 | `AND` | data_title_records rec3 header 0x2BC7 = 0F 10 (x=15,y=16), text 0x2BC9..0x2BCC (AND+00) |
| `str_title_speed_level` | `0x2BCF` | 14 | `3 SPEED LEVEL` | data_title_records rec4 header 0x2BCD = 0A 12 (x=10,y=18), text 0x2BCF..0x2BDC (13+00) |
| `str_title_symbol_row` | `0x2BDF` | 6 | `⟨0B⟩⟨0C⟩⟨0D⟩⟨0E⟩⟨0F⟩` | data_title_records rec5 header 0x2BDD = 11 15 (x=17,y=21), text 0x2BDF..0x2BE4 = 0B 0C 0D 0E 0F 00 (service glyphs, no ASCII) |
| `str_title_copyright` | `0x2BE7` | 29 | `COPYRIGHT 1983 +,-./< ⟨01⟩⟨02⟩⟨03⟩⟨04⟩⟨05⟩⟨06⟩` | data_title_records rec6 header 0x2BE5 = 02 16 (x=2,y=22), text 0x2BE7..0x2C03 (28+00) |
| `str_menu_how_many_players` | `0x2C8B` | 18 | `HOW MANY PLAYERS?` | data_records_players_count rec0 header 0x2C89 = 08 0B (x=8,y=11), text 0x2C8B..0x2C9C (17+00) |
| `str_menu_player` | `0x2C9D` | 7 | `PLAYER` | standalone literal: LXI D,0D0E @0x2C34 (D=0D row, E=0E col) |
| `str_menu_select_speed` | `0x2CDD` | 19 | `SELECT SPEED LEVEL` | data_records_speed_menu rec0 header 0x2CDB = 08 0B (x=8,y=11), text 0x2CDD..0x2CEE (18+00) |
| `str_menu_player_one` | `0x2CF2` | 13 | `^ PLAYER^1 ^` | data_records_speed_menu rec1 header 0x2CEF = 0A 0D (x=10,y=13), text 0x2CF2..0x2CFE (12+00) |
| `str_menu_low` | `0x2D01` | 4 | `LOW` | data_records_speed_menu rec2 header 0x2CFF = 0B 0F (x=11,y=15), text 0x2D01..0x2D04 (LOW+00) |
| `str_menu_normal` | `0x2D07` | 7 | `NORMAL` | data_records_speed_menu rec3 header 0x2D05 = 0B 11 (x=11,y=17), text 0x2D07..0x2D0D (NORMAL+00) |
| `str_menu_high` | `0x2D10` | 5 | `HIGH` | data_records_speed_menu rec4 (last) header 0x2D0E = 0B 13 (x=11,y=19), text 0x2D10..0x2D14 (HIGH+00) |
| `str_menu_speed` | `0x2D15` | 6 | `SPEED` | standalone literal: LXI D,0F12 |

Все 34 строки имеют: (а) терминатор `00` либо явную длину в заголовке/в `LXI B`; (б) единственный адресный сайт или принадлежность записи таблицы; (в) ссылку `data_* → str_*` или `func_* → str_*`; (г) свойство `evidence` с конкретными мнемониками и адресами.

Runtime-подтверждение «доходит до экрана» для титульного набора: знакостраница RAM содержит `0x56C0.. = 20 20 43 4F 80 89 82 73…` — то есть `␣␣COPYRI…` в строке 22, столбце 2, ровно как предписывает заголовок записи `0x2BE5 = 02 16` (`debug_read_memory` 22208, текущее состояние эмулятора).

## 3. Таблицы записей и служебные данные (11 объектов `data_*`)
| `data_*` | адрес | размер | что хранит | доказательство |
|---|---|---|---|---|
| `data_credits_logo_strip` | `0x0721` | 254 | Растровая строка русских кредитов: 32 ячейки 8x8 = коды 0xE0..0xFF шрифта, читается из RAM 0x6700 (LXI H,0721 / LXI D,6700 / LXI B,0100 / CALL 017C @0x2B3E) | LXI H,0721 |
| `data_records_keyword` | `0x16E3` | 2 | Запись [x=0A,y=01,KEYWORD?..00] 0x16E3..0x16F2 | LXI H,16E3 @0x125C |
| `data_msg_records` | `0x1CE2` | 3 | Таблица сообщений 0x1CE2..0x1DA5: 12 записей [dst_lo,dst_hi,len,текст], первая dst=0x7321 len=16 | LXI H,1CE2 @0x1C0C (func_init_playfield_buffers) |
| `data_level_keywords` | `0x1F49` | 80 | 20 четырёхсимвольных имён-ключей уровня (UNDR SNAK ... TRAP TANK) | LXI H,1F49 @0x1277 (func_probe_control_keys) and @0x1C52 (func_init_playfield_buffers) |
| `data_records_player_color` | `0x2029` | 2 | Запись [x=0D,y=01,D0 CC C1 D9 C5 D2 DE B1..00] 0x2029..0x2033: коды ASCII+0x80 дают глифы PLAYER^1 | LXI H,2029 @0x200F |
| `data_title_records` | `0x2B8B` | 2 | Таблица записей заставки 0x2B8B..0x2C03: 7 записей формата [x,y,текст..00] | LXI H,2B8B @0x2B63 then CALL 2D1B @0x2B66 (func_attract_draw_title) |
| `data_logo_strip_codes` | `0x2C04` | 30 | Коды глифов кредит-полосы E0..FD (30 байт) | LXI D,2C04 @0x2B6C |
| `data_records_players_count` | `0x2C89` | 2 | Запись [x=08,y=0B,HOW MANY PLAYERS?..00] 0x2C89..0x2C9C | LXI H,2C89 @0x2C2C |
| `data_records_speed_menu` | `0x2CDB` | 2 | Таблица записей меню скорости 0x2CDB..0x2D14: 5 записей [x,y,текст..00], первая x=08,y=0B | LXI H,2CDB @0x2CA7 |
| `data_glyph_block` | `0x3114` | 1024 | Шрифт 8x8: 128 глифов по 8 байт, адрес = 0x3114+8*код, байт0 = верхняя строка, MSB = левый пиксель | LXI H,3114 |
| `data_glyph_mode_table` | `0x3514` | 128 | Атрибуты (режимы) служебных глифов кодов 0x60..0x6F: 16 групп по 8 байт, ROM 0x3514+8*(код-0x60) -> RAM 0x5B00+8*(код-0x60) @0x23F2 (LXI H,3514 / LXI D,5B00 / LXI B,0080 / CALL 017C) | LXI D,5B00 |

**Размеры таблиц.** `rdb_lint` трактует пересечение объектов как **error**, поэтому объект на таблицу занимает только собственные дескрипторные байты (2 или 3 — заголовок первой записи), а полный охват (`0x2B8B..0x2C03`, `0x1CE2..0x1DA5`, `0x2CDB..0x2D14`) назван в комментарии, членство выражено связями `data_* → str_*`. Исключение — монолитные блоки данных без вложенных объектов: `data_glyph_block` (1024), `data_glyph_mode_table` (128), `data_credits_logo_strip` (254), `data_level_keywords` (80), `data_logo_strip_codes` (30).

## 4. Связи «функция → данные/строка»

Всего в RDB **366 связей** (было 309 на старте Stage 6). Добавлено 57: `data_msg_records` → 12 строк, `data_title_records` → 7, `data_records_players_count` → 2, `data_records_speed_menu` → 5, `data_records_keyword`/`data_records_player_color` → по 1, `data_logo_strip_codes` → `data_credits_logo_strip`, а также:

| функция | читает | сайт |
|---|---|---|
| `func_attract_draw_title` `0x2B61` | `data_title_records` (0x2B8B), `data_logo_strip_codes` (0x2C04), `str_menu_how_many_players`, `str_menu_player`, `str_menu_speed` | `LXI H,2B8B @0x2B63` / `LXI D,2C04 @0x2B6C` / `LXI H,2C89 @0x2C2C` / `LXI H,2C9D @0x2C37` / `LXI H,2D15 @0x2CB2` |
| `func_attract_init_scene` `0x2AFF` | `data_glyph_block` (0x3114), `data_credits_logo_strip` (0x0721) | `LXI H,3114; LXI D,6000; LXI B,0400; CALL 017C @0x2B32`; `LXI H,0721; LXI D,6700; LXI B,0100; CALL 017C @0x2B3E` |
| `func_init_title_screen` `0x23B5` | `data_glyph_block`, `data_glyph_mode_table` (0x3514), `str_hud_status` | `LXI H,3114 @0x23CC` (два прогона: 0x6000 и 0x6400), `LXI D,5B00; LXI H,3514; LXI B,0080; CALL 017C @0x23F2`, `LXI H,24B2; CALL 16F3 @0x249B` |
| `func_attract_menu_key_handler` `0x26C6` → блок `lbl_2ca4` `0x2CA4` | `data_records_speed_menu` | `LXI H,2CDB; MVI B,05; CALL 2D1B @0x2CA7..0x2CAC` |
| `func_probe_control_keys` `0x121F` | `data_records_keyword`, `data_level_keywords` | `LXI H,16E3; MVI B,01; CALL 2D1B @0x125C`, `LXI H,1F49 @0x1277` |
| `func_start_new_level` `0x1FAD` | `data_records_player_color` | `LXI H,2029; MVI B,01; CALL 2D1B @0x200F` |
| `func_init_playfield_buffers` `0x1BA1` | `data_msg_records`, `data_level_keywords` | `LXI H,1CE2 @0x1C0C`, `LXI H,1F49 @0x1C52` |
| `func_copy_record_entries` `0x1E5D` | `data_msg_records` | unpack `[dst_lo,dst_hi,len,text]`, `CALL 12E0 @0x1E66` |
| `func_draw_text_records` `0x2D1B` | все `data_records_*` | `MOV E,M; MOV D,M; CALL 16F3` |
| `func_level_complete_sequence` `0x2312` | `str_ready` | `LXI H,233A; LXI D,71CB; LXI B,0009; CALL 12E0 @0x231D` |
| `func_game_over_high_score` `0x223C` | `str_game_over`, `str_high_score` | `LXI H,2356; LXI D,714A; LXI B,000D; CALL 12E0 @0x2278`; `LXI H,2363; LXI D,71C8; LXI B,0011; CALL 12E0 @0x228A` |
| `func_draw_player_speed_text` `0x2374` | `str_player_label` | `LXI H,2388; LXI B,0007; CALL 12E0 @0x237B` |

## 5. `data_glyph_block`: адресация глифов

**Факт (код загрузки).** ROM-блок глифов — **`0x3114`, 1024 байта = 128 глифов × 8 байт**:

```
0x2B32 LXI H,3114 ; LXI D,6000 ; LXI B,0400 ; CALL 017C      ; один прогон в 0x6000 (аттракт-режим)
0x23C6 MVI B,02   ; LXI D,6000 ; LXI H,3114 ; LXI B,0400 ; CALL 017C ; DE := DE+0x400 ; DCR B ; JNZ
```

то есть игровая инициализация кладёт **две копии**: `RAM 0x6000` (коды `00..7F`) и `RAM 0x6400` (коды `80..FF` = зеркало тех же глифов — «цветовой» вариант, см. `str_color_player_one`).

**Формула адреса глифа** (свойство `glyph_formula` объекта `data_glyph_block`):

```
растр(код) = RAM 0x6000 + 8*код        (код 8 бит; 80..FF → зеркало 0x6400 + 8*(код-80h))
             RAM 0x6700 + 8*(код-E0h)  — кредит-полоса (блок 0x0721, коды E0..FF)
режим(код)  = RAM 0x5807 + 8*код       (шрифтовой путь) | RAM 0x5800 + 8*код (служебный путь 65..6F)
             режим = байт ANI 88h: 00 пусто, 88 solid FF, 80 копия, 08 инверсия
VRAM(плоскость 3) = 0x8000 + 256*столбец + (224 - 8*строка) + k,  k = 0..7 ↔ байты глифа 7..0
```

Байт 0 глифа = **верхняя** строка, MSB = левый пиксел; в VRAM строки лежат в обратном порядке (k=0 — нижняя строка), что и подтверждено дампом.

**Проверка формулы образом (текущее состояние эмулятора, три дампа).**

| что | адрес | дамп |
|---|---|---|
| код в знакостранице (`C` из COPYRIGHT) | `0x56C2` | `43` |
| растр кода `0x43` по формуле `0x6000+8*43h` | `0x6218` | `7C E2 E0 E0 E0 E2 7C 00` |
| VRAM-плоскость по формуле `0x8000+256*2+(224-8*22)` = `0x8230` | `0x8230` | `00 7C E2 E0 E0 E0 E2 7C` — **тот же растр, обратный порядок байт** ✔ |
| соседние плоскости | `0xA230` = `00 7C E2 E0 E0 E0 E2 7C`, `0xC230`/`0xE230` = `00…` | знак пишется в две младшие плоскости (цвет 3), две старшие — ноль |
| растр кода `0x42` (`B`), контроль шага 8 | `0x6210` | `FC 4E 4E 7C 4E 4E FC 00` ✔ |

**Служебные глифы.** `data_glyph_mode_table` (`0x3514`, 128 байт → `RAM 0x5B00` = `0x5800+8*60h`) задаёт режимы для кодов `0x60..0x6F`; коды `0x00..0x0F`, `0x2B..0x2F`, `0x3C` — это не буквы, а блочные/штриховые глифы, которыми набраны титульная «строка символов» (`str_title_symbol_row`, коды `0B 0C 0D 0E 0F`) и хвост `str_title_copyright` (коды `01..06`, `+ , - . / <`).

## 6. `glyph_scan` — сетка подтверждена растром

Стадия `glyph_scan` в прогоне **не создаётся** без CLI-флага `--glyph-address` (`utils/analyze/pipeline.py`: `Step("glyph_scan", …) if ctx.glyph_address else None`), поэтому в `pipeline.json` добавлены `stage_args.glyph_scan` (`--address 0x3114 --count 128 --layout mono --stride 8`), а сами запуски выполнены модулем напрямую:

| запуск | вердикт | RDB-объект | PNG |
|---|---|---|---|
| `--address 0x3114 --count 128` | `CANDIDATE` — «128 глиф(а) из 128, групп повторов 6, источник IMAGE» | `data_glyph_block` | `.scratch/pipeline/riseout/riseout_0x3114_8x8_mono_strip.png` + 128 файлов `riseout_0x3114_8x8_mono_NNN.png` |
| `--address 0x0721 --count 30` | `CANDIDATE` — «30 глиф(а) из 30, групп повторов 0, источник IMAGE» | `data_credits_logo_strip` | `.scratch/pipeline/riseout/riseout_0x0721_8x8_mono_strip.png` + 30 файлов |

Просмотр полос глазами (`.scratch/pipeline/riseout/riseout_0x3114_8x8_mono_strip.png`): читаются латинские `A…Z`, цифры `0…9`, знаки `? : " * + , - . / <`; `0x5E` — двойная горизонтальная линия. Просмотр `riseout_0x0721_8x8_mono_strip.png`: читается русская строка кредитов **«© Версия для „Вектор 06Ц", ПК „СчетМаш" г. Кишинев 1990»** — то есть блок `0x0721` это не шрифт, а **готовый растровый баннер** (32 ячейки 8×8).

6 групп повторов в шрифтовом блоке — это реально повторяющиеся растры (например пустые/дублирующиеся знаки `0x2B..0x2F`), что согласуется с назначением блока.

## 7. `vram_credits` — вердикт `no_data`, предсказание проверено вручную

В `pipeline.json` добавлено `stage_args.vram_credits = {"--string": "str_title_copyright", "--base-low": "0x081C", "--columns": "32"}` (дефолт модуля — `str_credits_koi8`, объекта с таким именем в riseout нет). Прогон:

```
PYTHONPATH=utils python3 -m analyze.cli vram_credits --rom … --org 0x0100 --rdb … --string str_title_copyright
→ verdict = "no_data: ни один предсказанный адрес не лёг в VRAM", status = CANDIDATE
→ cursors_found = ["0x56C2"], tables = {column_table: [null, 0], glyph_table: null}
```

Причина **не** «строка не рендерится», а методическая: модуль ищет в ROM таблицу баз столбцов и табличный указатель на глиф, а riseout вычисляет адрес арифметически (`LXI B,AC00 / DAD B / ANI 1F / … / LXI D,0800`), поэтому ни один предсказанный адрес не попадает в диапазон VRAM `0x8000..0xFFFF`. Косвенное, но сильное подтверждение рендера: модуль **сам нашёл живую копию строки** в знакостранице по адресу `0x56C2` (строка 22, столбец 2 — совпадает с заголовком записи `02 16`).

Прямая проверка «предсказание ↔ реальность» выполнена средствами MCP (раздел 5, таблица дампов): формула даёт `0x8230`, дамп VRAM содержит ровно растр `C` из RAM `0x6218` в обратном порядке байт. По семантике это **MATCHED**; формальный вердикт `MATCHED` недостижим, пока модуль `vram_credits` не научится арифметическую адресацию (это не правит TЗ-критерий «найдены глифы всех строк»).

## 8. Покрытие глифов — критерий ТЗ выполнен

Символьный алфавит всех 34 подтверждённых строк: **64 уникальных кода**. Для каждого код → адрес растра по формуле → 8 байт растра:

* `0x20` (пробел, встречается в 23 строках) — растр нулевой **по конструкции**: ветка `CPI 20 → JZ 0645` заполняет клетку нулями, растр не читается; это не отсутствие глифа;
* все остальные 63 кода имеют ненулевой растр в `data_glyph_block` (коды `<0x80`) либо в его зеркале `RAM 0x6400` (коды `B1,C1,C5,CC,D0,D2,D9,DE` = ASCII+0x80);
* коды `0x01..0x06`, `0x0B..0x0F`, `0x2B..0x2F`, `0x3C`, `0x5E` — служебные/блочные глифы, растры присутствуют;
* дополнительно проверены два табличных набора: `data_level_keywords` (80 байт, 24 уникальных кода — все глифы на месте) и `data_logo_strip_codes` (30 кодов `E0..FD`) — все растры в `data_credits_logo_strip` ненулевые, кроме **кода `0xE1`**: это намеренная пустая ячейка-разделитель внутри баннера (растр `00×8`), а не недостающий глиф.

Итог по ТЗ: «найдены глифы всех строк» — **выполнено**, пропусков нет.

## 9. Отбраковка ложных прогонов

| кандидат `strings_scan` | исход | причина |
|---|---|---|
| `str_080a` | **отбракован** | байты `0x080A..` = хвост растра кредит-полосы (`data_credits_logo_strip` заканчивается на `0x081E`) плюс идущий следом ROM-текст `STAX INX DAD LDAX DCX RST PSW POP PUSH` (`0x0811..`), попадающий в окно 256-байтовой копии `0x0721→0x6700`; адрес `0x080A` не имеет ни одного адресного сайта (`debug_find_immediate_in_range(2058)` = 0 совпадений), на экран как текст не выводится — это *растровые* байты, «читабельные» только в KOI8-трактовке сканера |
| `str_30ee` | **отбракован** | `0x30A2..0x3113` — таблица 16-битных убывающих значений (`0EE8, 0E12, 0D48, …`), музыкальные частоты; ни одного `LXI` на `12520`/`0x30EE`; байты образуют «текст» только случайно |
| `str_3148` | **отбракован** | попадает **внутрь** `data_glyph_block` (`0x3114..0x34FF`) — это растр 4-го глифа, а не строка |
| `str_24b0` | **заменён** | `0x24B0..0x24B1` = `7C C9` = `MOV A,H; RET` (конец `func_init_title_screen`), терминатор скан «увидел» на `0x24CF`; реальная строка начинается с `0x24B2` → `str_hud_status` |
| `str_1f49` | **переклассифицирован** | 80 байт `UNDR SNAK BIGI GRAS LADR 2TOW ASCI LOOP ROOM AMID 5TOW LAKE GOLG PYR2 PYR3 OOBA PYR1 PYR4 TRAP TANK` — не текст, а **20 четырёхбайтных ключей уровня** (20×4), адресуются как таблица (`LXI H,1F49 @0x1277`, `@0x1C52`); объект `data_level_keywords` (тип `data`) |
| `str_16e5`, `str_2b9d`, `str_2bb7`, `str_2c8b`, `str_2cdd` | **подтверждены и переименованы** | `str_prompt_keyword`, `str_title_hit_button`, `str_title_up_to_players`, `str_menu_how_many_players`, `str_menu_select_speed` |

Отбраковка фиксируется в RDB не «удалением следа», а отсутствием объекта: лишних объектов по этим адресам нет (проверено `debug_find_rdb_object`/выгрузкой списка).

## 10. KOI8-русские строки: их нет

`strings_scan` дал 1267 KOI8-прогонов против 309 ASCII — при проверке это оказалось **систематическим ложным классом**: riseout не хранит кириллический текст. Подтверждающие наблюдения:

1. единственный способ получить «русские» буквы в строке — байты `≥0x80`, а все такие байты в подтверждённых строках равны `ASCII+0x80` (`D0 CC C1 D9 C5 D2 DE B1` = «PLAYER^1»), то есть это **цветовой вариант того же глифа** (зеркало шрифта в `RAM 0x6400`, см. раздел 5), а не KOI8;
2. русскоязычные кредиты существуют, но как **растровый баннер** `0x0721` (коды `E0..FD`), а не как текст: набор символа в баннере не соответствует ни ASCII, ни KOI8, и читается только глазами (раздел 6);
3. ни одного адресного сайта на «кириллические» прогоны `0x080A/0x30EE/0x3148` нет.

Вывод зафиксирован в RDB свойством `charset_note` объекта `data_glyph_block`, чтобы сканеры последующих этапов не соблазнялись.

## 11. Линт, сборка, round-trip

| метрика | до Stage 6 | после Stage 6 |
|---|---|---|
| объектов RDB | 403 | **449** (+46: 11 `data_*`, 34 `str_*` из них переименовано/создано, 1 func-объект = 105 функций против 104) |
| типы | 104 func / 266 lbl / 33 var | **105 func / 266 lbl / 34 str / 33 var / 11 data** |
| связей | 309 | **366** |
| объектов со `evidence` | — | **46** |
| `rdb_lint` находок | 1067 (2 error / 1048 warning / 17 info) | **1022** (2 error / 1003 warning / 17 info) |
| в том числе `missing_evidence` | 132 | **87** (−45: ровно на число новых объектов) |
| `symbolic_operand_lint` | 375 находок, 0 блокирующих | **408** (361 `orphan_label` warn + 47 `should_be_symbolic` info) |
| `syntax_check` | clean | **clean** — ни одной `invalid character`, все комментарии однострочные |
| `roundtrip_verify` | byte-for-byte identical | **`verdict = "byte-for-byte identical"`** (`compared_bytes=20480`, `bytes_differing=0`, `size_match=true`, `offenders=[]`) |
| `measure_sizes` | 366 из 403 | 367 из 449 |

`+33` к `should_be_symbolic` — ожидаемая динамика: числа операндов начали «попадать» под новые имена. Два попадания заслуживающие  отметить: `STA 081B/081C` (запись в RAM) lint относит к `data_credits_logo_strip`, потому что ROM-байты `0x0721..0x081E` и RAM-адреса `0x081B..` в плоской модели эмулятора лежат в одном диапазоне; это info-подсказка, а не ошибка, и она же объясняет, почему RAM-переменные `var_*` в низких адресах соседствуют с ROM-блоками.

Две ошибки `rdb_lint` унаследованы с Stage 5 и в рамки Stage 6 не правились (правило 6): `overlap` `var_speed` (0x7C88..0x7C8F) перекрывает `var_bcd_display_ptr` @`0x7C8D`; `alias_invalid` у `var_field_marker_count` @`0x7C6E` (алиас содержит пояснение в скобках и не проходит шаблон имён). **Исправлены после завершения Stage 6** отдельной правкой через MCP: `var_speed` → `size=4` (индекс слота 0-базирован, игроков не более четырёх), алиас нормализован в `var_scroll_row_counter`; детали и доказательства — раздел «Поправки» в `Stage5.md`. После правок `rdb_lint`: 0 errors, экспорт пересобран, round-trip `byte-for-byte identical`.

## Verified Facts

1. Титул рисуется пакетом: `MVI B,07 @0x2B61`; `LXI H,2B8B @0x2B63`; `CALL 2D1B @0x2B66` — 7 записей формата `[x=столбец, y=строка, текст…, 00]`, охват таблицы `0x2B8B..0x2C03`.
2. `func_draw_text_records` (`0x2D1B`) из первых двух байт записи делает `E=x`, `D=y` и вызывает `func_draw_text_record` (`0x16F3`); `func_draw_text_record_safe` (`0x2D2F`) — `PUSH H/D/B; CALL 16F3; POP B/D/D; RET` (обёртка сохранения регистров).
3. Второй формат записей `[dst_lo, dst_hi, len, текст]` unpack-ится `func_copy_record_entries` (`0x1E5D`) и переносится `memcpy` (`0x12E0`, `HL→DE`, счёт `BC`) в RAM-буфер; адресатами являются `0x7321, 0x7363, 0x73A2, 0x7422, 0x7321, 0x7347, 0x7381, 0x73A1, 0x73C1, 0x7402, 0x7422, 0x7423` (12 записей `data_msg_records`).
4. In-code литералы (`str_ready`, `str_game_over`, `str_high_score`, `str_player_label`) не имеют терминатора: длина задаётся `LXI B,<len>` перед `CALL 12E0`; за `0x233A+9` сразу идёт код (`CD DF 1A = CALL 1ADF`).
5. Базовый адрес глифов — **`data_glyph_block` = `0x3114`**, 1024 байта = 128×8; загружается в `RAM 0x6000` (`LXI D,6000; LXI B,0400; CALL 017C @0x2B32`) и **дважды** (`0x6000` и `0x6400`) на игровой инициализации (`MVI B,02; LXI D,6000 @0x23C6..0x23C8`), где зеркало `0x6400` даёт цветовой вариант кодов `≥0x80`.
6. Формула растра `RAM 0x6000 + 8*код` подтверждена дампом: `0x6218` = растр `C`, `0x6210` = растр `B`, RAM `0x6770` = ROM `0x0791` (копия кредит-полосы).
7. Формула VRAM подтверждена дампом: знак `C` в клетке (столбец 2, строка 22) лёг в `0x8230..0x8237` как `00 7C E2 E0 E0 E0 E2 7C` — обратный порядок строк относительно RAM-растра; плоскости `0xA230` совпадает, `0xC230`/`0xE230` нулевые.
8. `0x5E` — печатный глиф «двойная линия» (`00 00 00 7E 7E 00 00 00`), а не управляющий маркер: он стоит перед цифрами (`PLAYER^1`, `RISE OUT^2!!`, `LEVEL INC:CTRL^`), позиции строк задаются исключительно заголовками записей или `LXI D`/`LXI B`.
9. Русские кредиты — растровый баннер `data_credits_logo_strip` (`0x0721`, 30 используемых ячеек `E0..FD` → `RAM 0x6700`, копируется 256 байт `LXI B,0100 @0x2B44`); коды для двух строк по 15 глифов лежат в `data_logo_strip_codes` (`0x2C04..0x2C21`), рисуются циклом `LDAX D; CALL 0551; INX H; INX D` (`0x2B71..0x2B7A`) в клетки `0x5709`/`0x5729`.
10. Таблица 20 ключей уровня — `data_level_keywords` (`0x1F49..0x1F98`, 20×4), читается как таблица (два сайта `LXI H,1F49` на `0x1277` и `0x1C52`), а не как текст.
11. Глифы есть для **всех** 64 кодов всех 34 подтверждённых строк; из 64 только `0x20` имеет нулевой растр, и это обработка пробела отдельной веткой (`CPI 20 → JZ 0645`), а не пробел в шрифте.
12. Round-trip после всех правок: `verdict = "byte-for-byte identical"`, 20480/20480 байт, 0 расхождений; `syntax_check` чистый.

## Inference (не прямое наблюдение)

* Назначение RAM-буфера `0x7000+32*строка+столбец` как «окна оверлея/поля», коммитом в знакостраницу которого занимается `func @0x21E4` (`MVI B,16; LXI H,72E0; …; LXI D,56E0`): координаты `0x71CB` = строка 14 столбец 11 и `0x714A` = строка 10 столбец 10 раскладываются ровно по этой модели, но полный обзор писателей буфера — не предмет Stage 6.
* Трактовка «цветового» назначения high-bit кодов: режим/палитра выводится из байта режима и палитровой рампы (`var_palette_ramp_ptr`), а не из самого кода; в строке `str_color_player_one` high-bit-вариант явно означает «PLAYER 1» в цвете — по смыслу вызова (`func_start_new_level`) и по соседству с номером слота.

## Open questions

1. Формальный `MATCHED` от `vram_credits` недостижим для riseout (модуль ожидает табличную адресацию) — нужен либо апгрейд модуля, либо другой ROM; зафиксировано как `no_data` + ручная проверка.
2. Точное число и набор записей, которые реально показываются в аттракт-режиме (часть `data_msg_records` — служебные строки GAME OVER/секретов,их  порядок показа зависит от состояния `var_*`); в трассе подтверждён только титульный набор + позиция COPYRIGHT.
3. Назначение текстового «осколка» `STAX INX DAD LDAX DCX RST PSW POP PUSH` на `0x0811..` (вне окна вывода, ноль адресных сайтов) — похоже на остаток листинга дизассемблера в образе; недоказуемо без источников.
4. `measure_sizes` даёт 367 расхождений размера: для строк размеры проставлены по терминатору/длине, для `lbl_*` — неизвестны (0 по умолчанию), что штатно.

## Что из ТЗ выполнено не полностью

* `vram_credits` = `MATCHED` — **не получен**; получен `no_data` по причине, описанной в разделе 7 (методика модуля не покрывает арифметическую адресацию riseout). Равносильная проверка выполнена вручную средствами MCP (раздел 5).
* `glyph_scan` как **стадия прогона** не запускалась автоматически: конвейер включает её только при CLI `--glyph-address` (в `pipeline.json` такой ключ выразить нельзя, а `utils/analyze` по правилам этапа менять запрещено). Добавлены `stage_args` (в прогоне выдано предупреждение «конфиг: stage_args для неизвестных стадий: glyph_scan») и выполнены два прямых запуска модуля с теми же параметрами.
* Флаг `--buffer` модуля `vram_credits` (nargs=2) через `stage_args` не выражается — в прямом запуске передан вручную (`--buffer 0x5400 0x5700`).
* Две `error`-находки `rdb_lint` унаследованы с Stage 5 (раздел 11) — правка чужих объектов вне Stage 6 без причины запрещена правилом 6; устранены отдельной правкой после закрытия Stage 6.
