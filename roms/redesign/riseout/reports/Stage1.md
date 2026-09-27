# Stage 1. Механические факты (riseout.rom)

> Сгенерировано `report_gen.py` из JSON-результатов модулей `utils/analyze/`. Дата прогона: 2026-09-28.

## Goal

Зафиксировать все механические факты одного прогона utils/analyze: карту памяти и активность чтения/записи, посев RDB до fixpoint, экспорт в ASM и побайтовый round-trip.

## ROM

| ключ | значение |
|---|---|
| `image` | org=0x0100, path=/home/alexey/Projects/vector-games/roms/, size=20480 |
| `origin` | 0x0100 |
| `rdb` | /home/alexey/Projects/vector-games/roms/redesign/riseout/src/riseout.rdb |
| `rom` | riseout.rom |
| `rom_size` | 20480 |

## Method

Один прогон run_pipeline.sh riseout (Stage 0, apply): probe/coverage/disassembly/memory_diff/io_signature — карта и активность; seed_rdb/rdb_lint — посев и целостность RDB; export_asm/toolchain_lint/symbolic_operand_lint/syntax_check/roundtrip_verify/measure_sizes — экспорт и сверка; abi_scan/strings_scan/table_shape/glyph_scan/vram_credits — кандидаты. Экспортная цепочка пересобрана после ручных правок RDB (Stage 2–6): run_pipeline.sh riseout --from export_asm. Многострочные комментарии RDB (34 объекта Stage 3) заменены однострочными: экспортёр вставлял переносы строк в layout.asm без экранирования, z80asm давал 34 × «error: invalid character», round-trip был blocked. После Stage 6 в rdb_lint осталось 2 blocking-находки, обе — наследие Stage 5: var_speed (0x7C88) имел size=8 и перекрывал var_bcd_display_ptr (0x7C8D), а алиас var_field_marker_count (0x7C6E) был записан текстом с пробелами и не проходил шаблон имён. Размер исправлен на доказанные 4 байта (индекс слота 0-базирован: LXI B,0000 / STA 7DBC @0x08EC; XRA A / STA 7C86 @0x2C25; MVI B,04 рисует ровно 4 варианта @0x2C3A), алиас нормализован в var_scroll_row_counter; errors=0.

Модули прогона:

* `abi_scan` — вердикт `функций: 32, кандидатов параметров: 97`, статус `CANDIDATE`, вызовов MCP: 9261
* `coverage` — вердикт `покрытие 44.64%, незанятых промежутков 34, без покрытия RDB 34`, статус `CANDIDATE`, вызовов MCP: 4
* `disassembly` — вердикт `анализ от 0x0100: 4663 инструкций, 802 references`, статус `OK`, вызовов MCP: 1
* `export_asm` — вердикт `экспортёр: rc=0, файлов 9, сборка: rc=0, 20480 байт`, статус `DERIVED`, вызовов MCP: 0
* `glyph_scan_0x0721` — вердикт `30 глиф(а) из 30, групп повторов 0, источник IMAGE`, статус `CANDIDATE`, вызовов MCP: 2
* `glyph_scan_0x3114` — вердикт `128 глиф(а) из 128, групп повторов 6, источник IMAGE`, статус `CANDIDATE`, вызовов MCP: 2
* `io_signature` — вердикт `аппаратных подписей: 23, поймано в трассе 8, пересечение с документацией 11`, статус `CANDIDATE`, вызовов MCP: 27
* `measure_sizes` — вердикт `367 расхождений(я) размера из 449 объектов`, статус `CANDIDATE`, вызовов MCP: 1
* `memory_diff` — вердикт `47 байт(а) RAM отличается от образа — 19 патч(а)`, статус `OK`, вызовов MCP: 6
* `pipeline` — вердикт `None`, статус `PARTIAL`, вызовов MCP: None
* `pipeline_state` — вердикт `None`, статус `finished`, вызовов MCP: None
* `probe` — вердикт `чистый старт: пауза на 0x2AAB через 10.0 с (вне функции)`, статус `OK`, вызовов MCP: 27
* `rdb_lint` — вердикт `1175 находок, 0 блокирующих`, статус `CANDIDATE`, вызовов MCP: 0
* `roundtrip_verify` — вердикт `byte-for-byte identical`, статус `OK`, вызовов MCP: 0
* `seed_rdb` — вердикт `применено: dry-run: functions 95, labels 265, links 58, существующих 0, итераций 2`, статус `PASS`, вызовов MCP: 1550
* `statistics` — вердикт `None`, статус `None`, вызовов MCP: None
* `strings_scan` — вердикт `строковых прогонов: 1576, из них уже строкой в RDB 0, строк в RDB без прогона 0`, статус `CANDIDATE`, вызовов MCP: 0
* `symbolic_operand_lint` — вердикт `408 находок, 0 блокирующих`, статус `CANDIDATE`, вызовов MCP: 0
* `syntax_check` — вердикт `clean: собралось без единой претензии`, статус `DERIVED`, вызовов MCP: 0
* `table_shape` — вердикт `разобрано диапазонов: 0, видов: нет`, статус `CANDIDATE`, вызовов MCP: 0
* `toolchain_lint` — вердикт `clean`, статус `CANDIDATE`, вызовов MCP: 0
* `vram_credits` — вердикт `no_data: ни один предсказанный адрес не лёг в VRAM`, статус `CANDIDATE`, вызовов MCP: 17

## Result summary

| ключ | значение |
|---|---|
| `by_code` | bad_name=360, missing_evidence=95, missing_properties=360, missing_size=360 |
| `by_severity` | error=0, info=0, warning=1175 |
| `findings` | 1175 |
| `labels` | labels=265, unknown_labels=, with_comment=0 |
| `objects` | 360 |
| `source_module` | rdb_lint |
| `unknown_bytes` | 0 |
| `unknowns` | 0 |
| `verdict` | 1175 находок, 0 блокирующих |

### Посев RDB (ТЗ §46)

| ключ | значение |
|---|---|
| `Aliases` | 0 |
| `Coverage %` | 44.64 |
| `Entry points` | 0x0100 |
| `Existing objects` | 0 |
| `Fixpoint` | True |
| `Functions` | 95 |
| `Iterations` | 2 |
| `Labels` | 265 |
| `Links` | 58 |
| `RDB conflicts` | 0 |
| `Status` | PASS |

_Числа посева детерминированы: это структурные кандидаты из `debug_analyze_code`/coverage, а не семантические факты (ТЗ §34)._

### Статистика прогона (ТЗ §30)

| ключ | значение |
|---|---|
| `mcp_calls_field_sum` | 10898 |
| `protocol_version` | 2025-03-26 |
| `retries` | 0 |
| `server` | v06c-mcp |
| `server_version` | 0.6.4 |
| `session` | shared (ТЗ §4) |
| `session_restarts` | 0 |
| `statistics_source` | .scratch/pipeline/riseout/statistics.json |
| `tools_exposed` | 73 |
| `total_mcp_bytes` | 2909 |
| `total_mcp_calls` | 9 |
| `total_mcp_ms` | 46.9 |
| `wall_ms` | 2888.1 |

Вызовы по инструментам:

* `debug_get_rdb_info` — 7 вызов(ов), 6.7 мс, 2450 байт
* `debug_get_state` — 1 вызов(ов), 0.6 мс, 331 байт
* `debug_load_rom` — 1 вызов(ов), 39.7 мс, 128 байт

Самые дорогие инструменты по времени:

* `debug_load_rom` — 39.7 мс всего, 39.7 мс максимум, 128 байт максимум на вызов
* `debug_get_rdb_info` — 6.7 мс всего, 2.3 мс максимум, 350 байт максимум на вызов
* `debug_get_state` — 0.6 мс всего, 0.6 мс максимум, 331 байт максимум на вызов

Кэш доказательств: hits=1, misses=0, stores=0, bypasses=0, hit_rate=100.0

Вызовы по модулям:

* `export_asm` — 0 вызов(ов), 0.0 мс, статус `DERIVED`
* `measure_sizes` — 1 вызов(ов), 0.6 мс, статус `CANDIDATE`
* `roundtrip_verify` — 0 вызов(ов), 0.0 мс, статус `OK`
* `symbolic_operand_lint` — 0 вызов(ов), 0.0 мс, статус `CANDIDATE`
* `syntax_check` — 0 вызов(ов), 0.0 мс, статус `DERIVED`
* `toolchain_lint` — 0 вызов(ов), 0.0 мс, статус `CANDIDATE`

### Ссылки на доказательства

* `export_asm` → `/home/alexey/Projects/vector-games/.scratch/export/pipeline` (out_dir)
* `measure_sizes` → `/home/alexey/Projects/vector-games/roms/redesign/riseout/src/riseout.rdb` (rdb)
* `pipeline` → `/home/alexey/Projects/vector-games/roms/redesign/riseout/src/riseout.rdb` (rdb)
* `rdb_lint` → `/home/alexey/Projects/vector-games/roms/redesign/riseout/src/riseout.rdb` (rdb)
* `roundtrip_verify` → `/home/alexey/Projects/vector-games/.scratch/export/pipeline` (out_dir)
* `roundtrip_verify` → `/home/alexey/Projects/vector-games/roms/redesign/riseout/src/riseout.rdb` (rdb)
* `symbolic_operand_lint` → `/home/alexey/Projects/vector-games/.scratch/export/pipeline` (out_dir)
* `symbolic_operand_lint` → `/home/alexey/Projects/vector-games/roms/redesign/riseout/src/riseout.rdb` (rdb)
* `syntax_check` → `/home/alexey/Projects/vector-games/.scratch/export/pipeline` (out_dir)
* `toolchain_lint` → `/home/alexey/Projects/vector-games/.scratch/export/pipeline` (out_dir)

## Findings

### `measure_sizes` (367: size-unknown×361, object-nested×6)

* **info** `size-unknown` `func_boot_init` — размера в RDB нет; линейная разборка от 0x0100 даёт 23 байт(а) до 0x0116
* **info** `size-unknown` `lbl_0117` — размера в RDB нет; линейная разборка от 0x0117 даёт 10 байт(а) до 0x0120
* **info** `size-unknown` `func_ret_stub_a` — размера в RDB нет; линейная разборка от 0x0121 даёт 3 байт(а) до 0x0123
* **info** `size-unknown` `func_put_char_glyph` — размера в RDB нет; линейная разборка от 0x0124 даёт 18 байт(а) до 0x0135
* **info** `size-unknown` `lbl_0136` — размера в RDB нет; линейная разборка от 0x0136 даёт 12 байт(а) до 0x0141
* **info** `size-unknown` `func_fill_char_glyph` — размера в RDB нет; линейная разборка от 0x0142 даёт 19 байт(а) до 0x0154
* **info** `size-unknown` `lbl_0155` — размера в RDB нет; линейная разборка от 0x0155 даёт 19 байт(а) до 0x0167
* **info** `size-unknown` `lbl_0168` — размера в RDB нет; линейная разборка от 0x0168 даёт 20 байт(а) до 0x017B
* **info** `size-unknown` `func_copy_text_block` — размера в RDB нет; линейная разборка от 0x017C даёт 2 байт(а) до 0x017D
* **info** `size-unknown` `lbl_017e` — размера в RDB нет; линейная разборка от 0x017E даёт 18 байт(а) до 0x018F
* **info** `size-unknown` `lbl_0190` — размера в RDB нет; линейная разборка от 0x0190 даёт 20 байт(а) до 0x01A3
* **info** `size-unknown` `func_ret_stub_b` — размера в RDB нет; линейная разборка от 0x01A4 даёт 1 байт(а) до 0x01A4
* **info** `size-unknown` `func_ret_stub_c` — размера в RDB нет; линейная разборка от 0x01A5 даёт 1 байт(а) до 0x01A5
* **info** `size-unknown` `func_ret_stub_d` — размера в RDB нет; линейная разборка от 0x01A6 даёт 2 байт(а) до 0x01A7
* **info** `size-unknown` `func_key_strobe_state` — размера в RDB нет; линейная разборка от 0x01A8 даёт 6 байт(а) до 0x01AD
* **info** `size-unknown` `lbl_01ae` — размера в RDB нет; линейная разборка от 0x01AE даёт 12 байт(а) до 0x01B9
* **info** `size-unknown` `lbl_01ba` — размера в RDB нет; линейная разборка от 0x01BA даёт 2 байт(а) до 0x01BB
* **info** `size-unknown` `func_key_code_decode` — размера в RDB нет; линейная разборка от 0x01BC даёт 6 байт(а) до 0x01C1
* **info** `size-unknown` `lbl_01c2` — размера в RDB нет; линейная разборка от 0x01C2 даёт 35 байт(а) до 0x01E4
* **info** `size-unknown` `func_ret_stub_e` — размера в RDB нет; линейная разборка от 0x01E5 даёт 1 байт(а) до 0x01E5
* _… ещё 347 в исходном JSON_

### `rdb_lint` (1175: missing_size×360, bad_name×360, missing_properties×360, missing_evidence×95)

* **warn** `missing_size` `func_0100` — size=0 — длина области неизвестна (v06c-asm-export не сможет выделить байты без размера)
* **warn** `missing_size` `lbl_0117` — size=0 — длина области неизвестна (v06c-asm-export не сможет выделить байты без размера)
* **warn** `missing_size` `func_0121` — size=0 — длина области неизвестна (v06c-asm-export не сможет выделить байты без размера)
* **warn** `missing_size` `func_0124` — size=0 — длина области неизвестна (v06c-asm-export не сможет выделить байты без размера)
* **warn** `missing_size` `lbl_0136` — size=0 — длина области неизвестна (v06c-asm-export не сможет выделить байты без размера)
* **warn** `missing_size` `func_0142` — size=0 — длина области неизвестна (v06c-asm-export не сможет выделить байты без размера)
* **warn** `missing_size` `lbl_0155` — size=0 — длина области неизвестна (v06c-asm-export не сможет выделить байты без размера)
* **warn** `missing_size` `lbl_0168` — size=0 — длина области неизвестна (v06c-asm-export не сможет выделить байты без размера)
* **warn** `missing_size` `func_017c` — size=0 — длина области неизвестна (v06c-asm-export не сможет выделить байты без размера)
* **warn** `missing_size` `lbl_017e` — size=0 — длина области неизвестна (v06c-asm-export не сможет выделить байты без размера)
* **warn** `missing_size` `lbl_0190` — size=0 — длина области неизвестна (v06c-asm-export не сможет выделить байты без размера)
* **warn** `missing_size` `func_01a4` — size=0 — длина области неизвестна (v06c-asm-export не сможет выделить байты без размера)
* **warn** `missing_size` `func_01a5` — size=0 — длина области неизвестна (v06c-asm-export не сможет выделить байты без размера)
* **warn** `missing_size` `func_01a6` — size=0 — длина области неизвестна (v06c-asm-export не сможет выделить байты без размера)
* **warn** `missing_size` `func_01a8` — size=0 — длина области неизвестна (v06c-asm-export не сможет выделить байты без размера)
* **warn** `missing_size` `lbl_01ae` — size=0 — длина области неизвестна (v06c-asm-export не сможет выделить байты без размера)
* **warn** `missing_size` `lbl_01ba` — size=0 — длина области неизвестна (v06c-asm-export не сможет выделить байты без размера)
* **warn** `missing_size` `func_01bc` — size=0 — длина области неизвестна (v06c-asm-export не сможет выделить байты без размера)
* **warn** `missing_size` `lbl_01c2` — size=0 — длина области неизвестна (v06c-asm-export не сможет выделить байты без размера)
* **warn** `missing_size` `func_01e5` — size=0 — длина области неизвестна (v06c-asm-export не сможет выделить байты без размера)
* _… ещё 1155 в исходном JSON_

### `symbolic_operand_lint` (408: orphan_label×361, should_be_symbolic×47)

* **warn** `orphan_label` layout.asm:297 — метка func_add_a_to_hl есть в ASM, но нет в RDB
* **warn** `orphan_label` layout.asm:2884 — метка func_add_score_display есть в ASM, но нет в RDB
* **warn** `orphan_label` layout.asm:4972 — метка func_attract_draw_row есть в ASM, но нет в RDB
* **warn** `orphan_label` layout.asm:5660 — метка func_attract_draw_title есть в ASM, но нет в RDB
* **warn** `orphan_label` layout.asm:4948 — метка func_attract_draw_window есть в ASM, но нет в RDB
* **warn** `orphan_label` layout.asm:4942 — метка func_attract_frame_step есть в ASM, но нет в RDB
* **warn** `orphan_label` layout.asm:5616 — метка func_attract_init_scene есть в ASM, но нет в RDB
* **warn** `orphan_label` layout.asm:5118 — метка func_attract_input_update есть в ASM, но нет в RDB
* **warn** `orphan_label` layout.asm:5593 — метка func_attract_key_code_scan есть в ASM, но нет в RDB
* **warn** `orphan_label` layout.asm:5561 — метка func_attract_key_row_scan есть в ASM, но нет в RDB
* **warn** `orphan_label` layout.asm:5241 — метка func_attract_load_overlay есть в ASM, но нет в RDB
* **warn** `orphan_label` layout.asm:4817 — метка func_attract_mode_loop есть в ASM, но нет в RDB
* **warn** `orphan_label` layout.asm:4901 — метка func_attract_overlay_driver есть в ASM, но нет в RDB
* **warn** `orphan_label` layout.asm:5544 — метка func_attract_plane_shift есть в ASM, но нет в RDB
* **warn** `orphan_label` layout.asm:5161 — метка func_attract_plot_bits есть в ASM, но нет в RDB
* **warn** `orphan_label` layout.asm:5510 — метка func_attract_timer_read есть в ASM, но нет в RDB
* **warn** `orphan_label` layout.asm:5494 — метка func_attract_timer_tick есть в ASM, но нет в RDB
* **warn** `orphan_label` layout.asm:2941 — метка func_blank_digit_cell есть в ASM, но нет в RDB
* **warn** `orphan_label` layout.asm:5944 — метка func_blink_overlay_pulse есть в ASM, но нет в RDB
* **warn** `orphan_label` layout.asm:5964 — метка func_blink_step_delay есть в ASM, но нет в RDB
* _… ещё 388 в исходном JSON_

### `toolchain_lint` (11: long-defb-use-incbin×11)

* **warn** `long-defb-use-incbin` layout.asm:208 — дамп из 327 байт начиная со строки 208: побайтовую точность надёжнее держать в INCBIN
* **warn** `long-defb-use-incbin` layout.asm:769 — дамп из 180 байт начиная со строки 769: побайтовую точность надёжнее держать в INCBIN
* **warn** `long-defb-use-incbin` layout.asm:807 — дамп из 254 байт начиная со строки 807: побайтовую точность надёжнее держать в INCBIN
* **warn** `long-defb-use-incbin` layout.asm:2256 — дамп из 96 байт начиная со строки 2256: побайтовую точность надёжнее держать в INCBIN
* **warn** `long-defb-use-incbin` layout.asm:4015 — дамп из 173 байт начиная со строки 4015: побайтовую точность надёжнее держать в INCBIN
* **warn** `long-defb-use-incbin` layout.asm:4040 — дамп из 80 байт начиная со строки 4040: побайтовую точность надёжнее держать в INCBIN
* **warn** `long-defb-use-incbin` layout.asm:5229 — дамп из 73 байт начиная со строки 5229: побайтовую точность надёжнее держать в INCBIN
* **warn** `long-defb-use-incbin` layout.asm:6351 — дамп из 248 байт начиная со строки 6351: побайтовую точность надёжнее держать в INCBIN
* **warn** `long-defb-use-incbin` layout.asm:6385 — дамп из 1024 байт начиная со строки 6385: побайтовую точность надёжнее держать в INCBIN
* **warn** `long-defb-use-incbin` layout.asm:6516 — дамп из 128 байт начиная со строки 6516: побайтовую точность надёжнее держать в INCBIN
* **warn** `long-defb-use-incbin` layout.asm:6535 — дамп из 7020 байт начиная со строки 6535: побайтовую точность надёжнее держать в INCBIN


## Verified Facts

* `disassembly` — анализ от 0x0100: 4663 инструкций, 802 references (`OK`)
* `memory_diff` — 47 байт(а) RAM отличается от образа — 19 патч(а) (`OK`)
* `probe` — чистый старт: пауза на 0x2AAB через 10.0 с (вне функции) (`OK`)
* `roundtrip_verify` — byte-for-byte identical (`OK`)
* `seed_rdb` — применено: dry-run: functions 95, labels 265, links 58, существующих 0, итераций 2 (`PASS`)

_Фактом результат считается только потому, что модуль выдал статус OK/FACT: совпадение байтов, совпадение предсказания с реальностью, нулевая разница. Сюда не попадают CANDIDATE (ТЗ §34)._

## Inferences

* `abi_scan` — функций: 32, кандидатов параметров: 97 (статус модуля: CANDIDATE)
* `abi_scan` аргумент ? у func_0100 (0x0100) — memory_argument: static: SHLD 0x033B (write); static: STA 0x071E (write) (уверенность: medium)
* `abi_scan` аргумент ? у func_0124 (0x0124) — memory_argument: static: STA 0x082A (write) (уверенность: medium)
* `abi_scan` аргумент ? у func_0142 (0x0142) — memory_argument: static: STA 0x082A (write) (уверенность: medium)
* `abi_scan` аргумент ? у func_0206 (0x0206) — memory_argument: static: STA 0x25E7 (write); static: STA 0x03C7 (write) (уверенность: medium)
* `abi_scan` аргумент ? у func_0551 (0x0551) — memory_argument: static: LDA 0x081C (read) (уверенность: medium)
* `abi_scan` аргумент ? у func_121f (0x121F) — memory_argument: static: STA 0x7C01 (write) (уверенность: medium)
* `abi_scan` аргумент A у func_12e0 (0x12E0) — input: static: A читается до любой записи (PUSH PSW @0x12E0); dynamic: константа во всех 3 срабатываниях (уверенность: medium)
* `abi_scan` аргумент ? у func_1751 (0x1751) — memory_argument: static: LHLD 0x7C04 (read); static: SHLD 0x7C04 (write) (уверенность: medium)
* `coverage` — покрытие 44.64%, незанятых промежутков 34, без покрытия RDB 34 (статус модуля: CANDIDATE)
* `export_asm` — экспортёр: rc=0, файлов 9, сборка: rc=0, 20480 байт (статус модуля: DERIVED)
* `glyph_scan_0x0721` — 30 глиф(а) из 30, групп повторов 0, источник IMAGE (статус модуля: CANDIDATE)
* `glyph_scan_0x3114` — 128 глиф(а) из 128, групп повторов 6, источник IMAGE (статус модуля: CANDIDATE)
* `io_signature` — аппаратных подписей: 23, поймано в трассе 8, пересечение с документацией 11 (статус модуля: CANDIDATE)
* `io_signature` var_port_01 — out, в трассе: да, участков кода: 1, роль по документации: КР580ВВ55 #1 порт C (магн/СС/УС/РУС) (уверенность: high)
* `io_signature` var_port_0c — out, в трассе: да, участков кода: 0, роль по документации: палитра (уверенность: medium)
* `io_signature` var_port_02 — rw, в трассе: да, участков кода: 0, роль по документации: КР580ВВ55 #1 порт B (бордюр, 512px, клавиатура) (уверенность: medium)
* `io_signature` var_port_00 — out, в трассе: да, участков кода: 0, роль по документации: КР580ВВ55 #1 управляющее слово (уверенность: medium)
* `io_signature` var_port_03 — out, в трассе: да, участков кода: 0, роль по документации: КР580ВВ55 #1 порт A (верт. скролл, маска строк) (уверенность: medium)
* `io_signature` var_port_0b — out, в трассе: да, участков кода: 0, роль по документации: КР580ВИ53 счётчик канала 0 (уверенность: medium)
* `io_signature` var_port_08 — out, в трассе: да, участков кода: 0, роль по документации: КР580ВИ53 управляющее слово (уверенность: medium)
* `io_signature` var_port_0a — out, в трассе: да, участков кода: 0, роль по документации: КР580ВИ53 счётчик канала 1 (уверенность: medium)
* `measure_sizes` — 367 расхождений(я) размера из 449 объектов (статус модуля: CANDIDATE)
* `pipeline` — вердикта нет (статус модуля: PARTIAL)
* `rdb_lint` — 1175 находок, 0 блокирующих (статус модуля: CANDIDATE)
* `strings_scan` — строковых прогонов: 1576, из них уже строкой в RDB 0, строк в RDB без прогона 0 (статус модуля: CANDIDATE)
* `strings_scan` str_1f49 — ascii, 80 байт, с завершающим нулём: UNDRSNAKBIGIGRASLADR2TOWASCILOOPROOMAMID5TOW (уверенность: medium)
* `strings_scan` str_080a — koi8, 58 байт, с завершающим нулём: ф))И))фSTAXINX DAD LDAXDCX RST PSW POP PUSHN (уверенность: medium)
* `strings_scan` str_30ee — ascii, 36 байт, с завершающим нулём: A/?2@1>1@1>1@1>1@1>126:626:626@63646 (уверенность: medium)
* `strings_scan` str_24b0 — koi8, 30 байт, с завершающим нулём: |иSCORE:    00 MEN: 5 LEVEL: 1 (уверенность: medium)
* `strings_scan` str_2b9d — ascii, 23 байт, с завершающим нулём: HIT BUTTON OR SPACE KEY (уверенность: medium)
* `strings_scan` str_2cdd — ascii, 18 байт, с завершающим нулём: SELECT SPEED LEVEL (уверенность: medium)
* `strings_scan` str_2c8b — ascii, 17 байт, с завершающим нулём: HOW MANY PLAYERS? (уверенность: medium)
* `strings_scan` str_3148 — koi8, 16 байт, с завершающим нулём: юPпTЮlЛlЛoО`u'%% (уверенность: medium)
* `strings_scan` str_2bb7 — ascii, 15 байт, с завершающим нулём: UP TO 4 PLAYERS (уверенность: medium)
* `strings_scan` str_16e5 — ascii, 13 байт, с завершающим нулём: KEYWORD? (уверенность: medium)
* `symbolic_operand_lint` — 408 находок, 0 блокирующих (статус модуля: CANDIDATE)
* `syntax_check` — clean: собралось без единой претензии (статус модуля: DERIVED)
* `table_shape` — разобрано диапазонов: 0, видов: нет (статус модуля: CANDIDATE)
* `toolchain_lint` — clean (статус модуля: CANDIDATE)
_… ещё 1 в исходном JSON_

## Hypotheses

_пусто_

## Unknowns

* `measure_sizes` `size-unknown` ×361 — размера в RDB нет; линейная разборка от 0x0100 даёт 23 байт(а) до 0x0116
* `pipeline_state` `(без правила)` ×1 — 
* модуль `statistics` не вернул статус — его результат `None` никуда не отнесён, проверьте формат вывода модуля

## Limitations

* Python не декодирует 8080-коды и не строит CFG: всё это отдаёт отладчик (ТЗ §8, §34)
* Имена и семантика — кандидаты; окончательное значение назначает AI по доказательствам
* RUNTIME-наблюдения не подменяют Facts из ROM-образа (ТЗ §17)
* Модули, не вошедшие в прогон, в отчёте не участвуют

## Recommended Next Steps

* [info] `measure_sizes` `size-unknown` → тип=function, кандидат на заполнение size через debug_update_rdb_object
* [info] `measure_sizes` `size-unknown` → тип=label, кандидат на заполнение size через debug_update_rdb_object
* [info] `measure_sizes` `object-nested` → вложенность может быть намеренной (записи внутри таблицы) — проверьте тип родителя
* [info] `symbolic_operand_lint` `should_be_symbolic` → заменить на var_key_ring
* [info] `symbolic_operand_lint` `should_be_symbolic` → заменить на data_credits_logo_strip
* [info] `symbolic_operand_lint` `should_be_symbolic` → заменить на func_irq_vblank_dispatcher
* [info] `symbolic_operand_lint` `should_be_symbolic` → заменить на var_ramp_frames
* [info] `symbolic_operand_lint` `should_be_symbolic` → заменить на var_field_dirty_flag
* [info] `symbolic_operand_lint` `should_be_symbolic` → заменить на func_irq_scroll_deferred
* [info] `symbolic_operand_lint` `should_be_symbolic` → заменить на func_read_keyword_input
* [info] `symbolic_operand_lint` `should_be_symbolic` → заменить на data_msg_records
* [info] `symbolic_operand_lint` `should_be_symbolic` → заменить на data_level_keywords

_Порядок этих шагов выбирает человек: генератор только собирает подсказки модулей без дублей._
