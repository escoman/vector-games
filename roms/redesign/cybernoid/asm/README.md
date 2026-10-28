# asm/ — Stage 9 раскладка (киберноид, unpacked)

**Рабочий ROM:** `../src/cybernoid_unpacked.r0m` (RAM-снимок после самораспаковки,
org `0x0000`, SHA256 `d29d7d813b3add02…`). **RDB:** `../src/cybernoid_unpacked.rdb`
(339 объектов).

## A-мастер (источник истины и сборки)

Всё, что генерирует `v06c-asm-export`, лежит здесь дословно и собирается:

| файл | роль |
|---|---|
| `main.asm` | точка сборки; единственная директива — `org 0000h` + `include "layout.asm"` |
| `layout.asm` | единый линейный листинг: весь код и все данные под одним ORG (Stage 6.23 §2.2) |
| `export.json` | метаданные экспортёра: покрытия, объекты, предупреждения, конфликты |
| `provenance.json` | SHA ROM/RDB, версия экспортёра, argv |

Команда сборки:

```bash
../../../../z88dk/bin/z80asm -b -m=8080_strict -o=roundtrip.bin main.asm
```

RC=0, размер 32769 байт (на 1 больше образа — из-за дефекта перекрывающихся RDB-
объектов, см. `../reports/Stage9.md`). Побайтовое совпадение с `.r0m` —
**не** достигается на этом шаге; контракт round-trip переносится на Stage 10.

## B-просмотры (только чтение)

Файлы класса-срезов в `data/`. **Не** включаются в сборку: `main.asm` знает
только `layout.asm`, второй `org` в z80asm не переваривается (см.
`toolchain_lint`, one-module). Байты в них — verbatim из `data/data.asm`, без
переформатирования; нужны только чтобы человек мог открыть «речь», «строки»,
«таблицы паролей» и т.п. одним куском.

| файл | RDB-объекты | назначение |
|---|---|---|
| `data/voices.inc` | `str_voice_*`, `str_speak_demo`, `var_voice_period`, `var_voice_bufptr`, `data_speak_char_index`, `label_0778` (= `data_speak_codes`), `data_pdm_planes`, `data_speak_plane_lengths` | движок речи (PDM) и его данные |
| `data/strings.inc` | `str_screen_0b96/0bb5/0bd7/0c39` | экранные строки display-list |
| `data/passwords.inc` | `data_password_table` | таблица паролей экрана 3.PASS |
| `data/fonts.inc` | `data_glyph_block` | глифы шрифта (stride 0x20) |
| `data/sprites.inc` | `data_sprites_base` | спрайтовые данные (кандидат) |
| `data/variables.inc` | `var_key_latch` | RAM-переменные |
| `data/code.asm` в `code/` | все `func_*` | code-view; не в сборке |
| `data/data.asm` | все `str_*/data_*/var_*/gap_*` | master data-view; род-source для B-срезов |

`gap_*` в B-просы не переносятся — они не покрыты RDB и живут только в мастере.

## Как regenerate

```bash
# 1. A-мастер (кэшируется в .scratch/export/cybernoid_unpacked)
PYTHONPATH=../../../../utils python3 -m analyze.cli export_asm \
  --rom ../src/cybernoid_unpacked.r0m --rdb ../src/cybernoid_unpacked.rdb \
  --origin 0x0000 --out-dir ../../../../.scratch/export/cybernoid_unpacked
# затем скопировать main.asm / layout.asm / code / data в asm/

# 2. B-просмотры
python3 ../../../../.scratch/stage9_views.py
```
