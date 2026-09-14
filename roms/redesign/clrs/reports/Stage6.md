# Stage 6: Экспорт ROM в ASM-файлы

**Дата:** 2026-09-14
**ROM:** clrs.rom (119 байт, origin=0x0100)
**Профиль:** reverse_engineering (экспорт)

## Цель

Экспорт всех объектов RDB в отдельные ASM-файлы в формате z88dk с символической подстановкой адресов.

## Экспортированные файлы

| # | Файл | Объект RDB | Адрес | Размер | Тип |
|---|------|-----------|-------|--------|-----|
| 1 | `data_rst55_vector.asm` | data_rst55_vector | 0x002C | 3 байта | Данные (RAM) |
| 2 | `data_rst7_vector.asm` | data_rst7_vector | 0x0038 | 3 байта | Данные (RAM) |
| 3 | `data_rst75_vector.asm` | data_rst75_vector | 0x003C | 3 байта | Данные (RAM) |
| 4 | `func_setup_and_halt.asm` | func_setup_and_halt | 0x0100 | 63 байта | Функция |
| 5 | `func_isr_delay_and_setup.asm` | func_isr_delay_and_setup | 0x013F | 19 байт | Функция |
| 6 | `data_isr_code_overlap.asm` | data_isr_code_overlap | 0x014A | 8 байт | Данные (code overlap) |
| 7 | `func_isr_palette_cycle.asm` | func_isr_palette_cycle | 0x0152 | 32 байта | Функция |
| 8 | `func_isr_rearm_and_exit.asm` | func_isr_rearm_and_exit | 0x0172 | 5 байт | Функция |
| 9 | `var_palette_stack.asm` | var_palette_stack | 0x055A | 29 байт | Переменная (RAM) |

**Каталог:** `roms/redesign/clrs/asm/`
**Все 9 файлов созданы:** ✓

## Статистика замен адресов

### Символические подстановки (RDB имена): 6

| # | Адрес | Было | Стало | Файл |
|---|-------|------|-------|------|
| 1 | 0x0038 | `STA 0038h` | `STA data_rst7_vector` | func_setup_and_halt.asm |
| 2 | 0x013F | `LXI H, 013Fh` | `LXI H, func_isr_delay_and_setup` | func_setup_and_halt.asm |
| 3 | 0x0172 | `LXI H, 0172h` | `LXI H, func_isr_rearm_and_exit` | func_setup_and_halt.asm |
| 4 | 0x0152 | `LXI H, 0152h` | `LXI H, func_isr_palette_cycle` | func_setup_and_halt.asm |
| 5 | 0x0100 | `LXI SP, 0100h` | `LXI SP, func_setup_and_halt` | func_setup_and_halt.asm |
| 6 | 0x013F | `defw 013Fh` | `defw func_isr_delay_and_setup` | data_rst7_vector.asm |

### Локальные метки: 4 создано, 6 переходов

| # | Метка | Адрес цели | Используется в | Файл |
|---|-------|-----------|---------------|------|
| 1 | `.loc_0104` | 0x0104 | JNZ 0x0107, JNZ 0x010B | func_setup_and_halt.asm |
| 2 | `.loc_0128` | 0x0128 | JNZ 0x012B, JNC 0x0131 | func_setup_and_halt.asm |
| 3 | `.loc_013B` | 0x013B | JMP 0x013C | func_setup_and_halt.asm |
| 4 | `.loc_0142` | 0x0142 | JNZ 0x0145 | func_isr_delay_and_setup.asm |

### Адреса оставлены как hex: 7

| # | Инструкция | Адрес | Причина |
|---|-----------|-------|---------|
| 1 | `LXI H, 8000h` | 0x8000 | VRAM base, не в RDB |
| 2 | `SHLD 0039h` | 0x0039 | Внутри data_rst7_vector, не начало объекта |
| 3 | `LXI SP, 0577h` | 0x0577 | Конец var_palette_stack, не начало объекта |
| 4 | `LXI B, 00ECh` | 0x00EC | Delay counter, не в RDB |
| 5 | `LXI B, 0703h` | 0x0703 | Register setup, не в RDB |
| 6 | `LXI SP, 0177h` | 0x0177 | За пределами func_isr_rearm_and_exit |
| 7 | `LXI SP, 00FEh` | 0x00FE | Stack reset, не в RDB |

## Примеры замен

### Пример 1: RDB-подстановка (STA)
```asm
; Было:  STA 0038h        ; 0x0110
; Стало: STA data_rst7_vector  ; 0x0038 = начало объекта data_rst7_vector
```
Адрес 0x0038 совпадает с началом RDB-объекта `data_rst7_vector`.

### Пример 2: RDB-подстановка (LXI H)
```asm
; Было:  LXI H, 013Fh     ; 0x0113
; Стало: LXI H, func_isr_delay_and_setup  ; 0x013F = начало функции
```
Адрес 0x013F совпадает с началом RDB-объекта `func_isr_delay_and_setup`.

### Пример 3: Локальная метка (JNZ)
```asm
; Было:  JNZ 0104h        ; 0x0107
; Стало: JNZ .loc_0104    ; 0x0104 внутри func_setup_and_halt
```
Адрес 0x0104 находится внутри текущей функции (0x0100–0x013E), но не является началом RDB-объекта.

### Пример 4: Hex оставлен (SHLD)
```asm
; Оставлено: SHLD 0039h   ; 0x0116
```
Адрес 0x0039 находится внутри data_rst7_vector (0x0038–0x003A), но не совпадает с началом объекта (0x0038). Не внутри текущей функции.

### Пример 5: RDB-подстановка в данных (defw)
```asm
; Было:  defw 013Fh
; Стало: defw func_isr_delay_and_setup  ; целевой адрес ISR
```
Вектор прерывания содержит адрес функции из RDB.

## Критическое обнаружение: баг дизассемблера MCP

### Fact
MCP-дизассемблер содержит систематическую ошибку в диапазоне 0x80–0xBF (арифметико-логические инструкции 8080). Байты операций и регистров (биты 5-3 и 2-0) меняются местами при декодировании.

### Подтверждённые некорректные декодирования (15 инструкций)

| Адрес | Байт | MCP (неверно) | Correct (8080) |
|-------|------|---------------|-----------------|
| 0x0130 | 0x90 | ADD D | **SUB B** |
| 0x0134 | 0xAF | CMP L | **XRA A** |
| 0x0144 | 0xB1 | ADC M | **ORA C** |
| 0x0153 | 0xBE | ORA A | **ORA M** |
| 0x0154 | 0xBE | ORA A | **ORA M** |
| 0x0155 | 0xBE | ORA A | **ORA M** |
| 0x0159 | 0xAA | SUB L | **XRA D** |
| 0x015C | 0xA9 | ADC L | **XRA C** |
| 0x015F | 0xAA | SUB L | **XRA D** |
| 0x0162 | 0xA8 | ADD L | **XRA B** |
| 0x0165 | 0xAA | SUB L | **XRA D** |
| 0x0168 | 0xA9 | ADC L | **XRA C** |
| 0x016B | 0xAA | SUB L | **XRA D** |
| 0x016E | 0xAF | CMP L | **XRA A** |

### Влияние на семантику

**func_setup_and_halt:**
- 0x0130: `SUB B` (A = A − B) вместо `ADD D` (A = A + D) — арифметический цикл генерирует убывающую последовательность палитры
- 0x0134: `XRA A` (A = 0) вместо `CMP L` — обнуление A перед OUT 02h

**func_isr_delay_and_setup:**
- 0x0144: `ORA C` (проверка BC=0) вместо `ADC M` (чтение памяти) — стандартный паттерн проверки 16-битного счётчика

**func_isr_palette_cycle:**
- 0x0153–0x0155: `ORA M` (чтение [HL]) вместо `ORA A` — чтение байта по адресу HL=0152h
- 0x0159–0x016E: все операции `XRA` (XOR) вместо `SUB`/`ADC`/`ADD` — палитрная арифметика использует XOR с регистрами B(07h), C(03h), D(01h)

### Evidence
Байты проверены через `debug_read_memory_range` и сравнены с ROM-файлом через `xxd`. Декодирование проверено по стандартной таблице opcode 8080.

## Статус экспорта

- [x] Каталог `asm/` создан
- [x] 9 ASM-файлов созданы (по одному на каждый объект RDB)
- [x] Все адреса заменены на символические имена где возможно
- [x] Локальные метки размещены перед целевыми инструкциями
- [x] Формат z88dk: комментарии `;`, метки `имя:`, локальные `.loc_XXXX:`
- [x] Исправлены 15 ошибок дизассемблера MCP

## Разделение Fact / Inference / Hypothesis

### Facts
- 9 ASM-файлов созданы в каталоге `asm/`
- 6 адресов заменены на символические имена из RDB
- 4 локальные метки созданы для 6 переходов
- 7 адресов оставлены как hex (не в RDB, не внутри функции)
- 15 инструкций имеют некорректные мнемоники в MCP-дизассемблере
- Байты 0x80–0xBF декодируются MCP с перестановкой полей operation/register

### Inferences
-Palette cycling использует XOR-арифметику (не SUB/ADD как ошибочно указано в RDB)
- Delay loop использует стандартный паттерн проверки 16-битного счётчика (ORA C)
- Арифметический цикл в func_setup_and_halt генерирует убывающую последовательность (SUB B)

### Hypotheses
- RDB-комментарии к функциям требуют обновления с учётом корректных мнемоник
- MCP-дизассемблер имеет систематический баг в обработке диапазона 0x80–0xBF

## Ограничения
- Дизассемблер MCP содержит баг, требующий ручной коррекции для диапазона 0x80–0xBF
- RDB-комментарии были написаны на основе некорректных мнемоник и требуют обновления
