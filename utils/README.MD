# Утилиты конвертации музыки и графики для Вектора-06Ц

Скрипты обеспечивают полную цепочку: исходные данные NES → компилируемые
файлы `.inc` для ROM Вектора-06Ц.

## Музыкальный пайплайн

```
NSF-экспорт (TXT) ──▶ txt2mus.py ──▶ .mus ──▶ find_repeats.py ──▶ _rep.mus ──▶ mus2inc.py ──▶ .inc
MIDI (.mid) ───────▶ midi2mus.py ──▶ .mus ─┘   (или правка .mus руками: mus_transpose.py)
WAV оригинала ─────▶ dmc2smp.py ───▶ .smp ────▶ mus2inc.py ──▶ .inc   (шум; в nu_pogodi не идут)
```

Или одной командой:

```
txt2inc.py track.txt -o track_music.inc
```

### txt2mus.py

Конвертер текстового экспорта NSF (Jackal, Castlevania) в партитуры `.mus`.

```bash
python3 utils/txt2mus.py track_0.txt [-o out.mus] [--tempo N] [--verify] [--self-test]
```

- Вход: `*.txt` (NSF-экспорт с секциями Square1/2, Triangle, Noise, DPCM)
- Выход: `.mus` — текстовая партитура с токенами O/L/P/ноты/BEGIN/END
- Секции: Square1 → score0, Square2 → score1, Triangle → score2, Noise+DPCM → drums
- Циклы: `BEGIN_CYCLE` / `END_CYCLE` → `BEGIN … END` со сбросом O/L
- Квантизация: PPQ = 32, темп из `--tempo` или из framerate (60 Гц → T225)

### mus_transpose.py

Транспонирование готовой партитуры `.mus` по октавам: меняет только команды
`O<n>` в выбранных партиях, остальное (ноты, длительности, повторы, темп,
комментарии) не трогает.

```bash
python3 utils/mus_transpose.py track.mus -n -1              # все голоса на октаву ниже
python3 utils/mus_transpose.py track.mus -n -1 --score 1     # только второй голос
python3 utils/mus_transpose.py track.mus -n 1 --dry-run      # отчёт без записи
python3 utils/mus_transpose.py --self-test
```

- Октавы прижимаются к диапазону 0..7 с предупреждением (очень низкие ноты
  `mus2inc.py` и так делает паузами — абсолютный номер ниже 12 не звучит)
- Печатает гистограмму октав «было/стало» по каждой партии — удобно для контроля
- Сделан потому, что ручная замена коротких токенов (`O5`→`O4`) в плотном тексте
  партитуры применяется частично: скрипт делает это детерминированно

### find_repeats.py

Поиск повторяющихся последовательностей токенов в `.mus` и замена на `[ ... ]n`.

```bash
python3 utils/find_repeats.py track.mus           # → track_rep.mus
python3 utils/find_repeats.py track.mus -o out.mus
```

- Алгоритм: перебор всех (позиция, длина), максимизация экономии токенов
- Защита границ: L/O-модификатор не отрывается от ноты
- Сбросы O/L при необходимости добавляются *внутрь* `[ ]n`
- Strip-оптимизация: удаление дублирующего ведущего модификатора
- Типичное сжатие: −40…55%

### mus2inc.py

Компилятор партитур `.mus` (и семплов `.smp`) в `.inc` для z88dk.

```bash
python3 utils/mus2inc.py track.mus -o track_music.inc [--name song_name] [--use-shared nes_drums]
```

- Формат `.mus`: `score0:`, `score1:`, `score2:`, `drums:`, `sample N:`, `Tempo:`, `Enabled:`
- Токены: O0–O7, L1–L128, P, C–B (с #/+/−), цифры (ударные), `[ ]n`, BEGIN/END
- Выход: `music_song_t` — структура с указателями на байткоды каналов
- Семплы: `--use-shared lib_name` — ссылка на общую библиотеку семплов
- Одиночный бинарный `.smp` как вход: партитур нет, компилируется только массив
  байтов (`--name miss_sample`) — так шумовой эффект попадает в ROM без `.mus`
  и играется через `drum_sample_play()` из `lib/snd/drums.asm`

### txt2inc.py

Оркестратор полной цепочки: TXT → .mus → повторы → .inc.

```bash
python3 utils/txt2inc.py track.txt -o track_music.inc [--name song_name] [--use-shared nes_drums]
```

Вызывает последовательно `txt2mus.py`, `find_repeats.py`, `mus2inc.py`.
Используется в Makefile для автоматической сборки.

### unrepeat.py

Обратная операция: разворачивает `[ ... ]n` в плоские токены для проверки.

```bash
python3 utils/unrepeat.py track_rep.mus           # → track_back.mus
```

Round-trip: `track.mus → track_rep.mus → track_back.mus` — `diff` должен
показать только переносы строк, но не различия в токенах.

## Ударные и семплы

### dmc2smp.py

WAV -> шумовой семпл `.smp` для drums.asm. Историически — озвучка DPCM-образцов
NES, теперь читает любой PCM WAV (8/16 бит, mono/stereo), поэтому годится и для
снятия конвертов с записей оригинала (nu_pogodi: catch/miss/gameover/ld/lu/rd/ru).
Та же строка, что и в `make smp` игры: `-g 0.1` (порог тишины как доля от пика RMS,
ведущие и замыкающие тише — обрезаются).

```bash
python3 utils/dmc2smp.py kick.wav kick.smp --frames 8 [--k 24000]   # как раньше
python3 utils/dmc2smp.py miss.wav -g 0.1                     # кадры по длительности
python3 utils/dmc2smp.py src/sounds/ -o src/sounds/ -g 0.1    # каталог .wav -> .smp
python3 utils/dmc2smp.py gameover.wav --fixed-r6 12 -v       # один период на всё
python3 utils/dmc2smp.py --self-test
```

- Формат `.smp`: байт N (кадры 50 Гц, N <= 255 => максимум 5.1 с), затем N пар
  (R6, R10) — период шума и громкость канала C AY-3-8910
- Анализ WAV: RMS -> громкость (пик файла = R10 15), спектральный центроид ->
  период шума `R6 = K / центроид`, K калибруется на слух (по умолчанию 24000)
- `--frames` без задания = ровно 50 кадров/с (длительность как в оригинале);
  `-g/--gate` — кадры тишины обнуляются и обрезаются по краям (0 — прежнее
  поведение: минимальная громкость 1, ничего не обрезается)
- На маршруте Tape Out (nu_pogodi) R6 — индекс числа сдвигов LFSR, R10 — duty-окно:
  направление то же, но абсолютный тембр отличается, поэтому после конверсии
  нужен контроль на слух (см. smp2wav.py)

### txt2smp.py

Синтез стартовых конвертов `.smp` из параметров Noise-канала NSF-экспорта.

```bash
python3 utils/txt2smp.py music_txt/ -o music/samples/ [--force]
```

- Собирает события Noise из всех треков, вычисляет медианные параметры
- DPMC-семплы (kick/snare) не перезаписываются — используются реальные `.smp`

### smp2wav.py

WAV-превью семплов `.smp` (моделирование генератора шума AY-3-8910).

```bash
python3 utils/smp2wav.py music/samples/              # все семплы → WAV
python3 utils/smp2wav.py music/samples/kick.smp      # один файл
```

## Графика

### bmp2inc.py

Конвертер 16-цветного BMP в `.inc` для ROM Вектора-06Ц (RLE-сжатие).

```bash
python3 utils/bmp2inc.py rom_data/title.bmp          # → rom_data/title_bmp.inc
```

- Формат Вектора-06Ц: 256×256, 16 цветов, 4 битовые плоскости
- Выход: `*_screen_rle` — RLE-массив, `*_palette` — палитра (порт 0C)
- Оптимизация: жадное назначение индексов + локальный поиск для минимизации RLE
- Выводит `graph_rle_expand(src, x, y)` (lib/graphrle.asm)

## Анализ сборки

### romconsist.py

Разбор состава ROM по карте линкера (`zcc -m`): сколько байт занимают
ресурсы (rodata — таблицы треков, картинки), код программы, библиотеки и
runtime. Показывает крупнейшие файлы и символы — подсказывает, что ужимать,
когда ROM переваливает за 32 КБ.

Обычно запускается через Makefile проекта:

```bash
make consist          # пересобрать с -m, показать состав, удалить карту
```

Вручную (если `.map` уже есть):

```bash
python3 utils/romconsist.py jackal.map [--top N] [--min BYTES]
```

- Источник — карта линкера: секционные агрегаты `__<section>_size` и
  построчные символы с полями `module / section / source`
- Размер символа = адрес следующего символа (или хвост раздела) минус его адрес
- Константы `defc` (`type=const`) отсекаются — у них «адрес» равен значению
- В конце — вердикт по лимиту 32 КБ и крупнейший ресурс

## Зависимости

- Python 3.6+
- Стандартная библиотека (math, os, re, sys, struct, wave, argparse)
- Для `bmp2inc.py`: Pillow (`pip install Pillow`)
