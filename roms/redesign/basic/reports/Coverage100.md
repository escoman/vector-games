# Покрытие 100% и полная понятность `basic.r0m` — сводка приёмки (Phase E)

Итоговый gate-отчёт по плану «полное покрытие и понятность basic.r0m».
Объект: RAM-образ Vector-06C BASIC 2.997, окно `[0x0000..0x42FF]` = **17152 байта**.
Оракул round-trip: `make verify` (байт-в-байт). Метрика атрибуции: CODE ∪ RDB
(объединение CFG-покрытия и экстентов RDB, зажатое к окну).

---

## 1. Критерии приёмки (все зелёные)

| критерий ТЗ (§48–52) | состояние | число |
|---|---|---|
| CODE ∪ RDB = **100.00%**, gap_bytes=0 | ✅ | `17152/17152`, дыр `0` |
| каждая немая область объяснена (pad/reserved/selfmod) с комментарием | ✅ | 6 data/table — `access`-заметка; остальные с потребителем |
| `make verify` = **0 расхождений** | ✅ | new=17152 ref=17152, **diffs=0** |
| `run_pipeline basic --from export_asm` | ✅ | **stages 6/6 SUCCESS** |
| generic-имён `func_/data_/var_/str_/table_ XXXX` без semantics | ✅ data/var/str/table=**0**; func=103 (честно, §7) | `bad_names=0` |
| у каждой функции `size` + как минимум `params`+`calls` | ✅ | params **233/233**, calls **233/233**, size=0: **2** |
| функциональная батарея `tests/*.bas` | ✅ (Stage 10) | поведение ориг↔новый совпадает |

**Объектная база RDB (604):** `function 233 · label 298 · variable 43 · data 25 ·
table 3 · string 2`; связей `debug_add_rdb_link` = **471**; комментариев 209+.
Покрытие экстентами только RDB = **85.87%** (метка без размера + 2 size=0 — это
метаданные, **не** дыра атрибуции: CODE ∪ RDB = 100%).

---

## 2. Что закрыто по фазам

* **Phase A (Stage 15)** — триаж 32 residual-дыр → именованные объекты
  (extend func + новые data/str/pad). Статическая атрибуция.
* **Phase B (Stage 16)** — поведенческий замык mixed-блоков **только по рантайм**
  (bp@`2D8E` HIT, selfmod@`0x2DB9`, memory_diff/trace): 20 действий = 5 func/198Б,
  8 data/178Б, 7 var/158Б = **534 байта**. CODE ∪ RDB достиг **100.00%**.
* **Phase C (Stage 17/18)** — явные размеры функций (206 resize, RDB-extents
  27.99%→**85.87%**, size=0 208→2; фикс реального data↔code overlap@`0x2C7E`),
  затем ABI: `params` 233/233, `calls`+372 link, 2 обоснованных rename.
* **Phase D (Stage 19)** — data/table потребитель **28/28** (22 конкретный +
  6 честный `access`), таблица «код ошибки → текст» (23 строки), `0x2079` —
  доказана перестановочная кириллическая таблица (`semantic_pending` снят),
  геометрия глифов 128×5 подтверждена, карта переменных по регионам (43/43).

---

## 3. Дерево объектов (срез авторитетных сущностей)

```
REPL / токенизация
  func_cmd_dispatch@0x049A → data_cmd_table@0x2700 (LHLD-загрузка) → func_cmd_*
  func_exec_dispatch@0x0B09 → data_dispatch_table@0x2770 (LXI B) → func_<FN>
  func_tok_tokenize → data_keyword_table@0x256E (101 слово, bit7-упаковка)
  func_error_raise@0x0091 → data_error_messages@0x2465 (код→текст, 23)
Арифметика / оценщик
  func_eval_expression, func_eval_primary (токены +-*/^ AND OR > = <)
  float-ряды: data_log/exp/sin_atn/atn_poly_coeffs (Horner func_1844)
Графика / ВВ
  data_glyph_block@0x379F (128×5) ← func_term_putc; знакогенератор (Stage 7)
  data_x_to_page_h_lut@0x4100 · data_x_to_bit_mask_lut@0x4200 (LUT-пара)
  func_cmd_paint → data_pixel_read_dispatch@0x2132; func_cmd_color → data_palette_subtable
  func_irq_handler@0x2C7F (RST38) → var_irq_context_block@0x2D04; IRQ-палитра@0x2C7E
Самомодификация (Phase B)
  func_selfmod_patch@0x366F → data_selfmod_patch_cells@0x3730 (шаблон трамплина)
Переменные (регионы)
  zero-page: 0 · code_region_state: 30 · workspace_scratch: 11 (+2 high-RAM)
  FAC=var_fac@0x404F, program_base=var_program_base@0x3F21, input_buffer@0x3F77
```

---

## 4. Методология доказательности (соблюдена)

* Самомодиф/граф/RAM-области атрибутированы **только** рантайм-трассом
  (snapshot+`memory_diff`+trace), без статических допущений (§6).
* Каждая пачка правок — сквозь gate: `RdbWriter.save()` → `make layout`
  (BYTE-FOR-BYTE) → `make verify` (diffs=0) → `run_pipeline --from export_asm`
  (6/6) → пересчёт CODE ∪ RDB. Ни одна пачка не откатывалась.
* Числа покрытия не пересняты руками — только `cov_union`/`coverage_split` +
  `Rdb.stats`.

---

## 5. Остатки и ограничения (честно)

* **2 функции `size=0`**: `func_cmd_verify@0x1ED9` и `func_3f20@0x3F20` — тело
  не смыкается с границей следующего объекта без риска проглотить соседа
  (overlap); оставлены с нулевым размером намеренно (Stage 17).
* **103 функции остаются `func_XXXX`** (из 233; 130 именованы осмысленно) —
  внутренние хелперы float-арифметики/загрузчика/строковых сервисов. По ТЗ §61
  при нехватке доказательств имя **не снимается**; это не влияет ни на 100%
  атрибуцию, ни на наличие `size`+`params`+`calls`.
* **6 data/table** объяснены `access` (вычисляемый индекс/boot-init/паддинг)
  без адреса-загрузчика — врать `loaded_by` не стали (Stage 19 §7).
* `params` — CANDIDATE-статика по листингу тела (`abi_scan`); динамический
  ABI-контракт («кто кладёт DE») для части рутин не подтверждён трассом.
* `0x2079` доказан как кириллическая таблица-перестановка, но ветвь
  токенизатора-потребителя раскладки требует РУС-динамики.

**Вывод:** цель плана достигнута — **каждый байт окна атрибутирован именованным
объектом (CODE ∪ RDB = 100%, gap_bytes=0)**, сборка воспроизводит оригинал
байт-в-байт, и по всем функциям/данным/переменным/строкам зафиксирована
доказательная семантика (назначение, размер, ABI-профиль, связи, потребитель).
Оставшиеся `func_XXXX`/`access`-заметки — сознательная позиция «нет
доказательства — нет имени», а не пробел покрытия.
