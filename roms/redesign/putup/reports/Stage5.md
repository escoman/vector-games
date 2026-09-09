# Stage 5. Исследование прерываний

## Цель

Исследовать адреса прерываний, подпрограммы в них, занести/обновить в RDB сведения о прерываниях с описанием. Особое внимание — аппаратному прерыванию RST 7.

## ROM

- Файл: `./src/putup.rom`
- Размер: 17664 байт
- Адрес загрузки: 0x0100
- Платформа: Vector-06C (КР580ВМ80А / Intel 8080)

## Сведения из VECTOR_VERIFIED.md

Согласно проверенной документации (§10):

| Параметр | Значение | Статус |
|----------|----------|--------|
| Источник | VBlank (кадровый) | VERIFIED_BY_CODE |
| Тип | RST 7 (opcode FFh) | VERIFIED_BY_CODE |
| Вектор | 0038h | VERIFIED_BY_CODE |
| Частота | ~50 Гц (50.08) | VERIFIED_BY_CODE |
| Маскирование | EI/DI | VERIFIED_BY_CODE |
| Момент | Начало обратного хода | VERIFIED_BY_CODE |

## Карта векторов прерываний (0x0000–0x003F)

Данные из памяти после 5 секунд работы ROM:

| Адрес | Содержимое | Назначение | Статус |
|-------|-----------|------------|--------|
| 0x0000 | `C3 57 0B` | JMP 0x0B57 (rom_init) | **Используется** |
| 0x0003–0x0037 | `00 00 ...` | Не используются | Пусто |
| 0x0038 | `C3 A4 03` | JMP 0x03A4 (isr_handler) | **Используется** |
| 0x003B–0x003F | `00 00 ...` | Не используются | Пусто |

**Вывод:** ROM использует только два вектора:
1. **RESET** (0x0000) → rom_init (0x0B57)
2. **RST 7** (0x0038) → isr_handler (0x03A4)

Остальные RST-векторы (RST 0–6) не задействованы.

## Инициализация векторов (init_1, 0x0383)

Функция `init_1` вызывается из `rom_init` (0x0B66) и настраивает векторы прерываний в RAM:

```
0383: XRA A           ; A = 0
0384: OUT 10          ; видеоконтроллер
0386: STA 08CF        ; [0x08CF] = 0x00 (AY reg data)
0389: MVI A, E0       ; A = 0xE0
038B: STA 08D0        ; [0x08D0] = 0xE0 (draw offset)
038E: MVI A, C3       ; opcode JMP
0390: STA 0038        ; [0x0038] = C3 (RST 7 vector opcode)
0393: STA 0000        ; [0x0000] = C3 (RESET vector opcode)
0396: LXI H, 03A4     ; HL = isr_handler
0399: SHLD 0039       ; [0x0039-003A] = 03A4 (RST 7 target)
039C: LXI H, 0B57     ; HL = rom_init
039F: SHLD 0001       ; [0x0001-0002] = 0B57 (RESET target)
03A2: EI              ; разрешить прерывания
03A3: RET
```

**Факт:** После выполнения init_1 прерывания разрешены (EI), RST 7 активен.

## ISR-обработчик (isr_handler, 0x03A4–0x0400)

### Структура ISR

```
03A4: PUSH H/D/B/PSW          ; сохранение регистров (4 PUSH)
03A8: LXI H, 08DF
03AB: INR M                    ; frame_counter++ ([0x08DF])
03AC: LXI H, 08C3
03AF: CMP L; ORA A             ; проверка [0x08C3] == 0?
03B1: JZ 03D1                  ; если 0 → пропуск AY-обновления
```

### Фаза 1: Обновление регистров AY-3-8910 (0x03B4–0x03CE)

Выполняется когда `ay_sound_timer` ([0x08C3]) ≠ 0:

```
03B4: DCR M                    ; ay_sound_timer--
03B5: LXI D, 100F              ; DE = 0x100F (AY data in ROM)
03B8: LHLD 08DB                ; HL = kbd_buf_ptr
03BB: MOV A, E; OUT 02         ; записать регистр AY (порт 02)
03BE: MOV A, M; OUT 0C         ; записать данные AY (порт 0C)
03C1: DCR C; OUT 0C            ; повторная запись
03C4-03C6: NOP; NOP; NOP       ; задержка (timing)
03C7: DCX H; OUT 0C            ; ещё одна запись
03CA: DCR E; DCR D; OUT 0C     ; декремент, запись
03CE: JNZ 03BB                 ; цикл: 15 байт
```

**Факт:** 15 байт данных AY-3-8910 из ROM по адресу 0x100F передаются в регистры звувого чипа через порты 0x02 (адрес регистра) и 0x0C (данные). Между записями — NOP-задержки для тайминга.

### Фаза 2: Сброс мультиплексора AY (0x03D1–0x03D3)

```
03D1: MVI A, 88
03D3: OUT 00                   ; сброс AY mux
```

### Фаза 3: Сканирование клавиатуры (0x03D5–0x03E8)

```
03D5: LXI H, 08D3              ; HL = буфер клавиатуры
03D8: MVI A, FE                ; маска строки 0
03DA: PUSH PSW
03DB: OUT 03                   ; выбрать строку (порт 03)
03DD: IN 02                    ; читать столбцы (порт 02)
03DF: MOV M, A                 ; сохранить в [0x08D3 + row]
03E0: POP PSW
03E1: INX H                    ; следующая строка
03E2: RLC                      ; сдвиг маски
03E3: JC 03DA                  ; повтор для 8 строк
03E6: MVI A, 88
03E8: OUT 00                   ; сброс AY mux после сканирования
```

**Факт:** 8 строк клавиатуры сканируются последовательно. Маска строки: FE → FD → FB → F7 → EF → DF → BF → 7F. Данные сохраняются в буфер [0x08D3]–[0x08DA].

### Фаза 4: Восстановление AY и обновление анимации (0x03EE–0x0400)

```
03EE: LDA 08CF                 ; сохранить регистр AY
03F1: OUT 03                   ; восстановить через порт 03
03F3: LDA 08C4                 ; управляющий байт
03F6: OUT 02                   ; через порт 02
03F8: CALL 3858                ; isr_anim_update
03FB: POP PSW; POP B; POP D; POP H  ; восстановление
03FF: EI                       ; разрешить прерывания
0400: RET                      ; выход из ISR
```

## Подфункции ISR

### isr_anim_update (0x3858)

Управление анимацией объектов. Вызывается из ISR каждый кадр.

```
1. Загружает указатель объекта из [0x3854] → [0x0B41]
2. Читает тип объекта из [HL+2]
3. Проверяет anim_frame_counter [0x383A]
4. Если == 0 → CALL sub_3890 (сброс кадров)
5. CALL isr_obj_update_1 (3BCA) — таблица 0x445D, шаг 0x14
6. CALL isr_obj_update_2 (3C7D) — таблица 0x42F9, шаг 0x0A
7. Инкрементирует anim_frame_counter [0x383A]
```

### sub_3890

Обработка сброса кадров анимации. Читает данные из объекта по смещениям +2 и +6.

### isr_obj_update_1 (0x3BCA)

Обновление объектов типа 1:
- Таблица данных: 0x445D
- Размер записи: 0x14 (20) байт
- Читает тип из [HL+0x0D], вычисляет смещение в таблице

### isr_obj_update_2 (0x3C7D)

Обновление объектов типа 2:
- Таблица данных: 0x42F9
- Размер записи: 0x0A (10) байт
- Проверяет флаг [0x3BC8], читает тип из [HL+0x0A]

### init_objects (0x3D4E)

Инициализация объектов (вызывается из rom_init):
- Очищает счётчики анимации [0x383A]–[0x383D]
- Читает базовый указатель из [0x3856]
- Заполняет поля объектов по указателю [0x0B41]
- Копирует 3 байта в VRAM 0x03F8
- Завершается EI; RET

## Полная схема прерываний

```
CPU RESET → 0x0000: JMP 0x0B57 (rom_init)
  └→ rom_init:
       ├→ CALL init_1 (0x0383) — настройка векторов
       │    ├→ [0x0000] = JMP 0x0B57
       │    ├→ [0x0038] = JMP 0x03A4
       │    └→ EI
       ├→ CALL init_2 (0x0401) — графика
       ├→ CALL init_objects (0x3D4E) — объекты
       └→ переход в data_process_loop

VBlank ~50Hz → 0x0038: JMP 0x03A4 (isr_handler)
  └→ isr_handler:
       ├→ frame_counter++ [0x08DF]
       ├→ if ay_sound_timer > 0:
       │    ├→ ay_sound_timer--
       │    └→ отправить 15 регистров AY-3-8910 (ROM 0x100F → порты 02/0C)
       ├→ сброс AY mux (MVI A,88; OUT 00)
       ├→ сканирование 8 строк клавиатуры (OUT 03 / IN 02 → [0x08D3..0x08DA])
       ├→ восстановление AY регистра ([0x08CF] → OUT 03)
       ├→ CALL isr_anim_update (0x3858)
       │    ├→ if anim_counter == 0: CALL sub_3890
       │    ├→ CALL isr_obj_update_1 (0x3BCA) — табл. 0x445D, шаг 0x14
       │    ├→ CALL isr_obj_update_2 (0x3C7D) — табл. 0x42F9, шаг 0x0A
       │    └→ anim_counter++
       └→ EI; RET
```

## Переменные, связанные с прерываниями

| Адрес | Имя | Размер | Назначение |
|-------|-----|--------|------------|
| 0x08C3 | ay_sound_timer | 1 | Таймер обратного отсчёта AY-обновления |
| 0x08CF | ay_reg_data | 1 | Данные регистра AY (сохранение/восстановление) |
| 0x08D0 | draw_offset | 1 | Смещение рисования (установлено 0xE0) |
| 0x08D3 | kbd_row_data | 8 | Буфер строк клавиатуры (строки 0–7) |
| 0x08DB | kbd_buf_ptr | 2 | Указатель на буфер клавиатуры (→ 0x08B2) |
| 0x08DF | vblank_frame_counter | 1 | Счётчик кадров VBlank (~50 Гц) |
| 0x383A | anim_frame_counter | 1 | Счётчик кадров анимации |
| 0x383B | anim_counter_2 | 1 | Счётчик анимации 2 |
| 0x383C | anim_counter_3 | 1 | Счётчик анимации 3 |
| 0x3854 | obj_data_ptr | 2 | Указатель на данные объектов |

## RDB

- Путь: `./src/putup.rdb`
- Объектов: 56 (добавлено 3 новых: reset_vector, rst7_vblank_vector, ay_reg_data)
- Новых связей: 8 (векторы → цели, ISR → переменные, init_1 → векторы)
- RDB save: **success**

### Новые RDB-объекты

| Адрес | Имя | Тип | Описание |
|-------|-----|-----|----------|
| 0x0000 | reset_vector | data | RESET vector: JMP 0x0B57 (rom_init) |
| 0x0038 | rst7_vblank_vector | data | RST 7 vector: JMP 0x03A4 (isr_handler), ~50 Hz |
| 0x08CF | ay_reg_data | variable | AY register data latch |

### Обновлённые RDB-объекты

| Адрес | Имя | Изменения |
|-------|-----|-----------|
| 0x0383 | init_1 | Уточнён комментарий: полная последовательность настройки векторов |
| 0x03A4 | isr_handler | Уточнён комментарий: 4 фазы ISR, свойства interrupt_source и isr_phases |
| 0x08C3 | ay_sound_timer | Переименован из isr_counter_08C3, уточнено описание |
| 0x08D3 | kbd_row_data | Переименован из ay_init_data, уточнено: буфер клавиатуры 8 байт |
| 0x08DB | kbd_buf_ptr | Уточнено описание: указатель на буфер клавиатуры |
| 0x08DF | vblank_frame_counter | Переименован из isr_frame_counter, уточнено описание |

## Verified Facts

1. **RESET vector** at 0x0000 = `JMP 0x0B57` — confirmed by memory read at runtime
2. **RST 7 vector** at 0x0038 = `JMP 0x03A4` — confirmed by memory read at runtime
3. **init_1** writes both vectors to RAM — confirmed by disassembly (0x038E–0x039F)
4. **ISR frequency** ~50 Hz — confirmed by VECTOR_VERIFIED.md §10 (VERIFIED_BY_CODE)
5. **ISR performs AY sound update** — 15 registers from ROM 0x100F, confirmed by disassembly
6. **ISR scans 8 keyboard rows** — confirmed by loop at 0x03DA–0x03E3 (RLC + JC)
7. **ISR calls isr_anim_update** — confirmed by CALL 3858 at 0x03F8
8. **Other RST vectors (0–6) unused** — confirmed by zero bytes at 0x0003–0x0037

## Inferences

1. AY sound registers are updated at variable rate (controlled by countdown timer, not every frame)
2. Keyboard is scanned every VBlank (~50 Hz), providing responsive input
3. Animation updates are synchronized with VBlank through ISR, ensuring smooth motion
4. The ISR is designed to be fast: register save/restore, conditional sound update, mandatory keyboard scan

## Hypotheses

1. The 15 AY registers at ROM 0x100F likely contain music data (volume, frequency, noise settings for 3 channels)
2. The NOP delays in the AY update loop (0x03C4–0x03C6) are timing-critical for AY-3-8910 register latching

## Unknowns

1. Exact music data format at ROM 0x100F (requires Stage 6 analysis)
2. Whether the keyboard scan data at 0x08D3–0x08DA is used directly or processed further

## Limitations

- RST vector addresses are in RAM (overwritten by init_1), not ROM — behavior depends on correct initialization
- ISR timing analysis is based on disassembly; actual cycle counts depend on Vector-06C wait states
