# utils/analyze — детерминированный Python-фреймворк анализа ROM Vector-06C

Общий (не привязанный к конкретному ROM) набор скриптов, которые собирают
**доказательства** о поведении ROM через отладчик и раскладывают их по отчёту.
Фреймворк намеренно узкий по полномочиям:

* **Python** читает/сравнивает байты, считает, сортирует, ищет, строит
  интервалы и графики, оформляет отчёт.
* **Семантику** (что код *значит*) назначает AI. Python выдаёт **кандидатов**,
  никогда не повышая их до фактов самостоятельно.
* Единственный канал к эмулятору/отладчику — MCP-сервер **`v06c-mcp`**.
  Официальный CLI `v06c-asm-export` разрешён как внешний инструмент для
  экспорта ASM. Своих декодеров опкодов, дизассемблеров и CFG фреймворк не
  строит.

## Границы A/B/C (что модуль имеет право утверждать)

| слой | кто | пример |
|---|---|---|
| **A. Facts** | Python, проверяемо байт-в-байт | совпадение образа с пересборкой, совпадение VRAM-кредитов, покрытие |
| **B. Inferences / Candidates** | Python находит, с пометкой | сигнатуры ABI, форма таблиц, строки, вызываемые области |
| **C. Semantics** | только AI/человек | «эта функция рисует спрайт» |

Конверт результата несёт `status`, по которому [`report_gen.py`](report_gen.py)
раскладывает находки по разделам отчёта. Модуль без статуса попадает в
«неотнесённое» — это дефект модуля, а не тихая подмена.

## Зависимости

* **Python 3.6+**, только стандартная библиотека (плюс опции ниже).
* **Pillow** — нужен единственному модулю [`glyph_scan.py`](glyph_scan.py) для
  отрисовки растровой сетки глифов в PNG.
* **`v06c-mcp`** — MCP-сервер отладчика (stdio JSON-RPC). Путь по умолчанию
  задаётся переменной окружения `V06C_MCP` (или аргументом `--server`); в этом
  окружении — `/home/alexey/Projects/vector-debugger/debugger/build/v06c-mcp`.
* **`v06c-asm-export`** — экспорт ASM; нужен [`export_asm.py`](export_asm.py) и
  [`roundtrip_verify.py`](roundtrip_verify.py).
* **`z88dk-z80asm`** — сборка экспорта для проверок; лежит в
  `z88dk/bin/z88dk-z80asm` этого репозитория.

Без сервера и внешних бинарников работает всё, что читает файлы
([`rdb_lint.py`](rdb_lint.py), [`music2midi.py`](music2midi.py) в offline-режиме,
разбор RDB), а интеграционные тесты корректно скипаются.

## Быстрый старт: один прогон

Стандартный вход — launcher [`run_pipeline.sh`](run_pipeline.sh) (ТЗ Standard
Pipeline Launcher). ROM выбирается **по короткому профилю**, пути ROM/RDB/config
launcher резолвит сам:

```bash
./utils/analyze/run_pipeline.sh putup            # apply-прогон профиля putup
./utils/analyze/run_pipeline.sh riseout --resume # продолжить после прерывания
./utils/analyze/run_pipeline.sh testay --dry-run --verbose
```

Профили (`riseout` / `putup` / `testay`) — единственное место, где launcher
знает про конкретный ROM (таблица в начале скрипта). Добавить новую ROM = одна
запись в таблице + `roms/redesign/<rom>/pipeline.json`; `pipeline.py` не
трогается (§30). Все флаги после имени профиля уходят в `pipeline.py` **без
изменений** — launcher их не интерпретирует (§3/§4/§20): `--apply`,
`--dry-run`, `--resume`, `--clean`, `--only`, `--from`, `--until`, `--verbose`
и любые другие переключатели пайплайна.

Обратная совместимость: если первый аргумент — путь к `*.rom`/`*.ROM`/`*.bin`,
launcher работает в режиме явного пути (config не подключается):

```bash
./utils/analyze/run_pipeline.sh roms/redesign/putup/src/putup.rom --dry-run
```

Перед запуском launcher выводит сводку `ROM / RDB / CONFIG / ARGS`
(в stderr — чтобы stdout остался чистым под `--json`) и проверяет обязательные
файлы. Отсутствующий `pipeline.json` профиля или ROM — ошибка без запуска
пайплайна; **отсутствующий RDB ошибкой не является** (свежий образ родит его
первым `debug_save_rdb` внутри `seed_rdb`). Коды выхода launcher'а: `0` = код
`pipeline.py`, `1` = usage/нет python3, `2` = неизвестный профиль, `3` = нет
обязательного файла. Ctrl-C (`SIGINT`) пробрасывается в `pipeline.py`
нетронутым (controlled shutdown/checkpoint). Проверки — `test_launcher.py`.

Эквивалентный ручной запуск со всеми параметрами:

```bash
cd /home/alexey/Projects/vector-games
export PYTHONPATH=utils
python3 utils/analyze/cli.py pipeline \
  --rom   roms/redesign/putup/src/putup.rom \
  --rdb   roms/redesign/putup/src/putup.rdb \
  --spec  roms/redesign/putup/tools/music_spec.json \
  --glyph-address 0x2706 --runtime \
  --results .scratch/results/putup --export .scratch/export/putup \
  --out .scratch/Stage13.md --stage 13 --goal "Разбор putup.rom" --json
```

Полезные переключатели `pipeline`:

| флаг | смысл |
|---|---|
| *(без флагов)* | **apply**: мутации RDB разрешены, `seed_rdb` реально сеет и сохраняет |
| `--dry-run` | строго read-only: ни одной мутации RDB и ни одного `debug_save_rdb` |
| `--apply` | явный apply (семантически = дефолт; конфликт с `--dry-run` — ошибка) |
| `--resume` | продолжить с последнего подтверждённого checkpoint (валидация ROM/RDB/capabilities — до любого анализа) |
| `--clean` | удалить только checkpoint (`pipeline_state.json`); RDB/ROM/отчёты не трогаются |
| `--only a,b` (повторяемо) | прогнать отдельные stages; предки подтягиваются автоматически |
| `--from` / `--until` | срез канонического порядка (включительно) |
| `--config FILE` | JSON-конфиг: разрешённые stages + persistence-политика |
| `--annotations FILE` | stage `apply_annotations` с JSON-аннотациями (см. ниже) |
| `--reports DIR` | куда писать `pipeline.md`/`pipeline.json`/checkpoint (по умолчанию = `--results`) |
| `--list` | показать topo-порядок stages и выйти |
| `--runtime` | разрешить модулям читать RUNTIME-байты через MCP (нужно `music2midi` с runtime-источником) |
| `--glyph-address` | адрес блока глифов; без него шаг `glyph_scan` пропускается (адрес ROM-специфичен) |
| `--no-cache` | не использовать и не писать кэш доказательств |
| `--spec` | `music_spec.json` для шага `music2midi`; без него шаг пропускается |

Выход — сводка `{steps, succeeded, failed, skipped, exit_nonzero, status,
mode, total_mcp_calls, wall_ms, cache, statistics, report, results,
checkpoint, pipeline_report, pipeline_json}`. Код возврата `0`, если ни один
stage не упал и не было фатальной остановки (ненулевой код линтера — это
находка, не крах: он идёт в `exit_nonzero`, а не в `failed`).

## Точка входа `cli.py`

Модули — часть пакета `analyze` (импорты вида `from analyze.x`), поэтому прямой
запуск файла не работает. Диспетчер подкладывает `utils/` в `sys.path`:

```bash
python3 utils/analyze/cli.py <команда> [параметры…]   # == python3 -m analyze.<команда>
python3 utils/analyze/cli.py <команда> --help
```

Команды сгруппированы по слоям анализа:

### Доступ и доказательства
| модуль | назначение | вход | выход |
|---|---|---|---|
| `mcp_session.py` | клиент MCP, общий сеанс, счётчики, разбор адреса, конверт | — | библиотека |
| `capabilities.py` | `tools/list`, какие инструменты реально есть | сервер | список инструментов |
| `evidence_cache.py` | кэш ответов сервера + provenance (конверты) | сеанс | `evidence/*.json`, `index.jsonl` |

### Статика и рантайм
| модуль | назначение | тип вывода |
|---|---|---|
| `probe.py` | каноническая чистая загрузка ROM, базовые факты | Fact (boot OK) |
| `coverage.py` | покрытие кода, слепые зоны (машинный payload: blind_targets/reachable/gaps/fixpoint) | Fact/Partial |
| `disassembly.py` | запрос дизасемблера у сервера (без своего декодера) | Evidence |
| `seed_rdb.py` | первичный посев RDB: entry → analyze → функции/метки/ссылки до fixpoint; `--apply --save-every N` — пачки с save+checkpoint | Fact (PASS) / Candidate |
| `apply_annotations.py` | нанесение JSON-аннотаций на RDB (валидация до первого изменения, идемпотентно, пачками) | Fact (PASS) / Candidate |
| `rdb.py` / `naming.py` | модель RDB (включая aliases); единые шаблоны имён (§28) и технические имена затравок | библиотека |
| `rdb_lint.py` | целостность RDB (пересечения, висячие ссылки, имена) | Findings (rc=1 при находках) |
| `memory_diff.py` | «рантайм не подменил образ» (§13) | Fact/Findings |
| `io_signature.py` | порт-сигнатуры I/O | Candidate |
| `abi_scan.py` | кандидаты соглашений вызова | Candidate |
| `strings_scan.py` | строки KOI8/RUS | Candidate |
| `table_shape.py` | форма данных/таблиц | Candidate |
| `glyph_scan.py` | растровая сетка глифов → PNG | Candidate |
| `vram_credits.py` | предсказание VRAM-картинки против реальности (§23) | Fact (MATCHED) |

### Экспорт и проверка сборки
| модуль | назначение |
|---|---|
| `export_asm.py` | экспорт ROM в ASM через `v06c-asm-export` (+ сборка `z80asm`) |
| `toolchain_lint.py` | линтер собранного ASM (строгие литералы 8080) |
| `syntax_check.py` | проверка синтаксиса `z88dk-z80asm` |
| `symbolic_operand_lint.py` | находки символических операндов в экспорте |
| `roundtrip_verify.py` | побайтовое кольцо ROM→ASM→бинарь→ROM (0 расхождений = Fact) |
| `measure_sizes.py` | размеры объектов против RDB |

### Музыка, отчёт, сервис
| модуль | назначение |
|---|---|
| `music2midi.py` | ROM-байтокод → MIDI по `music_spec.json` |
| `report_gen.py` | сборка отчёта §29 из JSON-результатов + сводка §30 |
| `pipeline.py` | стандартный исполнитель: stages, DAG, persistence, resume |
| `pipeline_state.py` | checkpoint (атомарная запись), verify сохранённого RDB, валидация resume |
| `clear_cache.py` | очистка/прореживание кэша доказательств |

## Первичный анализ и посев RDB (Stage 6.27)

Команда `seed_rdb` выполняет детерминированный **первичный** статический
анализ ROM и сеёт результат в RDB — без участия AI и без ручных правок.
Единственный источник семантики lower-level — отладчик: Python **не** имеет
своего 8080-декодера, CFG-построителя или дизассемблера (архитектурный
запрет ТЗ §48); все кандидаты рождаются из ответов `debug_analyze_code` и
`debug_coverage_report`.

**Поток (Primary static analysis → RDB seeding → Coverage fixpoint):**

1. точки входа (по умолчанию `--org`, повторяемо `--entry`) → `function`-кандидат;
2. `debug_analyze_code` по активным адресам → ссылки: `CALL`/`RST` →
   `function`, `JMP`/`JCC` → `label` (приоритет: function > label для одного
   адреса);
3. `build_plan` — чистая детерминированная функция (сортированные адреса,
   ссылки, кандидаты; тот же вход → тот же план); существующие объекты
   RDB **всегда важнее** кандидатов: ни переименования, ни перезаписи (ТЗ §19);
4. план применяется через `RdbWriter` (единственный канал записи, ТЗ §21),
   затем пересчёт покрытия (`coverage.py`), слепые цели внутри дыр
   досеваются метками — и цикл повторяется, пока появляется хоть один новый
   активный адрес (**fixpoint**, ТЗ §26–§27);
5. сохраняются только размеры, известные отладчику; иначе `size = 0`
   («не выдумываем», ТЗ §25).

**Object model (явно, ТЗ §14–§15):**

```text
ONE ADDRESS = ONE RDB OBJECT   — один адрес, один объект; ветвление внутри
                                 функции — конфликт, а не новый объект
MULTIPLE NAMES = ALIASES       — вторичные имена живут в property `aliases`
                                 (sorted, без дубликатов, первичное имя не
                                 дублируется), а не в отдельных объектах
```

`RdbWriter.add_alias/remove_alias/aliases` — API алиасов (ТЗ §29–§30);
`rdb_lint` следит за дублями/коллизиями алиасов, self/duplicate-ссылками и
вложенностью объектов (ТЗ §28).

**Evidence vs candidates:** посев порождает только **технические** имена
(`func_0100`, `lbl_3000`) и помечает каждое доказательство происхождения
(`seed_source` / `seed_evidence` / `seed_from`). Семантические имена — всегда
CANDIDATE, Python не повышает их до фактов; `status=PASS` у `seed_rdb`
означает «механика сошлась к fixpoint», а не «названия верны» (ТЗ §34).

**Dry-run / apply:** по умолчанию `seed_rdb` — **сухой прогон** (ТЗ §20):
план считается и печатается, RDB не трогается; запись — только с `--apply`
(атомарный `debug_save_rdb` в конце, ТЗ §22). В `pipeline` шаг `seed_rdb`
идёт dry-run-ом сразу после `coverage`/`disassembly` (ТЗ §36–§37).

```bash
# план (ничего не пишем):
python3 utils/analyze/cli.py seed_rdb --rom <rom> --rdb <rdb> --org 0x0100 --json
# применить посев:
python3 utils/analyze/cli.py seed_rdb --rom <rom> --rdb <rdb> --apply
```

Выход — конверт ТЗ §44: `{module, status, entry_points, functions_added,
labels_added, links_added, aliases_added, existing_objects, iterations,
fixpoint, mcp_calls}` плюс `coverage_percent`, `blind_targets`, `conflicts`,
`skipped`. Ошибки уровня анализа (unknown target, overlap, неизвестный
размер) — находки в JSON, не крах прогона; `FAILED` только для реальных сбоев
(MCP недоступен, битый RDB, exception) (ТЗ §45).

## Стандартный pipeline (ТЗ Standard ROM Analysis Pipeline)

`pipeline.py` — стандартный исполнитель: декларативные **stages** с DAG-
зависимостями, RDB-persistence (SAVE → VERIFY → CHECKPOINT),
checkpoint/resume, dry-run/apply, таксономия ошибок, отчёты прогона.
ROM-специфики в нём нет (§46): какие stages и адреса — решает TZ.md/config.

### Модель stages и DAG

Каждый stage — модуль пакета (`Step` historic name) с `depends_on` и
`mutates_rdb`. Результат — `StageResult`: `SUCCESS / SKIPPED / PARTIAL /
FAILED / BLOCKED` (CANDIDATE-статус модуля = PARTIAL, не отказ; BLOCKED —
предок в отказе, §22). Порядок — стабильная topo-сортировка с тай-брейком
по объявлению, поэтому совпадает с прежним линейным:

| stage | depends_on | мутирует RDB | optional |
|---|---|---|---|
| probe | — | – | |
| coverage, disassembly, memory_diff, music2midi | probe | – | music2midi: есть `--spec` |
| seed_rdb | coverage, disassembly | **да** | |
| rdb_lint, io_signature, abi_scan, strings_scan, table_shape, measure_sizes | seed_rdb | – | |
| glyph_scan | seed_rdb | – | `--glyph-address` |
| vram_credits | strings_scan | – | |
| apply_annotations | seed_rdb | **да** | `--annotations` |
| export_asm | rdb_lint (+apply_annotations, когда включён) | – | |
| toolchain_lint, symbolic_operand_lint, syntax_check | export_asm | – | |
| roundtrip_verify | syntax_check | – | |

### Persistence: SAVE → VERIFY → CHECKPOINT

RDB на диске — persistent state анализа. После каждого mutating-stage:
`debug_save_rdb` (единственный разрешённый способ записи; `*.rdb` руками не
правим) → verify (файл существует, ненулевой, читается, счёт объектов
совпадает с живым `debug_get_rdb_info`) → атомарный checkpoint. Read-only
stage получает только checkpoint — «stage завершён» без записи в
`pipeline_state.json` не считается. Не больше `max_unsaved_objects=10`
несохранённых изменений: `seed_rdb`/`apply_annotations` режут свою работу на
пачки через `--save-every 10` и после каждого batch сами зовут save +
`pipeline_state.checkpoint_active()` (хук registered pipeline-ом; вне
pipeline — no-op). Промежуточный checkpoint принудительно, если stage идёт
дольше `max_checkpoint_seconds=300`. Fail verify — фатал (`RDB_CORRUPTED` /
`SAVE_VERIFY_FAILED`): сохранённые батчи никогда не откатываются из-за
отказа более позднего stage (§31).

Политика переопределяется `--config` (JSON; YAML сознательно не
 поддерживаем — stdlib-only): `persistence: {max_unsaved_objects,
 max_checkpoint_seconds, save_after_stage, verify_after_save,
 checkpoint_after_save}`, `stages: [разрешённые имена]`.

### Формат checkpoint и resume

`pipeline_state.json` (version 1) лежит в `--reports`; пишется атомарно:
`.tmp` → flush+fsync → rename — после kill файл либо старый корректный,
либо новый корректный. Ключи: rom/rom_sha256, rdb/rdb_sha256,
last_completed_stage, completed_stages, current_stage, current_batch,
processed_objects, pending_objects, checkpoint_time (ISO UTC), rdb_objects,
rdb_links, status, dry_run.

`--resume` валидирует **до любого анализа**: checkpoint читаем →
ROM sha256 (`ROM_MISMATCH`) → RDB sha256 (`RDB_CHANGED_OUTSIDE_PIPELINE`,
`RDB_MISSING`) → capabilities (`REQUIRED_CAPABILITY_MISSING`). Завершённые
stages пропускаются, но checkpointу не верятся на слово (§9): нужен
артефакт `results/<key>.json` и число объектов в RDB >= подтверждённого.
Прерванный stage перезапускается с нуля — apply идемпотентен; подтверждённые
батчи не пере-применяются. `--clean` удаляет только checkpoint.

### Режимы и безопасность

Дефолт — **apply** (решение пользователя): мутации разрешены, `seed_rdb`
реально сеет. `--dry-run` — строго read-only: guard на `session.call`
блокирует весь список `RDB_MUTATING_TOOLS` (object/link/alias/comment/
save); даже если модуль проглотит нарушение в свой except, сигнал остаётся
на сеансе и прогон останавливается с `DRY_RUN_VIOLATION`; после dry-run
sha256 RDB обязан совпадать с допрогонным. Ошибки: fatal
(`ROM_MISMATCH, RDB_CORRUPTED, MCP_UNAVAILABLE, REQUIRED_CAPABILITY_MISSING,
CHECKPOINT_CORRUPTED, SAVE_VERIFY_FAILED, …`) — STOP с кодом и nonzero rc;
recoverable (`MCP_TIMEOUT, MCP_DISCONNECTED, STEP_EXCEPTION`) — до 3
повторов с backoff 1/2/4 c только для read-only stages (mutator
перезапускается целиком через `--resume`). Смерть сервера — один
переподъём сеанса на прогон с пере-`debug_load_rom`.

### Отчёты прогона

`reports/pipeline.md` — человекочитаемый отчёт *о прогоне* (ROM/SHA256/
режим/resume/старт/финиш/итог + таблица stages + ошибки);
`reports/pipeline.json` — машиночитаемый (version 1, статусы, длительности,
дельты MCP по stage, история checkpoint-ов). Отчёт *о ROM* (`--out`,
`report_gen`) и `statistics.json` — прежние, они не заменяются.

### Аннотации: `apply_annotations.py`

Вход — JSON `{"objects": [{"address", "name", "type", "size", "comment",
"properties", "aliases", "links": [{"to", "kind"}]}]}`. До первого
MCP-mutating вызова файл целиком валидируется (диапазон ROM, тип,
`naming.validate`, самосогласованность ссылок); любая ошибка — FAILED
конверт и ноль мутаций. Применение — `RdbWriter` (N отдельных `debug_*`-
вызовов; пакетный API не имитируем, но при появлении
`debug_apply_rdb_batch` в профиле возможностей модуль перейдёт на него сам).
Повтор того же файла не создаёт дублей (идемпотентность §12).

### E2E-правило (обязательное)

Интеграционные тесты **никогда** не трогают tracked RDB (`putup.rdb`,
`TESTAY.rdb`, `clrs.rdb`): фикстура копируется во временный каталог,
прогон идёт по копии, после — проверка `git diff -- roms/` пуст.
Отсутствующий опциональный ROM (`riseout`) — SKIP, не FAIL.

## Кэш доказательств и его очистка

Ответы сервера кешируются, чтобы повторный сбор отчёта не дёргал эмулятор.
Расположение (см. `evidence_cache.for_rom`):

```
<каталог ROM>/.analyze/cache/<stem>[-<sha[:8]>]/
    evidence/   ← конверты ответов сервера
    derived/    ← производные артефакты (§16 DERIVED)
    index.jsonl ← журнал-указатель
```

Можно переопределить корень переменной окружения `V06C_ANALYZE_CACHE`
(тогда кэш всех ROM складывается в одно место). Ключ конверта —
`sha1(инструмент + нормализованные параметры + identity ROM + отпечаток
рантайма)`, поэтому смена состояния эмулятора (после run/pause/load_rom) сама
инвалидирует записи. Каталог `.analyze/` добавлен в `.gitignore`.

```bash
# что бы удалилось (по умолчанию ТОЛЬКО показ):
python3 utils/analyze/cli.py clear_cache --rom roms/redesign/putup/src/putup.rom
# реально удалить:
python3 utils/analyze/cli.py clear_cache --rom … --run
# прибрать все кэши в дереве:
python3 utils/analyze/cli.py clear_cache --scan . --run
# прореживать только файлы старше 30 дней:
python3 utils/analyze/cli.py clear_cache --root .scratch/results/putup/.analyze --older-than 30 --run
```

После удаления срезается опустевшая служебная оболочка (`…/cache` и сам
`.analyze`), но не родитель-каталог проекта; отключить — `--keep-empty-parents`.

## Конверт результата (§29/§30/§34)

Каждый модуль с `--json` печатает один объект как минимум с полями:

```
module, status, verdict, note, mcp_calls, candidates, cache, session_stats
```

Вкладка `status` определяет раздел отчёта:

| статусы | секция |
|---|---|
| `OK` `FACT` `MATCHED` `CLEAN` | Verified Facts |
| `CANDIDATE` `PARTIAL` `DERIVED` | Inferences / Hypotheses |
| `MISMATCH` `FAIL` `FAILED` `ERROR` `BLOCKED`, либо `verdict` с префиксом `blocked:` | Limitations |
| отсутствие статуса | «неотнесённое» (дефект модуля) |

## Статистика прогона (§30)

`pipeline.py` пишет `statistics.json`: суммарные вызовы MCP, вызовы по
инструментам, попадания/промахи кэша, wall-time, самые дорогие вызовы.
`report_gen.py --statistics <файл>` подмешивает их в отчёт; при общем сеансе
сумма поля `mcp_calls` по модулям перекрывается, поэтому итоговый
`total_mcp_calls` берётся из файла статистики.

## ROM-специфичное

В `roms/redesign/<rom>/tools/` живут только привязанные к одному ROM артефакты:
генераторы макета (`gen_layout.py`, `sizes.json`) и `music_spec.json` /
`putup2midi.py` — обёртки над общим `music2midi.py` с адресами дорожек этого
ROM. Общие методы в `tools/` не дублируются.

## Тесты

Два уровня в [`tests/`](tests):

```bash
# юнит-тесты (без эмулятора, быстрые, всегда проходят):
python3 utils/analyze/tests/test_units.py
# юниты стандартного pipeline (FakeSession; checkpoint/DAG/persistence/resume/
# safety/dry-run/идемпотентность):
python3 utils/analyze/tests/test_pipeline.py
# интеграция на реальных ROM (boot сервера; скипается без v06c-mcp):
python3 utils/analyze/tests/test_integration.py
# launcher run_pipeline.sh (ТЗ Launcher §35: профили, пути, forward аргументов,
# exit-коды, отсутствующие файлы, SIGINT — на stub-репозитории, без сервера):
python3 utils/analyze/tests/test_launcher.py
# + полные E2E-прогоны pipeline на ВРЕМЕННЫХ КОПИЯХ rom/rdb как критерий
#   приёмки (§56: kill→resume, apply-детерминизм, riseout-условно; ~мин):
V06C_ANALYZE_E2E=1 python3 utils/analyze/tests/test_integration.py
```

Юниты покрывают чистые функции: шаблоны имён, ключ/конверт кэша, классификацию
статусов и сводку отчёта, подстановку плейсхолдеров и порядок шагов `pipeline`,
checkpoint-механику (`pipeline_state`), атомарность записи, валидацию resume,
dry-run guard и DAG на FakeSession, расположение/срезание кэша в `clear_cache`,
разбор адреса и общий конверт.
Интеграция проверяет контракт конверта на `putup.rom` и `TESTAY.ROM` в одном
общем сеансе и то, что кандидат не повышается до факта (§34); E2E-прогоны
работают только с копиями фикстур во временных каталогах.
