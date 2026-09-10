# Stage 3. Подробное исследование функций

**ROM:** `./src/putup.rom`
**Метод:** Дизассемблирование + анализ потоков данных каждой функции
**RDB объектов:** 55 (добавлены 6 функций распаковки)
**Связей установлено:** 30

---

## 1. Функции ROM (0x0100–0x07FF)

### 1.1. `func_rom_entry` — 0x0100 (4 байта)

```asm
DI              ; запрет прерываний
JMP 0x0B57      ; переход к распакованной main_init
```

**Назначение:** Точка входа ROM. Немедленно передаёт управление распакованному коду.

**Связи:** → `func_main_init` (0x0B57)

---

### 1.2. `func_read_16bit_de` — 0x010C (16 байт)

```asm
MOV E, M        ; E = [HL] (младший байт)
INX H           ; HL++
MOV D, M        ; D = [HL] (старший байт)
INX H           ; HL++
CALL 0x1BD4     ; дополнение/коррекция DE
MOV A, M        ; A = [HL]
CALL 0x0803     ; render_block (загрузка данных)
INX H
MOV A, M
CALL 0x0803     ; повтор
LXI B, 001F     ; +31
DAD B
MOV A, M
CALL 0x0803     ; ещё раз
INX H
MOV A, M
CALL 0x0803     ; и ещё
```

**Назначение:** Читает 16-бит значение из [HL] в DE, затем 4 раза вызывает `func_render_block` для отрисовки блока данных с разными смещениями. Используется для загрузки элементов игрового поля.

**Связи:** → `func_render_block` (0x0803) ×4, → `func_read_16bit_v2` (0x1BD4)

---

### 1.3. `func_sound_init` — 0x0121 (36 байт)

```asm
PUSH D; PUSH PSW
MVI E, 0F; MVI A, 0A
CALL 0x01BC         ; dispatch: A=0A, E=0F → запись в 0x031A
MVI A, 05; MVI E, 00
CALL 0x01BC         ; dispatch: A=05, E=00 → запись в 0x031B
MVI E, 32; MVI A, 04
CALL 0x01BC         ; dispatch: A=04, E=32 → запись в 0x031C
CALL 0x0EF7         ; vram_clear
MVI A, 0A; MVI E, 00
CALL 0x01BC         ; dispatch: A=0A, E=00
POP PSW; POP D; RET
```

**Назначение:** Инициализация звуковых каналов. 4 раза вызывает диспетчер с разными параметрами для записи в таблицу 0x031A–0x0325 и вывода в порт ВИ53. Также очищает VRAM.

**Связи:** → `func_jmp_table_dispatch` (0x01BC) ×4, → `func_vram_clear` (0x0EF7)

---

### 1.4. `func_data_loader2` — 0x0145 (10 байт)

```asm
PUSH H
CALL 0x0800     ; block_copy (копирование в VRAM)
INX H           ; HL++
SHLD 0x0B53     ; сохранить обновлённый указатель
POP H; RET
```

**Назначение:** Упрощённый загрузчик данных. Вызывает `func_copy_to_vram`, инкрементирует указатель и сохраняет его.

**Связи:** → `func_copy_to_vram` (0x0800), → `var_data_stream_ptr` (0x0B53)

---

### 1.5. `func_store_data_ptr` — 0x014F (4 байта)

```asm
SHLD 0x0B53     ; сохранить HL как указатель данных
RET
```

**Назначение:** Сохраняет HL в `var_data_stream_ptr`. Используется как вспомогательная функция.

---

### 1.6. `func_piece_type_lookup` — 0x0153 (29 байт)

```asm
DCR A           ; A = тип_фигуры - 1
JM skip         ; если A был 0 → пропуск
XRA A; RET      ; вернуть 0
skip:
XRA A
CALL 0x0197     ; read_timer_data → A = таймер[0x08D3]
RRC × 4         ; верхний nibble
ANI 0F          ; индекс 0–8
LXI H, 016C     ; таблица
MOV E, A; MVI D, 00
DAD D           ; HL += индекс
MOV A, M        ; A = таблица[индекс]
RET
```

**Таблица по адресу 0x016C (9 байт):**
| Индекс | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 |
|--------|---|---|---|---|---|---|---|---|---|
| Значение | 00 | 03 | 02 | 05 | 07 | 01 | 04 | 06 | 05 |

**Назначение:** По типу фигуры и значению таймера определяет вариант отображения. Верхний nibble таймера используется как индекс в 9-байтной таблице перестановок.

**Связи:** → `func_read_timer_data` (0x0197), → data 0x016C

---

### 1.7. `func_keyboard_timer` — 0x017C (25 байт)

```asm
DCR A           ; декремент кадрового счётчика
JM reset        ; если < 0 → сброс
CMP L; RET      ; вернуть результат
reset:
MVI A, 07       ; сброс счётчика на 7
CALL 0x0197     ; read_timer_data
ANI 80          ; проверить бит 7
JZ skip         ; если 0 → пропуск
IN 01           ; чтение клавиатуры
ANI 20          ; проверка SPACE (бит 5)
JZ skip         ; не нажата → пропуск
CMP L; RET      ; клавиша нажата
skip:
CMA; RET        ; инверсия (клавиша не нажата)
```

**Назначение:** Опрос клавиатуры с кадровым таймером. Каждые 7 кадров проверяет SPACE (IN 0x01, ANI 0x20). Возвращает ненулевое значение если SPACE нажата.

**Связи:** → `func_read_timer_data` (0x0197)

---

### 1.8. `func_read_timer_data` — 0x0197 (10 байт)

```asm
PUSH H
LXI H, 08D3     ; таблица таймера
CALL 0x032C     ; table_lookup (индексация)
MOV A, M        ; A = [результат]
POP H; RET
```

**Назначение:** Читает значение из таблицы таймера по адресу 0x08D3 через `func_table_lookup`.

**Связи:** → `func_table_lookup` (0x032C), → `data_timer_table` (0x08D3)

---

### 1.9. `func_data_loader` — 0x01A1 (13 байт)

```asm
LHLD 0x0B53     ; HL = data_stream_ptr
CALL 0x0800     ; block_copy (копирование в VRAM)
INX H           ; HL++
SHLD 0x0B53     ; сохранить обновлённый указатель
RET
```

**Назначение:** Основной загрузчик данных. Читает указатель из `var_data_stream_ptr`, вызывает копирование в VRAM, инкрементирует указатель.

**Связи:** → `func_copy_to_vram` (0x0800), → `var_data_stream_ptr` (0x0B53)

---

### 1.10. `func_set_stream_pos` — 0x01AE (12 байт)

```asm
LDA 08FE        ; A = позиция (младший байт)
MOV D, A
LDA 08FF        ; A = позиция (старший байт)
MOV E, A
CALL 0x1BD4     ; read_16bit_v2
JMP 0x014F      ; → store_data_ptr
```

**Назначение:** Устанавливает позицию потока данных из переменных 0x08FE/0x08FF.

**Связи:** → `func_store_data_ptr` (0x014F), → `func_read_16bit_v2` (0x1BD4)

---

### 1.11. `func_jmp_table_dispatch` — 0x01BC (24 байта)

```asm
PUSH H; PUSH D; PUSH PSW
LXI H, 01CD     ; указатель на таблицу переходов
ANI 0F          ; маска младших 4 бит
CMP B
CALL 0x032C     ; table_lookup (HL + A*2)
MOV D, M; INX H ; D = младший байт адреса
MOV H, M; MOV L, D ; HL = 16-бит адрес
PCHL             ; вычисленный переход
```

**Назначение:** Диспетчер на основе таблицы переходов. A (ANI 0F) — индекс. Читает 16-бит адрес из `data_jmp_table` и выполняет PCHL.

**Таблица (0x01CD):** 16 записей:
- **0–11:** Запись параметра в 0x031A–0x0325 → `func_sound_timer_write` → возврат
- **12–15:** Загрузка HL с адресом параметра → `func_mul7` → возврат

**Связи:** → `data_jmp_table` (0x01CD), → `func_table_lookup` (0x032C)

---

### 1.12. `func_sound_timer_write` — 0x0201 (13 байт)

```asm
LXI H, 031A     ; таблица параметров звука
CALL 0x020E     ; mul7 → HL = [0x031A] × 7
MOV A, L; OUT 0B ; младший байт → порт ВИ53
MOV A, H; OUT 0B ; старший байт → порт ВИ53
RET
```

**Назначение:** Запись значения в счётчик ВИ53 (порт 0x0B). Читает 16-бит параметр из `var_sound_params`, умножает на 7, выводит.

**Связи:** → `func_mul7` (0x020E), → `var_sound_params` (0x031A)

---

### 1.13. `func_mul7` — 0x020E (11 байт)

```asm
MOV A, M; INX H    ; A = [HL] (младший)
MOV H, M; MOV L, A ; HL = 16-бит значение
DAD H              ; HL × 2
MOV E, L; MOV D, H ; DE = HL × 2
DAD H              ; HL × 4
DAD D              ; HL × 4 + × 2 = × 6
DAD H              ; HL × 12... нет, × 6 + × 6 = ...
RET
```

**Фактически:** HL = [HL] × 7 через: ×2 (DAD H) + сохранить (DE) + ×4 (DAD H ×2) + ×6 (DAD D) + ×7 (DAD H)... Нет. Точный расчёт:
1. DAD H → HL = val × 2
2. DE = HL (val × 2)
3. DAD H → HL = val × 4
4. DAD D → HL = val × 4 + val × 2 = val × 6
5. DAD H → HL = val × 12

**Уточнение:** Результат = val × 12 (не ×7). Назначение — масштабирование частоты таймера.

**Назначение:** Умножение 16-бит значения на 12 (через DAD-цепочку). Масштабирование частоты для ВИ53.

---

### 1.14. `func_table_lookup` — 0x032C (20 байт)

```asm
XRA B           ; A = A XOR B
MOV L, A        ; L = результат
RNC             ; если нет переноса → RET
INR H           ; иначе H++ (старшая часть)
RET
```

**Назначение:** Вычисление адреса: HL = HL + (A XOR B). Если есть перенос — инкрементирует H. Используется для индексации таблиц.

---

### 1.15. `func_read_16bit_v2` — 0x0351 (4 байта)

```asm
MOV E, M; INX H
MOV D, M; INX H
RET
```

**Назначение:** Читает 16-бит из [HL] в DE. Альтернативная версия `func_read_16bit_de`.

---

### 1.16. `func_calc_vram_offset` — 0x0355 (15 байт)

```asm
MVI C, FF       ; счётчик
loop:
INR C           ; C++
DAD D           ; HL += DE
JC loop         ; повторять при переносе
MOV A, L; SBB D ; вычитание с заимствованием
MOV E, A
MOV A, H; SUB E
MOV D, A
MOV A, C; XCHG
RET
```

**Назначение:** 16-бит деление/вычисление через повторное сложение. Вычисляет частное и остаток от деления HL/DE. Используется для расчёта координат VRAM.

---

### 1.17. `func_rom_init` — 0x0383 (33 байта)

```asm
XRA A
OUT 10          ; сброс банковской памяти
STA 08CF        ; сохранение
MVI A, E0
STA 08D0        ; палитра/смещение = 0xE0
MVI A, C3
STA 0038        ; JMP opcode в вектор ISR
STA 0000        ; JMP opcode в 0x0000
LXI H, 03A4
SHLD 0039       ; адрес ISR (JMP 0x03A4)
LXI H, 0B57
SHLD 0001       ; адрес main_init (JMP 0x0B57)
EI              ; разрешение прерываний
RET
```

**Назначение:** Инициализация системы:
1. Сброс порта 0x10 (банковская память)
2. Установка палитры/смещения 0xE0
3. Установка вектора ISR: 0x0038 → JMP 0x03A4
4. Установка JMP 0x0B57 в 0x0000
5. EI — разрешение прерываний

**Связи:** → `data_isr_vector` (0x0038), → `func_isr` (0x03A4)

---

### 1.18. `func_isr` — 0x03A4 (ISR)

**Полный анализ:**

```asm
; Сохранение регистров
PUSH H; PUSH D; PUSH B; PUSH PSW

; Инкремент ISR-счётчика
LXI H, 08DF
INR M

; Проверка кадрового счётчика
LXI H, 08C3
XRA A; ORA A
JZ skip_palette   ; если 0 → пропустить палитру

; Кадровый счётчик ≠ 0: палитровая анимация
DCR M              ; декремент
LXI DE, 100F       ; 16 цветов + счётчик
LHLD 08DB          ; указатель данных палитры
palette_loop:
MOV A, E
OUT 02             ; порт скроллинга
MOV A, M
OUT 0C             ; запись цвета
DCR C
OUT 0C             ; запись (задержка)
NOP × 3
DCX H
OUT 0C             ; запись
DCR E; DCR D
OUT 0C             ; запись
JNZ palette_loop   ; цикл 16 итераций

skip_palette:
; Проверка перехода состояния
MVI A, 8A
OUT 00             ; управление PIA
LXI H, 08D3
MVI A, FE
PUSH PSW
OUT 03             ; скроллинг
IN 02              ; чтение порта
MOV M, A           ; сохранение
POP PSW
INX H
RLC                ; сдвиг
...
; Восстановление регистров и RET
```

**Назначение:** Обработчик прерываний:
1. Инкремент ISR-счётчика (0x08DF)
2. Если кадровой счётчик (0x08C3) ≠ 0 — палитровая анимация: чтение 16 цветов из ROM и запись в порт 0x0C
3. Обновление скроллинга (порт 0x03)
4. Проверка состояния для перехода из заставки в игру

**Связи:** → `var_frame_count_isr` (0x08DF), → `var_frame_counter` (0x08C3), → `var_data_ptr` (0x08DB), → `var_vram_scroll` (0x08CF)

---

### 1.19. `func_decompress` — 0x0401 (46 байт) — распаковка данных при старте

**Полная структура:**

```asm
PUSH H; PUSH D; PUSH B; PUSH PSW   ; сохранение регистров
CALL 0x04CD                         ; func_decomp_transpose
LXI H, 6000                         ; целевой адрес в RAM
LXI D, 3041                         ; источник (конец данных)
MVI B, 00                           ; счётчик циклов (256)
loop:
  PUSH B; PUSH D
  CALL 0x0439   ; func_decomp_plane0 (биты 7,3)
  POP D; PUSH D
  CALL 0x045E   ; func_decomp_plane1 (биты 6,2)
  POP D; PUSH D
  CALL 0x0483   ; func_decomp_plane2 (биты 5,1)
  POP D; PUSH D
  CALL 0x04A8   ; func_decomp_plane3 (биты 4,0)
  POP D; POP B
  DCR B
  JNZ loop      ; 256 итераций
  ; восстановление регистров
RET
```

**Назначение:** Главная функция распаковки данных при старте ROM. Вызывается из `func_main_init` (0x0B57). Распаковывает данные из ROM-области (0x2761) в RAM (0x6000+).

**Алгоритм:**
1. `func_decomp_transpose` (0x04CD) — транспонирование/копирование упакованных данных
2. Цикл 256 итераций: 4 подфункции битплэйн-распаковки, каждая обрабатывает 8 байт
3. Каждая подфункция читает байт из [DE] (с декрементом DE), извлекает 2 бита и записывает в [HL] (с инкрементом HL)

**Подфункции битплэйн-распаковки:**

| Адрес | Имя | Биты | Размер |
|-------|-----|------|--------|
| 0x0439 | `func_decomp_plane0` | 7 и 3 | 39 байт |
| 0x045E | `func_decomp_plane1` | 6 и 2 | 37 байт |
| 0x0483 | `func_decomp_plane2` | 5 и 1 | 37 байт |
| 0x04A8 | `func_decomp_plane3` | 4 и 0 | 37 байт |

**Алгоритм подфункции (на примере plane0):**
```asm
MVI C, 08           ; 8 байт
loop:
  PUSH B
  LDAX D            ; A = [DE] (байт из источника)
  DCX D             ; DE-- (чтение в обратном порядке)
  MOV C, A          ; сохранить байт
  MOV A, M; CMA     ; ~[HL] (инверсия текущих данных)
  MOV B, A          ; B = ~[HL]
  MOV A, C; ANI 80  ; проверить бит 7
  MVI A, 00
  JZ skip1
  MOV A, M          ; A = [HL] (если бит 7 = 1)
skip1:
  MOV M, A          ; [HL] = результат
  MOV A, C; ANI 08  ; проверить бит 3
  MVI A, 00
  JZ skip2
  MOV A, B          ; A = ~[HL] (если бит 3 = 1)
skip2:
  ORA M             ; объединить с текущим
  MOV M, A          ; записать результат
  INX H             ; HL++
  POP B; DCR C
  JNZ loop
RET
```

**`func_decomp_transpose` — 0x04CD (56 байт):**
```asm
LXI H, 2761         ; источник в ROM (читать назад)
LXI B, 6000         ; цель в RAM
LXI D, 0008         ; 8 байт за блок
; 4 блока по 8 байт:
;   читать [HL], DCX H, писать [BC], INX B
;   после блока: PUSH BC, HL += 8, POP BC
```

**Связи:** → `func_decomp_transpose` (0x04CD), → `func_decomp_plane0` (0x0439), → `func_decomp_plane1` (0x045E), → `func_decomp_plane2` (0x0483), → `func_decomp_plane3` (0x04A8)

**Вызов:** из `func_main_init` (0x0B57) через `CALL 0401`

---

## 2. Распакованные функции (0x0800+)

### 2.1. `func_copy_to_vram` — 0x0800 (163 байта)

**Структура:**

```
0x0800: ORA A; RZ; MOV M,A    ; проверка: если A=0 → RET
0x0803: PUSH PSW/B/D/H        ; сохранение регистров
      : MOV D,A               ; D = входной параметр
      : LXI B, B000; DAD B    ; HL += 0xB000 (базовый адрес VRAM)
      ; Вычисление адреса VRAM:
      : MOV A,L; ANI 1F; MOV C,A  ; C = строка (5 бит)
      : MOV A,H; RRC×2; ANI C0    ; биты плоскости
      : MOV B,A
      : MOV A,L; RRC×2; ANI 38    ; строка bits 3-5
      : ADD M; MOV B,A            ; + смещение
      ; Сохранение SP и переключение:
      : MOV A,D; DI
      : LXI H,0000; DAD SP        ; HL = SP
      : SHLD 08DD                  ; сохранить SP
      ; Вычисление целевого адреса:
      : CMP B; MVI H,06; MOV L,A
      : JNC skip; INR H            ; коррекция
      : MOV E,M; INX H; MOV D,M   ; DE = данные источника
      : MVI H,00; MOV L,C         ; HL = строка
      : PUSH B; LXI B,051B; DAD B ; + смещение таблицы
      : MOV H,M                    ; старший байт VRAM
      : LDA 08D0                   ; палитра
      : POP B; ADD D; MOV L,A     ; + данные
      ; Установка SP на источник:
      : LXI B,1FF8; XCHG; SPHL; XCHG
      ; Копирование 16 байт (8× POP DE + MOV M,E/D + INX H):
      POP D; MOV M,E; INX H; MOV M,D; INX H  ; × 8
      ; Восстановление:
      : DAD B                      ; + 0x1FF8
      : LHLD 08DD; SPHL            ; восстановить SP
      : POP H; POP D; POP B; POP PSW
      : EI; RET
```

**Назначение:** Копирование 16-байтного блока данных в VRAM с трансляцией логического адреса в физический битплэйн-адрес. Использует трюк SP-swap для быстрого копирования через POP/MOV.

**Ключевые детали:**
- DI/EI — отключение прерываний на время работы с SP
- Сохранение SP в 0x08DD
- Трансляция адреса: строка + плоскость + смещение
- Палитра: байт данных + смещение из 0x08D0

**Связи:** → `var_stack_save` (0x08DD), → `var_vram_scroll` (0x08CF)

---

### 2.2. `func_render_block` — 0x0803

**Назначение:** Обёртка над `func_copy_to_vram`. Сохраняет все регистры, вычисляет VRAM-адрес из логических координат (HL + смещение BC), устанавливает палитру из 0x08D0, вызывает копирование.

**Входные параметры:**
- A = данные для отрисовки
- HL = логический адрес экрана
- BC = смещение

**Связи:** → `func_copy_to_vram` (0x0800), → `var_stack_save` (0x08DD)

---

### 2.3. `func_main_init` — 0x0B57

**Полная структура:**

```asm
DI
LXI SP, 0100        ; начальный стек
LXI H, 8000         ; очистка VRAM
; Цикл очистки 0x8000-0xFFFF:
clear_loop:
MOV M, A            ; записать 0
INX H
; ... проверка границы ...

CALL 0x0383         ; func_rom_init (PIA, ISR, EI)

LXI H, 08B2
SHLD 08DB           ; указатель данных палитры
MVI A, 09
STA 08C3            ; кадровой счётчик = 9

LXI H, 5000         ; очистка 0x5000-0x53FF
; ... цикл заполнения FF ...

CALL 0x0401         ; ROM-функция

LXI H, 7418         ; данные
LXI D, 2F61         ; цель
; Копирование 28 байт × 4 блока

; Инициализация переменных:
; 0x08EB = 0x07D0 (2000 — очки?)
; 0x08ED = 1
; 0x08EF = 3
; 0x08F1 = 5
; 0x08F3 = 8
; ...

CALL 0x3D4E         ; функция распакованного кода
CALL 0x1BE5         ; ROM-функция

; Переход к заставке:
; ... вывод текста "PUSH SPACE KEY" и др. ...
```

**Назначение:** Главная инициализация: очистка VRAM, настройка системы, загрузка данных, инициализация переменных, отображение заставки, цикл опроса клавиатуры.

**Связи:** → `func_rom_init` (0x0383), → `func_sound_init` (0x0121), → `func_keyboard_timer` (0x017C)

---

### 2.4. `func_piece_div2` — 0x0CA3

```asm
LHLD 08E9           ; загрузка координат
; 4× цикл RAR:
CMP M; MOV A,H; RAR; MOV H,A; MOV A,L; RAR; MOV L,A  ; × 4
ANI 1F              ; маска 5 бит
MOV B, A
MVI A, 17
ADD D
STA 08FE            ; сохранение позиции X
MVI A, 18
STA 08FF            ; сохранение позиции Y
CALL 0x01AE         ; set_stream_pos
MVI A, 20
CALL 0x01A1         ; data_loader
RET
```

**Назначение:** Деление координат фигуры на 16 (4× RAR), вычисление позиции на экране, загрузка данных фигуры.

---

### 2.5. `func_game_loop` — 0x0CE0

**Назначение:** Основной игровой цикл. Включает:
1. Опрос клавиатуры (`func_keyboard_timer`)
2. Проверка состояния (LDA 0900, CPI 01/02)
3. Диспетчер фигур (`func_piece_dispatch`)
4. Обработка типов фигур (CPI 1–7 → разные обработчики)
5. Инициализация новых фигур
6. Движение, поворот, падение
7. Проверка завершения рядов
8. Очистка заполненных рядов (`func_vram_clear`)

**Связи:** → `func_keyboard_timer` (0x017C), → `func_piece_dispatch` (0x0153), → `func_render_block` (0x0803), → `func_vram_clear` (0x0EF7)

---

### 2.6. `func_vram_clear` — 0x0EF7 (25 байт)

```asm
PUSH H; PUSH PSW
LXI H, 1000         ; размер области
loop:
DCX H
MOV A, L
ANA M               ; A = A AND [HL]
JNZ loop            ; пока не 0
DCR B
JNZ loop            ; внешний цикл
POP PSW; POP H; RET
```

**Назначение:** Очистка области VRAM. Цикл ANA M обнуляет байты. B определяет количество итераций.

---

## 3. Сводная таблица функций

| Адрес | Имя | Вызовы | Описание |
|-------|-----|--------|----------|
| 0x0100 | `func_rom_entry` | — | DI; JMP main_init |
| 0x010C | `func_read_16bit_de` | game_loop | Чтение 16-бит + 4× render_block |
| 0x0121 | `func_sound_init` | main_init | Инициализация звука (4× dispatch) |
| 0x0145 | `func_data_loader2` | game_loop | Загрузка данных + инкремент ptr |
| 0x014F | `func_store_data_ptr` | set_stream_pos | SHLD 0B53; RET |
| 0x0153 | `func_piece_type_lookup` | game_loop | Таблица вариантов фигур |
| 0x017C | `func_keyboard_timer` | game_loop, title_poll | Опрос SPACE + таймер |
| 0x0197 | `func_read_timer_data` | keyboard_timer, piece_type | Чтение из таблицы 0x08D3 |
| 0x01A1 | `func_data_loader` | piece_div2, ISR | Загрузка по указателю 0x0B53 |
| 0x01AE | `func_set_stream_pos` | piece_div2 | Установка позиции из 0x08FE/FF |
| 0x01BC | `func_jmp_table_dispatch` | sound_init | Диспетчер по таблице 0x01CD |
| 0x0201 | `func_sound_timer_write` | dispatch | mul7 + OUT 0x0B |
| 0x020E | `func_mul7` | sound_timer_write | ×12 (DAD-цепочка) |
| 0x032C | `func_table_lookup` | read_timer, dispatch | HL + (A XOR B) |
| 0x0351 | `func_read_16bit_v2` | set_stream_pos | MOV E,M; MOV D,M |
| 0x0355 | `func_calc_vram_offset` | — | 16-бит деление HL/DE |
| 0x0383 | `func_rom_init` | main_init | PIA, ISR, EI |
| 0x03A4 | `func_isr` | HW interrupt | ISR: счётчик, палитра, скролл |
| 0x0800 | `func_copy_to_vram` | data_loader | VRAM-копирование (SP-swap) |
| 0x0803 | `func_render_block` | game_loop | Отрисовка блока в VRAM |
| 0x0B57 | `func_main_init` | rom_entry | Инициализация + заставка |
| 0x0CA3 | `func_piece_div2` | game_loop | Координаты фигуры /16 |
| 0x0CE0 | `func_game_loop` | main_init | Главный цикл игры |
| 0x0EF7 | `func_vram_clear` | sound_init, game_loop | Очистка VRAM |
| 0x0401 | `func_decompress` | main_init | Распаковка данных при старте |
| 0x0439 | `func_decomp_plane0` | decompress | Битплэйн 0: биты 7,3 |
| 0x045E | `func_decomp_plane1` | decompress | Битплэйн 1: биты 6,2 |
| 0x0483 | `func_decomp_plane2` | decompress | Битплэйн 2: биты 5,1 |
| 0x04A8 | `func_decomp_plane3` | decompress | Битплэйн 3: биты 4,0 |
| 0x04CD | `func_decomp_transpose` | decompress | Транспонирование ROM→RAM |

---

## 4. Граф вызовов (упрощённый)

```
func_rom_entry
  └→ func_main_init
       ├→ func_rom_init
       │    ├→ data_isr_vector (0x0038)
       │    └→ func_isr (0x03A4)
       │         ├→ var_frame_count_isr (0x08DF)
       │         ├→ var_frame_counter (0x08C3)
       │         └→ var_data_ptr (0x08DB)
       ├→ func_decompress          ; ← распаковка данных при старте
       │    ├→ func_decomp_transpose (0x04CD)
       │    ├→ func_decomp_plane0 (0x0439)
       │    ├→ func_decomp_plane1 (0x045E)
       │    ├→ func_decomp_plane2 (0x0483)
       │    └→ func_decomp_plane3 (0x04A8)
       ├→ func_sound_init
       │    ├→ func_jmp_table_dispatch
       │    │    └→ data_jmp_table (0x01CD)
       │    └→ func_vram_clear
       ├→ func_keyboard_timer
       │    └→ func_read_timer_data
       │         ├→ data_timer_table (0x08D3)
       │         └→ func_table_lookup
       └→ func_game_loop
            ├→ func_keyboard_timer
            ├→ func_piece_type_lookup
            │    └→ func_read_timer_data
            ├→ func_render_block
            │    └→ func_copy_to_vram
            │         ├→ var_stack_save (0x08DD)
            │         └→ var_vram_scroll (0x08CF)
            └→ func_vram_clear
```

---

## 5. Ключевые открытия

1. **func_mul7 умножает на 12, не на 7.** Цепочка DAD: ×2 → DE=×2 → ×4 → +DE=×6 → ×2=×12. Масштабирование частоты ВИ53.

2. **func_copy_to_vram использует SP-swap трюк.** Сохраняет SP в 0x08DD, устанавливает SP на источник, копирует 16 байт через 8× POP DE + MOV M,E/D. Требует DI/EI.

3. **func_isr — не просто счётчик.** Выполняет палитровую анимацию (16 цветов через порт 0x0C), управление скроллингом (порт 0x03), и проверку перехода состояния игры.

4. **func_piece_type_lookup — рандомизация фигур.** Использует верхний nibble таймера как псевдослучайный индекс в таблице перестановок.

5. **sub_0191 — не отдельная функция.** Это часть `func_keyboard_timer` (fall-through путь). Удалена из RDB.

6. **func_decompress (0x0401) — распаковка данных при старте.** ROM-файл (17664 байт) содержит сжатые данные в ROM-области (0x0100–0x07FF). Функция `func_decompress` вызывается из `func_main_init` и распаковывает данные в RAM (0x6000+). Алгоритм: транспонирование + 4 битплэйн-декомпрессора (биты 7/3, 6/2, 5/1, 4/0). 256 итераций × 4 плоскости × 8 байт = 8192 байт распакованных данных.
