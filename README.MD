# Vector Games

Исходники ROM-проектов для ПК «Вектор-06Ц» (КР580ВМ80A / i8080): игры,
саундтреки NES, демо и тесты оборудования. Всё собирается локальным
тулчейном z88dk (`z88dk/` в корне репозитория) и запускается в эмуляторе
(PPSSPP — собранные ROM, Python-эмулятор — для отладки).

Звук: 3 тональных канала КР580ВИ53 + AY-3-8910 (шум/ударные).
Графика: 4 бит-плоскости VRAM, режимы 256×256 (16 цветов) и 512×256.
Всё синхронизировано от единого кадрового прерывания (50 Гц).

## Части проекта

| Папка | Что там | Документация |
|-------|---------|--------------|
| `lib/` | Библиотека взаимодействия с железом (без clib z88dk): gfx, snd, kbd, unpack, mem, comps, sys | [lib/README.md](lib/README.md) |
| `roms/games/` | Игры: портированная «Ну, погоди!» | [Makefile](roms/games/nu_pogodi/Makefile), [SPRITES.md](roms/games/nu_pogodi/SPRITES.md), [TEST.md](roms/games/nu_pogodi/TEST.md) |
| `roms/musics/` | Саундтреки NES (Jackal, Castlevania, DuckTales 2, Super Mario) и музыкальные демо/тесты | [roms/musics/README.MD](roms/musics/README.MD) |
| `roms/demos/` | Демо beam-race-рендеринга (огонь) | [OPTIMIZATION.MD](roms/demos/fire2/OPTIMIZATION.MD) |
| `roms/tests/` | Тесты отдельных функций библиотеки и режимов экрана | — |
| `roms/redesign/` | Реверс-инжиниринг оригинальных ROM Вектора (putup, riseout, clrs, testay): отчёты по стадиям | TZ.md / TZ2.md в папках проектов |
| `utils/` | Python-скрипты конверляции музыки, графики и семплов | [utils/README.MD](utils/README.MD) |
| `utils/emulator/` | Python-эмулятор Вектора-06Ц (8080) и тестовая обвязка | [v06_emu.py](utils/emulator/v06_emu.py), [v07_emu.md](utils/emulator/v07_emu.md) |
| `utils/analyze/` | Фреймворк анализа ROM (disassembly, RDB, отчёты) | [utils/analyze/README.MD](utils/analyze/README.MD) |
| `docs/` | Техническая документация по Вектору-06Ц и z88dk | список ниже |
| `release/` | Результат сборки (`make` в корне) | [release/README.MD](release/README.MD) |
| `z88dk/` | Локальный тулчейн (zcc, z80asm, clibs для vector06c) | — |

## Документация (docs/)

- [VECTOR.MD](docs/VECTOR.MD) — полная документация по процессору, ASM и машинному коду
- [VECTOR_VERIFIED.md](docs/VECTOR_VERIFIED.md) — результаты фактологического аудита документации
- [VECTOR_CPU_COMMANDS.md](docs/VECTOR_CPU_COMMANDS.md) — система команд КР580ВМ80A
- [512x256.MD](docs/512x256.MD) — режим экрана 512×256
- [vector_techinfo.md](docs/vector_techinfo.md) — техинформация по ПК «Вектор» (EMU80)
- [Z88DK.md](docs/Z88DK.md), [Z88DK_512_SOUND.md](docs/Z88DK_512_SOUND.md) — разбор библиотеки z88dk
- [Z88DK_CALL.md](docs/Z88DK_CALL.md) — соглашения о вызовах C ↔ ASM

## Сборка

```bash
make          # собрать все ROM (musics + tests), скопировать в release/
make full     # clean + сборка
make clean    # убрать артефакты всех проектов + release/
```

Отдельный проект:

```bash
cd roms/<группа>/<project>
make          # собрать ROM
make deploy   # собрать + скопировать в ROMS эмулятора PPSSPP
make full     # clean + deploy
```

Игры (`roms/games/`) и демо (`roms/demos/`) собираются только из своих
папок; у каждого проекта свой Makefile с дополнительными целями
(ассеты, музыка, проверка раунд-трипа).

## Пайплайн конвертации музыки

```
NSF-экспорт (TXT) ─▶ txt2mus.py ─▶ .mus ─▶ find_repeats.py ─▶ _rep.mus ─▶ mus2inc.py ─▶ .inc
MIDI (.mid) ──────▶ midi2mus.py ─┘            (правка .mus: mus_transpose.py)
WAV ──────────────▶ dmc2smp.py ──▶ .smp ─────▶ txt2smp.py / smp2wav.py (шумовые семплы)
```

Графика: `bmp2inc.py` / `bmp2inc512.py` / `bmp2inc_lz.py` — BMP → `.inc`
(RLE- и LZ-потоки в VRAM). Подробно — в [utils/README.MD](utils/README.MD).

## Зависимости

- **z88dk** — локальная папка `z88dk/` (переопределяется `make Z88DK=...`)
- **Python 3.6+** — скрипты конвертации и эмулятор
- **Pillow** — для bmp2inc.py (заставки)
- **vector-debugger (MCP)** — эмулятор с отладчиком для реверс-инжиниринга
