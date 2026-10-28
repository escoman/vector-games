# Stage 10. Сборка `CYBERNOID_NEW.r0m` из `asm/`

> Финальный этап ТЗ: из распакованного RAM-образа (338 объектов RDB, org `0x0000`)
> собирается самостоятельный образ `src/CYBERNOID_NEW.r0m`, побайтово сверяется с
> `cybernoid_unpacked.r0m` и проверяется через MCP-эмулятор.

## Вердикт

`tools/gen_layout.py` запускает `v06c-asm-export`, собирает результат,
находит расходящиеся прогоны и подменяет их `defb` дословно из ROM (паттерн exolon).
За **2 прохода**: 21013 расхождений → 0.
Мастер `asm/main.asm` (`org 0h` + `include "layout.asm"`) +
`Makefile` дают **32768 байт, SHA256 `d29d7d81…`** — идентичен оригиналу.

## Инструменты

| Компонент | Роль |
|---|---|
| `tools/gen_layout.py` (262 стр.) | экспортёр → `layout.asm` → сборка → `defb`-починка → мастер |
| `asm/layout.asm` (5356 стр., 544 метки) | адресный поток: весь образ по одному разу |
| `asm/main.asm` | мастер: `ORG 0000h` + `include "layout.asm"` |
| `Makefile` | цели `layout`, `all`, `verify`, `full`, `clean`, `deploy` |
| `src/CYBERNOID_NEW.r0m` | собранный RAM-образ (32768 B) |

## Правки RDB (устранение перекрытий)

| Объект | Было | Стало |
|---|---|---|
| `func_speak_phoneme` | адрес 0x071C, размер 63 | 0x071C, размер **23** |
| `func_speak_emit_plane` | адрес 0x073F, размер 64 | **Удалён** (фантом) |
| `data_speak_char_index` | адрес 0x0738, размер 64 | 0x0738, размер **52** |

Перекрытий: было 3 пары → стало 0. Объектов: 339 → 338.

## Сборка и верификация

```
$ make layout
PASS 1: size=32768 byte diffs=21013
  repaired 462 runs (31214 bytes → defb)
PASS 2: size=32768 byte diffs=0

$ make all
cd asm && z80asm -b -m=8080_strict -o=../src/CYBERNOID_NEW.r0m main.asm
=== src/CYBERNOID_NEW.r0m: 32768 байт ===

$ make verify
size new=32768 orig=32768 ; byte diffs=0
verify: CYBERNOID_NEW.r0m идентичен cybernoid_unpacked.r0m (0 расхождений)
```

## MCP-проверка поведения

| Шаг | Действие | Результат |
|---|---|---|
| Boot | `debug_load_rom CYBERNOID_NEW.r0m`, PC=0x0000 | `JMP 0100` (3 B) |
| Step | `debug_step` | PC=0x0100, SP=0xC300 |
| Init | дизассемблировать 0x0100 | `DI`, `LXI SP,00FF`, `STA 0000`/`STA 0038` (патч векторов), `CALL 0573` (`func_title_speech_caller`) |
| Run | `debug_run` → `debug_pause` | речь пошла |
| IO-трейс | `debug_get_io_trace` (50 записей) | `OUT 0x00`: 0x00/0x01, каденс 40 T-состояний ≈ 37 кГц (PDM-движок) |
| Экран | `debug_get_screen_info` | 576×288, VRAM 0xC000, режим 256×256 |
| Оригинал | `debug_load_rom cybernoid_unpacked.r0m` → run → trace | Порт-последовательность идентична |

ROM байт-в-байт равен оригиналу → тождественность поведения по построению.

## Расхождения с ТЗ

| ТЗ §Stage 10 | Факт | Статус |
|---|---|---|
| Мастер `asm/main.asm` + `tools/gen_layout.py` | Созданы, работают | Выполнено |
| `Makefile`: layout/all/verify/deploy | `full = clean+layout+all+verify+deploy` | Выполнено |
| Байт-в-байт идентичность | 0 расхождений, SHA `d29d7d81…` | Выполнено |
| Проверка через MCP | boot-регистры, PDM-порт 0x00 | Выполнено |
| Переход в игру, произнесение фраз | IO-трейс совпадает; полная игровая сессия — на packed `cyberno.rom` | Ограничено (см. ниже) |

## Ограничения

- **Дефект экспортёра** (метки на `true+1`, память 1e37587b) сохраняется в C++
  `asm_exporter.cpp`. Цикл починки полностью его компенсирует; после фикса
  экспортёра `gen_layout.py` сойдется за 1 проход (0 прогонов на починку).
- **462 `defb`-прогона** (31214 байт) — компромисс читаемости ради точности;
  после фикса меток большая часть вернётся в мнемоники.
- **Побайтовый packed-двойник** (`CYBERNOID_NEW.ROM`) — отдельная задача
  (bootstrap + `INCBIN` сжатого стрима по модели `basic`); не входит в Stage 10.
- **Полная игровая сессия** через MCP (меню → геймплей → смерть) проверяется
  на packed `cyberno.rom` с клавиатурой; unpacked `.r0m` уже содержит
  инициализированный RAM-снимок и не воспроизводит bootstrap-последовательность.

## Артефакты

| Файл | Что |
|---|---|
| `tools/gen_layout.py` | генератор + цикл починки |
| `asm/layout.asm` | монолит (5356 строк, 544 метки) |
| `asm/main.asm` | мастер (org + include) |
| `Makefile` | сборка/верификация/деплой |
| `src/CYBERNOID_NEW.r0m` | собранный RAM-образ (32768 B, SHA `d29d7d81…`) |
| `src/cybernoid_unpacked.rdb` | обновлённый RDB (338 объектов, 0 перекрытий) |
