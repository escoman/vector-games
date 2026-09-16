# Stage 2 — Исследование ROM и выгрузка функций (TESTAY.ROM)

ROM: `src/TESTAY.ROM` — 3712 байта (0xE80), чистый i8080, origin загрузки `0x0100`.
Приложение: плеер музыки на AY-3-8910, без графики (VRAM 0x8000–0xFFFF не трогается).
Все данные получены через MCP `vector-debugger` (`debug_analyze_code`,
`debug_disassemble_range`, `debug_read_memory_range`, `debug_get_io_trace`). RDB заполнялась
исключительно через MCP RDB API. Скриптов пост-обработки данных MCP не использовалось.

## Методика

1. Многоточечный `debug_analyze_code` (18 точек входа) → достижимый код, цели переходов.
2. Анализатор НЕ добирает цели Jcc и вычисляемых прыжков (PCHL), поэтому «разрывы» внутри
   известных функций сидированы явными объектами (например `func_053D_ei_ret` @0x053D,
   `func_cmd_retn_inx` @0x024B) и `debug_disassemble_range` подтверждал реальный код на этих
   адресах, а не данные.
3. Для каждого объекта — комментарий (рус.), для функций — `prototype` в properties,
   связи call-graph через `debug_add_rdb_link`.

## Итог покрытия (подтверждено export.json)

| Показатель | Значение |
|---|---|
| rom_bytes | 3712 |
| code_bytes | 1069 |
| data_bytes | 2643 |
| instruction_count | 615 |
| uncovered | [] (пусто) |
| complete | **true** |
| unresolved_references | **0** |
| objects / links | 51 / 40 |

code_bytes(1069) + data_bytes(2643) = 3712 → покрытие 100%.

## Карта функций (30)

| Адрес | Имя | Разм | Назначение |
|---|---|---|---|
| 0x0100 | func_rom_entry | 3 | Точка входа: `JMP func_init_song`; самомодиф. в `JMP func_main_loop` |
| 0x0105 | func_search_value | 6 | Линейный поиск по таблице (CMP M/RZ/DAD B), шаг BC |
| 0x010B | func_read_word_de | 5 | Чтение 16-бит слова [HL]→DE, HL+=2 (fallthrough в 0x0110) |
| 0x0110 | func_add_selfmod_base | 6 | HL += самоизм. база [0x0111]; DE=HL |
| 0x0116 | func_event_decode | 66 | Декод события паттерна (записи по 6, индекс A*3) |
| 0x0158 | func_pattern_fetch | 74 | Загрузка/переход паттерна, обновление указателей потока |
| 0x01A2 | func_thunk_decrypt_dispatch | 12 | Диспетчер дешифровки трюка (0x055F→0x056A) |
| 0x01AE | func_player_tick | 90 | Тик: делитель темпа + продвижение 3 каналов |
| 0x0208 | func_command_dispatch | 52 | Интерпретатор команд (CPI 60/70/80/81/82/8F) |
| 0x023C | func_cmd_handler_60 | 15 | Команды <0x60: запись значения в поток |
| 0x024B | func_cmd_retn_inx | 2 | `INX H; RET` (общий выход команды 0x81) |
| 0x024D | func_cmd_note_pitch | 30 | Нота 0x60–0x6F: поиск по pitch-таблице канала |
| 0x026B | func_cmd_rest | 16 | Пауза: [поток+7]=0xFF |
| 0x027B | func_cmd_zero | 4 | Команда 0x82 → A=0 → note_lookup |
| 0x027F | func_cmd_sui70 | 2 | Команды 0x70–0x7F: SUI 0x70 |
| 0x0281 | func_note_lookup | 32 | Поиск ноты/длительности (шаг 0x21, база [0x0460]) |
| 0x02A1 | func_cmd_80 | 34 | Команды 0x80–0x8E: смена параметров канала |
| 0x02C3 | func_duration_decode | 64 | Декод длительности/удержания |
| 0x0303 | func_vol_store | 8 | Сохранение громкости ([0x0495]) |
| 0x030B | func_channel_gate | 47 | Проверка/установка гейта канала ([0x049C]) |
| 0x033A | func_channels_process | 206 | Обработка 3 каналов → аккумуляторы AY, хвост `JMP 0x0442` |
| 0x0408 | func_pitch_calc | 58 | Расчёт периода тона (master table 0x057A) |
| 0x0442 | func_ay_write_registers | 28 | Вывод в AY: OUT 0x15/0x14, регистры 0x0A..0x00 |
| 0x049D | func_main_loop | 50 | Главный цикл: tick + задержка + IN 0x01 |
| 0x04CF | func_init_song | 110 | Инициализация: разбор заголовка 0x0657, очистка 0x046F |
| 0x053D | func_053D_ei_ret | 2 | `EI; RET` (сидиран для покрытия) |
| 0x053F | func_store_de_to_bc | 10 | Сохранить DE в [BC], [BC+1] с сохранением регистров |
| 0x0549 | func_patch_entry_jump | 10 | Однократный патч: `SHLD 0101` → вход на 0x049D; PCHL |
| 0x055F | func_thunk_slot_addr | 11 | Адрес XOR-слота = 0x0700+2*lo(retaddr) |
| 0x056A | func_xor_decrypt_loop | 16 | XOR-расшифровка 12-байтного слота; RET→трюк |

## Call graph (связи RDB, 40)

```
func_rom_entry(0x0100) -> func_init_song(0x04CF)          ; начальный переход
func_rom_entry(0x0100) -> func_main_loop(0x049D)          ; после самомодификации
func_init_song(0x04CF)  -> func_read_word_de(0x010B), func_store_de_to_bc(0x053F),
                           func_add_selfmod_base(0x0110), func_search_value(0x0105),
                           func_patch_entry_jump(0x0549), data_song_header(0x0655)
func_patch_entry_jump   -> func_ay_write_registers(0x0442)
func_main_loop(0x049D)  -> func_player_tick(0x01AE)
func_player_tick(0x01AE)-> func_thunk_decrypt_dispatch(0x01A2), func_pattern_fetch(0x0158),
                           func_command_dispatch(0x0208), func_channels_process(0x033A)
func_thunk_decrypt_dispatch -> func_thunk_slot_addr(0x055F), func_xor_decrypt_loop(0x056A),
                               data_xor_key(0x0553)
func_pattern_fetch(0x0158)  -> func_search_value(0x0105), func_read_word_de(0x010B)
func_command_dispatch(0x0208)-> {0x023C,0x024D,0x027F,0x026B,0x024B,0x02A1,0x027B,0x0281},
                               func_search_value(0x0105)
func_cmd_note_pitch(0x024D) -> func_search_value(0x0105)
func_note_lookup(0x0281)    -> func_search_value(0x0105)
func_cmd_80(0x02A1)         -> func_search_value(0x0105)
func_channels_process(0x033A)-> func_duration_decode(0x02C3), func_event_decode(0x0116),
                               func_vol_store(0x0303), func_pitch_calc(0x0408),
                               func_channel_gate(0x030B), func_ay_write_registers(0x0442)
func_pitch_calc(0x0408)     -> music_pitch_table(0x057A)
func_thunk_slot_addr(0x055F)-> music_streams(0x0700)
func_xor_decrypt_loop(0x056A)-> music_streams(0x0700)
```

## Расположение данных

| Адрес | Дл. | Тип | Имя | Комментарий |
|---|---|---|---|---|
| 0x0103 | 2 | var | var_cur_stream_ptr | рабочий указатель потока (вписан в код, самомодиф.) |
| 0x045E/60/62 | 2×3 | var | var_pattern_base_A/B/C | базы паттернов каналов |
| 0x0464 | 2 | var | var_pitch_table_base | база pitch-таблицы |
| 0x0466/67/68 | 1×3 | var | var_tempo / _counter / var_song_length | темп, счётчик, длина |
| 0x0469/6B/6D | 2×3 | var | var_stream_ptr_A/B/C | текущие указатели потоков |
| 0x046F | 45 | data | data_channel_state | таблица состояния 3 каналов |
| 0x049C | 1 | var | var_ay_note_reg | рабочий регистр вывода AY |
| 0x0553 | 12 | data | data_xor_key | XOR-ключ `77 6C 67 D0 B6 6A 7F 7F 3F B3 38 9F` |
| 0x057A | 192 | table | music_pitch_table | 96 периодов тона 0x0EF8..0x000F |
| 0x063A | 27 | str | str_credit_contact | "(833)62-74-48 VICTOR SATURO" |
| 0x0655 | 7 | data | data_song_header | темп + 3 абсолютных указателя паттернов |
| 0x065C | 18 | str | str_credit_song | "SONG BY ST COMPILE" |
| 0x066E | 146 | data | data_song_params | таблицы параметров трека |
| 0x0700 | 2090 | data | music_streams | нотные потоки + XOR-трюки |
| 0x0F2A | 86 | data | data_padding_tail | хвостовое заполнение 0 |

## Ключевые механизмы (Fact, подтверждено)

- **Самомодификация входа.** `func_init_song` в конце вызывает `func_patch_entry_jump`
  (0x0549): `LXI H,049D / SHLD 0101 / PCHL` переписывает операнд входного `JMP` по адресу
  0x0101. После этого повторный вход в 0x0100 ведёт сразу в главный цикл 0x049D.
  (САМОМОДИФИКАЦИЯ по 0x0101, НЕ 0x04A2 — подтверждено снимками.)
- **XOR-трюки.** `func_thunk_slot_addr` вычисляет слот `0x0700+2*lo(адрес возврата)`,
  `func_xor_decrypt_loop` инволютивно XOR'ит 12 байт ключом 0x0553 и `RET` передаёт
  управление в расшифрованный трюк. Из-за инволютивности большие интервалы дают нулевую
  дельту памяти — вывод «нет изменений» по этому основанию ошибочен.
- **Вывод в AY.** `func_ay_write_registers` обходит регистры 0x0A→0x00: `OUT 0x15` (№)
  + `OUT 0x14` (значение). Подтверждено I/O-трассой.

## Артефакты

- RDB: `src/TESTAY.rdb` — 51 объект, 40 связей, `dirty=false`, `exists_on_disk=true`
  (проверено `debug_get_rdb_info`).
- Экспорт ASM: `v06c-asm-export --rom src/TESTAY.ROM --rdb src/TESTAY.rdb --output asm`
  → `asm/main.asm`, `asm/layout.asm`, `asm/code/code.asm`, `asm/data/data.asm`,
  `asm/export.json`. Покрытие complete=true, неразрешённых ссылок 0, конфликтов 0.

