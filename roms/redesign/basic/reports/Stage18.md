# Stage 18 — Семантика функций: params / calls / links + rename (Phase C)

ТЗ Phase C / §Gate. Вход: у всех функций стоит `size` (Stage17), но нет ABI и
связей. Выход: **`params` у 233/233 функций**, **372 call-graph-связи**
(`debug_add_rdb_link`), **2 обоснованных rename**; round-trip **byte-for-byte**
(`make verify` diffs=0, `run_pipeline --from export_asm` **6/6**), `bad_names=0`.
Инструмент: `tools/stage18_function_semantics.py` (`--check` / `--apply`).

---

## 0. Источники доказательств (всё от отладчика, не догадки)

* `debug_get_function_context(addr)` → `instructions[]`, `callees`, `callers`,
  `memory_reads/writes`, `stack_behavior`;
* `analyze.abi_scan.static_signature(instructions)` → регистровый ABI по листингу
  тела: **вход** = регистр читается до любой записи; **выход** = пишется в конце;
  **saves** = PUSH∩POP (сохранение вызываемого, в параметры не идёт);
  `LDA/STA/LHLD/SHLD` с abs-адресом → `reads`/`writes` (аргумент через память).
  Это CANDIDATE-статика (ТЗ §20) — честный профиль, а не «у функции 2 параметра».

Связи: `callees` отладчика **плюс** цели `CALL/JMP/RST`, разобранные из текста
инструкций (call-graph ловит не все хвостовые `JMP`); каждая цель резолвится к
покрывающему RDB-объекту (`Rdb.at`) → `func → объект`.

---

## 1. Что записано

| артефакт | объём | где |
|---|---|---|
| `params` (in/out/saves) | **233/233** функций | свойство `params` |
| `calls` (резолвнутые цели) | **233/233** (у листьев-векторов пусто) | свойство `calls` + links |
| связей `debug_add_rdb_link` | **+372** (всего в RDB 471) | граф вызовов |
| `reads`/`writes` abs-ячеек | где обнаружены static-память-операнды | свойства `reads`/`writes` |
| rename | **2** (см. §3) | `debug_update_rdb_object` |

Примеры профилей (из `--check`):
* `func_rst_fetch_sep @0x0008` — `in[H,L] out[A,H,L]` (выборка+продвижение HL);
* `func_rst_advance_text @0x0010` — `in[H,L] out[A]`;
* `func_rst_cmp_dehl @0x0020` — `in[D,E,H,L] out[A]` (сравнение пар);
* `func_rst_fac_sign @0x0028` — `out[A]`, `reads=2` (LDA/STA-аргументы через память);
* `func_003e` — `saves[B]` (PUSH B … POP B) — сохраняемый регистр отделён от входов.

Диспетчер ↔ обработчики сшиты: у `func_cmd_dispatch`, `func_exec_dispatch` и
командных обработчиков `calls`/links указывают на целевые `func_cmd_*`/`func_*`
(в т.ч. через таблицы `data_cmd_table`/`data_dispatch_table`).

---

## 2. Свойства сохраняются в байтах? (round-trip)

Имена (`func_XXXX → func_<sem>`), свойства и связи **не двигают ни одного
байта**: экспортёр (`v06c-asm-export`) эмитит переходы по числовым адресам
(`JMP 2C7F`), а метки — из имён RDB; переименование меняет только текстовую
метку, не опкоды/операнды. Подтверждение оракулом: `make layout` → BYTE-FOR-BYTE
(17152/17152, расхождений 0); `make verify` → diffs=0.

---

## 3. Обоснованные rename (2)

| адрес | было | стало | доказательство (тело + вызовы) |
|---|---|---|---|
| `0x00A1` | `func_00a1` | **`func_print_packed_string`** | цикл `MOV A,M / ANI 7F / CALL 1C95(func_putchar) / MOV A,M / ORA A / INX H / JP loop` — печатает упакованную строку пока bit7=0; вызывается с `LXI H,msg` (напр. `0x2544`) |
| `0x031F` | `func_031f` | **`func_is_delimiter`** | веер `CPI 20/3A/2C/3B/22` + `RZ` на каждом — предикатор разделителей (пробел, `:`, `,`, `;`, `\"`) |

Оба имени валидны (`naming.validate`, bad_names=0) и подкреплены свойством
`semantic_evidence`.

---

## 4. Gate (сквозной протокол)

| шаг | результат |
|---|---|
| `stage18 --check` | 233 функций, 372 связи-кандидата, rename 2 |
| `stage18 --apply` (`RdbWriter.save()`) | actions 959: `property` 584, `link` 372, `rename` 2, `save` 1; objects 604, dirty=False |
| `make layout` | round-trip **BYTE-FOR-BYTE OK (17152/17152, 0)** |
| `make verify` | **new=17152 ref=17152 ; byte diffs=0** |
| `run_pipeline.sh basic --from export_asm` | **stages 6/6 SUCCESS** (export_asm, toolchain_lint, symbolic_operand_lint, syntax_check, roundtrip_verify, measure_sizes) |
| контроль RDB | params 233/233, calls 233/233, links 471, bad_names 0 |

---

## 5. Limitations (честно)

* **103 функций остаются `func_XXXX`**. Командные обработчики и диспетчеры
  именованы ещё на Stage2/5 (`func_cmd_*`, `func_exec_dispatch`, …); среди
  оставшихся — внутренние хелперы (float-арифметика `0x0E0D/0x12A6/0x16A3/0x3284`,
  загрузчик/инициализация, строковые/варийные сервисы), чья точная роль требует
  сосредоточенного реверс-инжиниринга с динамикой (bp+регистры на входе). По
  ТЗ §61 при нехватке доказательств `func_`-имя **не снимается**; это **не**
  блокирует ни 100% атрибуцию, ни наличие `size`+`params`+`calls` (критерий
  Phase E §51 выполнен для всех 233).
* `params` — **CANDIDATE-статика** по листингу тела (`abi_scan`), без динамического
  подтверждения значений регистров на входе: список вход/выход/сохраняемых
  обоснован, но контракт «кто кладёт DE» для отдельных рутин не доказан трассом.
  Динамика (`HitSampler`) — следующий заход при необходимости.
* `links` включают и хвостовые `JMP`/`RST`-цели (control-flow), не только `CALL`:
  граф отражает достижимость, что соответствует «сшить диспетчер ↔ обработчики».
* Семантика данных/переменных/строк и `asm/equates.asm` (page-zero карта) —
  **Phase D (Stage19)**.
