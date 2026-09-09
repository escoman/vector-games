# ТЗ: Реинжиниринг ROM putup.rom

## Цель

Восстановить код и данные игры PUTUP (Vector-06C) для последующего воссоздания ROM из исходников.
Итоговый `putup_new.rom` должен быть байт-в-байт идентичен оригиналу.

## Исходные данные

- `src/putup.rom` — 17664 байта, загружается по адресу 0x0100
- `src/putup.rdb` — база анализа RDB (84 функции, все с именами `sub_XXXX`)
- Эмулятор Vector-06C с MCP-сервером для отладки

## Структура ROM (карта памяти)

### Кодовые регионы (определены через RDB + debug_analyze_code)

| Адрес       | Размер  | Описание |
|-------------|---------|----------|
| 0x0100      | 4       | ROM entry: DI; JP main_init |
| 0x0104      | 29      | load_and_draw_text, put_char_vram helpers |
| 0x0121      | ~175    | draw_sprite_tiles, put_char_vram, draw_tile, keyboard_check, pixel_draw_dispatch |
| 0x0200      | ~387    | sprite_render, string_draw_loop, coord_calculator, collision helpers |
| 0x0383      | ~30     | sys_init (настройка ISR), isr_handler |
| 0x0401      | ~656    | graphics_decompress, bitplane_render, graphics_render_dispatch |
| 0x053B      | ~141    | graphics_render_continue, graphics_render_dispatch |
| 0x0800      | ~320    | Game helper code (до sprite_definitions) |
| 0x0B57      | ~912    | main_init, game_loop_hud, movement_handler, collision_detect, entity_dispatch_loop, delay_routine, input_handler |
| 0x0F09      | ~2675   | 10 entity handlers, multiply_16bit, score_display_update, timer_countdown |
| 0x197C      | ~708    | game_state_handler, draw_multi_char, draw_function, copy_de_to_hl, screen_clear |
| 0x3D00      | ~256    | system_palette_routine, system_init_routine, system_dispatch |

### Регионы данных

| Адрес       | Размер  | Описание |
|-------------|---------|----------|
| 0x016C      | 16      | Jump table (8 адресов × 2 байта) |
| 0x0280      | 16      | Jump table для pixel_draw_dispatch |
| 0x051B      | 33      | ALU operation table |
| 0x0691      | ~287    | Sprite lookup table (MOV L,C/D/E паттерны) |
| 0x093A      | ~454    | Sprite definitions (пиксельные данные) |
| 0x1C40      | ~4897   | Graphics tile data |
| 0x2F61      | 224     | Music data: 28 блоков × 8 байт (копируется в RAM 0x7418) |
| 0x3041      | ~2041   | Fill data + system variables |
| 0x3E00      | ~1792   | ROM tail data |

### Межфайловые зависимости (план)

```
asm/header.asm         → asm/game.asm (JP main_init)
asm/text.asm           → asm/draw.asm (CALL copy_de_to_hl)
asm/sprites.asm        → asm/sprite_render.asm, asm/game.asm
asm/sprite_render.asm  → asm/text.asm (CALL draw_tile_01A1)
asm/graphics.asm       → asm/sprite_render.asm (CALL sound_or_draw)
asm/game.asm           → asm/system.asm (CALL sys_init)
                       → asm/graphics.asm (CALL graphics_decompress)
                       → asm/text.asm, asm/sprites.asm, asm/draw.asm
asm/entities.asm       → asm/text.asm, asm/sprites.asm, asm/draw.asm, asm/game.asm
asm/draw.asm           → asm/text.asm, asm/sprites.asm, asm/game.asm, asm/entities.asm
asm/system_routines.asm → asm/sprites.asm (CALL pixel_draw_dispatch)
```

## Инструменты MCP

### Доступные

| Инструмент | Назначение |
|------------|------------|
| `debug_read_memory_range` | Чтение до 16384 байт за вызов (bulk ROM access) |
| `debug_disassemble` | Дизассембляция N инструкций от адреса |
| `debug_analyze_code` | CFG-анализ от точки входа (JMP/CALL/Jcc/RST) |
| `debug_get_symbols` | Список всех функций (84 шт.) |
| `debug_get_function` | Информация о функции (адрес, размер) |
| `debug_create_function` | Создать функцию в RDB |
| `debug_rename_function` | Переименовать функцию |
| `debug_set_comment` | Добавить комментарий к функции |
| `debug_save_rdb` | Сохранить RDB |

### Нужные (отсутствуют)

| Инструмент | Назначение |
|------------|------------|
| `debug_export_rom` | Выгрузка ROM в бинарный файл на диске |
| `debug_disassemble_range` | Дизассембляция диапазона с авто-метками ветвлений |

## Конвертация 8080 → z80asm

| 8080 (Intel)           | z80asm (Zilog)         |
|------------------------|------------------------|
| `LXI H,nnnn`          | `ld hl,nnnn`          |
| `MOV A,M`             | `ld a,(hl)`           |
| `MOV M,A`             | `ld (hl),a`           |
| `MVI A,nn`            | `ld a,nn`             |
| `LDA addr`            | `ld a,(addr)`         |
| `STA addr`            | `ld (addr),a`         |
| `LHLD addr`           | `ld hl,(addr)`        |
| `SHLD addr`           | `ld (addr),hl`        |
| `LDAX D` / `STAX B`  | `ld a,(de)` / `ld (bc),a` |
| `INX H` / `DCX D`    | `inc hl` / `dec de`   |
| `DAD B` / `DAD D`    | `add hl,bc` / `add hl,de` |
| `ORA A` / `XRA A`    | `or a` / `xor a`      |
| `ANI nn` / `ORI nn`  | `and nn` / `or nn`    |
| `CPI nn`              | `cp nn`               |
| `JZ/JNZ/JC addr`     | `jp z/nz/c,addr`      |
| `CALL addr`           | `call addr`           |
| `PUSH PSW` / `POP PSW`| `push af` / `pop af`  |
| `RRC`/`RLC`/`RAR`/`RAL` | `rrca`/`rlca`/`rra`/`rla` |
| `CMA`/`CMC`/`STC`    | `cpl` / `ccf` / `scf` |
| `RNZ`/`RZ`/`RC`      | `ret nz`/`ret z`/`ret c` |
| `DB nn` / `DW nnnn`  | `defb nn` / `defw nnnn` |

**Ограничение:** НЕ использовать `jr` (не поддерживается КР580ВМ80А).

## План работы

1. **Извлечь данные** — прочитать регионы данных через `debug_read_memory_range`, сохранить в `assets/*.inc`
2. **Дизассемблировать код** — для каждого кодового региона использовать `debug_disassemble` + ручная конвертация в z80asm
3. **Создать asm-файлы** — записать в `asm/*.asm` с ORG, PUBLIC/EXTERN, метками
4. **Создать Makefile** — сборка через z80asm
5. **Верификация** — `putup_new.rom` == `putup.rom` (байт-в-байт)

## Структура проекта (целевая)

```
putup/
├── Makefile
├── putup.asm              (master file с include)
├── asm/
│   ├── header.asm         — 0x0100: ROM entry
│   ├── text.asm           — 0x0104: text rendering
│   ├── sprites.asm        — 0x0121: sprite/tile drawing
│   ├── sprite_render.asm  — 0x0200: sprite rendering via I/O ports
│   ├── graphics.asm       — 0x0401: graphics decompression + VRAM write
│   ├── game.asm           — 0x0B57: main game logic
│   ├── entities.asm       — 0x0F09: entity handlers
│   ├── draw.asm           — 0x197C: draw functions
│   ├── system.asm         — 0x0383: sys_init, isr_handler
│   └── system_routines.asm — 0x3D00: system routines
├── assets/
│   ├── lookup_tables.inc  — jump table + ALU table
│   ├── sprite_table.inc   — sprite lookup table
│   ├── sprite_defs.inc    — sprite definitions
│   ├── gfx_data.inc       — graphics tile data
│   ├── music_data.inc     — music data
│   └── system_data.inc    — fill data + system vars
└── src/
    ├── putup.rom          (оригинал)
    └── putup.rdb          (база анализа)
```

## Примечания

- z80asm не поддерживает ORG в каждом файле при сборке нескольких файлов — используется master file с `include`
- z80asm не поддерживает cross-file PUBLIC/EXTERN — все файлы компилируются как единое целое через `include`
- `debug_analyze_code` находит только статически достижимый код (не видит косвенные вызовы через jump tables)
- В ROM есть jump tables (0x016C, 0x0280) которые линейный дизассемблер интерпретирует как код
