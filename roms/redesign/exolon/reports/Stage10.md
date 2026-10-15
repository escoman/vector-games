# Stage 10. Сборка `EXOLON_NEW.ROM` из `asm/` (монолит)

> Финальный этап TZ: из монолита `asm/code.asm` (Stage 8) собирается standalone
> `src/EXOLON_NEW.ROM`, побайтово сверяется с оригиналом и проверяется через
> MCP-эмулятор. Прежний INCBIN-подход (502 `.bin`) **отменён** — см. Stage 8.

## Вердикт (TL;DR)

`tools/gen_layout.py` генерирует **`asm/code.asm`** (весь код мнемониками +
`defb`/`defm`-секции данных) и мастер **`asm/exolon_new.asm`** (`org 0100h` +
`include "code.asm"`). `make layout → all → verify` собирает `src/EXOLON_NEW.ROM`
(32512 B) с **0 побайтовых расхождений** (SHA `92be64d1…`). Отличия от первого
варианта: код ассемблируется из **мнемоник** (редактируется в `code.asm`), а не
берётся `INCBIN`-блобами; `asm/bin/` упразднён.

## Инструменты

| Компонент | Роль |
|---|---|
| `tools/gen_layout.py` | exportёр→`layout.asm` → чинка `rst` → `defb`-починка data-прогонов → монолит `asm/code.asm` + мастер |
| `asm/code.asm` | адресный поток: все байты окна по одному разу |
| `asm/exolon_new.asm` | мастер: `ORG 0100h` + `include "code.asm"` |
| `Makefile` | цели `layout`, `all` (z80asm), `verify`, `deploy`, `full`, `clean` |
| `src/EXOLON_NEW.ROM` | результат (32512 B) |

## Сборка и верификация

```
$ make layout
базовая сборка: расхождений 199 → чиним data-прогоны
repaired runs: 23 (1564 байт данных → defb/defm)
code.asm: 9779 строк; round-trip: 0 расхождений

$ make all
cd asm && z80asm -b -m=8080_strict -o=../src/EXOLON_NEW.ROM exolon_new.asm
=== src/EXOLON_NEW.ROM: 32512 байт ===

$ make verify
size new=32512 orig=32512 ; byte diffs=0
verify: EXOLON_NEW.ROM идентичен exolon.rom (0 расхождений)
```

В отличие от «голого» pipeline-листа (180 синтакс-ошибок `rst <vector>`), монолит
после чинки `rst` и `defb`-починки собирается **с rc=0 без единой ошибки**.

## MCP-проверка поведения

| Шаг | Действие | Результат |
|---|---|---|
| Boot | `debug_load_rom EXOLON_NEW.ROM`, PC=0x0100, step | JMP → 0x786B (entry dispatcher) |
| Info | run 3 с | экран «КЛАВИШИ УПРАВЛЕНИЯ…», транслит |
| Title | type_key RUS, 4 с | логотип EXOLON, меню 1-4, copyright; `OUT 0x00 = 00/01` (beeper music) |
| Game | type_key 1, 5 с | HUD (AMMO/GRENADES/POINTS/LIVES/ZONES), рельеф, спрайты; `IN 0x0A` (VI53 frame-sync) |
| Ports | io_trace | `IN 0x0A`, `OUT 0x00` (PIA CW 88h/8Ah + TapeOut PC0), `OUT 0x02` (plane), `OUT 0x0C` (palette), `OUT 0x03` (scroll), `IN 0x01` (kbd) |

ROM байт-в-байт равен оригиналу → поведение тождественно `exolon.rom` по
построению (сверка MCP — контрольная, не единственная гарантия).

## Расхождения с ТЗ

| ТЗ §Stage 10 | Факт | Статус |
|---|---|---|
| Мастер `asm/exolon_new.asm` + `tools/gen_layout.py` | Созданы, работают | Выполнено |
| Гэпы `asm/bin/gap_*.bin` | **Отменены**: гэпы/данные — `defb`-секции в `code.asm` | Изменено осознанно (см. Stage 8) |
| `Makefile`: layout/all/verify/deploy | Работают (`full = clean+layout+all+verify+deploy`) | Выполнено |
| Байт-в-байт идентичность | 0 расхождений | Выполнено |
| Проверка через MCP | boot→info→title→game, порты | Выполнено |

## Артефакты

| Файл | Что |
|---|---|
| `tools/gen_layout.py` | генератор монолита (export → rst-fix → defb-repair → verify) |
| `asm/code.asm` | монолит (9779 строк, 641 метка) |
| `asm/exolon_new.asm` | мастер (org + include) |
| `Makefile` | сборка/верификация/деплой |
| `src/EXOLON_NEW.ROM` | собранный ROM (32512 B, SHA `92be64d1…`) |

## Limitations

- **Не scatter-загрузка.** `z80asm` не принимает второй `ORG`, поэтому код/данные
  лежат в одном адресном потоке (`code.asm`), а не в отдельных файлах-классах.
- **`defb`-златки** в 23 mis-decoded-прогонах данных — компромисс читаемости ради
  побайтовой точности.
- Флаг `-s` (публичные символы) не нужен: всё в одном include-потоке, метки видны
  ассемблеру целиком.
