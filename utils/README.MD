# Утилиты конвертации музыки и графики для Вектора-06Ц

Скрипты обеспечивают полную цепочку: исходные данные NES → компилируемые
файлы `.inc` для ROM Вектора-06Ц.

## Музыкальный пайплайн

```
NSF-экспорт (TXT) ──▶ txt2mus.py ──▶ .mus ──▶ find_repeats.py ──▶ _rep.mus ──▶ mus2inc.py ──▶ .inc
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

Конвертер DPCM-семплов NES (извлечённых в WAV) в формат `.smp` для drums.asm.

```bash
python3 utils/dmc2smp.py kick.wav kick.smp --frames 8 [--k 24000]
```

- Формат `.smp`: байт N (кадры 50 Гц), затем N пар (R6, R10) — период шума
  и громкость канала C AY-3-8910
- Анализ WAV: RMS → громкость, центроид → период шума AY

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

## Зависимости

- Python 3.6+
- Стандартная библиотека (math, os, re, sys, struct, wave, argparse)
- Для `bmp2inc.py`: Pillow (`pip install Pillow`)
