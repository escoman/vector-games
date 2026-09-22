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

`pipeline.py` — единственный «дирижёр»: поднимает **один длинный MCP-сеанс**
(§3/§4) и прогоняет в нём все модули по порядку, складывая JSON-результаты,
статистику §30 и отчёт §29.

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
| `--only <шаг>` (повторяемо) | прогнать отдельные шаги (например `--only probe --only rdb_lint`) |
| `--list` | показать порядок шагов и выйти |
| `--runtime` | разрешить модулям читать RUNTIME-байты через MCP (нужно `music2midi` с runtime-источником) |
| `--glyph-address` | адрес блока глифов; без него шаг `glyph_scan` пропускается (адрес ROM-специфичен) |
| `--no-cache` | не использовать и не писать кэш доказательств |
| `--spec` | `music_spec.json` для шага `music2midi`; без него шаг пропускается |

Выход — сводка `{steps, succeeded, failed, exit_nonzero, total_mcp_calls,
wall_ms, cache, statistics, report, results}`. Код возврата `0`, если ни один
шаг не упал (ненулевой код линтера — это находка, не крах: он идёт в
`exit_nonzero`, а не в `failed`).

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
| `coverage.py` | покрытие кода, слепые зоны | Fact/Partial |
| `disassembly.py` | запрос дизасемблера у сервера (без своего декодера) | Evidence |
| `rdb.py` / `naming.py` | модель RDB; единые шаблоны имён (§28) | библиотека |
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
| `pipeline.py` | дирижёр прогона в одном сеансе |
| `clear_cache.py` | очистка/прореживание кэша доказательств |

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
# интеграция на реальных ROM (boot сервера; скипается без v06c-mcp):
python3 utils/analyze/tests/test_integration.py
# + полный прогон pipeline на putup как критерий приёмки (§35, ~30 c):
V06C_ANALYZE_E2E=1 python3 utils/analyze/tests/test_integration.py
```

Юниты покрывают чистые функции: шаблоны имён, ключ/конверт кэша, классификацию
статусов и сводку отчёта, подстановку плейсхолдеров и порядок шагов `pipeline`,
расположение/срезание кэша в `clear_cache`, разбор адреса и общий конверт.
Интеграция проверяет контракт конверта на `putup.rom` и `TESTAY.ROM` в одном
общем сеансе и то, что кандидат не повышается до факта (§34).
