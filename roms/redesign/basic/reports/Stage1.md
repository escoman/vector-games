# Stage 1. Механические факты (basic.r0m, RAM-образ)

> Сгенерировано `report_gen.py` из JSON-результатов модулей `utils/analyze/`. Дата прогона: 2026-10-16.

## Goal

_цель анализа назначает человек или AI; здесь её нет — передайте `--goal`._

## ROM

| ключ | значение |
|---|---|
| `image` | org=0x0000, path=/home/alexey/Projects/vector-games/roms/, size=17152 |
| `origin` | 0x0000 |
| `rdb` | /home/alexey/Projects/vector-games/roms/redesign/basic/src/basic.rdb |
| `rom` | basic.r0m |
| `rom_size` | 17152 |

## Method

Один долгий MCP-сеанс, кэш доказательств, пакетные инструменты отладчика; Python читает и сравнивает байты и не декодирует коды (ТЗ §8, §33).

Модули прогона:

* `abi_scan` — вердикт `функций: 32, кандидатов параметров: 100`, статус `CANDIDATE`, вызовов MCP: 5235
* `coverage` — вердикт `покрытие 40.65%, незанятых промежутков 64, без покрытия RDB 64`, статус `CANDIDATE`, вызовов MCP: 4
* `disassembly` — вердикт `анализ от 0x0000: 10000 инструкций, 828 references`, статус `OK`, вызовов MCP: 1
* `export_asm` — вердикт `экспортёр: rc=0, файлов 9, сборка: rc=0, 17152 байт`, статус `DERIVED`, вызовов MCP: 0
* `io_signature` — вердикт `аппаратных подписей: 30, поймано в трассе 7, пересечение с документацией 10`, статус `CANDIDATE`, вызовов MCP: 16
* `measure_sizes` — вердикт `432 расхождений(я) размера из 434 объектов`, статус `CANDIDATE`, вызовов MCP: 1
* `memory_diff` — вердикт `85 байт(а) RAM отличается от образа — 46 патч(а)`, статус `OK`, вызовов MCP: 3
* `pipeline` — вердикт `None`, статус `PARTIAL`, вызовов MCP: None
* `pipeline_state` — вердикт `None`, статус `finished`, вызовов MCP: None
* `probe` — вердикт `чистый старт: пауза на 0x2C0A через 3.0 с (вне функции)`, статус `OK`, вызовов MCP: 16
* `rdb_lint` — вердикт `1432 находок, 0 блокирующих`, статус `CANDIDATE`, вызовов MCP: 0
* `roundtrip_verify` — вердикт `byte-for-byte identical`, статус `OK`, вызовов MCP: 0
* `seed_rdb` — вердикт `применено: dry-run: functions 128, labels 306, links 108, существующих 0, итераций 2`, статус `PASS`, вызовов MCP: 1909
* `statistics` — вердикт `None`, статус `None`, вызовов MCP: None
* `strings_scan` — вердикт `строковых прогонов: 894, из них уже строкой в RDB 0, строк в RDB без прогона 0`, статус `CANDIDATE`, вызовов MCP: 0
* `symbolic_operand_lint` — вердикт `clean: все адресные операнды именованные`, статус `CANDIDATE`, вызовов MCP: 0
* `syntax_check` — вердикт `clean: собралось без единой претензии`, статус `DERIVED`, вызовов MCP: 0
* `table_shape` — вердикт `разобрано диапазонов: 0, видов: нет`, статус `CANDIDATE`, вызовов MCP: 0
* `toolchain_lint` — вердикт `clean`, статус `CANDIDATE`, вызовов MCP: 0
* `vram_credits` — вердикт `в RDB нет объекта с именем str_credits_koi8, а адрес из строки не читается`, статус `SKIPPED`, вызовов MCP: 8

## Result summary

| ключ | значение |
|---|---|
| `by_code` | bad_name=434, missing_evidence=128, missing_properties=434, missing_size=434, past_image=2 |
| `by_severity` | error=0, info=0, warning=1432 |
| `findings` | 1432 |
| `labels` | labels=306, unknown_labels=, with_comment=0 |
| `objects` | 434 |
| `source_module` | rdb_lint |
| `unknown_bytes` | 0 |
| `unknowns` | 0 |
| `verdict` | 1432 находок, 0 блокирующих |

### Посев RDB (ТЗ §46)

| ключ | значение |
|---|---|
| `Aliases` | 0 |
| `Coverage %` | 40.65 |
| `Entry points` | 0x0000 |
| `Existing objects` | 0 |
| `Fixpoint` | True |
| `Functions` | 128 |
| `Iterations` | 2 |
| `Labels` | 306 |
| `Links` | 108 |
| `RDB conflicts` | 0 |
| `Status` | PASS |

_Числа посева детерминированы: это структурные кандидаты из `debug_analyze_code`/coverage, а не семантические факты (ТЗ §34)._

### Статистика прогона (ТЗ §30)

| ключ | значение |
|---|---|
| `mcp_calls_field_sum` | 7193 |
| `protocol_version` | 2025-03-26 |
| `retries` | 0 |
| `server` | v06c-mcp |
| `server_version` | 0.6.6 |
| `session` | shared (ТЗ §4) |
| `session_restarts` | 0 |
| `statistics_source` | .scratch/pipeline/basic/statistics.json |
| `tools_exposed` | 76 |
| `total_mcp_bytes` | 2881 |
| `total_mcp_calls` | 9 |
| `total_mcp_ms` | 39.0 |
| `wall_ms` | 3921.9 |

Вызовы по инструментам:

* `debug_get_rdb_info` — 7 вызов(ов), 7.0 мс, 2408 байт
* `debug_get_state` — 1 вызов(ов), 0.7 мс, 349 байт
* `debug_load_rom` — 1 вызов(ов), 31.3 мс, 124 байт

Самые дорогие инструменты по времени:

* `debug_load_rom` — 31.3 мс всего, 31.3 мс максимум, 124 байт максимум на вызов
* `debug_get_rdb_info` — 7.0 мс всего, 1.7 мс максимум, 344 байт максимум на вызов
* `debug_get_state` — 0.7 мс всего, 0.7 мс максимум, 349 байт максимум на вызов

Кэш доказательств: hits=1, misses=0, stores=0, bypasses=0, hit_rate=100.0

Вызовы по модулям:

* `export_asm` — 0 вызов(ов), 0.0 мс, статус `DERIVED`
* `measure_sizes` — 1 вызов(ов), 0.7 мс, статус `CANDIDATE`
* `roundtrip_verify` — 0 вызов(ов), 0.0 мс, статус `OK`
* `symbolic_operand_lint` — 0 вызов(ов), 0.0 мс, статус `CANDIDATE`
* `syntax_check` — 0 вызов(ов), 0.0 мс, статус `DERIVED`
* `toolchain_lint` — 0 вызов(ов), 0.0 мс, статус `CANDIDATE`

### Ссылки на доказательства

* `export_asm` → `/home/alexey/Projects/vector-games/.scratch/export/pipeline` (out_dir)
* `measure_sizes` → `/home/alexey/Projects/vector-games/roms/redesign/basic/src/basic.rdb` (rdb)
* `pipeline` → `/home/alexey/Projects/vector-games/roms/redesign/basic/src/basic.rdb` (rdb)
* `rdb_lint` → `/home/alexey/Projects/vector-games/roms/redesign/basic/src/basic.rdb` (rdb)
* `roundtrip_verify` → `/home/alexey/Projects/vector-games/.scratch/export/pipeline` (out_dir)
* `roundtrip_verify` → `/home/alexey/Projects/vector-games/roms/redesign/basic/src/basic.rdb` (rdb)
* `symbolic_operand_lint` → `/home/alexey/Projects/vector-games/.scratch/export/pipeline` (out_dir)
* `syntax_check` → `/home/alexey/Projects/vector-games/.scratch/export/pipeline` (out_dir)
* `toolchain_lint` → `/home/alexey/Projects/vector-games/.scratch/export/pipeline` (out_dir)

## Findings

### `measure_sizes` (432: size-unknown×432)

* **info** `size-unknown` `func_0000` — размера в RDB нет; линейная разборка от 0x0000 даёт 8 байт(а) до 0x0007
* **info** `size-unknown` `func_0008` — размера в RDB нет; линейная разборка от 0x0008 даёт 8 байт(а) до 0x000F
* **info** `size-unknown` `func_0010` — размера в RDB нет; линейная разборка от 0x0010 даёт 16 байт(а) до 0x001F
* **info** `size-unknown` `func_0020` — размера в RDB нет; линейная разборка от 0x0020 даёт 9 байт(а) до 0x0028
* **info** `size-unknown` `func_0028` — размера в RDB нет; линейная разборка от 0x0028 даёт 0 байт(а) до —
* **info** `size-unknown` `func_0038` — размера в RDB нет; линейная разборка от 0x0038 даёт 3 байт(а) до 0x003A
* **info** `size-unknown` `func_003b` — размера в RDB нет; линейная разборка от 0x003B даёт 3 байт(а) до 0x003D
* **info** `size-unknown` `func_003e` — размера в RDB нет; линейная разборка от 0x003E даёт 12 байт(а) до 0x0049
* **info** `size-unknown` `func_004a` — размера в RDB нет; линейная разборка от 0x004A даёт 18 байт(а) до 0x005B
* **info** `size-unknown` `func_005c` — размера в RDB нет; линейная разборка от 0x005C даёт 13 байт(а) до 0x0068
* **info** `size-unknown` `lbl_0069` — размера в RDB нет; линейная разборка от 0x0069 даёт 11 байт(а) до 0x0073
* **info** `size-unknown` `lbl_0074` — размера в RDB нет; линейная разборка от 0x0074 даёт 9 байт(а) до 0x007C
* **info** `size-unknown` `lbl_007b` — размера в RDB нет; линейная разборка от 0x007B даёт 0 байт(а) до —
* **info** `size-unknown` `lbl_0083` — размера в RDB нет; линейная разборка от 0x0083 даёт 21 байт(а) до 0x0097
* **info** `size-unknown` `lbl_0098` — размера в RDB нет; линейная разборка от 0x0098 даёт 9 байт(а) до 0x00A0
* **info** `size-unknown` `func_00a1` — размера в RDB нет; линейная разборка от 0x00A1 даёт 20 байт(а) до 0x00B4
* **info** `size-unknown` `lbl_00b5` — размера в RDB нет; линейная разборка от 0x00B5 даёт 48 байт(а) до 0x00E4
* **info** `size-unknown` `lbl_00e5` — размера в RDB нет; линейная разборка от 0x00E5 даёт 38 байт(а) до 0x010A
* **info** `size-unknown` `lbl_010b` — размера в RDB нет; линейная разборка от 0x010B даёт 50 байт(а) до 0x013C
* **info** `size-unknown` `lbl_013d` — размера в RDB нет; линейная разборка от 0x013D даёт 14 байт(а) до 0x014A
* _… ещё 412 в исходном JSON_

### `rdb_lint` (1432: missing_size×434, bad_name×434, missing_properties×434, missing_evidence×128, past_image×2)

* **warn** `missing_size` `func_0000` — size=0 — длина области неизвестна (v06c-asm-export не сможет выделить байты без размера)
* **warn** `missing_size` `func_0008` — size=0 — длина области неизвестна (v06c-asm-export не сможет выделить байты без размера)
* **warn** `missing_size` `func_0010` — size=0 — длина области неизвестна (v06c-asm-export не сможет выделить байты без размера)
* **warn** `missing_size` `func_0020` — size=0 — длина области неизвестна (v06c-asm-export не сможет выделить байты без размера)
* **warn** `missing_size` `func_0028` — size=0 — длина области неизвестна (v06c-asm-export не сможет выделить байты без размера)
* **warn** `missing_size` `func_0038` — size=0 — длина области неизвестна (v06c-asm-export не сможет выделить байты без размера)
* **warn** `missing_size` `func_003b` — size=0 — длина области неизвестна (v06c-asm-export не сможет выделить байты без размера)
* **warn** `missing_size` `func_003e` — size=0 — длина области неизвестна (v06c-asm-export не сможет выделить байты без размера)
* **warn** `missing_size` `func_004a` — size=0 — длина области неизвестна (v06c-asm-export не сможет выделить байты без размера)
* **warn** `missing_size` `func_005c` — size=0 — длина области неизвестна (v06c-asm-export не сможет выделить байты без размера)
* **warn** `missing_size` `lbl_0069` — size=0 — длина области неизвестна (v06c-asm-export не сможет выделить байты без размера)
* **warn** `missing_size` `lbl_0074` — size=0 — длина области неизвестна (v06c-asm-export не сможет выделить байты без размера)
* **warn** `missing_size` `lbl_007b` — size=0 — длина области неизвестна (v06c-asm-export не сможет выделить байты без размера)
* **warn** `missing_size` `lbl_0083` — size=0 — длина области неизвестна (v06c-asm-export не сможет выделить байты без размера)
* **warn** `missing_size` `lbl_0098` — size=0 — длина области неизвестна (v06c-asm-export не сможет выделить байты без размера)
* **warn** `missing_size` `func_00a1` — size=0 — длина области неизвестна (v06c-asm-export не сможет выделить байты без размера)
* **warn** `missing_size` `lbl_00b5` — size=0 — длина области неизвестна (v06c-asm-export не сможет выделить байты без размера)
* **warn** `missing_size` `lbl_00e5` — size=0 — длина области неизвестна (v06c-asm-export не сможет выделить байты без размера)
* **warn** `missing_size` `lbl_010b` — size=0 — длина области неизвестна (v06c-asm-export не сможет выделить байты без размера)
* **warn** `missing_size` `lbl_013d` — size=0 — длина области неизвестна (v06c-asm-export не сможет выделить байты без размера)
* _… ещё 1412 в исходном JSON_

### `toolchain_lint` (26: long-defb-use-incbin×26)

* **warn** `long-defb-use-incbin` layout.asm:604 — дамп из 74 байт начиная со строки 604: побайтовую точность надёжнее держать в INCBIN
* **warn** `long-defb-use-incbin` layout.asm:629 — дамп из 167 байт начиная со строки 629: побайтовую точность надёжнее держать в INCBIN
* **warn** `long-defb-use-incbin` layout.asm:776 — дамп из 269 байт начиная со строки 776: побайтовую точность надёжнее держать в INCBIN
* **warn** `long-defb-use-incbin` layout.asm:878 — дамп из 183 байт начиная со строки 878: побайтовую точность надёжнее держать в INCBIN
* **warn** `long-defb-use-incbin` layout.asm:916 — дамп из 477 байт начиная со строки 916: побайтовую точность надёжнее держать в INCBIN
* **warn** `long-defb-use-incbin` layout.asm:1221 — дамп из 92 байт начиная со строки 1221: побайтовую точность надёжнее держать в INCBIN
* **warn** `long-defb-use-incbin` layout.asm:1933 — дамп из 188 байт начиная со строки 1933: побайтовую точность надёжнее держать в INCBIN
* **warn** `long-defb-use-incbin` layout.asm:3276 — дамп из 120 байт начиная со строки 3276: побайтовую точность надёжнее держать в INCBIN
* **warn** `long-defb-use-incbin` layout.asm:3312 — дамп из 95 байт начиная со строки 3312: побайтовую точность надёжнее держать в INCBIN
* **warn** `long-defb-use-incbin` layout.asm:3416 — дамп из 90 байт начиная со строки 3416: побайтовую точность надёжнее держать в INCBIN
* **warn** `long-defb-use-incbin` layout.asm:3445 — дамп из 394 байт начиная со строки 3445: побайтовую точность надёжнее держать в INCBIN
* **warn** `long-defb-use-incbin` layout.asm:3569 — дамп из 417 байт начиная со строки 3569: побайтовую точность надёжнее держать в INCBIN
* **warn** `long-defb-use-incbin` layout.asm:3628 — дамп из 368 байт начиная со строки 3628: побайтовую точность надёжнее держать в INCBIN
* **warn** `long-defb-use-incbin` layout.asm:3778 — дамп из 614 байт начиная со строки 3778: побайтовую точность надёжнее держать в INCBIN
* **warn** `long-defb-use-incbin` layout.asm:4002 — дамп из 719 байт начиная со строки 4002: побайтовую точность надёжнее держать в INCBIN
* **warn** `long-defb-use-incbin` layout.asm:4099 — дамп из 963 байт начиная со строки 4099: побайтовую точность надёжнее держать в INCBIN
* **warn** `long-defb-use-incbin` layout.asm:4276 — дамп из 140 байт начиная со строки 4276: побайтовую точность надёжнее держать в INCBIN
* **warn** `long-defb-use-incbin` layout.asm:4607 — дамп из 74 байт начиная со строки 4607: побайтовую точность надёжнее держать в INCBIN
* **warn** `long-defb-use-incbin` layout.asm:4631 — дамп из 154 байт начиная со строки 4631: побайтовую точность надёжнее держать в INCBIN
* **warn** `long-defb-use-incbin` layout.asm:4924 — дамп из 627 байт начиная со строки 4924: побайтовую точность надёжнее держать в INCBIN
* _… ещё 6 в исходном JSON_


## Verified Facts

* `disassembly` — анализ от 0x0000: 10000 инструкций, 828 references (`OK`)
* `memory_diff` — 85 байт(а) RAM отличается от образа — 46 патч(а) (`OK`)
* `probe` — чистый старт: пауза на 0x2C0A через 3.0 с (вне функции) (`OK`)
* `roundtrip_verify` — byte-for-byte identical (`OK`)
* `seed_rdb` — применено: dry-run: functions 128, labels 306, links 108, существующих 0, итераций 2 (`PASS`)

_Фактом результат считается только потому, что модуль выдал статус OK/FACT: совпадение байтов, совпадение предсказания с реальностью, нулевая разница. Сюда не попадают CANDIDATE (ТЗ §34)._

## Inferences

* `abi_scan` — функций: 32, кандидатов параметров: 100 (статус модуля: CANDIDATE)
* `abi_scan` аргумент L у func_0008 (0x0008) — input: static: L читается до любой записи (MOV A, M @0x0008); dynamic: значение меняется между 2 срабатываниями (0x007A,0x007C) (уверенность: high)
* `abi_scan` аргумент L у func_0010 (0x0010) — input: static: L читается до любой записи (INX H @0x0010); dynamic: значение меняется между 2 срабатываниями (0x0076,0x0079,0x0079) (уверенность: high)
* `abi_scan` аргумент E у func_0020 (0x0020) — input: static: E читается до любой записи (SUB E @0x0024); dynamic: значение меняется между 3 срабатываниями (0x007A,0x007B,0x007C) (уверенность: high)
* `abi_scan` аргумент L у func_0020 (0x0020) — input: static: L читается до любой записи (ORA L @0x0023); dynamic: значение меняется между 3 срабатываниями (0x007A,0x007B,0x007C) (уверенность: high)
* `abi_scan` аргумент L у func_00a1 (0x00A1) — input: static: L читается до любой записи (MOV A, M @0x00A1); dynamic: значение меняется между 3 срабатываниями (0x004B,0x004C,0x004D) (уверенность: high)
* `abi_scan` аргумент A у func_01c5 (0x01C5) — input: static: A читается до любой записи (XRA A @0x01CD); dynamic: значение меняется между 2 срабатываниями (0x0000,0x0021) (уверенность: high)
* `abi_scan` аргумент A у func_0367 (0x0367) — input: static: A читается до любой записи (MOV B, A @0x0374); dynamic: значение меняется между 2 срабатываниями (0x0000,0x0008,0x0008) (уверенность: high)
* `abi_scan` аргумент A у func_07bc (0x07BC) — input: static: A читается до любой записи (XRA A @0x07BC); dynamic: значение меняется между 3 срабатываниями (0x002C,0x00C3,0x000A) (уверенность: high)
* `coverage` — покрытие 40.65%, незанятых промежутков 64, без покрытия RDB 64 (статус модуля: CANDIDATE)
* `export_asm` — экспортёр: rc=0, файлов 9, сборка: rc=0, 17152 байт (статус модуля: DERIVED)
* `io_signature` — аппаратных подписей: 30, поймано в трассе 7, пересечение с документацией 10 (статус модуля: CANDIDATE)
* `io_signature` var_port_02 — rw, в трассе: да, участков кода: 3, роль по документации: КР580ВВ55 #1 порт B (бордюр, 512px, клавиатура) (уверенность: high)
* `io_signature` var_port_01 — rw, в трассе: да, участков кода: 3, роль по документации: КР580ВВ55 #1 порт C (магн/СС/УС/РУС) (уверенность: high)
* `io_signature` var_port_00 — out, в трассе: да, участков кода: 4, роль по документации: КР580ВВ55 #1 управляющее слово (уверенность: high)
* `io_signature` var_port_03 — out, в трассе: да, участков кода: 3, роль по документации: КР580ВВ55 #1 порт A (верт. скролл, маска строк) (уверенность: high)
* `io_signature` var_port_08 — out, в трассе: да, участков кода: 2, роль по документации: КР580ВИ53 управляющее слово (уверенность: high)
* `io_signature` var_port_04 — out, в трассе: да, участков кода: 1, роль по документации: КР580ВВ55 #2 управляющее слово (уверенность: high)
* `io_signature` var_port_0c — out, в трассе: да, участков кода: 0, роль по документации: палитра (уверенность: medium)
* `io_signature` var_port_05 — rw, в трассе: нет, участков кода: 3, роль по документации: КР580ВВ55 #2 порт C #2 (уверенность: medium)
* `measure_sizes` — 432 расхождений(я) размера из 434 объектов (статус модуля: CANDIDATE)
* `pipeline` — вердикта нет (статус модуля: PARTIAL)
* `rdb_lint` — 1432 находок, 0 блокирующих (статус модуля: CANDIDATE)
* `strings_scan` — строковых прогонов: 894, из них уже строкой в RDB 0, строк в RDB без прогона 0 (статус модуля: CANDIDATE)
* `strings_scan` str_2663 — koi8, 116 байт, с завершающим нулём: BEEпPAUSеVERIFыHOMеEDIтDELETеMERGеAUTоHIMEмю (уверенность: medium)
* `strings_scan` str_372d — koi8, 13 байт, с завершающим нулём: ц/7)))))))К~Ф (уверенность: medium)
* `strings_scan` str_0c80 — koi8, 11 байт, с завершающим нулём: яs#r#КАиOЕ! (уверенность: medium)
* `strings_scan` str_204e — koi8, 11 байт, с завершающим нулём: зK yЧ`зl O> (уверенность: medium)
* `strings_scan` str_0f77 — koi8, 10 байт, с завершающим нулём: х+F+NЕ++n& (уверенность: medium)
* `strings_scan` str_2455 — koi8, 10 байт, с завершающим нулём: 'Авб2$:#:Ж (уверенность: medium)
* `strings_scan` str_352f — koi8, 10 байт, с завершающим нулём: 295мX5мB5Ж (уверенность: medium)
* `strings_scan` str_0425 — koi8, 9 байт, с завершающим нулём: яЫКЧА>имJ (уверенность: medium)
* `strings_scan` str_1b09 — koi8, 9 байт, с завершающим нулём: К*!?е>ямJ (уверенность: medium)
* `strings_scan` str_2e35 — koi8, 9 байт, с завершающим нулём: 2W+Я2V+#> (уверенность: medium)
* `symbolic_operand_lint` — clean: все адресные операнды именованные (статус модуля: CANDIDATE)
* `syntax_check` — clean: собралось без единой претензии (статус модуля: DERIVED)
* `table_shape` — разобрано диапазонов: 0, видов: нет (статус модуля: CANDIDATE)
* `toolchain_lint` — clean (статус модуля: CANDIDATE)

## Hypotheses

_пусто_

## Unknowns

* `measure_sizes` `size-unknown` ×432 — размера в RDB нет; линейная разборка от 0x0000 даёт 8 байт(а) до 0x0007
* `pipeline_state` `(без правила)` ×1 — 
* `vram_credits` `(без правила)` ×1 — 
* модуль `statistics` не вернул статус — его результат `None` никуда не отнесён, проверьте формат вывода модуля

## Limitations

* Python не декодирует 8080-коды и не строит CFG: всё это отдаёт отладчик (ТЗ §8, §34)
* Имена и семантика — кандидаты; окончательное значение назначает AI по доказательствам
* RUNTIME-наблюдения не подменяют Facts из ROM-образа (ТЗ §17)
* Модули, не вошедшие в прогон, в отчёте не участвуют

## Recommended Next Steps

* [warn] `toolchain_lint` `long-defb-use-incbin` → вынести байты в .bin и заменить на incbin
* [info] `measure_sizes` `size-unknown` → тип=function, кандидат на заполнение size через debug_update_rdb_object
* [info] `measure_sizes` `size-unknown` → тип=label, кандидат на заполнение size через debug_update_rdb_object

_Порядок этих шагов выбирает человек: генератор только собирает подсказки модулей без дублей._
