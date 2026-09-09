# Stage 4. Определение параметров функций

## Цель

Для всех 30 функций в RDB определить входные параметры (регистры), возвращаемые значения и побочные эффекты. Сохранить параметры как свойства RDB-объектов через `debug_set_rdb_property`.

## Методология

1. Дизассемблирование каждой функции через `debug_disassemble_range`
2. Анализ первых инструкций: какие регистры читаются до записи (входные параметры)
3. Анализ вызовов: что передаётся в CALL (через регистры или глобальные переменные)
4. Анализ RET: какие регистры содержат результат (возвращаемое значение)
5. Анализ сохранения/восстановления регистров (PUSH/POP) — что сохраняется

## Результаты

### Сводная таблица параметров функций

| Адрес | Имя | Параметры (вход) | Возврат | Описание |
|-------|-----|-------------------|---------|----------|
| 0x0100 | rom_entry | none | void (JMP) | Точка входа ROM. DI; JMP rom_init |
| 0x0145 | data_read_loop | A=data_byte, HL=source_ptr | void | Обёртка draw_to_vram. Сохраняет HL в [0x0B53] |
| 0x017C | dec_mod8 | A=counter | A=(A-1) mod 8 | Циклический декремент. Возврат к 7 при уходе в минус |
| 0x019B | sub_019B | none (читает [0x08D3]) | A=data_value | Табличный поиск через sub_032C. HL сохраняется |
| 0x01A1 | kbd_input_handler | none (IN 01) | A=keyboard_state | Читает порт клавиатуры 0x01, тестирует бит 5 |
| 0x01AE | calc_and_draw | none (читает [0x08FE/FF]) | void | Загружает X/Y из глобальных переменных, вызывает calc_obj_addr |
| 0x0321 | data_dispatch | HL=data_stream_ptr | void | Цикл: читает [HL], вызывает kbd_input_handler до нулевого маркера |
| 0x032C | sub_032C | A=index, HL=table_ptr | A=looked_up_value | 16-битный табличный поиск с арифметикой carry |
| 0x0383 | init_1 | none | void | Устанавливает вектор RST 7 (JMP 0x03A4), draw_offset=0xE0, EI |
| 0x03A4 | isr_handler | none (ISR entry) | void (IRET) | ISR: AY-3-8910, клавиатура, анимация. Сохраняет H/D/B/PSW |
| 0x0401 | init_2 | none | void (preserves all) | Графический цикл 256 итераций от 0x6000. PUSH/POP всех регистров |
| 0x0439 | main_logic | HL=VRAM_buf_ptr, DE=data_src | void | Обработка битов 7/4. Модифицирует 8 байт по HL |
| 0x045E | sub_045E | HL=VRAM_buf_ptr, DE=data_src | void | Обработка битов 6/3. Та же структура, что main_logic |
| 0x0483 | sub_0483 | HL=VRAM_buf_ptr, DE=data_src | void | Обработка битов 5/1. Та же структура, что main_logic |
| 0x04A8 | sub_04A8 | HL=VRAM_buf_ptr, DE=data_src | void | Обработка битов 4/0. Та же структура, что main_logic |
| 0x04CD | sub_04CD | none (HL=0x2761, BC=0x6000) | void | Копирует 8-байтные блоки из ROM в VRAM 0x6000 |
| 0x0800 | draw_to_vram | A=data_byte, HL=encoded_vram_addr | void | Разворачивает 1 байт в 8 вертикальных строк VRAM через стек |
| 0x0B57 | rom_init | none (entry from JMP) | void (never returns) | Инициализация: очистка RAM, загрузка данных, копирование графики |
| 0x0C65 | data_process_loop | none (globals) | void (loops forever) | Сканирует 0x5180 на маркеры 0x75/0xFE |
| 0x0C95 | scan_loop_tail | HL=scan_ptr, B=counter | void | Хвост цикла сканирования. INX H; DCR B; JNZ |
| 0x197C | game_main_loop | none (globals) | void (loops forever) | Игровой цикл: счётчик кадров, ROM-таблицы, копирование/отрисовка объектов |
| 0x1B87 | obj_copy_data | DE=object_index | void | Копирует 4 байта через data_read_loop в RAM объектов |
| 0x1BA8 | obj_draw_data | DE=object_index | void | Рисует 4 байта через draw_to_vram в VRAM |
| 0x1BD4 | calc_obj_addr | D=type_index, E=slot_index | HL=address | HL = E×32 + D×256 + 0x5000 |
| 0x1BE5 | obj_setup | none (HL=0x5000, BC=0x0400) | void | Заполняет 0x400 байт по 0x5000, ждёт клавишу 0x20 |
| 0x384E | isr_anim_update | none (globals) | void | Обновляет анимацию: читает [0x3854], инкрементирует [0x383A] |
| 0x3890 | sub_3890 | none (globals) | void | Сброс кадров анимации при достижении лимитов |
| 0x3BCA | isr_obj_update_1 | none (globals) | void | Обновляет объекты по типу из [HL+0x0D], таблица 0x445D (шаг 0x14) |
| 0x3C7D | isr_obj_update_2 | none (globals) | void | Обновляет объекты по типу из [HL+0x0A], таблица 0x42F9 (шаг 0x0A) |
| 0x3D4E | init_objects | none (globals) | void | Очищает счётчики анимации, заполняет поля объектов из [0x3856] |
| 0x3DCD | sub_3DCD | none (HL=0x3DE8, DE=0x03F8) | void | Копирует 3 байта в VRAM 0x03F8 через порт 0x08 |

## Классификация функций по типу параметров

### 1. Точки входа (нет параметров, не возвращаются)
- `rom_entry` (0x0100) → JMP rom_init
- `rom_init` (0x0B57) → инициализация, переход в data_process_loop
- `data_process_loop` (0x0C65) → бесконечный цикл обработки
- `game_main_loop` (0x197C) → бесконечный игровой цикл

### 2. Функции с регистровыми параметрами
- `draw_to_vram` (0x0800): **A** + **HL** → void
- `dec_mod8` (0x017C): **A** → **A**
- `sub_032C` (0x032C): **A** + **HL** → **A**
- `calc_obj_addr` (0x1BD4): **D** + **E** → **HL**
- `main_logic` (0x0439): **HL** + **DE** → void
- `sub_045E/0483/04A8`: **HL** + **DE** → void

### 3. Функции-обёртки (передают параметры через)
- `data_read_loop` (0x0145): пропускает A/HL в draw_to_vram
- `calc_and_draw` (0x01AE): читает глобальные → D/E в calc_obj_addr
- `obj_copy_data` (0x1B87): DE → calc_obj_addr → data_read_loop
- `obj_draw_data` (0x1BA8): DE → calc_obj_addr → draw_to_vram

### 4. Функции без параметров (работают с глобальными переменными)
- `kbd_input_handler` (0x01A1): IN 01
- `isr_handler` (0x03A4): ISR, CPU auto-push
- `isr_anim_update` (0x384E): читает [0x3854], [0x383A]
- `isr_obj_update_1` (0x3BCA): читает [0x3854], [0x0B41]
- `isr_obj_update_2` (0x3C7D): читает [0x3BC8], [0x3854], [0x0B41]
- `init_objects` (0x3D4E): читает [0x3856]
- `sub_3890` (0x3890): читает [0x3854], [0x383B/383C]

### 5. Инициализационные функции (без параметров, self-contained)
- `init_1` (0x0383): настройка прерываний
- `init_2` (0x0401): графический цикл
- `sub_04CD` (0x04CD): копирование графики
- `obj_setup` (0x1BE5): инициализация объектов
- `sub_3DCD` (0x3DCD): копирование в VRAM

## Свойства RDB

Для каждой функции установлены свойства через `debug_set_rdb_property`:
- `params` — описание входных параметров
- `returns` — описание возвращаемого значения

Для `draw_to_vram` (0x0800) дополнительно установлены:
- `param_A`, `param_HL` — детальные описания параметров
- `calling_convention` — register-based
- `description` — полное описание работы функции

## Статистика

- Всего функций в RDB: **30**
- Функций с регистровыми параметрами: **8**
- Функций без параметров (глобальные): **12**
- Точек входа: **4**
- Функций-обёрток: **4**
- Инициализационных: **5** (включая точки входа)
- Функций с возвращаемым значением: **3** (dec_mod8, sub_019B, sub_032C, calc_obj_addr)

## RDB

- Файл: `./src/putup.rdb`
- Объектов: 53
- Сохранение: **success**
