# Stage 1. Механические факты (cyberno.rom)

> Сгенерировано `report_gen.py` из JSON-результатов модулей `utils/analyze/`. Дата прогона: 2026-10-27.

## Goal

_цель анализа назначает человек или AI; здесь её нет — передайте `--goal`._

## ROM

| ключ | значение |
|---|---|
| `image` | org=0x0100, path=/home/alexey/Projects/vector-games/roms/, size=27392 |
| `origin` | 0x0100 |
| `rdb` | /home/alexey/Projects/vector-games/roms/redesign/cybernoid/src/cyberno.rdb |
| `rom` | cyberno.rom |
| `rom_size` | 27392 |

## Method

Один долгий MCP-сеанс, кэш доказательств, пакетные инструменты отладчика; Python читает и сравнивает байты и не декодирует коды (ТЗ §8, §33).

Модули прогона:

* `abi_scan` — вердикт `функций: 32, кандидатов параметров: 106`, статус `CANDIDATE`, вызовов MCP: 9145
* `coverage` — вердикт `покрытие 23.99%, незанятых промежутков 61, без покрытия RDB 61`, статус `CANDIDATE`, вызовов MCP: 3
* `disassembly` — вердикт `анализ от 0x0100: 4156 инструкций, 720 references`, статус `OK`, вызовов MCP: 0
* `export_asm` — вердикт `экспортёр: rc=0, файлов 9, сборка: rc=1, 17152 байт`, статус `DERIVED`, вызовов MCP: 0
* `io_signature` — вердикт `аппаратных подписей: 77, поймано в трассе 4, пересечение с документацией 8`, статус `CANDIDATE`, вызовов MCP: 22
* `measure_sizes` — вердикт `285 расхождений(я) размера из 314 объектов`, статус `CANDIDATE`, вызовов MCP: 1
* `memory_diff` — вердикт `25728 байт(а) RAM отличается от образа — 1247 патч(а)`, статус `OK`, вызовов MCP: 7
* `pipeline` — вердикт `None`, статус `PARTIAL`, вызовов MCP: None
* `pipeline_state` — вердикт `None`, статус `finished`, вызовов MCP: None
* `probe` — вердикт `чистый старт: пауза на 0x0F15 через 20.0 с (вне функции)`, статус `OK`, вызовов MCP: 19
* `rdb_lint` — вердикт `1093 находок, 0 блокирующих`, статус `CANDIDATE`, вызовов MCP: 0
* `roundtrip_verify` — вердикт `blocked: сборка не прошла, см. syntax_check по каталогу /home/alexey/Projects/vector-games/.scratch/export/pipeline`, статус `IMAGE`, вызовов MCP: 0
* `seed_rdb` — вердикт `применено: dry-run: functions 122, labels 192, links 62, существующих 0, итераций 2`, статус `PASS`, вызовов MCP: 1361
* `statistics` — вердикт `None`, статус `None`, вызовов MCP: None
* `strings_scan` — вердикт `строковых прогонов: 748, из них уже строкой в RDB 0, строк в RDB без прогона 0`, статус `CANDIDATE`, вызовов MCP: 0
* `symbolic_operand_lint` — вердикт `4 находок, 0 блокирующих`, статус `CANDIDATE`, вызовов MCP: 0
* `syntax_check` — вердикт `blocked: 136 ошибка(ов) сборки`, статус `DERIVED`, вызовов MCP: 0
* `table_shape` — вердикт `разобрано диапазонов: 0, видов: нет`, статус `CANDIDATE`, вызовов MCP: 0
* `toolchain_lint` — вердикт `clean`, статус `CANDIDATE`, вызовов MCP: 0
* `vram_credits` — вердикт `в RDB нет объекта с именем str_credits_koi8, а адрес из строки не читается`, статус `SKIPPED`, вызовов MCP: 8

## Result summary

| ключ | значение |
|---|---|
| `by_code` | bad_name=314, missing_evidence=122, missing_properties=314, missing_size=314, past_image=29 |
| `by_severity` | error=0, info=0, warning=1093 |
| `findings` | 1093 |
| `labels` | labels=192, unknown_labels=, with_comment=0 |
| `objects` | 314 |
| `source_module` | rdb_lint |
| `unknown_bytes` | 0 |
| `unknowns` | 0 |
| `verdict` | 1093 находок, 0 блокирующих |

### Посев RDB (ТЗ §46)

| ключ | значение |
|---|---|
| `Aliases` | 0 |
| `Coverage %` | 23.99 |
| `Entry points` | 0x0100 |
| `Existing objects` | 0 |
| `Fixpoint` | True |
| `Functions` | 122 |
| `Iterations` | 2 |
| `Labels` | 192 |
| `Links` | 62 |
| `RDB conflicts` | 0 |
| `Status` | PASS |

_Числа посева детерминированы: это структурные кандидаты из `debug_analyze_code`/coverage, а не семантические факты (ТЗ §34)._

### Статистика прогона (ТЗ §30)

| ключ | значение |
|---|---|
| `mcp_calls_field_sum` | 10566 |
| `protocol_version` | 2025-03-26 |
| `retries` | 0 |
| `server` | v06c-mcp |
| `server_version` | 0.6.7 |
| `session` | shared (ТЗ §4) |
| `session_restarts` | 0 |
| `statistics_source` | .scratch/pipeline/cybernoid/statistics.json |
| `tools_exposed` | 86 |
| `total_mcp_bytes` | 8839082 |
| `total_mcp_calls` | 10586 |
| `total_mcp_ms` | 195191.4 |
| `wall_ms` | 739690.3 |

Вызовы по инструментам:

* `debug_get_state` — 8568 вызов(ов), 9037.4 мс, 3416577 байт
* `debug_set_rdb_property` — 942 вызов(ов), 263.9 мс, 19782 байт
* `debug_add_rdb_object` — 314 вызов(ов), 91.2 мс, 6594 байт
* `debug_run` — 133 вызов(ов), 695.8 мс, 2793 байт
* `debug_pause` — 101 вызов(ов), 1010.7 мс, 2121 байт
* `debug_remove_breakpoint` — 96 вызов(ов), 79.3 мс, 2016 байт
* `debug_set_breakpoint` — 96 вызов(ов), 738.4 мс, 2688 байт
* `debug_add_rdb_link` — 62 вызов(ов), 19.1 мс, 1302 байт
* `debug_get_rdb_info` — 56 вызов(ов), 32.3 мс, 23177 байт
* `debug_type_key` — 41 вызов(ов), 4984.8 мс, 861 байт
* `debug_save_rdb` — 40 вызов(ов), 175.1 мс, 840 байт
* `debug_create_memory_snapshot` — 37 вызов(ов), 33.8 мс, 2322 байт
* `debug_load_rom` — 37 вызов(ов), 480.0 мс, 4810 байт
* `debug_get_function_context` — 32 вызов(ов), 176627.0 мс, 61767 байт
* `debug_read_memory_range` — 12 вызов(ов), 30.9 мс, 222639 байт
* `debug_find_immediate_in_range` — 4 вызов(ов), 127.8 мс, 41977 байт
* `debug_find_bytecode_sequence` — 2 вызов(ов), 4.9 мс, 2022 байт
* `debug_list_keys` — 2 вызов(ов), 3.2 мс, 15370 байт
* `debug_list_rdb_objects` — 2 вызов(ов), 1.0 мс, 66 байт
* `debug_coverage_report` — 1 вызов(ов), 150.6 мс, 67696 байт
* `debug_disassemble_image` — 1 вызов(ов), 520.0 мс, 4376074 байт
* `debug_get_cpu_state` — 1 вызов(ов), 0.5 мс, 193 байт
* `debug_get_io_trace` — 1 вызов(ов), 29.2 мс, 209909 байт
* `debug_get_memory_access_log` — 1 вызов(ов), 40.1 мс, 269786 байт
* `debug_get_memory_access_map` — 1 вызов(ов), 6.8 мс, 50377 байт
* `debug_get_screen_info` — 1 вызов(ов), 0.5 мс, 176 байт
* `debug_get_symbols` — 1 вызов(ов), 6.4 мс, 34751 байт
* `debug_get_vram_info` — 1 вызов(ов), 0.9 мс, 396 байт

Самые дорогие инструменты по времени:

* `debug_get_function_context` — 176627.0 мс всего, 5812.1 мс максимум, 7237 байт максимум на вызов
* `debug_get_state` — 9037.4 мс всего, 32.1 мс максимум, 413 байт максимум на вызов
* `debug_type_key` — 4984.8 мс всего, 130.0 мс максимум, 21 байт максимум на вызов
* `debug_pause` — 1010.7 мс всего, 23.5 мс максимум, 21 байт максимум на вызов
* `debug_set_breakpoint` — 738.4 мс всего, 24.2 мс максимум, 28 байт максимум на вызов

Кэш доказательств: hits=54, misses=28, stores=28, bypasses=0, hit_rate=65.9

Вызовы по модулям:

* `abi_scan` — 9145 вызов(ов), 192538.0 мс, статус `CANDIDATE`
* `coverage` — 3 вызов(ов), 1.3 мс, статус `CANDIDATE`
* `disassembly` — 0 вызов(ов), 0.0 мс, статус `OK`
* `export_asm` — 0 вызов(ов), 0.0 мс, статус `DERIVED`
* `io_signature` — 22 вызов(ов), 389.9 мс, статус `CANDIDATE`
* `measure_sizes` — 1 вызов(ов), 520.0 мс, статус `CANDIDATE`
* `memory_diff` — 7 вызов(ов), 33.7 мс, статус `OK`
* `probe` — 19 вызов(ов), 1122.7 мс, статус `OK`
* `rdb_lint` — 0 вызов(ов), 0.0 мс, статус `CANDIDATE`
* `roundtrip_verify` — 0 вызов(ов), 0.0 мс, статус `IMAGE`
* `seed_rdb` — 1361 вызов(ов), 550.8 мс, статус `PASS`
* `strings_scan` — 0 вызов(ов), 0.0 мс, статус `CANDIDATE`
* `symbolic_operand_lint` — 0 вызов(ов), 0.0 мс, статус `CANDIDATE`
* `syntax_check` — 0 вызов(ов), 0.0 мс, статус `DERIVED`
* `table_shape` — 0 вызов(ов), 0.0 мс, статус `CANDIDATE`
* `toolchain_lint` — 0 вызов(ов), 0.0 мс, статус `CANDIDATE`
* `vram_credits` — 8 вызов(ов), 21.6 мс, статус `SKIPPED`

### Ссылки на доказательства

* `export_asm` → `/home/alexey/Projects/vector-games/.scratch/export/pipeline` (out_dir)
* `measure_sizes` → `/home/alexey/Projects/vector-games/roms/redesign/cybernoid/src/cyberno.rdb` (rdb)
* `pipeline` → `/home/alexey/Projects/vector-games/roms/redesign/cybernoid/src/cyberno.rdb` (rdb)
* `rdb_lint` → `/home/alexey/Projects/vector-games/roms/redesign/cybernoid/src/cyberno.rdb` (rdb)
* `roundtrip_verify` → `/home/alexey/Projects/vector-games/.scratch/export/pipeline` (out_dir)
* `roundtrip_verify` → `/home/alexey/Projects/vector-games/roms/redesign/cybernoid/src/cyberno.rdb` (rdb)
* `symbolic_operand_lint` → `/home/alexey/Projects/vector-games/.scratch/export/pipeline` (out_dir)
* `symbolic_operand_lint` → `/home/alexey/Projects/vector-games/roms/redesign/cybernoid/src/cyberno.rdb` (rdb)
* `syntax_check` → `/home/alexey/Projects/vector-games/.scratch/export/pipeline` (out_dir)
* `toolchain_lint` → `/home/alexey/Projects/vector-games/.scratch/export/pipeline` (out_dir)

## Findings

### `measure_sizes` (285: size-unknown×285)

* **info** `size-unknown` `func_0100` — размера в RDB нет; линейная разборка от 0x0100 даёт 122 байт(а) до 0x0179
* **info** `size-unknown` `lbl_017a` — размера в RDB нет; линейная разборка от 0x017A даёт 17 байт(а) до 0x018A
* **info** `size-unknown` `lbl_018b` — размера в RDB нет; линейная разборка от 0x018B даёт 25 байт(а) до 0x01A3
* **info** `size-unknown` `lbl_01a4` — размера в RDB нет; линейная разборка от 0x01A4 даёт 26 байт(а) до 0x01BD
* **info** `size-unknown` `func_01be` — размера в RDB нет; линейная разборка от 0x01BE даёт 6 байт(а) до 0x01C3
* **info** `size-unknown` `func_01c4` — размера в RDB нет; линейная разборка от 0x01C4 даёт 70 байт(а) до 0x0209
* **info** `size-unknown` `lbl_020a` — размера в RDB нет; линейная разборка от 0x020A даёт 12 байт(а) до 0x0215
* **info** `size-unknown` `lbl_0216` — размера в RDB нет; линейная разборка от 0x0216 даёт 15 байт(а) до 0x0224
* **info** `size-unknown` `lbl_0225` — размера в RDB нет; линейная разборка от 0x0225 даёт 13 байт(а) до 0x0231
* **info** `size-unknown` `lbl_0232` — размера в RDB нет; линейная разборка от 0x0232 даёт 6 байт(а) до 0x0237
* **info** `size-unknown` `lbl_0238` — размера в RDB нет; линейная разборка от 0x0238 даёт 1 байт(а) до 0x0238
* **info** `size-unknown` `lbl_0239` — размера в RDB нет; линейная разборка от 0x0239 даёт 28 байт(а) до 0x0254
* **info** `size-unknown` `func_0255` — размера в RDB нет; линейная разборка от 0x0255 даёт 9 байт(а) до 0x025D
* **info** `size-unknown` `lbl_025e` — размера в RDB нет; линейная разборка от 0x025E даёт 152 байт(а) до 0x02F5
* **info** `size-unknown` `lbl_02f6` — размера в RDB нет; линейная разборка от 0x02F6 даёт 42 байт(а) до 0x031F
* **info** `size-unknown` `func_0320` — размера в RDB нет; линейная разборка от 0x0320 даёт 34 байт(а) до 0x0341
* **info** `size-unknown` `func_0342` — размера в RDB нет; линейная разборка от 0x0342 даёт 22 байт(а) до 0x0357
* **info** `size-unknown` `lbl_0358` — размера в RDB нет; линейная разборка от 0x0358 даёт 7 байт(а) до 0x035E
* **info** `size-unknown` `lbl_035f` — размера в RDB нет; линейная разборка от 0x035F даёт 13 байт(а) до 0x036B
* **info** `size-unknown` `func_036c` — размера в RDB нет; линейная разборка от 0x036C даёт 9 байт(а) до 0x0374
* _… ещё 265 в исходном JSON_

### `rdb_lint` (1093: missing_size×314, bad_name×314, missing_properties×314, missing_evidence×122, past_image×29)

* **warn** `missing_size` `func_0100` — size=0 — длина области неизвестна (v06c-asm-export не сможет выделить байты без размера)
* **warn** `missing_size` `lbl_017a` — size=0 — длина области неизвестна (v06c-asm-export не сможет выделить байты без размера)
* **warn** `missing_size` `lbl_018b` — size=0 — длина области неизвестна (v06c-asm-export не сможет выделить байты без размера)
* **warn** `missing_size` `lbl_01a4` — size=0 — длина области неизвестна (v06c-asm-export не сможет выделить байты без размера)
* **warn** `missing_size` `func_01be` — size=0 — длина области неизвестна (v06c-asm-export не сможет выделить байты без размера)
* **warn** `missing_size` `func_01c4` — size=0 — длина области неизвестна (v06c-asm-export не сможет выделить байты без размера)
* **warn** `missing_size` `lbl_020a` — size=0 — длина области неизвестна (v06c-asm-export не сможет выделить байты без размера)
* **warn** `missing_size` `lbl_0216` — size=0 — длина области неизвестна (v06c-asm-export не сможет выделить байты без размера)
* **warn** `missing_size` `lbl_0225` — size=0 — длина области неизвестна (v06c-asm-export не сможет выделить байты без размера)
* **warn** `missing_size` `lbl_0232` — size=0 — длина области неизвестна (v06c-asm-export не сможет выделить байты без размера)
* **warn** `missing_size` `lbl_0238` — size=0 — длина области неизвестна (v06c-asm-export не сможет выделить байты без размера)
* **warn** `missing_size` `lbl_0239` — size=0 — длина области неизвестна (v06c-asm-export не сможет выделить байты без размера)
* **warn** `missing_size` `func_0255` — size=0 — длина области неизвестна (v06c-asm-export не сможет выделить байты без размера)
* **warn** `missing_size` `lbl_025e` — size=0 — длина области неизвестна (v06c-asm-export не сможет выделить байты без размера)
* **warn** `missing_size` `lbl_02f6` — size=0 — длина области неизвестна (v06c-asm-export не сможет выделить байты без размера)
* **warn** `missing_size` `func_0320` — size=0 — длина области неизвестна (v06c-asm-export не сможет выделить байты без размера)
* **warn** `missing_size` `func_0342` — size=0 — длина области неизвестна (v06c-asm-export не сможет выделить байты без размера)
* **warn** `missing_size` `lbl_0358` — size=0 — длина области неизвестна (v06c-asm-export не сможет выделить байты без размера)
* **warn** `missing_size` `lbl_035f` — size=0 — длина области неизвестна (v06c-asm-export не сможет выделить байты без размера)
* **warn** `missing_size` `func_036c` — size=0 — длина области неизвестна (v06c-asm-export не сможет выделить байты без размера)
* _… ещё 1073 в исходном JSON_

### `symbolic_operand_lint` (4: should_be_symbolic×4)

* **info** `should_be_symbolic` layout.asm:197 — lxi 0100h: число 0x0100 = начало func_0100 (function)
* **info** `should_be_symbolic` layout.asm:4607 — lxi 0100h: число 0x0100 = начало func_0100 (function)
* **info** `should_be_symbolic` layout.asm:4619 — lxi 0100h: число 0x0100 = начало func_0100 (function)
* **info** `should_be_symbolic` layout.asm:7404 — lxi 100eh: число 0x100E = начало lbl_100e (label)

### `syntax_check` (136: assembler-error×136)

* **error** `assembler-error` layout.asm:1122 — undefined symbol: label_0038
* **error** `assembler-error` layout.asm:1122 — constant expression expected
* **error** `assembler-error` layout.asm:1125 — undefined symbol: label_0038
* **error** `assembler-error` layout.asm:1125 — constant expression expected
* **error** `assembler-error` layout.asm:1153 — undefined symbol: label_0038
* **error** `assembler-error` layout.asm:1153 — constant expression expected
* **error** `assembler-error` layout.asm:1166 — undefined symbol: label_0038
* **error** `assembler-error` layout.asm:1166 — constant expression expected
* **error** `assembler-error` layout.asm:1186 — undefined symbol: label_0038
* **error** `assembler-error` layout.asm:1186 — constant expression expected
* **error** `assembler-error` layout.asm:1200 — undefined symbol: label_0038
* **error** `assembler-error` layout.asm:1200 — constant expression expected
* **error** `assembler-error` layout.asm:1202 — undefined symbol: label_0008
* **error** `assembler-error` layout.asm:1202 — constant expression expected
* **error** `assembler-error` layout.asm:1208 — undefined symbol: label_0038
* **error** `assembler-error` layout.asm:1208 — constant expression expected
* **error** `assembler-error` layout.asm:1226 — undefined symbol: label_0038
* **error** `assembler-error` layout.asm:1226 — constant expression expected
* **error** `assembler-error` layout.asm:1245 — undefined symbol: label_0038
* **error** `assembler-error` layout.asm:1245 — constant expression expected
* _… ещё 116 в исходном JSON_

### `toolchain_lint` (16: long-defb-use-incbin×16)

* **warn** `long-defb-use-incbin` layout.asm:431 — дамп из 137 байт начиная со строки 431: побайтовую точность надёжнее держать в INCBIN
* **warn** `long-defb-use-incbin` layout.asm:615 — дамп из 160 байт начиная со строки 615: побайтовую точность надёжнее держать в INCBIN
* **warn** `long-defb-use-incbin` layout.asm:826 — дамп из 836 байт начиная со строки 826: побайтовую точность надёжнее держать в INCBIN
* **warn** `long-defb-use-incbin` layout.asm:1098 — дамп из 172 байт начиная со строки 1098: побайтовую точность надёжнее держать в INCBIN
* **warn** `long-defb-use-incbin` layout.asm:1417 — дамп из 143 байт начиная со строки 1417: побайтовую точность надёжнее держать в INCBIN
* **warn** `long-defb-use-incbin` layout.asm:1442 — дамп из 73 байт начиная со строки 1442: побайтовую точность надёжнее держать в INCBIN
* **warn** `long-defb-use-incbin` layout.asm:1492 — дамп из 84 байт начиная со строки 1492: побайтовую точность надёжнее держать в INCBIN
* **warn** `long-defb-use-incbin` layout.asm:1521 — дамп из 168 байт начиная со строки 1521: побайтовую точность надёжнее держать в INCBIN
* **warn** `long-defb-use-incbin` layout.asm:1976 — дамп из 74 байт начиная со строки 1976: побайтовую точность надёжнее держать в INCBIN
* **warn** `long-defb-use-incbin` layout.asm:2327 — дамп из 90 байт начиная со строки 2327: побайтовую точность надёжнее держать в INCBIN
* **warn** `long-defb-use-incbin` layout.asm:4307 — дамп из 67 байт начиная со строки 4307: побайтовую точность надёжнее держать в INCBIN
* **warn** `long-defb-use-incbin` layout.asm:4553 — дамп из 67 байт начиная со строки 4553: побайтовую точность надёжнее держать в INCBIN
* **warn** `long-defb-use-incbin` layout.asm:5282 — дамп из 1648 байт начиная со строки 5282: побайтовую точность надёжнее держать в INCBIN
* **warn** `long-defb-use-incbin` layout.asm:5879 — дамп из 3656 байт начиная со строки 5879: побайтовую точность надёжнее держать в INCBIN
* **warn** `long-defb-use-incbin` layout.asm:6639 — дамп из 3723 байт начиная со строки 6639: побайтовую точность надёжнее держать в INCBIN
* **warn** `long-defb-use-incbin` layout.asm:7441 — дамп из 7318 байт начиная со строки 7441: побайтовую точность надёжнее держать в INCBIN


## Verified Facts

* `disassembly` — анализ от 0x0100: 4156 инструкций, 720 references (`OK`)
* `memory_diff` — 25728 байт(а) RAM отличается от образа — 1247 патч(а) (`OK`)
* `probe` — чистый старт: пауза на 0x0F15 через 20.0 с (вне функции) (`OK`)
* `seed_rdb` — применено: dry-run: functions 122, labels 192, links 62, существующих 0, итераций 2 (`PASS`)

_Фактом результат считается только потому, что модуль выдал статус OK/FACT: совпадение байтов, совпадение предсказания с реальностью, нулевая разница. Сюда не попадают CANDIDATE (ТЗ §34)._

## Inferences

* `abi_scan` — функций: 32, кандидатов параметров: 106 (статус модуля: CANDIDATE)
* `abi_scan` аргумент L у func_0100 (0x0100) — input: static: L читается до любой записи (SHLD 0001 @0x010F); dynamic: значение меняется между 2 срабатываниями (0x0044,0x0000) (уверенность: high)
* `abi_scan` аргумент ? у func_0320 (0x0320) — memory_argument: static: LHLD 0x033F (read); static: SHLD 0x033F (write) (уверенность: medium)
* `abi_scan` аргумент ? у func_036c (0x036C) — memory_argument: static: LDA 0x01B4 (read) (уверенность: medium)
* `abi_scan` аргумент ? у func_03f7 (0x03F7) — memory_argument: static: LDA 0x01B4 (read); static: STA 0x01B4 (write) (уверенность: medium)
* `abi_scan` аргумент ? у func_0530 (0x0530) — memory_argument: static: LHLD 0x020E (read); static: SHLD 0x020E (write) (уверенность: medium)
* `abi_scan` аргумент ? у func_0546 (0x0546) — memory_argument: static: LDA 0x01B4 (read) (уверенность: medium)
* `abi_scan` аргумент ? у func_0565 (0x0565) — memory_argument: static: STA 0x01B4 (write) (уверенность: medium)
* `abi_scan` аргумент ? у func_0b10 (0x0B10) — memory_argument: static: LHLD 0x0C7E (read); static: SHLD 0x0C7E (write) (уверенность: medium)
* `coverage` — покрытие 23.99%, незанятых промежутков 61, без покрытия RDB 61 (статус модуля: CANDIDATE)
* `export_asm` — экспортёр: rc=0, файлов 9, сборка: rc=1, 17152 байт (статус модуля: DERIVED)
* `io_signature` — аппаратных подписей: 77, поймано в трассе 4, пересечение с документацией 8 (статус модуля: CANDIDATE)
* `io_signature` var_port_00 — out, в трассе: да, участков кода: 1, роль по документации: КР580ВВ55 #1 управляющее слово (уверенность: high)
* `io_signature` var_port_0c — out, в трассе: да, участков кода: 0, роль по документации: палитра (уверенность: medium)
* `io_signature` var_port_02 — rw, в трассе: да, участков кода: 0, роль по документации: КР580ВВ55 #1 порт B (бордюр, 512px, клавиатура) (уверенность: medium)
* `io_signature` var_port_03 — out, в трассе: да, участков кода: 0, роль по документации: КР580ВВ55 #1 порт A (верт. скролл, маска строк) (уверенность: medium)
* `measure_sizes` — 285 расхождений(я) размера из 314 объектов (статус модуля: CANDIDATE)
* `pipeline` — вердикта нет (статус модуля: PARTIAL)
* `rdb_lint` — 1093 находок, 0 блокирующих (статус модуля: CANDIDATE)
* `strings_scan` — строковых прогонов: 748, из них уже строкой в RDB 0, строк в RDB без прогона 0 (статус модуля: CANDIDATE)
* `strings_scan` str_439c — koi8, 44 байт, с завершающим нулём: oтoЙoТoЙoТoЙoТoЙoТoЙoТoЙoТoЙoТoЙoТoЙoТoЙoТoЙ (уверенность: medium)
* `strings_scan` str_098d — koi8, 42 байт, с завершающим нулём: .Z^ЧJSEM HLAS VAS'EHO POC'I'TAC'E SPEKTRUM (уверенность: medium)
* `strings_scan` str_45cc — koi8, 30 байт, с завершающим нулём: ЪЪ?ЭoЖOТkжOТoЖOТoЖOТoЖOТoЖKтoЖ (уверенность: medium)
* `strings_scan` str_0b96 — koi8, 28 байт, с завершающим нулём: pЦTHE%FEDERATION%WILL%REWARD (уверенность: medium)
* `strings_scan` str_0bb5 — ascii, 26 байт, с завершающим нулём: ENTER%<FREEMAN>%IN%HISCORE (уверенность: medium)
* `strings_scan` str_4578 — koi8, 26 байт, с завершающим нулём: oЖKтoЖOТoЖOТoЖOТoЖOТkжOТoЖ (уверенность: medium)
* `strings_scan` str_0e1f — ascii, 25 байт, с завершающим нулём: �FREEMANE%ENTER%YOUR%NAM6 (уверенность: medium)
* `strings_scan` str_0bd7 — koi8, 23 байт, с завершающим нулём: ЕPLEASE%ENTER%YOUR%NAME (уверенность: medium)
* `strings_scan` str_2813 — ascii, 23 байт, с завершающим нулём: ?_ovz|pZ\Z\Z\Z\~@JTJTJT (уверенность: medium)
* `strings_scan` str_0c39 — koi8, 18 байт, с завершающим нулём: йCONGRATULATIONS%% (уверенность: medium)
* `symbolic_operand_lint` — 4 находок, 0 блокирующих (статус модуля: CANDIDATE)
* `table_shape` — разобрано диапазонов: 0, видов: нет (статус модуля: CANDIDATE)
* `toolchain_lint` — clean (статус модуля: CANDIDATE)

## Hypotheses

* `io_signature` var_port_01 — rw, в трассе: нет, участков кода: 0, роль по документации: КР580ВВ55 #1 порт C (магн/СС/УС/РУС) (уверенность: low)
* `io_signature` var_port_06 — in, в трассе: нет, участков кода: 0, роль по документации: КР580ВВ55 #2 порт B #2 (covox) (уверенность: low)
* `io_signature` var_port_07 — rw, в трассе: нет, участков кода: 0, роль по документации: КР580ВВ55 #2 порт A #2 (уверенность: low)
* `io_signature` var_port_09 — rw, в трассе: нет, участков кода: 0, роль по документации: КР580ВИ53 счётчик канала 2 (уверенность: low)

## Unknowns

* `measure_sizes` `size-unknown` ×285 — размера в RDB нет; линейная разборка от 0x0100 даёт 122 байт(а) до 0x0179
* `pipeline_state` `(без правила)` ×1 — 
* `vram_credits` `(без правила)` ×1 — 
* модуль `statistics` не вернул статус — его результат `None` никуда не отнесён, проверьте формат вывода модуля

## Limitations

* Python не декодирует 8080-коды и не строит CFG: всё это отдаёт отладчик (ТЗ §8, §34)
* Имена и семантика — кандидаты; окончательное значение назначает AI по доказательствам
* RUNTIME-наблюдения не подменяют Facts из ROM-образа (ТЗ §17)
* Модули, не вошедшие в прогон, в отчёте не участвуют
* модуль `roundtrip_verify` завершился отказом: blocked: сборка не прошла, см. syntax_check по каталогу /home/alexey/Projects/vector-games/.scratch/export/pipeline
* модуль `syntax_check` завершился отказом: blocked: 136 ошибка(ов) сборки

## Recommended Next Steps

* [error] `roundtrip_verify` `blocked` → разобрать отказ модуля: blocked: сборка не прошла, см. syntax_check по каталогу /home/alexey/Projects/vector-games/.scratch/export/pipeline
* [error] `syntax_check` `assembler-error` → имя есть в RDB, но не выгружено в ASM, либо hex-литера без ведущего нуля (DFh → 0DFh)
* [error] `syntax_check` `blocked` → разобрать отказ модуля: blocked: 136 ошибка(ов) сборки
* [warn] `toolchain_lint` `long-defb-use-incbin` → вынести байты в .bin и заменить на incbin
* [info] `measure_sizes` `size-unknown` → тип=function, кандидат на заполнение size через debug_update_rdb_object
* [info] `measure_sizes` `size-unknown` → тип=label, кандидат на заполнение size через debug_update_rdb_object
* [info] `symbolic_operand_lint` `should_be_symbolic` → заменить на func_0100
* [info] `symbolic_operand_lint` `should_be_symbolic` → заменить на lbl_100e

_Порядок этих шагов выбирает человек: генератор только собирает подсказки модулей без дублей._

## Аддендум Stage 1 (ручная проверка round-trip)

**Причина блокировки сборки (136 ошибок = 68 пар) — одна, не «hex без нуля».**
Все 68 `undefined symbol` — это `rst label_00XX` в ниже-origin адреса RST-
страницы (`0x0008/0018/0028/0030/0038`). Пример: регион `0x0BD0` — строка
`"PLEASE%ENTER%YOUR%NAME%"`, а байты-заполнители `FFh` дизассемблер читает как
`RST 7` (0x0038). Это **ложная разборка данных как кода**, а не дефект экспорта.

**Что зафиксировано в RDB (база знаний).** Досеяны 5 объектов `Label` на
zero-page (RST-векторы 0x0008…0x0038) с комментариями: экспортёр пишет для них
`EQU label_00XX = XXh`, из-за чего **настоящие** bootstrap-ссылки на low-RAM
(`func_0100`: `mvi a,0c3h; sta label_0038` — тремплин JMP) собираются корректно.
Проверено экспериментом: EQU-алиасы появились в `layout.asm`, но счётчик ошибок
не изменился — значит оставшиеся `rst` это ровно ложно-разобранные данные.

**Статус контракта round-trip:** выполняется частично — все gap-регионы уже
покрыты `INCBIN` (побайтово точно); блокируют только данные, помеченные кодом.
Классификация `data_ranges` (сейчас `data_ranges: 0`) — работа Stage 2+ (string/
table/glyph-регионы → объекты `Data`), после чего `export_asm` выдаст `defb 0FFh`
вместо `rst` и round-trip сойдётся к 0 расхождений. Контракт действует до Stage 10.
