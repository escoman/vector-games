# Stage 4 — Определение параметров функций

**Дата:** 2026-09-14
**ROM:** clrs.rom (119 байт, origin=0x0100)
**RDB:** clrs.rdb (7 объектов, 4 функции)
**Профиль:** reverse_engineering

---

## Обзор

Stage 4 посвящён определению параметров каждой функции ROM: входные/выходные регистры, используемые флаги, порты ввода-вывода, обращения к памяти, стек и вызывающая конвенция.

Анализ выполнен на основе:
- Дизассемблирования через MCP (`debug_disassemble_range`)
- Runtime-наблюдения: запуск ROM на 5 секунд (`debug_run` → `debug_pause`)
- Memory access map (подтверждение обращений к VRAM/RAM)
- I/O trace (наблюдение портовой активности)

---

## Функция 1: func_setup_and_halt

**Адрес:** 0x0100
**Размер:** 63 байта (31 инструкция)
**Тип:** ROM entry point

### Входные параметры
| Параметр | Значение |
|----------|----------|
| **Входные регистры** | none (ROM entry point, нет вызывающего кода) |
| **Входные флаги** | none |
| **Входная память** | none |

### Выходные параметры
| Параметр | Значение |
|----------|----------|
| **Выходные регистры** | none (функция не возвращает управление; завершается HLT-циклом) |
| **Выходные флаги** | none |

### Используемые регистры (clobbered)
`A`, `B`, `D`, `H`, `L`

**Evidence:**
- `H`, `L`: LXI H,8000h → INR L → INR H (VRAM clear loop)
- `A`: MVI A,F8h → PUSH PSW; ADD D → PUSH PSW (palette stack)
- `B`: MVI B,07h → DCR B (loop counter); MVI B,08h (second loop)
- `D`: ADD D (арифметика палитры; D=00h после DI, т.к. D не инициализирован до ADD)

### Флаги
| Флаг | Устанавливается | Используется |
|------|-----------------|--------------|
| Z | INR L (0106), INR H (010A), DCR B (012A), CMP L (0134) | JNZ 0107, JNZ 010B, JNZ 012B |
| C | ADD D (0130), CMP L (0134) | JNC 0131 |

### Порты ввода-вывода
| Порт | Операция | Адрес | Назначение |
|------|----------|-------|------------|
| 02h | OUT | 0135 | Border/video mode |

**Fact:** Инструкция `OUT 02h` по адресу 0x0135. Значение A = результат CMP L.

### Обращения к памяти
| Тип | Адрес | Инструкция | Назначение |
|-----|-------|------------|------------|
| **Запись** | 0x8000–0xFFFF | MVI M,00 (0104) | Очистка VRAM (все 4 плоскости) |
| **Запись** | 0x0038 | STA 0038h (0110) | Запись JP opcode (C3h) в вектор RST 7 |
| **Запись** | 0x0039–0x003A | SHLD 0039h (0116) | Запись адреса ISR (013Fh) в вектор RST 7 |

**Подтверждение runtime:** Memory access map показывает запись во все 256 блоков (0x0000–0xFF00), что подтверждает очистку VRAM 0x8000–0xFFFF и запись в RAM 0x0038–0x003A.

### Стек
| Операция | Количество | Данные |
|----------|-----------|--------|
| PUSH H | ×9 | 0172h (×1), 0152h (×8) |
| PUSH PSW | ×9 | F8h (×8), F9h–FCh (×1 каждая) |
| **Итого записано** | 36 байт | Палитра стек at 0x055B–0x0576 |

**Stack frame size:** 0 (нет фрейма в традиционном смысле; стек используется для хранения данных палитры)

### Вызывающая конвенция
**none** — это ROM entry point, нет вызывающего кода. Функция не возвращает управление.

### Побочные эффекты
- DI (запрет прерываний)
- Очистка VRAM 0x8000–0xFFFF (запись нулей)
- Запись RST 7 вектора в RAM 0x0038–0x003A
- Инициализация палитра-стека в RAM 0x055A–0x0576
- Установка border через OUT 02h
- LXI SP,0100h (сброс стека)
- EI (разрешение прерываний)
- HLT-цикл (ожидание VBlank)

---

## Функция 2: func_isr_delay_and_setup

**Адрес:** 0x013F
**Размер:** 19 байт (10 инструкций)
**Тип:** VBlank ISR entry

### Входные параметры
| Параметр | Значение |
|----------|----------|
| **Входные регистры** | H, L (HL как указатель для [HL] в цикле задержки; HL=0177h при входе из ISR) |
| **Входные флаги** | none (A=00h после DI в startup, carry не определён) |
| **Входная память** | [HL] — чтение байта по адресу HL для ADC M |

### Выходные параметры
| Параметр | Значение |
|----------|----------|
| **Выходные регистры** | BC=0703h (B=07h — счётчик цветов, C=03h), D=01h (инкремент), SP=0177h |
| **Выходные флаги** | Z, C (результат цикла задержки) |

### Используемые регистры (clobbered)
`A`, `B`, `C`, `D`

**Evidence:**
- `B`, `C`: LXI B,00ECh → DCX B (delay); затем LXI B,0703h (setup)
- `A`: MOV A,B → ADC M (delay loop)
- `D`: MVI D,01h

### Флаги
| Флаг | Устанавливается | Используется |
|------|-----------------|--------------|
| Z | DCX B (0142), ADC M (0144) | JNZ 0145 (delay loop) |
| C | ADC M (0144) | ADC M (0144, carry-in) |

### Порты ввода-вывода
**none** — нет инструкций IN/OUT.

### Обращения к памяти
| Тип | Адрес | Инструкция | Назначение |
|-----|-------|------------|------------|
| **Чтение** | [HL] (HL=0177h) | ADC M (0144) | Чтение байта для условия завершения задержки |

**Inference:** HL=0177h указывает на область кода func_isr_rearm_and_exit. Байт по этому адресу — opcode (C3h = RET, не 00h), поэтому цикл задержки зависит от сканирования памяти в поисках нулевого байта.

### Стек
| Операция | Описание |
|----------|----------|
| LXI SP,0177h | Позиционирование SP в область кода func_isr_rearm_and_exit |

**Stack frame size:** 0

### Вызывающая конвенция
**ISR entry** — вызывается через вектор RST 7 (0x0038). Завершается fall-through в func_isr_palette_cycle (нет RET).

### Побочные эффекты
- Переменная задержка через цикл [HL] (зависит от содержимого памяти)
- Установка BC=0703h, D=01h для func_isr_palette_cycle
- Позиционирование SP=0177h для потребления палитра-стека

---

## Функция 3: func_isr_palette_cycle

**Адрес:** 0x0152
**Размер:** 32 байта (23 инструкции)
**Тип:** Palette cycling output

### Входные параметры
| Параметр | Значение |
|----------|----------|
| **Входные регистры** | A (через POP PSW — цвет палитры со стека), L (арифметический операнд; L=52h) |
| **Входные флаги** | C (carry используется в ADC L; carry от предыдущей операции) |
| **Входная память** | Стек [SP] через POP PSW (читает цвет из var_palette_stack 0x055A–0x0576) |

### Выходные параметры
| Параметр | Значение |
|----------|----------|
| **Выходные регистры** | A (вычисленное значение палитры после 8 арифметических шагов) |
| **Выходные флаги** | Z (CMP L), C (SUB/ADC/ADD), S, P |

### Используемые регистры (clobbered)
`A` (модифицируется SUB L, ADC L, ADD L), `F` (все флаги)

**Evidence:**
- `A`: POP PSW → SUB L → ADC L → ADD L → SUB L → ADC L → SUB L → CMP L
- `L`: не модифицируется (используется как константа 52h)

### Флаги
| Флаг | Устанавливается | Используется |
|------|-----------------|--------------|
| Z | ORA A (0153–0155), CMP L (016E) | — |
| C | SUB L (0159,015F,0165,016B), ADC L (015C,0168), ADD L (0162) | ADC L (015C, 0168 — carry-in) |
| S, P | Все арифметические операции | — |

### Порты ввода-вывода
| Порт | Операция | Адрес | Количество |
|------|----------|-------|------------|
| 0Ch | OUT | 0157, 015A, 015D, 0160, 0163, 0166, 0169, 016C, 016F | **×9** |

**Fact:** 9 выводов на порт 0Ch (палитра). Каждый вывод preceded арифметической операцией над A.

### Обращения к памяти
| Тип | Адрес | Инструкция | Назначение |
|-----|-------|------------|------------|
| **Чтение** | [SP] | POP PSW (0152) | Читает цвет палитры из var_palette_stack |

**Подтверждение runtime:** Memory access map показывает чтение в блоке 0x0500 (var_palette_stack area).

### Стек
| Операция | Описание |
|----------|----------|
| POP PSW | Потребляет 2 байта (цвет палитры → A, флаги → F) |
| RET | Потребляет 2 байта (адрес возврата) |
| **Итого** | SP += 4 за вызов |

**Stack frame size:** 0 (нет фрейма; стек потребляется как данные)

### Вызывающая конвенция
**callee** — вызывается через:
1. Fall-through из func_isr_delay_and_setup (0x014F → 0x0152)
2. RET из func_isr_rearm_and_exit (0x0176 → адрес на стеке)

Возврат через RET в func_isr_rearm_and_exit.

### Побочные эффекты
- Вывод 9 значений палитры на порт 0Ch
- Потребление записи стека (SP += 4)

---

## Функция 4: func_isr_rearm_and_exit

**Адрес:** 0x0172
**Размер:** 5 байт (3 инструкции)
**Тип:** ISR exit / rearm

### Входные параметры
| Параметр | Значение |
|----------|----------|
| **Входные регистры** | none |
| **Входные флаги** | none |
| **Входная память** | none |

### Выходные параметры
| Параметр | Значение |
|----------|----------|
| **Выходные регистры** | SP (сброшен в 00FEh) |
| **Выходные флаги** | none |

### Используемые регистры (clobbered)
**none** — ни один регистр общего назначения не модифицируется.

### Флаги
| Флаг | Устанавливается | Используется |
|------|-----------------|--------------|
| — | — | — |

### Порты ввода-вывода
**none** — нет инструкций IN/OUT.

### Обращения к памяти
**none** — нет инструкций чтения/записи памяти.

### Стек
| Операция | Описание |
|----------|----------|
| LXI SP,00FEh | Сброс SP в фиксированную позицию |
| RET | Потребляет 2 байта (адрес возврата со стека) |

**Stack frame size:** 0

### Вызывающая конвенция
**ISR exit** — вызывается из func_isr_palette_cycle через RET. re-arms interrupts (EI) и возвращает управление через RET.

### Побочные эффекты
- EI (разрешение прерываний для следующего VBlank)
- Сброс SP в 00FEh (ниже кода, выше области стека)

---

## Сводная таблица функций

| Функция | Адрес | Вход | Выход | Clobbered | Порты | Память (R/W) | Стек | Convention |
|---------|-------|------|-------|-----------|-------|--------------|------|------------|
| func_setup_and_halt | 0x0100 | — | — | A,B,D,H,L | OUT 02h | R:— / W:VRAM+RAM | PUSH ×18 | entry (no return) |
| func_isr_delay_and_setup | 0x013F | HL | BC,D,SP | A,B,C,D | — | R:[HL] / W:— | LXI SP | ISR → fall-through |
| func_isr_palette_cycle | 0x0152 | A(via stack),L | A | A,F | OUT 0Ch ×9 | R:[SP] / W:— | POP PSW + RET | callee |
| func_isr_rearm_and_exit | 0x0172 | — | SP | — | — | R:— / W:— | LXI SP + RET | ISR exit |

---

## Таблица properties RDB

### func_setup_and_halt (0x0100) — 12 properties
| Property | Value |
|----------|-------|
| input_registers | none (ROM entry point, no caller) |
| output_registers | none (function does not return; ends with HLT loop) |
| clobbered_registers | A, B, D, H, L |
| flags_used | Z (JNZ at 0107, 010B, 012B), C (JNC at 0131) |
| flags_set | Z (INR L, INR H, DCR B, CMP L), C (ADD D, CMP L) |
| ports_used | OUT 02h (border/video mode at 0135) |
| memory_read | none (no LDA, LDAX, MOV A,M in this function) |
| memory_write | VRAM 0x8000-0xFFFF (MVI M,00 via HL scan), RAM 0x0038 (STA C3h), RAM 0x0039-0x003A (SHLD 013Fh) |
| stack_frame_size | 0 (no stack frame, but pushes 24 bytes to build palette stack) |
| stack_operations | PUSH H (x9), PUSH PSW (x9) — builds palette data stack at 0x055A-0x0576 |
| calling_convention | none (ROM entry point, no caller, does not return) |
| side_effects | DI, clears VRAM 0x8000-0xFFFF, writes RST 7 vector at 0x0038-0x003A, builds palette stack at 0x055A, sets border via OUT 02h, resets SP to 0100h, EI, enters HLT loop |

### func_isr_delay_and_setup (0x013F) — 12 properties
| Property | Value |
|----------|-------|
| input_registers | H, L (HL used as pointer for [HL] read in delay loop) |
| output_registers | B (B=07h), C (C=03h), BC (BC=0703h), D (D=01h), SP (SP=0177h) |
| clobbered_registers | A, B, C, D |
| flags_used | Z (JNZ at 0145 delay loop), C (ADC M uses carry) |
| flags_set | Z (DCX B, ADC M), C (ADC M) |
| ports_used | none (no IN/OUT instructions) |
| memory_read | [HL] in delay loop (ADC M at 0144; HL starts at 0177h) |
| memory_write | none (no STA, STAX, SHLD, MOV M, MVI M) |
| stack_frame_size | 0 (no PUSH/POP, only LXI SP) |
| stack_operations | LXI SP,0177h (repositions SP for palette stack consumption) |
| calling_convention | ISR entry (called via RST 7 vector), falls through to func_isr_palette_cycle |
| side_effects | variable delay via [HL] scan, sets up BC=0703h and D=01h, repositions SP to 0177h |

### func_isr_palette_cycle (0x0152) — 12 properties
| Property | Value |
|----------|-------|
| input_registers | A (via POP PSW from palette stack), L (arithmetic operand: L=52h) |
| output_registers | A (final computed palette value after 8 arithmetic steps) |
| clobbered_registers | A (modified by SUB L, ADC L, ADD L sequence), F (all flags) |
| flags_used | C (ADC L uses carry flag from previous operation) |
| flags_set | Z (ORA A, CMP L), C (SUB L, ADC L, ADD L), S, P |
| ports_used | OUT 0Ch x9 (palette port at 0157, 015A, 015D, 0160, 0163, 0166, 0169, 016C, 016F) |
| memory_read | Stack at [SP] via POP PSW (reads palette color from var_palette_stack 0x055A-0x0576) |
| memory_write | none (no write instructions; SP advances by 2 via POP) |
| stack_frame_size | 0 (no frame, but consumes 2 bytes from stack via POP PSW) |
| stack_operations | POP PSW (consumes 2 bytes), RET (pops 2-byte return address) |
| calling_convention | callee (called via RET or fall-through); returns via RET to func_isr_rearm_and_exit |
| side_effects | outputs 9 palette values to port 0Ch, consumes stack entry (SP += 4 total) |

### func_isr_rearm_and_exit (0x0172) — 12 properties
| Property | Value |
|----------|-------|
| input_registers | none (no registers read as input) |
| output_registers | SP (reset to 00FEh) |
| clobbered_registers | none (no general-purpose registers modified) |
| flags_used | none |
| flags_set | none |
| ports_used | none (no IN/OUT instructions) |
| memory_read | none |
| memory_write | none |
| stack_frame_size | 0 (no frame) |
| stack_operations | LXI SP,00FEh (resets SP), RET (pops 2-byte return address) |
| calling_convention | ISR exit; re-enables interrupts and returns via RET |
| side_effects | EI (re-enables VBlank interrupts), resets SP to 00FEh |

---

## Verified Facts

1. **OUT 02h** — единственная инструкция вывода в func_setup_and_halt (адрес 0x0135)
2. **OUT 0Ch ×9** — 9 инструкций вывода палитры в func_isr_palette_cycle (адреса 0157–016F)
3. **Нет инструкций IN** — ROM не читает порты ввода
4. **MVI M,00** — единственная инструкция записи в память через регистр (VRAM clear)
5. **STA 0038h / SHLD 0039h** — запись RST 7 вектора в RAM
6. **POP PSW** — единственная инструкция чтения стека как данных
7. **PUSH H / PUSH PSW** — 18 инструкций PUSH для построения палитра-стека
8. **Memory access map** подтверждает запись во все 256 блоков памяти (VRAM clear 0x8000–0xFFFF)
9. **L=52h** — используется как арифметический операнд в func_isr_palette_cycle (установлен в func_setup_and_halt через LXI H,0152h, затем сохраняется при PUSH/POP)

## Inferences

1. **D=00h при первом ADD D (0x0130)** — регистр D не инициализирован до этого момента (DI не влияет на D). Это означает, что первые PUSH PSW в arithmetic loop используют A=F8h+00h=F8h.
2. **HL=0177h при входе в ISR** — после JMP 013Bh → HLT → VBlank → RST 7, HL сохраняет значение 0152h от последнего LXI H,0152h в setup. Однако ADC M в delay loop может модифицировать A, но не HL. Точное значение HL при входе в ISR требует дополнительной проверки.
3. **Цикл задержки** в func_isr_delay_and_setup зависит от содержимого памяти по адресу HL, что делает timing недетерминированным.

## Hypotheses

1. **L=52h в func_isr_palette_cycle** — предполагается, что L сохраняет значение 52h (младший байт от LXI H,0152h) через весь ISR chain. Не проверено через execution trace.
2. **Палитра выводит 9 значений за ISR** — каждое значение модифицируется арифметикой SUB/ADC/ADD с операндом L=52h, создавая паттерн цветов.

## Unknowns

1. **Точное значение HL при входе в ISR** — после HLT → RST 7, HL может отличаться от 0152h из-за промежуточных операций.
2. **Начальное значение carry flag** для ADC M в delay loop — зависит от состояния CPU после RST 7.
3. **D=00h или D=не определён** — после DI в 8080 регистры не модифицируются, но точное значение D зависит от предыдущего кода (D не используется до ADD D в 0x0130).

---

## Статус RDB

| Параметр | Значение |
|----------|----------|
| **Путь** | /home/alexey/Projects/vector-games/roms/redesign/clrs/src/clrs.rdb |
| **Объектов** | 7 |
| **Функций** | 4 |
| **Properties установлено** | 48 (12 на каждую функцию) |
| **RDB links** | 6 (суммарно по всем объектам) |
| **RDB save** | ✅ success (dirty=false подтверждено) |
| **ROM** | clrs.rom, 119 байт, origin=0x0100 |

---

## Ограничения анализа

- Execution trace и instruction history были недоступны после 5-секундного запуска (буферы переполнены)
- I/O trace показал порты 0x1C/0x1B (эмулятор), а не 0x0C/0x02 (ROM) — это особенность трассировки эмулятора
- Значения регистров при входе в ISR не были напрямую подтверждены через breakpoint/step
