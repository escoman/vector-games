# Исследование ROM ./src/riseout.rom с помощью mcp-сервиса и python-фреймворка `analyze`

Объект: `./src/riseout.rom`, 20480 байт, SHA256
`c265014b3db42ccc3454c8c9e6a1d9cb47f43e00c373f494ece1b47f675a6991`.
Первые байты — `F3 31 00 01 CD B5 04 …` (`DI`, `LXI SP,0100h`, `CALL 04B5h`),
entry `0x0100`, верх образа `0x50FF`. В ROM читаются KOI8/ASCII-тексты
`^LEVEL COMPLETE^`, `RISE OUT^2!!`, `^ READY ^`, `^ GAME OVER ^`,
`SCORE: 00 MEN: 5 LEVEL: 1`, `HIT BUTTON OR SPACE KEY`, `SELECT SPEED LEVEL`.
В игре две мелодии — на заставке и на уровне; обе выгружаются в MIDI.

Методика учитывает, что для механических шагов
есть готовый детерминированный фреймворк `utils/analyze` (устройства и команды
модулей — в `utils/analyze/README.MD`, здесь они не дублируются). Все Stage,
где нужно лишь «вызвать MCP → посчитать → оформить», делает фреймворк; ИИ
включается только там, где нужна семантика.

## Stage 0. Автоматизированное исследование (главный вход)

Весь детерминированный слой поднимается **одной командой**:

```bash
utils/analyze/run_pipeline.sh riseout            # полный прогон (apply по умолчанию)
utils/analyze/run_pipeline.sh riseout --dry-run  # строго read-only, ничего не пишет
utils/analyze/run_pipeline.sh riseout --resume   # продолжить с чекпоинта
utils/analyze/run_pipeline.sh riseout --clean    # стереть чекпоинт и начать заново
```

Launcher берёт профиль `riseout` (пути ROM/RDB + профильный `pipeline.json`) и
прогоняет DAG стадий в топологическом порядке:

`probe → coverage → disassembly → seed_rdb → rdb_lint → memory_diff →
io_signature → abi_scan → strings_scan → table_shape → vram_credits →
export_asm → toolchain_lint → symbolic_operand_lint → syntax_check →
roundtrip_verify → measure_sizes`.

Что даёт автоматика:

- **RDB-файл `src/riseout.rdb` рождается здесь.** Стадия `seed_rdb` в apply-режиме
  досевает функции/метки/ссылки до fixpoint и в конце вызывает `debug_save_rdb`.
  Ручной «холодный старт» больше не нужен: launcher и pipeline сами держат порядок
  «не открывать `--rdb`, пока файла нет», а отсутствующий `.rdb` — не ошибка.
- **Facts (проверяемо байт-в-байт):** memory map, покрытие, линт целостности RDB,
  round-trip сборки ROM→ASM→бинарь→ROM, снапшоты.
- **Candidates (с пометкой, решает ИИ):** ABI-параметры (`abi_scan`),
  KOI8/ASCII-строки (`strings_scan`), формы таблиц (`table_shape`),
  порт-сигнатуры I/O (`io_signature`), глифы (`glyph_scan`),
  VRAM-предсказание (`vram_credits`).
- **Отчёты:** `.scratch/pipeline/riseout/pipeline.md` + атомарный чекпоинт
  `pipeline_state.json` (с `--resume`).

Профильный `pipeline.json` разворачивает **максимальное** автоматическое
исследование через `stage_args` (переопределение флагов любой стадии без
разрастания CLI): глубокий посев (`seed_rdb --max-depth`), длинные рантайм-трассы
с нажатием клавиш (`probe`/`io_signature`/`memory_diff`/`abi_scan`
`--seconds`/`--run-seconds`/`--key`), расширенные `abi_scan`/`table_shape`.
Клавиши (`ENTER`/`SPACE`/стрелки) заводят ROM вглубь — это ловит больше IO-портов,
RAM-патчей и функций, чем короткий простой.

**Где автоматика упирается (и дальше только ИИ):** статическое покрытие сходится
на достижимом из entry (у riseout — ~44 %, остальное графика/таблицы и, вероятно,
банки); `table_shape`/`vram_credits`/`music2midi` молчат, пока ИИ не занесёт в RDB
таблицы, строки-кредиты и музыкальные спеки (Stage 7, 9a, 9b ниже).

## Stage 0'. Принципы и разделение ответственности

Именование объектов в RDB — префиксы `func_`, `data_`, `str_`, `music_`, `var_`,
`lbl_`; суффикс `_unknown` для недообследованного (снимается, когда назначение
установлено). Единственный источник правил именования — `utils/analyze/naming.py`.

| слой | кто | что делает |
|---|---|---|
| **A. Facts** | Python (`utils/analyze`) | загрузка ROM, покрытие, round-trip сборки, VRAM-кредиты, размеры объектов, MIDI по готовой спеке |
| **B. Candidates** | Python находит с пометкой | сигнатуры ABI, форма таблиц, строки KOI8/RUS, порт-сигнатуры I/O, границы гэпов |
| **C. Semantics** | только ИИ/человек | «эта функция — драйвер музыки», «эта таблица — частоты», имена и комментарии |

Политика доступа: Python-скрипты идут к эмулятору **только** через MCP
`v06c-mcp`; единственный легальный внешний бинарь — `v06c-asm-export`. Декодировать
опкоды и строить CFG скриптам запрещено — это делает отладчик. Ad-hoc py-ки в
обход пакета не пишутся: общего алгоритма нет в `utils/analyze` — расширяем пакет;
в `tools/` держим только ROM-специфичное (адреса дорожек, layout, спеки).

Канонический старт — только `debug_load_rom`; **не** `debug_reset` (вешает CPU на
busy-wait `OUT 1C / IN 1B`, BP не достигается). Промежуточные отчёты —
`./reports/StageN.md`; RDB — `./src/riseout.rdb`; ASM — `./asm/`; спеки —
`./tools/`; готовые MIDI — `./riseout_title.mid`, `./riseout_level.mid`.

## Stage 1. Карта памяти, активность чтения/записи

Полностью делает `run_pipeline.sh` (стадии `probe`, `disassembly`, `memory_diff`,
`coverage`). Отчёт `./reports/Stage1.md` собирается из JSON-результатов прогона
`report_gen.py` — **обязательно с фильтром по модулям стадии**; без `--modules`
генератор подмешивает общий разбор вызовов со всего сеанса, и Stage1.md станет
неотличимым от отчётов других стадий (это уже приводило к «клонам»):

```bash
report_gen.py --results .scratch/pipeline/riseout \
  --modules probe,disassembly,coverage,memory_diff,io_signature \
  --stage 1 --title "Stage 1. Карта памяти и активность чтения/записи (riseout.rom)" \
  --out reports/Stage1.md
```

Verified Facts / Inferences / Limitations. Руками ничего не переснимается.

## Stage 2. Посев RDB, линт, покрытие до fixpoint

Делает `run_pipeline.sh` (`seed_rdb → rdb_lint → coverage`). Здесь **создаётся
`src/riseout.rdb`**. Объекты получают только технические имена (`func_0100`,
`data_3b00`), `size = 0`, если отладчик не дал размер; один адрес — один объект
(AFTER.md §5), вторые имена — в `properties.aliases`. Отчёт `./reports/Stage2.md`
генерировать тем же `report_gen.py` с фильтром
`--modules seed_rdb,rdb_lint,coverage --stage 2` (см. Stage 1 про обязательность
`--modules`).

## Stage 3. Подробное исследование функций (семантика — за ИИ)

Python дал кандидатов — ИИ называет. Для каждой функции из RDB: осмысленное имя
(снимает `_unknown`), комментарий-назначение (русский текст), свойства
`params`/`reads`/`writes`/`calls`; связи `debug_add_rdb_link`
(function→function/data/music/interrupt). Сохранение RDB — только
`debug_save_rdb`, не правкой JSON на диске. Отчёт `./reports/Stage3.md`.

## Stage 4. Параметры функций

Кандидатов ABI даёт `abi_scan` (`--all --limit …`). ИИ подтверждает/переименовывает
и пишет в RDB `properties.params` (рег/стек/накопитель, размер, семантика).
Отчёт `./reports/Stage4.md`.

## Stage 5. Прерывания

Векторы: `0x0008/0x0010/0x0018/0x0020` (RST 0/8/16/24), `0x0038` (RST 32),
`0x003C` INTERPT (`docs/VECTOR_VERIFIED.md`). Особое внимание — `RST 7`
(аппаратный VBlank 50 Гц): кадровый тикер, потенциальный драйвер звука/анимации.
Порт-сигнатуры из `io_signature` совмещаются с адресами обработчиков; каждый
обработчик — объект `func_irq_*` с комментарием. Отчёт `./reports/Stage5.md`.

## Stage 6. Главный игровой цикл

На старте — заставка `HIT BUTTON OR SPACE KEY`. Найти цикл опроса клавиатуры
(порт `KEYSTROB`/`KEYDATA`) → `lbl_title_key_poll`; пройти код после нажатия
(инициализация уровня → игровой цикл) → `func_main_game_loop`. Шаг за шагом
(десятки итераций) выявить игровые переменные и зафиксировать в RDB: `var_score`,
`var_lives`, `var_level`, `var_speed`, `var_player_x` и т.п.
Отчёт `./reports/Stage6.md`.

## Stage 7. Вывод текста на экран

Строки-кандидатов находит `strings_scan` (в ROM уже видны, напр.: `^LEVEL COMPLETE^`
@0x1BE5, `RISE OUT^2!!` @0x1C9A, `^ READY ^` @0x223A, `^ GAME OVER ^…` @0x2256,
`SCORE: 00 MEN: 5 LEVEL: 1` @0x23B2, `HIT BUTTON OR SPACE KEY` @0x2A9D,
`SELECT SPEED LEVEL` @0x2BDD — и другие, включая KOI8-русские). ИИ подтверждает,
классифицирует, создаёт объекты `str_*` (комментарий = содержимое строки).
Найти функцию вывода строк и её базовый адрес глифов (`data_glyph_block`);
растровую сетку подтвердить `glyph_scan` (PNG на адресе блока), предсказание
картинки сверить с реальностью `vram_credits` (`MATCHED` = рендерится как
предсказано, иначе `MISMATCH` — разбирается ИИ). Задача выполнена, когда найдены
глифы всех строк. Отчёт `./reports/Stage7.md`.

## Stage 8. Экспорт функций в ASM и round-trip

Делает `run_pipeline.sh` (`export_asm` → `toolchain_lint` →
`symbolic_operand_lint` → `syntax_check` → `roundtrip_verify`): экспорт через
`v06c-asm-export` в формате z88dk (`DEFB/DEFW/DEFM`, `INCBIN`, метки без точки),
символьные имена там, где адрес совпал с началом RDB-объекта (иначе hex,
внутри функций `loc_XXXX`), и побайтовая сверка ROM→ASM→бинарь (`0 расхождений =
Fact`). ИИ лишь дополняет имена/комментарии в RDB до финального экспорта.
Отчёт `./reports/Stage8.md` генерировать `report_gen.py` с фильтром
`--modules export_asm,toolchain_lint,symbolic_operand_lint,syntax_check,roundtrip_verify,measure_sizes --stage 8`.

## Stage 9. Карты уровней

Из строк `LEVEL COMPLETE`/`MORE LEVELS IN`/`LEVEL: 1`/`SELECT SPEED LEVEL` видно,
что уровней несколько и они перебираются по кругу (аркада «уходи с уровня наверх»:
карта = сетка платформ + спавн игрока + бонусы/выход). В `func_level_loader`
найти: формулу адреса карты `base + (level-1)*stride`, цикл обхода `M×N`
(1 или 2 байта на тайл), координаты спавна/выхода. Определить `data_level_maps`,
`LEVEL_COUNT`, проверить `LEVEL_COUNT*stride == data_next_addr - data_level_maps_addr`.
Создать `data_level_01 … data_level_NN`, помня «один адрес — один объект»: если
база совпадает с первой картой, `data_level_01` не плодится, первые `stride` байт
описывает комментарий `data_level_maps`. Границы/размеры подтвердить `table_shape`
и `measure_sizes`. Отчёт `./reports/Stage9.md`.

## Stage 10. Выгрузка данных в ASM

Для каждого data-объекта RDB — файл `./asm/<имя>.asm` (z88dk). ROM-backed
(`data_*`/`str_*`/`music_*`, таблицы указателей) — фактические байты (`DEFB` по
8/16, `DEFW` для слов, `DEFM`+явный терминатор `0x00`/`0xFF`); RAM-backed
(`var_*`, runtime-буферы, векторы, растр `0x6000…`) — только EQU/метки, без байтов.
В таблицах указателей — символьные имена по правилу Stage 8. Крупные блоки
(глифы/логотипы/паттерны) допустимо выгружать `INCBIN asm/bin/<имя>.bin` (бинарь —
прямой `debug_read_memory_range`, без пост-обработки). Отчёт `./reports/Stage10.md`.

## Stage 11a. Мелодия ЗАСТАВКИ → `riseout_title.mid`

1) Драйвер: `RST 7` (VBlank ~50 Гц) или явный тикер в цикле `HIT BUTTON OR SPACE
   KEY`; функция, пишущая в звуковые порты (0x09/0x0A/0x0B — каналы/строб VI53;
   0x0B/0x0D — AY регистр/данные). В RDB: `func_music_driver_title` + комментарий
   («вызывается из…», «пишет в порты…», «шаг = N тиков VBlank»).
2) Партитуры: базы дорожек (по голосу) и таблица указателей (или `base + N*stride`);
   текущие указатели чтения в RAM (`var_music_ptr_title_NN`); признаки конца/петли.
   В RDB: `data_music_scores_title`, `data_music_track_title_NN`, `var_music_ptr_title_NN`.
3) Формат ноты: разделение байта на «тон/делитель таймера» и «длительность в
   шагах»; спец-коды (пауза/повтор/темп/громкость/цикл); таблица
   `data_note_freq_table_title` (период VI53 или регистр AY) — проверить
   равнотемперированность `period[i] ≈ round(K/2^(i/12))`, `K ≈ 3822` при 1.5 МГц,
   A4=440. **offset кода → MIDI note** ставим экспериментально.
4) Порт-вывод по каналам: чип/голос, последовательность `OUT` (регистр→данные→строб),
   преобразование «код ноты → значение в порт»; сверка с `docs/VECTOR_VERIFIED.md`.
5) Спека `./tools/music_spec_title.json` по схеме `v06c-music-spec/1`;
   обязательные поля
   `schema/title/rom/org/output/format/ppq/tempo/note_offset/rest_code/velocity`,
   `provenance.facts_from`, `tracks[]` (`name/address/length/source`
   `image|runtime`/`midi_channel/gm_program/step_ticks/expect` — дамп кодов,
   сверяется побайтово). Markdown-спека: `./reports/Stage11a_music_spec.md`.
6) MIDI: `music2midi --spec tools/music_spec_title.json -o riseout_title.mid
   --rom src/riseout.rom` (с `--runtime`, если дорожка читается из RAM — ROM должен
   работать на заставке). Обновить связи RDB (`func_music_driver_title` ↔
   `data_music_*` ↔ `var_music_ptr_*`) и комментарий «код → частота», `debug_save_rdb`.
7) Критерий приёмки: MIDI открывается, ноты/длительности соответствуют слуху,
   `expect`-дампы совпали. Отчёт `./reports/Stage11a.md`.

## Stage 11b. Мелодия УРОВНЯ → `riseout_level.mid`

Аналог 11a для внутриигровой мелодии. Отличия: найти переключение «заставка →
уровень» (смена базы/таблицы указателей либо `var_music_track_index`, либо загрузка
«уровневого» трека в RAM). `func_music_driver_level` — та же функция или её второй
экземпляр (если адрес тот же — алиас через `properties.aliases`, «один адрес — один
объект»). Новый набор `data_music_track_level_NN` (возможно другой stride/длина),
`data_music_scores_level`, `var_music_ptr_level_NN`; формат ноты сверяется заново
только по таблице периодов и темпу. Спека `./tools/music_spec_level.json`
(`output` = `../riseout_level.mid`), `./reports/Stage11b_music_spec.md`, MIDI через
`music2midi --runtime` (партитура уровня разворачивается в RAM по ходу игры — нужен
живой эмулятор на уровне). Критерий: MIDI открывается; `title` vs `level` слышно
разными; `expect`-дампы сошлись. Отчёт `./reports/Stage11b.md`.

## Stage 12. Сборка нового `RISEOUT_NEW.ROM` из `./asm/`

1) Мастер компоновки `asm/riseout_new.asm` + генератор `tools/gen_layout.py`
   раскладывает объекты RDB по адресам
   оригинала; для гэпов пишет `asm/bin/gap_*.bin` verbatim из `debug_read_memory_range`.
2) `Makefile`: `layout`, `src/RISEOUT_NEW.ROM`
   (z80asm `-b -m=8080_strict -s`), `verify` (побайтовая сверка с `riseout.rom`:
   0 расхождений), `deploy` (по `finally.mk`).
3) Цель — ROM, работающий как оригинал (допустимо со сдвинутым адресным
   пространством); байт-в-байт идентичность — достаточный, но не обязательный
   критерий.
4) Проверка поведения через MCP (boot-регистры, заставка, SPACE→игра, HUD/VRAM,
   порты звука 0x09/0x0A/0x0B). Отчёт `./reports/Stage12.md`.

## Приоритеты и порядок

- **Stage 0 (`run_pipeline.sh`) — точка входа**: он закрывает Stage 1, 2, 8 и
  значительную часть 4/7/9/10 механикой. Затем ИИ добирает Level C (семантику,
  имена, таблицы, карты) и Stage 11a/11b (обе обязательны — экспорт двух MIDI).
- Порядок ручных этапов: 3 → 4 → 5 → 6 → 7 → 9 → 10 → 11a → 11b → 12.
- **Правила исполнения (обязательны для исполнителя, чтобы не зациклиться):**
  1. **Один Stage = один заход.** Ручные этапы идут строго последовательно,
     **нельзя** делегировать пачку Stage одному агенту/под-агенту за раз. Каждый
     этап — отдельный проход и отдельный `reports/StageN.md`.
  2. **Сохранять RDB инкрементально.** Каждую пачку правок (имена/комментарии/
     `params`/связи) сразу фиксировать `debug_save_rdb` и проверять сохранение;
     не копить все правки до конца этапа. Единственный канал записи —
     `debug_save_rdb` (`.rdb` руками не править).
  3. **Отчёты стадий — только через `report_gen.py --modules <модули стадии>`**
     (карта модулей в Stage 1/2/8 выше). Иначе `StageN.md` выглядят одинаково.
- После ручных правок RDB — пересобрать экспорт/round-trip (`run_pipeline.sh
  riseout --resume` либо `--only export_asm`+зависимые).

## Итоговые артефакты, которые должны существовать на выходе

```
roms/redesign/riseout/
├── TZ.md                              (этот файл)
├── pipeline.json                      (профиль запуска: stage_args, persistence)
├── Makefile
├── riseout_title.mid                  (Stage 11a)
├── riseout_level.mid                  (Stage 11b)
├── src/
│   ├── riseout.rom                    (исходник)
│   ├── riseout.rdb                    (рождается Stage 0; финал — после Stage 12)
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
