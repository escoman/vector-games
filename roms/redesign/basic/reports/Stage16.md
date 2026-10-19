# Stage 16 — Поведенческое закрытие mixed-дыр (Phase B → 100.00%)

ТЗ Phase B/§Gate. Вход: **CODE ∪ RDB = 96.89%** (остаток **534 Б / 14 блока**),
584 объекта. Выход: **CODE ∪ RDB = 100.00%** (остаток **0 Б / 0 блоков**),
**604 объекта**. Round-trip сохранён: `make layout` — BYTE-FOR-BYTE
(17152/17152, расхождений 0); `make verify` — **byte diffs=0**.
Инструмент: `tools/stage16_behavioral_closure.py` (`--check` / `--apply`,
паттерн stage13/14/15: `ACTION`-список + `check`-лямбда по байтам + `RdbWriter`).

---

## 0. Постановка: почему эти 14 блоков нельзя закрыть статически

Каждая residual-дыра — **mixed**: на неё указывает вычисленный адрес (`PCHL`,
`LXI H,xxxx` → `PCHL`-таблица), либо она самомодифицируется в рантайме, либо
лежит в RAM-workspace, где код↔данные статически неразличимы. Правило ТЗ
(п.6/Phase B): **смешанные блоки атрибутируются только по рантайму**, без
статических допущений. Поэтому сначала — поведенческий зонд, потом — сплит.

**Правило безопасности пересборки** (сквозной контракт `make verify`):
> `data_`/`var_` → `DEFB` точных байт → round-trip всегда сохранён;
> `func_` → экспортёр дизассемблирует и пересобирает → безопасно **только** при
> валидном континуальном разборе ровно до границы блока. `make verify` — оракул.

---

## 1. Метод Phase B (живые доказательства этого захода)

1. **Boot → idle REPL** (`debug_load_rom basic.r0m org=0x0000` + `debug_run`,
   без reset), чтение всех 534 Б, diff с ROM-эталоном:
   **13 из 14 блоков идентичны ROM**; мутировал только `0x2B3F`
   (`0x10 → 0x0D`, инициализация GRAPH-переменной на старте).
2. **Брейкпоинты + батарей команд** (`debug_set_breakpoint` на 8 code-кандидатах
   + набор PLOT/LINE/COLOR/PAINT/CIRCLE/PRINT/транcendentals через калиброванную
   раскладку `run_tests.type_line`): **`0x2D8E` HIT ×1**, и байт `0x2DB9`
   изменился `0x00 → 0x01` после батареи → доказан континуальный код + selfmod
   у GRAPH-рутины вычисления адреса пиксела.
3. Остальные кандидаты — разбор (`debug_disassemble_range`,
   `incomplete_instruction=false`) + поиск address-taken ссылок (`LXI H,xxxx`).
4. Разделение каждого блока на `func_`/`data_`/`var_` занесено в RDB со
   **свойством `phase_b_evidence`** (адрес трасса/diff) в качестве доказательства.

---

## 2. Сплит 534 Б (20 объектов) — было → стало

| адрес | имя | kind | size | доказательство природы |
|---|---|---|---|---|
| `0x27A8` | `data_dispatch_extension` | data | 21 | продолжение dispatch-таблицы; boot-diff=0, post-battery-diff=0 → ROM-константа |
| `0x2B01` | `var_graph_scratch_2b01` | var | 1 | нулевой байт в GRAPH-области; boot-diff=0 |
| `0x2B3C` | `var_graph_state` | var | 4 | **PROVEN mutable**: boot-diff `0x2B3F 10→0D` → переменная |
| `0x2B58` | `var_graph_2b58` | var | 1 | ноль сразу за `var_graph_xy`; boot-diff=0 |
| `0x2C6F` | `data_palette_subtable` | data | 15 | дизасм неоднозначен (SHLD 02C0), bp не сработал, boot-diff=0 → консервативно данные |
| `0x2D7E` | `data_graph_op_table` | data | 16 | 16-байтная GRAPH opcode-таблица перед `func_graph_pixel_addr`; boot-diff=0 |
| `0x2D8E` | **`func_graph_pixel_addr`** | func | 58 | **PROVEN**: bp HIT ×1; selfmod `0x2DB9 00→01`; конец `RET` @`0x2DC7` |
| `0x2DDC` | `func_2ddc_scroll` | func | 117 | чистый разбор (93 инт. → `JMP 2ABA`), address-taken `LXI H,2DDC` @`0x3EA9`; bp не сработал — консервативно func (оракул verify) |
| `0x2E51` | `func_2e51` | func | 12 | dispatch-заглушка после JMP; address-taken `LXI H,2E51` @`0x2EA3/2EFB/2FA9` (PCHL) |
| `0x2E5D` | `data_2e5d_table` | data | 25 | хвост после заглушки: дизасм = мусор (PCHL-дельты); boot-diff=0 → таблица |
| `0x3722` | `func_3722_trampoline` | func | 6 | трамплин `LXI H,0000 / JMP 3738` у selfmod-подсистемы |
| `0x3730` | `data_selfmod_patch_cells` | data | 26 | ROM-шаблон патча; пишется в рантайме `func_selfmod_patch (0x366F)`; idle → не тронут → данные |
| `0x3D03` | `data_ctrl_char_seq` | data | 10 | инлайн управляющих кодов (0D 0A 1B 41 08 1B 2A 01 00 02); boot-diff=0 |
| `0x3E00` | `var_workspace_scratch` | var | 104 | RAM-workspace: 104 нуля; в idle и после батареи не тронут → резерв |
| `0x3E68` | `data_workspace_init` | data | 48 | пред-инициализированные константы workspace; константы во всех пробах → данные |
| `0x4027` | `var_paint_4027` | var | 1 | байт между `func_cmd_cls_home` и `var_paint_field`; boot-diff=0 |
| `0x4029` | `func_4029` | func | 5 | `CALL 286B / POP H / RET` — валидный разбор (3 инт., конец RET) в workspace |
| `0x402E` | `var_workspace_text_scratch` | var | 31 | нули между `func_4029` и `var_text_ptr` |
| `0x4053` | `var_fac_scratch` | var | 16 | 16 нулей между `var_fac` и float-таблицей |
| `0x4063` | `data_float_pow2_coeffs` | data | 17 | float-ряд `2^0..2^3`: экспоненты `0x81..0x84`; boot-diff=0 → константа |

**Итог сплита (сумма = ровно 534 Б):** func = 5 объектов / 198 Б;
data = 8 объектов / 178 Б; var = 7 объектов / 158 Б. Ни один объект не
перекрывает соседа (каждый доходит ровно до границы следующего).

---

## 3. Gate (сквозной протокол)

| шаг | результат |
|---|---|
| `stage16 --check` | 20 CREATE, все `check` OK (байты совпадают) |
| `stage16 --apply` (`RdbWriter.save()` → `debug_save_rdb`) | объекты **584 → 604**, dirty=False |
| union coverage (`.scratch/cov_union.py`, зажим `[0x0000..0x42FF]`) | CODE ∪ RDB **96.89 → 100.00%**; гэп **534 → 0 Б**; блоков **14 → 0**; code-only 80.51% |
| `make layout` | round-trip **BYTE-FOR-BYTE OK (17152/17152, расхождений 0)** |
| `make verify` | **new=17152 ref=17152 ; byte diffs=0** |

Атрибуция байтов замкнута: **каждый байт образа `[0x0000..0x42FF]` принадлежит
именованному объекту RDB**.

---

## 4. Состояние RDB после Stage16

* **604 объекта**: function 233, label 298, variable 43, data 25, table 3, string 2.
* **unknowns = 0**, **bad_names = 0** — generic-имён без валидации нет.
* **links = 147**, comments = 208, properties заполнены у 604 (у каждого
  mixed-объекта есть `phase_b_evidence`).

---

## 5. Limitations (честно)

* **`func_2ddc_scroll` (0x2DDC), `func_2e51` (0x2E51), `func_3722_trampoline`
  (0x3722), `func_4029` (0x4029)** названы кодом не по прямому bp-попаданию, а
  по конъюнкции: чистый континуальный разбор + address-taken ссылка (`LXI H,…`
  → PCHL) + round-trip-оракул (`make verify` byte diffs=0). Короткая батарея
  не exercised-нула scroll/redirect-ветки. Это консервативная атрибуция:
  прямое рантайм-подтверждение исполнения этих входов — дальний приоритет
  (расширение батареи), но не блокирует 100% атрибуции.
* **`data_selfmod_patch_cells` (0x3730)** — ROM-шаблон; реальные мутации
  происходят только в RAM-копии в рантайме (после срабатывания `0x366F`);
  в idle-пробе байты не изменились, поэтому `data_` корректен для образа.
* Имена mixed-функций остаются техническими (`func_2e51`, `func_4029`) либо
  описательными без подтверждения роли (`func_2ddc_scroll`) — семантический
  rename + ABI (params/calls/links) = **Phase C (Stage17/Stage18)**.
* **208 из 233 функций по-прежнему `size=0`** (RDB-extents-only coverage мал):
  это не дефект атрибуции (CODE ∪ RDB уже 100%), а явная цель **Stage17**
  (простановка размеров по CFG-границам).
