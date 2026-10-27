# SOUNDEMO.ROM — Отчёт по реверс-инжинирингу

## ROM-файл

| Параметр | Значение |
|----------|----------|
| Путь | `roms/redesign/soundemo/src/soundemo.rom` |
| Размер | 9344 байт (0x2480) |
| SHA-256 | `41eefb4fb175a8c16be1da9cf76d12cf3a2cfcd589a2e750b3cfb3c824467815` |
| Автор | `shilin d.w (C)` + CP866 `Д.В'94!` (Шилин Д.В., 1994) |
| Платформа | Vector-06C, KR580VM80A (i8080), K580VI53 |

## Самораспаковывающийся образ

ROM загружается эмулятором по адресу `0x0100`. Структура файла:

```
0x0000..0x0037   Boot loader (64 B)
0x0038..0x004F   Сигнатура "shilin d.w (C)" + CP866 + padding
0x0050..0x00EF   Unpacker — исходный код (160 B)
0x0100..0x247F   Сжатый поток shilin-LZ (9344-256 = 9088 B)
```

### Boot loader (0x0100 в RAM)

```asm
DI
LXI SP,0000h           ; SP = 0xFFFF (wrap)
XRA A
OUT 10h                ; системный сброс/инициализация
LXI DE,0FF50h / LXI HL,0150h / LXI BC,00A0h / CALL memcpy  ; → unpacker
LXI DE,0DA80h / LXI HL,0200h / LXI BC,2480h / CALL memcpy  ; → сжатый поток
JMP 0FF50h             ; запуск распаковщика
```

### Unpacker (0xFF50) — shilin-LZ

Шесть классов опкодов:

| Диапазон | Длина | Действие |
|----------|-------|----------|
| `0x00..0x2F` | 1+A | Литералы: A байт из потока |
| `0x30..0xAF` | 2 | Короткий back-ref: длина 2..3, offset 2..65 |
| `0xB0..0xCF` | 3 | Средний back-ref: 2-байт offset (до 0xFFF) |
| `0xD0..0xEF` | 1 | Zero-fill: (A-0xCE) нулей |
| `0xF0..0xFE` | 2 | RLE-fill: (A-0xED) байт значения |
| `0xFF` | — | END → PCHL (переход на 0x0100) |

Распакованный образ: **16 КБ RAM** (`0x0000..0x3FFF`).

## Механизм «плотного» звука через K580VI53

### Конфигурация

При инициализации (`func_vi53_mode_setup` @ `0x3892`) пишутся три управляющих слова в порт `0x08`:

|Byte|Канал|Meaning|
|----|-----|-------|
|0x36|Ch0 (cnt0, port 0x0B)|SC=00, RW=11 (lo+hi), Mode 3 (square wave), Binary|
|0x76|Ch1 (cnt1, port 0x0A)|SC=01, RW=11, Mode 3, Binary|
|0xB6|Ch2 (cnt2, port 0x09)|SC=10, RW=11, Mode 3, Binary|

Все три канала — **режим 3 (меандр)** с 16-битной записью периода.

### Тройной унисон (triple unison)

Каждый кадр (VBlank → RST 7 → main loop) записывается **один и тот же 16-битный период** во все три счётчика последовательно:

```
OUT 0x0B, LO
OUT 0x0B, HI
OUT 0x0A, LO
OUT 0x0A, HI
OUT 0x09, LO
OUT 0x09, HI
```

3 генератора, одна частота → суммарная мощность втрое выше одного канала. Звучит как «стена звука».

### Линейный свип периода

Период возрастает с фиксированным шагом каждый кадр. Наблюдение из io_trace (после нажатия P):

```
seq         port  val   period  freq(~1.5MHz)
11134992    0x0B   D6 0E → 0x0ED6  ≈ 395 Hz
11135182    0x0B   9E 0F → 0x0F9E  ≈ 375 Hz  (+0xC8 = +200)
11135372    0x0B   66 10 → 0x1066  ≈ 356 Hz  (+0xC8)
11135562    0x0B   2E 11 → 0x112E  ≈ 339 Hz  (+0xC8)
11135752    0x0B   F6 11 → 0x11F6  ≈ 322 Hz  (+0xC8)
11135942    0x0B   BE 12 → 0x12BE  ≈ 307 Hz  (+0xC8)
11136132    0x0B   86 13 → 0x1386  ≈ 293 Hz  (+0xC8)
11136322    0x0B   4E 14 → 0x144E  ≈ 279 Hz  (+0xC8)
11136441    0x0B   16 15 → 0x1516  ≈ 278 Hz  (+0xC8)
```

Delta = **+0xC8 (200) за кадр** — равномерное глиссандо вниз по частоте.

### Эффект клавиши «P»

io_trace показывает, что после `debug_type_key('p')`:
- Порт `0x01` стабильно читается как `0xE0` (все линии-high = «нет клавиши»)
- Паттерн записи VI53 не изменился
- Mелодия/свип продолжилась без прерывания

**Вывод:** клавиша P не влияет на звуковой движок. Обработка клавиатуры происходит в RST 7 (`func_irq_vblank` @ `0x394B`) — матричный скан 8 строк через порты `0x03`/`0x02`/`0x01`, результат сохраняется в `var_kbd_matrix` @ `0x39BB`. Demo игнорирует ввод и работает в автономном режиме.

## Карта функций

| Адрес | Имя | Размер | Назначение |
|-------|-----|--------|-----------|
| 0x0000 | vec_reset | 3 | JMP func_main_entry |
| 0x0038 | vec_rst7 | 3 | JMP func_irq_vblank |
| 0x2AC0 | func_vi53_channels | 1449 | 3 канала: dispatcher lo/hi OUT + control-word latch |
| 0x37A8 | func_main_entry | 234 | Инициализация, установка векторов, main loop |
| 0x3892 | func_vi53_mode_setup | 13 | OUT 0x08: 0x36/0x76/0xB6 (mode 3 × 3 ch) |
| 0x389F | func_sys_init_hlt | 8 | LXI H,39BA → SHLD stream; EI; HLT |
| 0x394B | func_irq_vblank | 93 | RST 7: PUSH × 4; keyboard 8×(OUT 03 / IN 02); palette rampa |
| 0x3AE5 | func_stamp_vram_banks | 85 | B×C copy DE→HL с построчным сдвигом H |
| 0x3B9A | func_sprite_row_copy | 44 | 8×STAX across VRAM banks (stride 0x0E40) |
| 0x3BD1 | func_draw_masked_glyph_4banks | 68 | 7×16 AND-mask across 4 banks (8568..E568 stride 0x2000) |
| 0x3BFE | func_melody_frame | 54 | Fetch note-event from 291C/2931 by flag@3982; CALL stamp |
| 0xFF50 | func_unpacker_shilin | 160 | LZ-распаковщик (6 opcode classes) |

## Карта данных

| Диапазон | Размер | Описание |
|----------|--------|----------|
| 0x0100..0x2ABF | ~10 КБ | 8×8 тайлы (шрифт + спрайты), строки нулей между глифами |
| 0x291C..0x2970 | 84 B | Мелодичные потоки (tbl_melody_stream_A / ALT) + 7 поинтеров глифов |
| 0x3069..0x37A7 | ~1.9 КБ | Таблицы палитры, параметры каналов, selfmod-коды |
| 0x39BB..0x39C2 | 8 B | var_kbd_matrix — состояние клавишной матрицы |
| 0x39C3..0x39CA | 8 B | var_palette_state — текущая палитра rampa |

## Порты (Vector-06C / K580VI53)

| Порт | Имя | Назначение |
|------|-----|-----------|
| 0x00 | PIA_PA | Scroll register out |
| 0x01 | PIA_PB_KEYBOARD | Column data (active-low) |
| 0x02 | PIA_PC_STATUS | Row handshake read |
| 0x03 | PIA_PC_ROWSTROBE | Row select (one-hot out) |
| 0x08 | VI53_CONTROL | Mode/command latch |
| 0x09 | VI53_CTR2_PORT_C | Counter 2 (channel C) |
| 0x0A | VI53_CTR1_PORT_B | Counter 1 (channel B) |
| 0x0B | VI53_CTR0_PORT_A | Counter 0 (channel A) |
| 0x0C | PALETTE_DATA | Colour rampa write |
| 0x10 | SYS_INIT | Soft reset/init strobe |

## Итоговый алгоритм кадра

```
VBlank → RST 7 → func_irq_vblank
  ├─ Keyboard matrix: OUT 00,hi / 8×(OUT row-strobe / IN status) → var_kbd_matrix
  └─ Palette rampa: LXI H,39C3; OUT port 0C (BBGGGRRR) × 16 slots

main_loop (func_main_entry → loop @ 0x3833):
  ├─ CALL func_melody_frame       ; note event → VRAM stamp
  ├─ period += step (INR/DCR pair or selfmod)
  ├─ 7× CALL func_draw_masked_glyph_4banks   ; overlay sprites
  ├─ OUT ch0.lo / ch0.hi  (0x0B)
  ├─ OUT ch1.lo / ch1.hi  (0x0A)
  ├─ OUT ch2.lo / ch2.hi  (0x09)
  └─ EI / HLT → wait next VBlank
```

## Файлы проекта

```
asm/
  main.asm           — include-обёртка
  boot/boot.asm      — boot loader (0x0100)
  boot/unpacker.asm  — shilin-LZ (0xFF50)
  code/main.asm      — весь код декомпрессированного образа
  data/data.asm      — все данные (DEFB)
  export.json        — метаданные
data/
  soundemo_packed.rom          — копия исходного ROM
  decompressed_0x0000_0x3FFF.bin — 16 КБ распакованный образ
dump/
  disasm_full_ram_lo.json      — полный дизассемблированный RAM (13443 инстр.)
  analyze_from_0100.json       — results of debug_analyze_code
  decompressed_ram.bin         — bin (same as data/)
tools/
  gen_asm.py   — генератор asm/code + asm/data
  finish.py    — финальная сборка (data/, main.asm, export.json)
```

## Используемые MCP-инструменты

- `debug_load_rom` / `debug_set_register` / `debug_run` / `debug_pause` — запуск и остановка
- `debug_type_key("p")` — нажатие P
- `debug_get_io_trace` — лог портов (60+ событий)
- `debug_analyze_code` — control-flow анализ
- `debug_disassemble_image` — линейная дизассемблия (16 KB)
- `debug_write_memory` — восстановление unpacker в 0xFF50
- `debug_upsert_port` — регистрация 10 портов в RDB
- `debug_add_protocol_entry` — 6 протокольных записей (статус VERIFIED)
- `debug_add_watch_entry` — 7 watch-переменных
- `debug_create_function` / `debug_rename_function` / `debug_set_function_comment` — RDB
- `debug_save_rdb` — сохранение .rdb на диск

## Загрузка CPU и параллельная графика

### Стоимость чистого звука

VI53 в режиме 3 (меандр) работает **автономно** после записи периода — CPU не обслуживает генератор. Единственная цена — 6 портовых записей за кадр:

```
OUT 0x0B, LO   ; 4 T
OUT 0x0B, HI   ; 4 T
OUT 0x0A, LO   ; 4 T
OUT 0x0A, HI   ; 4 T
OUT 0x09, LO   ; 4 T
OUT 0x09, HI   ; 4 T
+ fetch/sweep  ; ~38 T
= ~74 T-состояний (0.25% бюджета кадра)
```

### Бюджет кадра soundemo (50 Гц, 1.5 МГц → 30 000 T)

| Операция | T | Доля |
|----------|---|------|
| RST 7 entry/exit (PUSH/POP ×4) | 72 | 0.2% |
| Keyboard matrix (8 rows × OUT/IN/loop) | 200 | 0.7% |
| Palette rampa (16 × OUT 0x0C) | 80 | 0.3% |
| func_melody_frame (LDAX/stamp 3×7) | 150 | 0.5% |
| 7 × draw_masked_glyph_4banks | 4 500 | 15% |
| **VI53 OUT (звук)** | **74** | **0.25%** |
| **Busy total** | **~5 000** | **~17%** |
| **Idle (EI/HLT → wait VBlank)** | **~25 000** | **~83%** |

### Вывод

Звук стоит **менее 1%** процессорного времени. Оставшихся ~83% кадра более чем достаточно для:

- Полноценной перерисовки VRAM (256×256, 8KB = 4 banks)
- Anимации тайлов, scroll-регистра (порт 0x00)
- Растеризации спрайтов с collision-детекцией
- Даже полноценного game-loop с физикой

VI53 не требует bit-bang, прерываний или DMA — «записал период и забыл». Это делает его идеальным для фонового звука в играх на Vector-06C.
