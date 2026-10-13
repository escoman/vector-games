# Stage 1. Механические факты (exolon.rom)

> Сгенерировано `report_gen.py` из JSON-результатов модулей `utils/analyze/`. Дата прогона: 2026-10-14.

## Goal

_цель анализа назначает человек или AI; здесь её нет — передайте `--goal`._

## ROM

| ключ | значение |
|---|---|
| `image` | org=0x0100, path=/home/alexey/Projects/vector-games/roms/, size=32512 |
| `origin` | 0x0100 |
| `rdb` | /home/alexey/Projects/vector-games/roms/redesign/exolon/src/exolon.rdb |
| `rom` | exolon.rom |
| `rom_size` | 32512 |

## Method

Один долгий MCP-сеанс, кэш доказательств, пакетные инструменты отладчика; Python читает и сравнивает байты и не декодирует коды (ТЗ §8, §33).

Модули прогона:

* `abi_scan` — вердикт `функций: 32, кандидатов параметров: 153`, статус `CANDIDATE`, вызовов MCP: 9425
* `coverage` — вердикт `покрытие 28.67%, незанятых промежутков 79, без покрытия RDB 79`, статус `CANDIDATE`, вызовов MCP: 4
* `disassembly` — вердикт `анализ от 0x0100: 5345 инструкций, 920 references`, статус `OK`, вызовов MCP: 1
* `export_asm` — вердикт `экспортёр: rc=0, файлов 5, сборка: rc=0, 32512 байт`, статус `DERIVED`, вызовов MCP: 0
* `io_signature` — вердикт `аппаратных подписей: 56, поймано в трассе 1, пересечение с документацией 10`, статус `CANDIDATE`, вызовов MCP: 19
* `measure_sizes` — вердикт `406 расхождений(я) размера из 406 объектов`, статус `CANDIDATE`, вызовов MCP: 2
* `memory_diff` — вердикт `93 байт(а) RAM отличается от образа — 31 патч(а)`, статус `OK`, вызовов MCP: 7
* `pipeline` — вердикт `None`, статус `PARTIAL`, вызовов MCP: None
* `pipeline_state` — вердикт `None`, статус `finished`, вызовов MCP: None
* `probe` — вердикт `чистый старт: пауза на 0x0B47 через 15.0 с (вне функции)`, статус `OK`, вызовов MCP: 28
* `rdb_lint` — вердикт `1371 находок, 0 блокирующих`, статус `CANDIDATE`, вызовов MCP: 0
* `roundtrip_verify` — вердикт `byte-for-byte identical`, статус `OK`, вызовов MCP: 0
* `seed_rdb` — вердикт `применено: dry-run: functions 153, labels 253, links 90, существующих 0, итераций 2`, статус `PASS`, вызовов MCP: 1774
* `statistics` — вердикт `None`, статус `None`, вызовов MCP: None
* `strings_scan` — вердикт `строковых прогонов: 1088, из них уже строкой в RDB 0, строк в RDB без прогона 0`, статус `CANDIDATE`, вызовов MCP: 0
* `symbolic_operand_lint` — вердикт `clean: все адресные операнды именованные`, статус `CANDIDATE`, вызовов MCP: 0
* `syntax_check` — вердикт `clean: собралось без единой претензии`, статус `DERIVED`, вызовов MCP: 0
* `table_shape` — вердикт `разобрано диапазонов: 0, видов: нет`, статус `CANDIDATE`, вызовов MCP: 0
* `toolchain_lint` — вердикт `clean`, статус `CANDIDATE`, вызовов MCP: 0
* `vram_credits` — вердикт `в RDB нет объекта с именем str_credits_koi8, а адрес из строки не читается`, статус `SKIPPED`, вызовов MCP: 7

## Result summary

| ключ | значение |
|---|---|
| `by_code` | bad_name=406, missing_evidence=153, missing_properties=406, missing_size=406 |
| `by_severity` | error=0, info=0, warning=1371 |
| `findings` | 1371 |
| `labels` | labels=253, unknown_labels=, with_comment=0 |
| `objects` | 406 |
| `source_module` | rdb_lint |
| `unknown_bytes` | 0 |
| `unknowns` | 0 |
| `verdict` | 1371 находок, 0 блокирующих |

### Посев RDB (ТЗ §46)

| ключ | значение |
|---|---|
| `Aliases` | 0 |
| `Coverage %` | 28.67 |
| `Entry points` | 0x0100 |
| `Existing objects` | 0 |
| `Fixpoint` | True |
| `Functions` | 153 |
| `Iterations` | 2 |
| `Labels` | 253 |
| `Links` | 90 |
| `RDB conflicts` | 0 |
| `Status` | PASS |

_Числа посева детерминированы: это структурные кандидаты из `debug_analyze_code`/coverage, а не семантические факты (ТЗ §34)._

### Статистика прогона (ТЗ §30)

| ключ | значение |
|---|---|
| `mcp_calls_field_sum` | 11267 |
| `protocol_version` | 2025-03-26 |
| `retries` | 0 |
| `server` | v06c-mcp |
| `server_version` | 0.6.5 |
| `session` | shared (ТЗ §4) |
| `session_restarts` | 0 |
| `statistics_source` | .scratch/pipeline/exolon/statistics.json |
| `tools_exposed` | 74 |
| `total_mcp_bytes` | 4885762 |
| `total_mcp_calls` | 10 |
| `total_mcp_ms` | 1001.3 |
| `wall_ms` | 4812.5 |

Вызовы по инструментам:

* `debug_get_rdb_info` — 7 вызов(ов), 9.2 мс, 2429 байт
* `debug_disassemble_image` — 1 вызов(ов), 968.5 мс, 4882876 байт
* `debug_get_state` — 1 вызов(ов), 0.5 мс, 331 байт
* `debug_load_rom` — 1 вызов(ов), 23.2 мс, 126 байт

Самые дорогие инструменты по времени:

* `debug_disassemble_image` — 968.5 мс всего, 968.5 мс максимум, 4882876 байт максимум на вызов
* `debug_load_rom` — 23.2 мс всего, 23.2 мс максимум, 126 байт максимум на вызов
* `debug_get_rdb_info` — 9.2 мс всего, 2.4 мс максимум, 347 байт максимум на вызов
* `debug_get_state` — 0.5 мс всего, 0.5 мс максимум, 331 байт максимум на вызов

Кэш доказательств: hits=0, misses=1, stores=1, bypasses=0, hit_rate=0.0

Вызовы по модулям:

* `export_asm` — 0 вызов(ов), 0.0 мс, статус `DERIVED`
* `measure_sizes` — 2 вызов(ов), 968.9 мс, статус `CANDIDATE`
* `roundtrip_verify` — 0 вызов(ов), 0.0 мс, статус `OK`
* `symbolic_operand_lint` — 0 вызов(ов), 0.0 мс, статус `CANDIDATE`
* `syntax_check` — 0 вызов(ов), 0.0 мс, статус `DERIVED`
* `toolchain_lint` — 0 вызов(ов), 0.0 мс, статус `CANDIDATE`

### Ссылки на доказательства

* `export_asm` → `/home/alexey/Projects/vector-games/.scratch/export/pipeline` (out_dir)
* `measure_sizes` → `/home/alexey/Projects/vector-games/roms/redesign/exolon/src/exolon.rdb` (rdb)
* `pipeline` → `/home/alexey/Projects/vector-games/roms/redesign/exolon/src/exolon.rdb` (rdb)
* `rdb_lint` → `/home/alexey/Projects/vector-games/roms/redesign/exolon/src/exolon.rdb` (rdb)
* `roundtrip_verify` → `/home/alexey/Projects/vector-games/.scratch/export/pipeline` (out_dir)
* `roundtrip_verify` → `/home/alexey/Projects/vector-games/roms/redesign/exolon/src/exolon.rdb` (rdb)
* `symbolic_operand_lint` → `/home/alexey/Projects/vector-games/.scratch/export/pipeline` (out_dir)
* `syntax_check` → `/home/alexey/Projects/vector-games/.scratch/export/pipeline` (out_dir)
* `toolchain_lint` → `/home/alexey/Projects/vector-games/.scratch/export/pipeline` (out_dir)

## Findings

### `measure_sizes` (406: size-unknown×406)

* **info** `size-unknown` `func_0100` — размера в RDB нет; линейная разборка от 0x0100 даёт 3 байт(а) до 0x0102
* **info** `size-unknown` `func_0103` — размера в RDB нет; линейная разборка от 0x0103 даёт 13 байт(а) до 0x010F
* **info** `size-unknown` `lbl_0110` — размера в RDB нет; линейная разборка от 0x0110 даёт 16 байт(а) до 0x011F
* **info** `size-unknown` `func_0120` — размера в RDB нет; линейная разборка от 0x0120 даёт 15 байт(а) до 0x012E
* **info** `size-unknown` `lbl_012f` — размера в RDB нет; линейная разборка от 0x012F даёт 3 байт(а) до 0x0131
* **info** `size-unknown` `lbl_0132` — размера в RDB нет; линейная разборка от 0x0132 даёт 21 байт(а) до 0x0146
* **info** `size-unknown` `func_0147` — размера в RDB нет; линейная разборка от 0x0147 даёт 29 байт(а) до 0x0163
* **info** `size-unknown` `lbl_0164` — размера в RDB нет; линейная разборка от 0x0164 даёт 53 байт(а) до 0x0198
* **info** `size-unknown` `func_0199` — размера в RDB нет; линейная разборка от 0x0199 даёт 16 байт(а) до 0x01A8
* **info** `size-unknown` `func_01a9` — размера в RDB нет; линейная разборка от 0x01A9 даёт 46 байт(а) до 0x01D6
* **info** `size-unknown` `lbl_01d7` — размера в RDB нет; линейная разборка от 0x01D7 даёт 616 байт(а) до 0x043E
* **info** `size-unknown` `func_043f` — размера в RDB нет; линейная разборка от 0x043F даёт 1 байт(а) до 0x043F
* **info** `size-unknown` `lbl_0440` — размера в RDB нет; линейная разборка от 0x0440 даёт 8 байт(а) до 0x0447
* **info** `size-unknown` `func_0448` — размера в RDB нет; линейная разборка от 0x0448 даёт 29 байт(а) до 0x0464
* **info** `size-unknown` `func_0465` — размера в RDB нет; линейная разборка от 0x0465 даёт 16 байт(а) до 0x0474
* **info** `size-unknown` `func_0475` — размера в RDB нет; линейная разборка от 0x0475 даёт 25 байт(а) до 0x048D
* **info** `size-unknown` `func_048e` — размера в RDB нет; линейная разборка от 0x048E даёт 25 байт(а) до 0x04A6
* **info** `size-unknown` `func_04a7` — размера в RDB нет; линейная разборка от 0x04A7 даёт 28 байт(а) до 0x04C2
* **info** `size-unknown` `lbl_04c3` — размера в RDB нет; линейная разборка от 0x04C3 даёт 5 байт(а) до 0x04C7
* **info** `size-unknown` `func_04c8` — размера в RDB нет; линейная разборка от 0x04C8 даёт 28 байт(а) до 0x04E3
* _… ещё 386 в исходном JSON_

### `rdb_lint` (1371: missing_size×406, bad_name×406, missing_properties×406, missing_evidence×153)

* **warn** `missing_size` `func_0100` — size=0 — длина области неизвестна (v06c-asm-export не сможет выделить байты без размера)
* **warn** `missing_size` `func_0103` — size=0 — длина области неизвестна (v06c-asm-export не сможет выделить байты без размера)
* **warn** `missing_size` `lbl_0110` — size=0 — длина области неизвестна (v06c-asm-export не сможет выделить байты без размера)
* **warn** `missing_size` `func_0120` — size=0 — длина области неизвестна (v06c-asm-export не сможет выделить байты без размера)
* **warn** `missing_size` `lbl_012f` — size=0 — длина области неизвестна (v06c-asm-export не сможет выделить байты без размера)
* **warn** `missing_size` `lbl_0132` — size=0 — длина области неизвестна (v06c-asm-export не сможет выделить байты без размера)
* **warn** `missing_size` `func_0147` — size=0 — длина области неизвестна (v06c-asm-export не сможет выделить байты без размера)
* **warn** `missing_size` `lbl_0164` — size=0 — длина области неизвестна (v06c-asm-export не сможет выделить байты без размера)
* **warn** `missing_size` `func_0199` — size=0 — длина области неизвестна (v06c-asm-export не сможет выделить байты без размера)
* **warn** `missing_size` `func_01a9` — size=0 — длина области неизвестна (v06c-asm-export не сможет выделить байты без размера)
* **warn** `missing_size` `lbl_01d7` — size=0 — длина области неизвестна (v06c-asm-export не сможет выделить байты без размера)
* **warn** `missing_size` `func_043f` — size=0 — длина области неизвестна (v06c-asm-export не сможет выделить байты без размера)
* **warn** `missing_size` `lbl_0440` — size=0 — длина области неизвестна (v06c-asm-export не сможет выделить байты без размера)
* **warn** `missing_size` `func_0448` — size=0 — длина области неизвестна (v06c-asm-export не сможет выделить байты без размера)
* **warn** `missing_size` `func_0465` — size=0 — длина области неизвестна (v06c-asm-export не сможет выделить байты без размера)
* **warn** `missing_size` `func_0475` — size=0 — длина области неизвестна (v06c-asm-export не сможет выделить байты без размера)
* **warn** `missing_size` `func_048e` — size=0 — длина области неизвестна (v06c-asm-export не сможет выделить байты без размера)
* **warn** `missing_size` `func_04a7` — size=0 — длина области неизвестна (v06c-asm-export не сможет выделить байты без размера)
* **warn** `missing_size` `lbl_04c3` — size=0 — длина области неизвестна (v06c-asm-export не сможет выделить байты без размера)
* **warn** `missing_size` `func_04c8` — size=0 — длина области неизвестна (v06c-asm-export не сможет выделить байты без размера)
* _… ещё 1351 в исходном JSON_

### `toolchain_lint` (21: long-defb-use-incbin×21)

* **warn** `long-defb-use-incbin` layout.asm:181 — дамп из 577 байт начиная со строки 181: побайтовую точность надёжнее держать в INCBIN
* **warn** `long-defb-use-incbin` layout.asm:522 — дамп из 97 байт начиная со строки 522: побайтовую точность надёжнее держать в INCBIN
* **warn** `long-defb-use-incbin` layout.asm:694 — дамп из 601 байт начиная со строки 694: побайтовую точность надёжнее держать в INCBIN
* **warn** `long-defb-use-incbin` layout.asm:833 — дамп из 105 байт начиная со строки 833: побайтовую точность надёжнее держать в INCBIN
* **warn** `long-defb-use-incbin` layout.asm:1125 — дамп из 2545 байт начиная со строки 1125: побайтовую точность надёжнее держать в INCBIN
* **warn** `long-defb-use-incbin` layout.asm:1871 — дамп из 1440 байт начиная со строки 1871: побайтовую точность надёжнее держать в INCBIN
* **warn** `long-defb-use-incbin` layout.asm:2629 — дамп из 352 байт начиная со строки 2629: побайтовую точность надёжнее держать в INCBIN
* **warn** `long-defb-use-incbin` layout.asm:2897 — дамп из 319 байт начиная со строки 2897: побайтовую точность надёжнее держать в INCBIN
* **warn** `long-defb-use-incbin` layout.asm:3011 — дамп из 83 байт начиная со строки 3011: побайтовую точность надёжнее держать в INCBIN
* **warn** `long-defb-use-incbin` layout.asm:3034 — дамп из 5217 байт начиная со строки 3034: побайтовую точность надёжнее держать в INCBIN
* **warn** `long-defb-use-incbin` layout.asm:3974 — дамп из 106 байт начиная со строки 3974: побайтовую точность надёжнее держать в INCBIN
* **warn** `long-defb-use-incbin` layout.asm:4291 — дамп из 75 байт начиная со строки 4291: побайтовую точность надёжнее держать в INCBIN
* **warn** `long-defb-use-incbin` layout.asm:6423 — дамп из 2247 байт начиная со строки 6423: побайтовую точность надёжнее держать в INCBIN
* **warn** `long-defb-use-incbin` layout.asm:6980 — дамп из 87 байт начиная со строки 6980: побайтовую точность надёжнее держать в INCBIN
* **warn** `long-defb-use-incbin` layout.asm:7171 — дамп из 96 байт начиная со строки 7171: побайтовую точность надёжнее держать в INCBIN
* **warn** `long-defb-use-incbin` layout.asm:7264 — дамп из 4333 байт начиная со строки 7264: побайтовую точность надёжнее держать в INCBIN
* **warn** `long-defb-use-incbin` layout.asm:8007 — дамп из 650 байт начиная со строки 8007: побайтовую точность надёжнее держать в INCBIN
* **warn** `long-defb-use-incbin` layout.asm:8244 — дамп из 719 байт начиная со строки 8244: побайтовую точность надёжнее держать в INCBIN
* **warn** `long-defb-use-incbin` layout.asm:8504 — дамп из 555 байт начиная со строки 8504: побайтовую точность надёжнее держать в INCBIN
* **warn** `long-defb-use-incbin` layout.asm:8727 — дамп из 249 байт начиная со строки 8727: побайтовую точность надёжнее держать в INCBIN
* _… ещё 1 в исходном JSON_


## Verified Facts

* `disassembly` — анализ от 0x0100: 5345 инструкций, 920 references (`OK`)
* `memory_diff` — 93 байт(а) RAM отличается от образа — 31 патч(а) (`OK`)
* `probe` — чистый старт: пауза на 0x0B47 через 15.0 с (вне функции) (`OK`)
* `roundtrip_verify` — byte-for-byte identical (`OK`)
* `seed_rdb` — применено: dry-run: functions 153, labels 253, links 90, существующих 0, итераций 2 (`PASS`)

_Фактом результат считается только потому, что модуль выдал статус OK/FACT: совпадение байтов, совпадение предсказания с реальностью, нулевая разница. Сюда не попадают CANDIDATE (ТЗ §34)._

## Inferences

* `abi_scan` — функций: 32, кандидатов параметров: 153 (статус модуля: CANDIDATE)
* `abi_scan` аргумент ? у func_0120 (0x0120) — memory_argument: static: SHLD 0x0090 (write) (уверенность: medium)
* `abi_scan` аргумент ? у func_0147 (0x0147) — memory_argument: static: LDA 0x00C5 (read) (уверенность: medium)
* `abi_scan` аргумент ? у func_01a9 (0x01A9) — memory_argument: static: SHLD 0x01EE (write) (уверенность: medium)
* `abi_scan` аргумент ? у func_0448 (0x0448) — memory_argument: static: LHLD 0x01CF (read); static: SHLD 0x01CF (write) (уверенность: medium)
* `abi_scan` аргумент ? у func_052b (0x052B) — memory_argument: static: STA 0x01A5 (write) (уверенность: medium)
* `coverage` — покрытие 28.67%, незанятых промежутков 79, без покрытия RDB 79 (статус модуля: CANDIDATE)
* `export_asm` — экспортёр: rc=0, файлов 5, сборка: rc=0, 32512 байт (статус модуля: DERIVED)
* `io_signature` — аппаратных подписей: 56, поймано в трассе 1, пересечение с документацией 10 (статус модуля: CANDIDATE)
* `io_signature` var_port_01 — in, в трассе: да, участков кода: 3, роль по документации: КР580ВВ55 #1 порт C (магн/СС/УС/РУС) (уверенность: high)
* `io_signature` var_port_00 — rw, в трассе: нет, участков кода: 13, роль по документации: КР580ВВ55 #1 управляющее слово (расхождение) (уверенность: medium)
* `io_signature` var_port_02 — rw, в трассе: нет, участков кода: 4, роль по документации: КР580ВВ55 #1 порт B (бордюр, 512px, клавиатура) (уверенность: medium)
* `io_signature` var_port_03 — rw, в трассе: нет, участков кода: 2, роль по документации: КР580ВВ55 #1 порт A (верт. скролл, маска строк) (уверенность: medium)
* `io_signature` var_port_04 — rw, в трассе: нет, участков кода: 1, роль по документации: КР580ВВ55 #2 управляющее слово (расхождение) (уверенность: medium)
* `io_signature` var_port_05 — out, в трассе: нет, участков кода: 1, роль по документации: КР580ВВ55 #2 порт C #2 (уверенность: medium)
* `io_signature` var_port_06 — rw, в трассе: нет, участков кода: 1, роль по документации: КР580ВВ55 #2 порт B #2 (covox) (уверенность: medium)
* `io_signature` var_port_07 — rw, в трассе: нет, участков кода: 2, роль по документации: КР580ВВ55 #2 порт A #2 (уверенность: medium)
* `measure_sizes` — 406 расхождений(я) размера из 406 объектов (статус модуля: CANDIDATE)
* `pipeline` — вердикта нет (статус модуля: PARTIAL)
* `rdb_lint` — 1371 находок, 0 блокирующих (статус модуля: CANDIDATE)
* `strings_scan` — строковых прогонов: 1088, из них уже строкой в RDB 0, строк в RDB без прогона 0 (статус модуля: CANDIDATE)
* `strings_scan` str_6cd0 — koi8, 78 байт, с завершающим нулём: BRAVERY BONUSzВп00000zЬшLIVES BONUSzЫщX 1000 (уверенность: medium)
* `strings_scan` str_3d2e — koi8, 42 байт, с завершающим нулём: б5=Яца<Ац"=ЧЦбO=~#Еfoеума<яаА#ца<ЧДбb=F#~м (уверенность: medium)
* `strings_scan` str_7926 — ascii, 32 байт, с завершающим нулём: DLQ NA^ALA IGRY NAVMITE RUS/LAT� (уверенность: medium)
* `strings_scan` str_784f — koi8, 30 байт, с завершающим нулём: TEL. 99-26-23, KOD - (0572)ЪС1 (уверенность: medium)
* `strings_scan` str_242d — koi8, 29 байт, с завершающим нулём: ЪЪЪЪЪЧЪЧЪЩЪЩЪЩЪЩЪЩЪЩЪЧЪЧЪЪЪЪЪ (уверенность: medium)
* `strings_scan` str_246c — koi8, 29 байт, с завершающим нулём: ЪЪЪЪЪЧЪЧЪЩЪЩЪЩЪЩЪЩЪЩЪЧЪЧЪЪЪЪЪ (уверенность: medium)
* `strings_scan` str_39ff — ascii, 25 байт, с завершающим нулём: jvvvvvvvvdjdjdjdjvuwpwtut (уверенность: medium)
* `strings_scan` str_36f9 — koi8, 23 байт, с завершающим нулём: тЙтЙТЙТooooooooЙТЙТЙТЙТ (уверенность: medium)
* `strings_scan` str_2b50 — koi8, 18 байт, с завершающим нулём: nOnOnOnM||~~z~tlЩj (уверенность: medium)
* `strings_scan` str_6e15 — koi8, 18 байт, с завершающим нулём: у()*+,-./yР01ЪФ0:ъ (уверенность: medium)
* `symbolic_operand_lint` — clean: все адресные операнды именованные (статус модуля: CANDIDATE)
* `syntax_check` — clean: собралось без единой претензии (статус модуля: DERIVED)
* `table_shape` — разобрано диапазонов: 0, видов: нет (статус модуля: CANDIDATE)
* `toolchain_lint` — clean (статус модуля: CANDIDATE)

## Hypotheses

* `abi_scan` аргумент L у func_0103 (0x0103) — input: static: L читается до любой записи (DAD SP @0x0106) (уверенность: low)
* `abi_scan` аргумент B у func_0103 (0x0103) — output: static: последняя запись в теле (LXI B, 0600 @0x010D) (уверенность: low)
* `abi_scan` аргумент D у func_0103 (0x0103) — output: static: последняя запись в теле (LXI D, 0000 @0x0107) (уверенность: low)

## Unknowns

* `measure_sizes` `size-unknown` ×406 — размера в RDB нет; линейная разборка от 0x0100 даёт 3 байт(а) до 0x0102
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
