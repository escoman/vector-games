# Исследование ROM ./src/riseout.rom с помощью mcp-сервиса и python-фреймворка `analyze`

Объект: `/home/alexey/Projects/vector-games/roms/redesign/riseout/src/riseout.rom`, 20480 байт, SHA256
`c265014b3db42ccc3454c8c9e6a1d9cb47f43e00c373f494ece1b47f675a6991`.
Первые байты образа — `F3 31 00 01 CD B5 04 …` (`DI`, `LXI SP,0100h`, `CALL 04B5h`),
то есть entry `0x0100`. В ROM читается KOI8/ASCII-тексты
`^LEVEL COMPLETE^`, `RISE OUT^2!!`, `^ READY ^`, `^ GAME OVER ^`,
`SCORE: 00 MEN: 5 LEVEL: 1`, `HIT BUTTON OR SPACE KEY`, `SELECT SPEED LEVEL`.
В игре две мелодии: на заставке (до нажатия кнопки) и на уровне. Обе надо
экспортировать в MIDI.

Методика наследует `../putup/TZ.md`, но учитывает, что для механических
шагов есть готовый детерминированный Python-фреймворк `utils/analyze`
(см. `utils/analyze/README.MD` и `../putup/AFTER.md`). Все Stage, где нужен
только «вызов MCP → посчитать → оформить», выполняются фреймворком; ИИ
останавливается только там, где нужна семантика.

## Stage 0. Принципы и разделение ответственности

### Именование объектов в RDB

Префиксы:
- функции — `func_`
- блоки данных — `data_`
- текстовые строки — `str_`
- музыкальные дорожки (ноты) — `music_`
- одиночные переменные — `var_`
- локальные метки внутри функции — `lbl_` (в asm — `loc_XXXX`, см. Stage 8)

Суффиксы:
- для объектов с пока неизвестным предназначением — `_unknown`;
- у объектов, назначение которых установлено, суффикс `_unknown` убираем.

### Разделение «Python vs ИИ» (по AFTER.md §2)

| слой | кто | что делает |
|---|---|---|
| **A. Facts** | Python (`utils/analyze`) | проверяемо байт-в-байт: загрузка ROM, покрытие, round-trip сборки, VRAM-кредиты, размеры объектов, MIDI-генерация по готовой спеке |
| **B. Candidates** | Python находит с пометкой | сигнатуры ABI, форма таблиц, строки KOI8/RUS, порт-сигнатуры I/O, кандидаты границ гэпов |
| **C. Semantics** | только ИИ/человек | «эта функция — драйвер музыки», «эта таблица — частоты», имена и комментарии |

Политика доступа к отладчику (AFTER.md §7 R1): Python-скрипты обращаются к
эмулятору **только** через MCP `v06c-mcp`; прямой линковки с `debugger_core`
из скриптов нет; единственный легальный внешний бинарь — `v06c-asm-export`.
Скрипты могут кэшировать ответы (`evidence_cache.py`), строить отчёты и
линты. Декодировать опкоды и строить CFG скриптам запрещено — это делает
отладчик.

### Холодный старт: две разные RDB

Различаются два состояния, и модули `utils/analyze` работают с ними по-разному:

- **Сессионная RDB в памяти отладчика** — существует сразу после `debug_load_rom`,
  на холодном старте пустая (`objects: []`). Мутируется вызовами
  `debug_add_rdb_object` / `debug_update_rdb_object` / `debug_set_rdb_comment`
  и т.п. Читается через `debug_list_rdb_objects`.
- **RDB-файл на диске** (`./src/riseout.rdb`) — появляется только после того,
  как кто-то дёрнет `debug_save_rdb` (без аргументов; сервер пишет по
  авто-выведенному пути-соседу от имени ROM-файла).

Python-слой: [`Rdb.load(path)`](../../../utils/analyze/rdb.py) — обычный `open()`,
при отсутствии файла кидает `FileNotFoundError`. [`Rdb.from_session(session)`](../../../utils/analyze/rdb.py) —
дёргает `debug_list_rdb_objects`, возвращает пустой `Rdb`, не падает.

Кто из модулей фреймворка пишет RDB-файл на диск: **только** `seed_rdb` под
`--apply` (в конце вызывает `RdbWriter.save()` → `debug_save_rdb`). Значение
по умолчанию — dry-run; шаг `seed_rdb` внутри `pipeline` тоже dry-run
(см. `utils/analyze/README.MD` «Dry-run / apply»). Практическое следствие:
`pipeline` **никогда не создаёт `.rdb`-файл**; для cold-start нужен отдельный
`seed_rdb --apply`.

Как модули относятся к отсутствующему `.rdb`:

| Категория | Модули | Поведение без файла |
|---|---|---|
| Не трогают RDB | `probe`, `disassembly`, `memory_diff`, `music2midi`, `report_gen` | Безопасно |
| Сессионные; безопасны, если **не** передавать `--rdb` | `coverage`, `seed_rdb`, `abi_scan`, `io_signature`, `strings_scan`, `table_shape`, `glyph_scan`, `vram_credits` | С `--rdb <нет файла>` → `FileNotFoundError` (внутри `pipeline` перехватывается как `StepError`, шаг → FAILED); без `--rdb` → работают по пустой сессии |
| Файл обязателен | `rdb_lint`, `export_asm` (внешний `v06c-asm-export --rdb`) | Не стартуют |
| Файл желателен, есть fallback | `symbolic_operand_lint`, `roundtrip_verify`, `measure_sizes` | Проверяют `os.path.isfile`; без файла идут с пустым списком объектов (симв. имён нет, размеры/round-trip беднее) |

Из этого следует **правильный порядок холодного старта** — Stage 1 идёт
совсем без `--rdb`, Stage 2 создаёт файл отдельным `seed_rdb --apply`, и
только с Stage 2.3+ можно звать полный `pipeline --rdb ...`.

### Что запрещается делать руками

- Не писать ad-hoc скриптов для пост-обработки MCP-данных в обход пакета
  `utils/analyze`. Если нужного модуля нет — расширять пакет, а не плодить
  одноразовые py-ки в `roms/redesign/riseout/tools/`.
- В `tools/` держать только ROM-специфичное (адреса дорожек riseout, layout,
  specs). Общие алгоритмы — в `utils/analyze/`.

### Отчёты и артефакты

- Промежуточные отчёты по каждому Stage: `./reports/StageN.md`
  (каталог создаём на первом сохранении).
- RDB: `./src/riseout.rdb` рядом с ROM.
- Экспортированный ASM: `./asm/` (одна функция / один data-объект = один
  файл).
- Инструменты и спеки конкретного ROM: `./tools/`.
- Готовые MIDI: `./riseout_title.mid` и `./riseout_level.mid` в корне
  проекта ROM (рядом с TZ.md).

## Stage 1. Общее исследование карты памяти, активности чтения/записи

Механический — делает `utils/analyze`. **На входе файла `src/riseout.rdb`
ещё нет**, поэтому в этом Stage `--rdb` не передаём ни в одной команде.

1) **Префлайт-сверка образа (обязательна до любого анализа).** Загрузить
   ROM и сверить первые 32 байта RAM-отображения `0x0100..0x011F` с
   ожидаемым дампом
   `F3 31 00 01 CD B5 04 21 0D 07 22 27 08 3E 03 32`
   `1E 07 21 00 80 16 00 72 23 7D B4 C2 17 01 C3 63`
   (он снят с файла `src/riseout.rom` при подготовке ТЗ; `sha256sum` —
   `c265014b…5a6991`).
   Инструменты: `debug_load_rom` (`path`, `org=0x0100`) +
   `debug_read_memory_range` (addr `0x0100`, length 32). Расхождение —
   стоп, проверить `sha256sum src/riseout.rom` и повторить загрузку.
   Без этой проверки есть риск, что последующий анализ опирается на
   residual RAM от предыдущей сессии (урок из `../clrs`: Stage 2 там
   «увидел» hardware-detection вместо VRAM clear именно из-за warm start).
2) **Один MCP-сеанс, только «безопасные» шаги** (те, что не открывают RDB):
   ```bash
   cd /home/alexey/Projects/vector-games
   export PYTHONPATH=utils
   python3 utils/analyze/cli.py pipeline \
     --only probe --only disassembly --only memory_diff \
     --rom  roms/redesign/riseout/src/riseout.rom \
     --rdb  roms/redesign/riseout/src/riseout.rdb \
     --org  0x0100 --entry 0x0100 \
     --results .scratch/results/riseout --export .scratch/export/riseout \
     --out     roms/redesign/riseout/reports/Stage1.md --stage 1 \
     --goal    "Stage 1: memory map и I/O riseout.rom" --json
   ```
   Ключевое — `--only`. Три выбранных шага не зовут `Rdb.load`, поэтому
   несуществующий `--rdb` не мешает. Шаг `probe` грузит ROM, даёт ему ~1 с
   и снимает CPU state, memory map, memory access map, I/O trace, снапшоты —
   это Stage 1 пп. 1–4 из первоначального ТЗ.
   (Флаг `--rdb` оставлен только потому, что `pipeline` требует его как
   `required=True`; ни один из трёх запущенных шагов его не откроет.)
3) Альтернатива без pipeline — три отдельных вызова, каждый сам поднимает
   сеанс:
   ```bash
   python3 utils/analyze/cli.py probe \
     --rom roms/redesign/riseout/src/riseout.rom --org 0x0100 --seconds 5
   python3 utils/analyze/cli.py disassembly \
     --rom ... --org 0x0100 --entry 0x0100
   python3 utils/analyze/cli.py memory_diff \
     --rom ... --org 0x0100 --hi 0x50FF
   ```
   (`0x50FF = 0x0100 + 20480 - 1` — верх образа riseout.)
4) Отчёт Stage 1 собирает `report_gen.py` из JSON-конвертов в
   `.scratch/results/riseout/*.json` (см. `utils/analyze/README.MD`
   «Конверт результата»). Секции: Verified Facts / Inferences / Limitations.
5) Канонический старт — только `debug_load_rom`; **не** `debug_reset`
   (AFTER.md §5: `debug_reset` вешает CPU на busy-wait `OUT 1C / IN 1B`,
   `sp=0xDCEC`, BP не достигается). Поведение после `debug_reset`
   не сравнимо с чистым стартом.

## Stage 2. Первичное обследование функций и блоков данных (посев RDB)

Механический — `seed_rdb.py` + `coverage.py` до fixpoint. **Именно этот
Stage создаёт `src/riseout.rdb` на диске** (единственный модуль во
фреймворке, который вызывает `debug_save_rdb`).

1) **Dry-run плана, сессия без `--rdb`** — файла ещё нет, не передаём:
   ```bash
   python3 utils/analyze/cli.py seed_rdb \
     --rom  roms/redesign/riseout/src/riseout.rom \
     --org  0x0100 --entry 0x0100 --hi 0x50FF --json
   ```
   Без `--rdb` база плана — пустая сессионная RDB (см. Stage 0
   «Холодный старт»). В stderr печатается пошаговый план: функции/метки/
   ссылки, которые добавит `--apply`.
2) **Применить посев — это и есть момент создания файла:**
   ```bash
   python3 utils/analyze/cli.py seed_rdb \
     --rom  roms/redesign/riseout/src/riseout.rom \
     --org  0x0100 --entry 0x0100 --hi 0x50FF --apply
   ```
   Алгоритм (см. README «Первичный анализ и посев RDB»): entry →
   `debug_analyze_code` → CALL/RST в `func_`, JMP/JCC в `lbl_` →
   пересчёт покрытия → досев слепых целей внутри дыр → **fixpoint**.
   Объекты получают только технические имена (`func_0100`, `data_3b00`);
   `size = 0`, если отладчик не дал размер. Один адрес — один объект
   (AFTER.md §5); вторые имена — в `properties.aliases`.
   В конце `RdbWriter.save()` вызывает `debug_save_rdb` → сервер пишет
   `src/riseout.rdb` рядом с ROM. Проверить:
   ```bash
   test -s roms/redesign/riseout/src/riseout.rdb && echo OK
   python3 -c "import json;d=json.load(open('roms/redesign/riseout/src/riseout.rdb'));print('objects:',len(d['objects']))"
   ```
3) **Теперь можно линтить.** `rdb_lint` требует файл, до шага 2 он бы упал:
   ```bash
   python3 utils/analyze/cli.py rdb_lint \
     --rdb roms/redesign/riseout/src/riseout.rdb \
     --rom roms/redesign/riseout/src/riseout.rom --json
   ```
   Ловит пересечения, висячие ссылки, алиас-коллизии. rc≠0 — находка,
   не падение.
4) **Покрытие и fixpoint (уже с `--rdb`, файл есть):**
   ```bash
   python3 utils/analyze/cli.py coverage \
     --rom  roms/redesign/riseout/src/riseout.rom \
     --rdb  roms/redesign/riseout/src/riseout.rdb \
     --org  0x0100 --entry 0x0100 --hi 0x50FF --json
   ```
   (Смысл отдельного `coverage` после `seed_rdb --apply`: `seed_rdb`
   досевал метки внутри дыр до fixpoint, но итоговый процент и слепые
   цели полезно снять вторично как независимое подтверждение.)
5) **Полный `pipeline` — опционально, на этом этапе уже безопасно.** С
   момента, когда файл есть, `pipeline --rdb ...` перестает ронять шаги
   coverage/seed_rdb(run)/rdb_lint/abi_scan/…
   ```bash
   python3 utils/analyze/cli.py pipeline \
     --rom  roms/redesign/riseout/src/riseout.rom \
     --rdb  roms/redesign/riseout/src/riseout.rdb \
     --org  0x0100 --entry 0x0100 --hi 0x50FF \
     --results .scratch/results/riseout --export .scratch/export/riseout \
     --out     roms/redesign/riseout/reports/Stage2.md --stage 2 \
     --goal    "Stage 2: посев RDB riseout" --json
   ```
   Внимательно: шаг `seed_rdb` внутри `pipeline` идёт **dry-run** и RDB
   не мутирует (см. Stage 0 «Кто пишет RDB-файл»). Шаг `music2midi`
   запустится, только если указан `--spec`; на Stage 2 спеки ещё нет —
   не передаём, `pipeline` его сам выкинет.
6) Отчёт `./reports/Stage2.md` (автоген из `report_gen.py`).

### Частые ошибки cold-start, которые ловит эта схема

- «`pipeline --rdb src/riseout.rdb` с самого начала» → coverage/seed_rdb/
  rdb_lint/abi_scan падают с `FileNotFoundError`, в отчёте Section
  «Limitations» пухнет от фейковых FAILED. Правильно: см. Stage 1 шаг 2
  (список `--only`) и Stage 2 шаг 2 (`seed_rdb --apply` без `--rdb`).
- «`seed_rdb --apply --rdb src/riseout.rdb`» → тот же `FileNotFoundError`
  ещё до начала посева (`Rdb.load` вызывается до `writer.save()`).
  Правильно: **не** передавать `--rdb` до тех пор, пока файла нет.
- «Запустить полный pipeline ДО `seed_rdb --apply`» → шаг `export_asm`
  получит несуществующий `--rdb` и или упадёт, или (в graceful-варианте)
  соберёт ASM без символьных имён. Правильно: `seed_rdb --apply` — до
  любого `export_asm`/`roundtrip_verify`.

## Stage 3. Подробное исследование функций (семантика — за ИИ)

Python даёт кандидатов, ИИ называет.

1) Дизассемблирование по RDB: `utils/analyze/cli.py disassembly` и
   `debug_disassemble_range`.
2) Для каждой функции из RDB ИИ читает код и обновляет:
   - осмысленное имя (снимает `_unknown`);
   - комментарий-назначение (русский текст);
   - свойства `params` (Stage 4), `reads`, `writes`, `calls`.
3) Связи: `debug_add_rdb_link` для function→function, function→data,
   function→music_track, function→interrupt.
4) Сохранение RDB — только через `debug_save_rdb` API, не редактированием
   JSON на диске.
5) Отчёт `./reports/Stage3.md`.

## Stage 4. Определение параметров функций

1) Кандидаты ABI даёт `abi_scan.py`:
   ```bash
   python3 utils/analyze/cli.py abi_scan \
     --rom ... --org 0x0100 --rdb ... --all --limit 200
   ```
2) ИИ подтверждает/переименовывает, пишет в RDB `properties.params`
   (рег/стек/накопитель, размер, семантика).
3) Сохранение RDB, отчёт `./reports/Stage4.md`.

## Stage 5. Исследование прерываний

1) Векторы: `0x0008` RST 0, `0x0010` RST 8, `0x0018` RST 16, `0x0020` RST 24,
   `0x0038` RST 32, `0x003C` INTERPT (см. `docs/VECTOR_VERIFIED.md`). Особое
   внимание — `RST 7` (аппаратный VBlank, 50 Гц): там кадровый тикер, он же
   потенциальный драйвер звука и анимации.
2) Прогнать `pipeline` шаг `io_signature`, он возвращает порт-сигнатуры
   (какие OUT встречались и как часто). Совмещаем с адресами обработчиков.
3) Каждый обработчик — отдельный объект `func_irq_*` с комментарием, в RDB.
4) `debug_save_rdb`, отчёт `./reports/Stage5.md`.

## Stage 6. Исследование главного игрового цикла

На текущий момент работает заставка с надписью `HIT BUTTON OR SPACE KEY`.

1) Найти в `func_main_init`/`func_0100` цикл опроса клавиатуры
   (порт `KEYSTROB`/`KEYDATA`, см. `docs/VECTOR_VERIFIED.md`). Пометить как
   `lbl_title_key_poll`.
2) Пройти код после нажатия: инициализация уровня → игровой цикл.
3) Найти главный игровой цикл, отметить `func_main_game_loop`.
4) Шаг за шагом (несколько десятков итераций) выявить игровые переменные:
   счёт (`SCORE`), жизни (`MEN`), уровень (`LEVEL`), скорость
   (`SELECT SPEED LEVEL`), координаты игрока. Зафиксировать в RDB
   (`var_score`, `var_lives`, `var_level`, `var_speed`, `var_player_x`, …).
5) `debug_save_rdb`, отчёт `./reports/Stage6.md`.

## Stage 7. Функции вывода текста на экран

1) Строки, которые точно есть (найдены grep'ом по ASCII/KOI8 в ROM):
   - `^LEVEL COMPLETE^` @ 0x1BE5
   - `LEVEL INC:CTRL^#` @ 0x1C63
   - `MORE LEVELS IN#t` @ 0x1C89
   - `RISE OUT^2!!` @ 0x1C9A
   - `^ READY ^` @ 0x223A
   - `^ GAME OVER ^HIGH SCORE:    00:` @ 0x2256
   - `SCORE:    00 MEN: 5 LEVEL: 1` @ 0x23B2
   - `HIT BUTTON OR SPACE KEY` @ 0x2A9D
   - `3 SPEED LEVEL` @ 0x2ACF
   - `SELECT SPEED LEVEL` @ 0x2BDD
   И другие (включая русские KOI8-строки) — надо найти.
2) Автопайплайн:
   ```bash
   python3 utils/analyze/cli.py strings_scan \
     --rom ... --org 0x0100 --hi <ROM_END> --rdb ...
   ```
   Возвращает список `str_*` кандидатов с адресом, длиной и кодировкой.
3) ИИ подтверждает, классифицирует, создаёт RDB-объекты
   (`debug_add_rdb_object`, `debug_set_rdb_comment` = содержимое строки).
4) Найти функцию вывода строк. В ней — базовый адрес, относительно
   которого считаются смещения глифов (`idx * GLYPH_SIZE` или таблица
   DEFW-указателей). Этот базовый адрес — `data_glyph_block`.
5) Растровая сетка глифов:
   ```bash
   python3 utils/analyze/cli.py glyph_scan \
     --rom ... --rdb ... --address <GLYPH_BASE> --count 256 \
     --out .scratch/results/riseout
   ```
   Требует Pillow; рисует PNG, по которому ИИ подтверждает 8×16 или иную
   форму. Размер глифа и адрес записываем в комментарий `data_glyph_block`.
6) Предсказание VRAM-картинки против реальности:
   ```bash
   python3 utils/analyze/cli.py vram_credits \
     --rom ... --rdb ... --string "HIT BUTTON OR SPACE KEY"
   ```
   Возвращает `MATCHED` = текст рендерится как предсказано; иначе `MISMATCH`
   (в отчёте — раздел Limitations, ИИ разбирается).
7) Задача выполнена, если найдены все глифы всех строк п.1.
8) Отчёт `./reports/Stage7.md`.

## Stage 8. Выгрузка функций в asm-файлы

Механический — `export_asm.py` + линты.

1) Экспорт через `v06c-asm-export` (официальный CLI отладчика):
   ```bash
   python3 utils/analyze/cli.py export_asm \
     --rom ... --rdb ... --org 0x0100 \
     --out roms/redesign/riseout/asm \
     --assemble \
     --z80asm  z88dk/bin/z88dk-z80asm \
     --exporter /home/alexey/Projects/vector-debugger/debugger/build/v06c-asm-export
   ```
   Формат z88dk (`DEFB`/`DEFW`/`DEFM`, `INCBIN`, метки без точки).
2) Symbolic operands: адреса, совпадающие с началом RDB-объекта,
   подставляются как имя; внутренние переходы получают `loc_XXXX`;
   нераспознанные остаются hex. Проверяется:
   ```bash
   python3 utils/analyze/cli.py symbolic_operand_lint \
     --dir roms/redesign/riseout/asm --rom ... --rdb ... --org 0x0100
   ```
3) Линтер строгих литералов 8080:
   ```bash
   python3 utils/analyze/cli.py toolchain_lint \
     --dir roms/redesign/riseout/asm --org 0x0100 --entry riseout_new.asm
   ```
4) Проверка синтаксиса z80asm:
   ```bash
   python3 utils/analyze/cli.py syntax_check \
     --dir roms/redesign/riseout/asm --entry riseout_new.asm \
     --z80asm z88dk/bin/z88dk-z80asm \
     --out roms/redesign/riseout/asm/syntax_check.bin
   ```
5) Round-trip: ROM → ASM → бинарь → ROM побайтово:
   ```bash
   python3 utils/analyze/cli.py roundtrip_verify \
     --rom ... --rdb ... --dir roms/redesign/riseout/asm \
     --org 0x0100 \
     --z80asm z88dk/bin/z88dk-z80asm \
     --exporter /home/alexey/Projects/vector-debugger/debugger/build/v06c-asm-export
   ```
   `0 расхождений = Fact`.
6) Отчёт `./reports/Stage8.md`.

## Stage 9. Поиск и исследование карт уровней

Из строк `LEVEL COMPLETE`, `MORE LEVELS IN`, `LEVEL: 1`, `SELECT SPEED
LEVEL`, `SCORE: 00 MEN: 5 LEVEL: 1` видно, что уровней несколько и они
перебираются по кругу. В riseout (аркадная игра «уходи с уровня наверх»)
карта — это, как правило, сетка платформ/кирпичей + стартовая позиция
игрока +位置 бонусов.

1) Найти в `func_main_init` переход из заставки в игру и `func_level_loader`
   (вызывается сразу после CLS, принимает номер уровня в `A` или `HL`).
2) В `func_level_loader` найти:
   - формулу адреса карты: `base + (level-1) * stride` (`stride` — размер
     одной карты в байтах);
   - цикл обхода карты: обычно `M×N` тайлов по 1 байту (tile id) или по
     2 байта (tile+color/plane);
   - параметры: координаты спавна игрока, число кирпичей/бонусов,
     содержимое «двери»/выхода.
3) Определить базовый адрес таблицы карт `data_level_maps` и число уровней
   `LEVEL_COUNT`. Проверить арифметику:
   `(LEVEL_COUNT * stride) == data_next_object_addr - data_level_maps_addr`.
4) Создать RDB-объекты `data_level_01 … data_level_NN` по той же схеме,
   что и в putup Stage 9. **Помнить AFTER.md §5**: RDB хранит ровно один
   объект на адрес. Если база таблицы совпадает с первой картой — база
   `data_level_maps` остаётся с адресом, а `data_level_01` не создаётся,
   первые stride байт описываются комментарием `data_level_maps`.
5) Обновить комментарий `data_level_maps`: базовый адрес, размер карты,
   формат записи тайла, число уровней, где хранятся координаты спавна и
   выхода.
6) Автопроверка границ и размеров:
   ```bash
   python3 utils/analyze/cli.py table_shape \
     --rom ... --org 0x0100 --rdb ...
   python3 utils/analyze/cli.py measure_sizes \
     --rom ... --org 0x0100 --rdb ...
   ```
7) Отчёт `./reports/Stage9.md`.

## Stage 10. Выгрузка блоков данных в asm-файлы

1) Для каждого объекта данных из RDB — отдельный файл `./asm/<имя>.asm`
   в формате z88dk. Имя файла = имя объекта.
2) Разделение по категории:
   - **ROM-backed** (`data_*`, `str_*`, `music_*`, таблицы указателей) —
     фактическое байтовое содержимое;
   - **RAM-backed** (`var_*`, runtime-буферы, векторы прерываний, область
     растра/глифов `0x6000…`) — только EQU/метки, без байтов (в образ ROM
     не входят).
3) Формат по типу:
   - массивы байт — `DEFB` группами по 8/16;
   - массивы слов и таблицы адресов — `DEFW`;
   - строки — `DEFM` + явный терминатор (`0x00` / `0xFF`) как в оригинале.
4) В таблицах указателей — символ. имена RDB по тому же правилу, что и
   Stage 8 (совпал с началом объекта — имя; иначе hex).
5) Заголовок файла — комментарий: имя объекта, адрес, размер, назначение
   (из RDB).
6) Крупные блоки (глифы, растровые логотипы, паттерны фона) допустимо
   выгружать через `INCBIN asm/bin/<имя>.bin`; бинарь формируется прямым
   `debug_read_memory_range` без пост-обработки скриптами.
7) Отчёт `./reports/Stage10.md`.

## Stage 11a. Мелодия ЗАСТАВКИ: драйвер, партитуры, порт-вывод, MIDI

Цель: по экспортированным данным восстановить партитуру титульной мелодии
и получить `./riseout_title.mid`.

1) Источник звука на заставке: `RST 7` (VBlank ~50 Гц) или явный тикер в
   цикле ожидания `HIT BUTTON OR SPACE KEY`. Найти функцию, которая на
   каждом кадре пишет в порты звуковых чипов (0x09/0x0A/0x0B — VI53
   каналы/строб; 0x0B/0x0D — AY регистр/данные, см.
   `docs/VECTOR_VERIFIED.md`). Пометить в RDB:
   `func_music_driver_title` (+ комментарий: «вызывается из …»,
   «пишет в порты …», «шаг = N тиков VBlank»).
2) Партитуры. Найти:
   - **базы** дорожек (по одной на каждый голос) и таблицу указателей на
     них (или формулу `base + N * stride`);
   - **текущие указатели чтения** в RAM (`var_music_ptr_00/01/02`) —
     зафиксировать адреса;
   - признаки конца/петли (`LOOP_CODE`, `END_CODE`).
   Занести в RDB: `data_music_scores_title` (таблица указателей, если
   есть), `data_music_track_title_NN` (каждая дорожка),
   `var_music_ptr_title_NN`.
3) Формат ноты. По коду драйвера установить:
   - разделение байт/слово на «тон/делитель таймера» и «длительность в
     шагах»;
   - специальные коды: пауза (`0x00` или иной), повтор, темп, громкость,
     зацикливание;
   - таблицу «код ноты → тон» (`data_note_freq_table_title`): период VI53
     или регистр AY. Проверить равнотемперированность:
     `period[i] ≈ round(K / 2^(i/12))`, каждые 12 шагов период делится пополам,
     при `f(VI53)=1.5 МГц` `K ≈ 3822`, «A4 = 440 Гц».
   - **offset кода → MIDI note**: для putup это `+30`; для riseout
     устанавливаем экспериментально по таблице периодов и (или) сверкой
     с портовыми дампами.
4) Порт-вывод. Для каждого канала:
   - чип (VI53 — 3 тональных; AY-3-8910 — тон+шум), номер голоса;
   - последовательность `OUT` (реестр → данные → строб);
   - преобразование «код ноты → значение в порт» (прямая запись, индекс
     в таблице периодов, удвоение/деление).
   Кратко сверяем с `docs/VECTOR_VERIFIED.md`.
5) Спецификация для конвертера. Сохраняем
   `./tools/music_spec_title.json` по схеме `v06c-music-spec/1` (см.
   `../putup/tools/music_spec.json` — валидный пример). Обязательные поля:
   - `schema`, `title`, `rom`, `org`, `output` (`../riseout_title.mid`);
   - `format`, `ppq`, `tempo_us_per_quarter`, `time_signature`;
   - `note_offset`, `rest_code`, `code_mask`, `velocity`;
   - `provenance.facts_from = "reports/Stage11a_music_spec.md"`;
   - `tracks[]` — по одной записи на голос: `name`, `address`, `length`,
     `source` (`image` если данные в ROM, `runtime` если читаем RAM через
     MCP), `midi_channel`, `gm_program`, `step_ticks`, `expect`
     (дамп кодов, сверяется побайтово перед записью).
6) Полный markdown-отчёт со спекой: `./reports/Stage11a_music_spec.md`
   (структура как `../putup/reports/Stage11_music_spec.md`).
7) Генерация MIDI:
   ```bash
   python3 utils/analyze/cli.py music2midi \
     --spec roms/redesign/riseout/tools/music_spec_title.json \
     -o    roms/redesign/riseout/riseout_title.mid \
     --rom roms/redesign/riseout/src/riseout.rom
   ```
   Если хоть одна дорожка помечена `source: runtime`, добавляем `--runtime`
   (в этом же MCP-сеансе ROM должен работать на заставке; иначе
   `music2midi` остановится с внятной ошибкой — см.
   `utils/analyze/music2midi.py`).
8) Обновить RDB: связи `func_music_driver_title` ↔
   `data_music_scores_title` ↔ `data_music_track_title_NN` ↔
   `var_music_ptr_title_NN`; комментарии с форматом события и таблицей
   «код → частота». `debug_save_rdb`.
9) Критерий приёмки: MIDI открывается в секвенсоре, длительности и
   ноты соответствуют слуховому впечатлению от заставки, побайтовые
   `expect`-дампы из спеки совпали.
10) Отчёт `./reports/Stage11a.md`.

## Stage 11b. Мелодия УРОВНЯ: драйвер, партитуры, порт-вывод, MIDI

Analog Stage 11a для внутриигровой мелодии. Отличия в том, где искать
драйвер и как вести себя с переключением «заставка → уровень».

1) Вход в уровень — после нажатия SPACE/BUTTON (Stage 6). Найти код,
   который в этот момент:
   - перезапускает/переключает указатели дорожек (common case — другой
     base, либо `var_music_track_index := 1`);
   - либо меняет таблицу указателей, из которой `func_music_driver`
     выбирает активную партитуру;
   - либо грузит отдельный «уровневый» трек в RAM-буфер.
2) `func_music_driver_level` — та же функция, что и на заставке, или её
   второй экземпляр. В RDB завести отдельный объект
   `func_music_driver_level` (алиас к `func_music_driver_title` через
   `properties.aliases`, если адрес тот же — см. правило «один адрес — один
   объект», AFTER.md §5).
3) Партитуры уровня: ищем новый набор баз `data_music_track_level_NN`,
   возможно другой stride и другую длину. Таблицу указателей
   `data_music_scores_level` (если есть). Указатели чтения RAM —
   `var_music_ptr_level_NN`.
4) Формат ноты уровня: в 99 % случаев он совпадает с заставочным (тот же
   драйвер). Повторно проверяем только:
   - таблицу периодов — общая или отдельная `data_note_freq_table_level`;
   - темп/скорость шага (`step_ticks`, частота прерывания).
5) Порт-вывод не меняется, если драйвер общий. Если у уровня добавлен
   шум/перкуссия AY — фиксируем отдельно.
6) Спецификация: `./tools/music_spec_level.json` по той же схеме, но
   `output` = `../riseout_level.mid`.
7) Отчёт-спека: `./reports/Stage11b_music_spec.md`.
8) Генерация MIDI:
   ```bash
   python3 utils/analyze/cli.py music2midi \
     --spec roms/redesign/riseout/tools/music_spec_level.json \
     -o    roms/redesign/riseout/riseout_level.mid \
     --rom roms/redesign/riseout/src/riseout.rom --runtime
   ```
   Флаг `--runtime` нужен, если дорожки уровня разворачиваются в RAM по
   ходу игры (обычно так: на заставке RAM содержит титульные данные, а
   партитура уровня подгружается после SPACE). Для чтения RAM в
   `music2midi` обязателен живой эмулятор на уровне.
9) Обновить RDB: те же связи, что и Stage 11a, плюс явная пометка, какой
   драйвер активен на каком экране. `debug_save_rdb`.
10) Критерий приёмки: MIDI открывается; при сравнении двух треков
    (`title` vs `level`) слышно, что это разные мелодии; `expect`-дампы
    сошлись.
11) Отчёт `./reports/Stage11b.md`.

## Stage 12. Сборка нового RISEOUT_NEW.ROM из исходников ./asm/

1) Мастер компоновки `asm/riseout_new.asm` + генератор `tools/gen_layout.py`
   (пример — `../putup/tools/gen_layout.py`) раскладывает объекты из
   RDB по адресам оригинала, для гэпов пишет `asm/bin/gap_*.bin`verbatim
   из `debug_read_memory_range`.
2) Makefile (`./Makefile` по образцу putup) с целями:
   - `layout` — перегенерировать мастер + gap-бинари;
   - `src/RISEOUT_NEW.ROM` — собрать z80asm-ом (`-b -m=8080_strict -s`);
   - `verify` — побайтовая сверка с `src/riseout.rom`: 0 расхождений;
   - `full = clean all deploy`;
   - `deploy` — по `finally.mk`.
3) Конечная цель — получить ROM, работающий как оригинал (пусть и со
   сдвинутым адресным пространством); байт-в-байт идентичность —
   достаточный, но не обязательный критерий.
4) Проверка поведения через MCP (boot-регистры, заставка, SPACE→игра,
   HUD/VRAM, музыкальные порты 0x09/0x0A/0x0B).
5) Отчёт `./reports/Stage12.md`.

## Stage 13. Опциональная «подчищенная» сборка RISEOUT_CLEAN.ROM

Как в `../putup/TZ.md` Stage 13 — по желанию. Если в riseout найдётся
конвейер распаковки глифов и гэп-регионы: собрать переработанный образ,
в котором блок глифов хранится распакованным, таблица символов не привязана
к абсолютному `0x6000`, гэпы классифицированы и разложены штатными
объектами (или удалены как мёртвые). Обязательна behavioral верификация
против оригинала через MCP.

Если в riseout распаковщика глифов нет и гэпы — только выравнивание,
Stage 13 **не выполняется**, в `reports/README.md` фиксируем причину.

Отчёт (если выполняется) — `./reports/Stage13.md`.

## Приоритеты и порядок

- Stage 0 → 1 → 2 → 8 → 3 → 4 → 5 → 6 → 7 → 9 → 10 → 11a → 11b → 12 → 13.
- Stage 1, 2, 8, 10, 11a/11b (кроме семантики) и 12 полностью
  механические: сначала прогоняем `pipeline`/CLI, получаем скелет,
  затем ИИ добирает Level C (семантику и имена).
- Stage 11a и 11b **оба обязательны** — цель задания включает экспорт
  двух MIDI.

## Итоговые артефакты, которые должны существовать на выходе

```
roms/redesign/riseout/
├── TZ.md                              (этот файл)
├── Makefile
├── riseout_title.mid                  (Stage 11a)
├── riseout_level.mid                  (Stage 11b)
├── src/
│   ├── riseout.rom                    (исходник)
│   ├── riseout.rdb                    (RDB после Stage 12)
│   └── RISEOUT_NEW.ROM                (Stage 12)
├── reports/
│   ├── Stage1.md … Stage12.md
│   ├── Stage11a_music_spec.md
│   └── Stage11b_music_spec.md
├── asm/                               (экспортированные функции и данные)
│   ├── riseout_new.asm                (мастер компоновки)
│   ├── func_*.asm, data_*.asm, str_*.asm, music_*.asm, var_*.asm
│   └── bin/gap_*.bin                  (вербатим-дампы гэпов)
└── tools/
    ├── gen_layout.py
    ├── sizes.json                     (для measure_sizes)
    ├── measure_order.json
    ├── music_spec_title.json          (Stage 11a)
    └── music_spec_level.json          (Stage 11b)
```
