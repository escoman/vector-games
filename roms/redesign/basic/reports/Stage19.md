# Stage 19 — Семантика данных / переменных / строк (Phase D)

ТЗ Phase D. Вход: CODE ∪ RDB = 100%, generic-имён `data_/var_/str_/table_` нет,
у всех функций `size` + `params`/`calls` (Stage 17/18). Выход: у **каждого**
data/table-объекта доказан потребитель (`loaded_by`/`used_by`/`consumer`) либо
честная заметка об индексации; распакована таблица «код ошибки → текст»; снят
`semantic_pending` у `0x2079`; проверена геометрия глифов; построена живая
карта переменных по регионам. Round-trip **byte-for-byte** (`make verify`
diffs=0, `run_pipeline --from export_asm` **6/6**). Инструмент:
`tools/stage19_data_semantics.py` (`--check` / `--apply`, только свойства и
комментарии — байты не двигаются).

---

## 0. Метод доказательств (всё детерминировано из ROM + RDB, без догадок)

Для data/table без ранее зафиксированного потребителя собираем два независимых
следa:

1. **Входящие связи RDB** — `debug_add_rdb_link` (Stage 18) и свойства функций
   `reads`/`writes`, чьи абсолю́тные адреса накрывают объект → `used_by`.
2. **Скан образа на абсолю́тные ссылки 16-битным операндом**: `LXI B/D/H/SP,addr`
   (`01/11/21/31`), `LHLD/LDA/STA/SHLD addr` (`2A/3A/32/22`). Это то, чем таблицу
   реально грузят в регистровую пару. Каждая ссылка атрибутируется покрывающей
   функции (`Rdb.at`) → `loaded_by` вида `LXI H@0x20EF(func_cmd_paint)`.

Где ни то, ни другое не срабатывает — обращение идёт через **вычисляемый
указатель/индекс** (диспетчеры по `PCHL`, boot-init, паддинг): пишем честную
заметку `access`, не выдумывая адрес.

---

## 1. Data/table: потребитель закрыт для 28/28

| адрес | объект | доказательство |
|---|---|---|
| `0x0398` | `data_0398_table` | `loaded_by` = `LXI H@0x037C(func_0378)` |
| `0x2132` | `data_pixel_read_dispatch` | `loaded_by` = `LXI H@0x20EF(func_cmd_paint)` |
| `0x2465` | `data_error_messages` | `loaded_by` = `LXI H@0x0091(func_error_raise)` |
| `0x256E` | `data_keyword_table` | `loaded_by` = `LXI D@0x1A2F(func_1a01)`; `used_by` = `func_tok_tokenize`, `func_cmd_list` |
| `0x2700` | `data_cmd_table` | `loaded_by` = `LHLD@0x04C0(func_cmd_dispatch)`; `used_by` = `func_cmd_dispatch` |
| `0x2770` | `data_dispatch_table` | `loaded_by` = `LXI B@0x0B09(func_exec_dispatch)`; `used_by` = `func_exec_dispatch` |
| `0x2C6F` | `data_palette_subtable` | `used_by` = `func_cmd_color` |
| `0x2C7E` | `data_irq_palette_table` | `used_by` = `func_irq_palette_refresh` |
| `0x2D7E` | `data_graph_op_table` | `loaded_by` = `LXI H@0x2D32` |
| `0x2F4F` | `data_2f4f_table` | `loaded_by` = `LXI H@0x2F2F(func_2ebc)` |
| `0x3730` | `data_selfmod_patch_cells` | `used_by` = `func_selfmod_patch`, `func_3722_trampoline` |
| `0x379F` | `data_glyph_block` | `loaded_by` = `LXI H@0x199C/0x2DF5/0x3D50`; `used_by` = `func_term_putc` |
| `0x3D03` | `data_ctrl_char_seq` | `loaded_by` = `LXI H@0x3DDF(func_3ddf)` |
| `0x40FC` | `data_render_lut_preamble` | `loaded_by` = `LXI H@0x0B3A`; `used_by` = `func_cmd_get` |

Плюс 4 float-ряда (Stage 14) и LUT-пара/маски с уже готовыми `consumer`.
Итого **22 объекта с конкретным потребителем**; **6 с честной заметкой `access`**
(индексация через вычисляемый указатель / boot-init / паддинг):
`data_26fc_pad`, `data_dispatch_extension`, `data_2e5d_table`, `data_3518_pad`,
`data_workspace_init`, `data_float_pow2_coeffs`. Ни один data/table не остался
без объяснения.

---

## 2. Таблица «код ошибки → текст» (`data_error_messages` @ 0x2465)

Кодировка «bit7 = последний символ сообщения» (как в таблице ключевых слов).
Распаковка даёт `codes` — 23 упорядоченные строки; код = порядковый номер.
Первые 19 — сообщения об ошибках (транслит латиницей: `~`=ч, `q`=я, `{`=о,
`x`=ш …); 20..23 — промпты REPL.

| код | текст | код | текст |
|---|---|---|---|
| 1 | NEXT bez FOR | 11 | delenie na nolx |
| 2 | sintaksi~eskaq | 12 | tolxko w programme |
| 3 | RETURN bez GOSUB | 13 | nesootw.dannyh |
| 4 | malo dannyh w DATA | 14 | mal bufer |
| 5 | newernyj argument | 15 | X$>255 |
| 6 | perepolnenie | 16 | slovno |
| 7 | net pamqti | 17 | nelxzq |
| 8 | net stroki | 18 | net DEF |
| 9 | newernyj indeks | 19 | o{ibka |
| 10 | powtornoe opisanie | 20..23 | `\r\n=>\r\n`, `\r\nstop`, ` w stroke `, `\r\nprogramma: ` |

Потребитель зафиксирован: `func_error_raise@0x0091` грузит `LXI H,2465h`.

---

## 3. `0x2079` — кириллица: `semantic_pending` снят

Гипотеза «кириллическое текстовое сообщение» **опровергнута доказательно**.
Под схемой `а-я@0xA1` (без `ё`) диапазон байт даёт: **30 из 32 букв а-я
встречаются РОВНО по разу**, порядок не азбучный, плюс служебные/пунктуационные
коды `0xC1`, `0xCD`, `0x5F('_')`, `0x2E('.')`. Декодированная последовательность
(`decoded_seq`):

```
я абчдехгцйклмнопр[?]стуфзвэьищюъш_ ? v .
```

Перестановка полного алфавита ⇒ это **кодовая таблица-маппинг (раскладка)**, а
не проза; потребитель — путь РУС/ЛАТ токенизатора (Stage 5; знакоместо per
Stage 7: глифы 96..126 = кириллица). Тип `string` оставлен ради минимального
churn, но комментарий фиксирует природу «ближе к таблице-маппингу». Свойства:
`semantic=CONFIRMED…`, `semantic_pending=no`, `decode_scheme`, `decoded_seq`.

---

## 4. `data_glyph_block` @ 0x379F — геометрия подтверждена

`verified_shape = 128 глифов × 5 байт = 640 (OK)`; побайтовая сверка с образом
(`img[0x379F:0x3A1F]`, длина кратна 5). Сверка сетки с `glyphs_chart.png` /
картой Stage 7 (полная перестановка 96..126, без `Ъ`/`Ё`).

---

## 5. Карта переменных по регионам (page-zero / workspace)

Каждой `var_` присвоено `region` (живой запрос к RDB; существовавшие значения
не перезаписаны). Раскладка: **zero-page (0x00–0xFF) — 0 переменных** — важная
находка: этот BASIC **не использует классический zero-page-блок**; состояние
размазано по кодовому region и высокому workspace.

| регион | число | пример |
|---|---:|---|
| `code_region_state` (0x0100–0x3CFF, состояние среди кода/selfmod) | **30** | `var_stmt_ptr@0x0464`, `var_fac`-adj, `var_irq_frame_counter@0x3A20`, `var_graph_xy@0x2B56` |
| `workspace_scratch` (0x3D00–0x42FF) | **11** | `var_program_base@0x3F21`, `var_input_buffer@0x3F77`, `var_fac@0x404F`, `var_workspace_scratch@0x3E00` |
| высокий RAM (уже было `region`) | **2** | `var_scratch_high@0x3A23`, `var_scratch_tail@0x3F87` |

Workspace-карта (`region=workspace_scratch`):

```
0x3DFC var_string_alloc_ptr        4   указатель аллокации строк
0x3E00 var_workspace_scratch       104 временный scratch (Phase B: boot-init нули)
0x3F21 var_program_base            2   база программы (текст BASIC)
0x3F76 var_input_delim             1   текущий разделитель INPUT
0x3F77 var_input_buffer            16  буфер строки ввода
0x4027 var_paint_4027              1   байт состояния PAINT
0x4028 var_paint_field             1   текущий цвет заполнения
0x402E var_workspace_text_scratch  31  текстовый scratch
0x404D var_text_ptr                2   указатель текстового потока
0x404F var_fac                      4   Floating ACCumulator (частотный регистр оценщика)
0x4053 var_fac_scratch             16  scratch вокруг FAC
```

### Почему карта НЕ в `asm/equates.asm`

ТЗ §44 просит page-zero карту в `equates.asm`. Проверено (`stage9_asm_layout.py`
`gen_equates`): `equates.asm` намеренно содержит только 19 аппаратных EQU и
**исключает** `var_*/data_*/func_*`, т.к. те уже эмитятся **метками** в `code.asm`.
Дублирующий `.EQU` дал бы **колизию имён → падение сборки**. Поэтому карта
реализована как (а) живые свойства `region` в RDB и (б) этот отчёт — переносимый
справочник без риска для round-trip. Отход от буквальной формулировки ТЗ
обоснован доказательством (сборка остаётся BYTE-FOR-BYTE).

---

## 6. Gate (сквозной протокол)

| шаг | результат |
|---|---|
| `stage19 --check` | объектов=23→(после var-прохода) свойств=55, коммент=1 |
| `stage19 --apply` (`RdbWriter.save()`) | actions 57: property 55, comment 1, save 1; objects 604, dirty=False |
| `make layout` | round-trip **BYTE-FOR-BYTE OK (17152/17152, 0)** |
| `make verify` | **new=17152 ref=17152 ; byte diffs=0** |
| `run_pipeline.sh basic --from export_asm` | **stages 6/6 SUCCESS** |
| контроль RDB | CODE∪RDB **100.00%** (gap_bytes=0); data/table с потребителем **28/28**; vars с `region` **43/43**; `bad_names=0` |

---

## 7. Limitations (честно)

* **6 data/table** объяснены как `access` (индексация через вычисляемый
  указатель/boot-init/паддинг) без конкретного адреса-загрузчика: `data_26fc_pad`,
  `data_dispatch_extension` (самомодиф-хвост диспетчера), `data_2e5d_table`,
  `data_3518_pad`, `data_workspace_init` (boot-обнуляемый scratch),
  `data_float_pow2_coeffs` (ряд внутри selfmod-окна). Природа «данные» доказана
  (Phase A/B), адресный потребитель — нет; врать `loaded_by` не стали.
* `0x2079` доказан как **перестановочная кириллическая таблица** (30/32 букв по
  разу), но точный потребитель раскладки (какая ветвь токенизатора её читает)
  требует динамического трасса РУС-режима — зафиксировано в комментарии, тип
  `string` сохранён ради стабильности сборки.
* Транслит сообщений — штатная латиница ROM-а (`~`/`q`/`{`/`x`); настоящий
  кириллический вывод идёт через знакогенератор Stage 7, а не через `0x2465`.
* `params` функций остались CANDIDATE-статикой (Stage 18); динамическое
  подтверждение ABI не входило в Phase D.
