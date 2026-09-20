# Stage 2. Первичное обследование функций и блоков данных

## Методика

1. ROM запущен (PC=0x0100), отработал ~5 с, затем пауза.
2. Достижимый код определён через MCP `debug_analyze_code` (multi-entry): точки входа `0x0100` (основной поток) и `0x03A4` (RST7 ISR — недостижим статически, входит по прерыванию).
3. Результаты анализа: **instruction_count = 3507, code_bytes = 6526, truncated = false**. Диапазон кода: `0x0100`–`0x3DE7` (разреженный, с перемежающимися таблицами данных).
4. Точки входа функций получены из декодированных MCP операндов `CALL`/`JMP` (310 CALL-инструкций). Все имена/дизассемблирование — из MCP.
5. RDB заполнена через `debug_add_rdb_object`, связи — через `debug_add_rdb_link`, сохранена `debug_save_rdb`.

## ROM Database (RDB)

- Путь: `./src/putup.rdb` (platform=vector06c, rom_sha256=8486442e…)
- Объектов: **64** (53 функции + 8 переменных + 3 блока данных)
- Связей: 17 (подтверждённые CALL/JMP/вектор/данные)
- RDB save: **success** (exists_on_disk=true)

### Точки входа (entry points)

| Адрес | Имя | Назначение |
|-------|-----|-----------|
| 0x0100 | func_entry | Точка входа ROM: `DI; JMP func_main_init` |
| 0x0B57 | func_main_init | Инициализация программы (SP, VRAM, банки, спрайты, переменные) |
| 0x0383 | func_hw_init | Аппаратная инициализация + установка векторов прерываний |
| 0x03A4 | func_vblank_isr | RST7/VBlank ISR |

### Функции с установленным назначением (именованы)

| Адрес | Имя | Кратко |
|-------|-----|--------|
| 0x0121 | func_palette_init | Инициализация палитры (серия CALL func_set_color, CALL 0x0EF7) |
| 0x014F | func_set_text_ptr | `SHLD 0x0B53` — установить курсор/указатель текста (параметр HL) |
| 0x017C | func_check_modkeys | Проверка модификаторов (IN 01h: Shift/Ctrl/RUS) |
| 0x0197 | func_read_keybuf | Чтение байта буфера клавиатуры 0x08D3 по индексу A |
| 0x01A1 | func_print_char_at_ptr | Печать символа по курсору 0x0B53 + инкремент курсора |
| 0x01BC | func_set_color | Установка ячейки палитры (параметры A/E) |
| 0x0321 | func_print_string | Посимвольный вывод строки до терминатора 0xFF |
| 0x032C | func_hl_add_a | `HL += A` |
| 0x0803 | func_print_char | Базовый вывод символа из A |

### Функции с неизвестным назначением (зарегистрированы как `func_XXXX_unknown`)

0x0104, 0x0145, 0x0153, 0x01AE, 0x0331, 0x0355, 0x0401, 0x0439, 0x045E, 0x0483,
0x04A8, 0x04CD, 0x0800, 0x0CA3, 0x0CE0, 0x0EF7, 0x1123, 0x1197, 0x11E9, 0x11EE,
0x121A, 0x130A, 0x1477, 0x1B87, 0x1BA8, 0x1BC9, 0x1BD4, 0x1BE5, 0x3858, 0x3902,
0x3940, 0x3946, 0x3B0F, 0x3BCA, 0x3C77, 0x3C7D, 0x3D48, 0x3D4E, 0x3DB8, 0x3DCD

> Назначение каждой будет установлено в Stage 3 (переименование + комментарии).

### Переменные (RAM, zeropage-образ 0x08xx и 0x0Bxx)

| Адрес | Имя | Размер | Назначение |
|-------|-----|--------|-----------|
| 0x08C3 | var_palette_timer | 1 | Таймер/счётчик обновления палитры (ISR) |
| 0x08C4 | var_portb_mode | 1 | Байт режима/бордюра, выводимый в порт 02h |
| 0x08CF | var_scroll | 1 | Регистр вертикального скролла (порт 03h) |
| 0x08D0 | var_screen_mode | 1 | Конфигурация экрана (0xE0) |
| 0x08DB | var_palette_ptr | 2 | Указатель таблицы палитры (=0x08B2) |
| 0x08DF | var_frame_counter | 1 | Счётчик кадров (INR в каждом VBlank) |
| 0x0B53 | var_text_ptr | 2 | Курсор вывода текста |

### Блоки данных

| Адрес | Имя | Тип | Примечание |
|-------|-----|-----|-----------|
| 0x08D3 | data_kbd_matrix | Data(8) | Буфер скана клавиатурной матрицы 8×8 (пишется в ISR) |
| 0x2F61 | data_sprites_2F61_unknown | Data | Источник спрайтовых данных, копируемых в 0x7418 при старте |
| 0x5000 | data_ram_buffer_5000 | Data(1024) | RAM-буфер, заполняется 0xFF при старте |
| 0x7418 | data_ram_sprites_7418 | Data | RAM: рабочая таблица спрайтов (приёмник копии из 0x2F61) |

### Константные таблицы (только чтение, по карте доступа Stage 1)

Не записываются программой → кандидаты на данные глифов/спрайтов/карт уровней:
- `0x2700`–`0x3700` (уточнение границ в Stage 7/9)
- `0x3E00`–`0x4400`

> Точные границы и назначение будут установлены в Stage 7 (глифы) и Stage 9 (карты уровней).

## Подтверждённые связи (RDB links)

```
func_entry(0100)      -> func_main_init(0B57)   [JMP]
func_main_init(0B57)  -> func_hw_init(0383)     [CALL]
func_main_init(0B57)  -> func_0401(0401)        [CALL]
func_main_init(0B57)  -> func_3D4E(3D4E)        [CALL]
func_main_init(0B57)  -> data_sprites_2F61      [чтение]
func_main_init(0B57)  -> data_ram_sprites_7418  [запись]
func_hw_init(0383)    -> func_vblank_isr(03A4)  [установка вектора RST7]
func_vblank_isr(03A4) -> func_3858(3858)        [CALL]
func_vblank_isr(03A4) -> data_kbd_matrix(08D3)  [запись скана]
func_check_modkeys    -> func_read_keybuf       [CALL]
func_read_keybuf      -> func_hl_add_a          [CALL]
func_print_char_at_ptr-> func_0800              [CALL]
func_print_string     -> func_print_char_at_ptr [CALL]
func_palette_init     -> func_set_color         [CALL]
func_palette_init     -> func_0EF7              [CALL]
func_0104             -> func_1BD4              [CALL]
func_0104             -> func_print_char(0803)  [CALL]
```

## Выводы

**Facts:**
1. Достижимый код: 3507 инструкций / 6526 байт в диапазоне 0x0100–0x3DE7.
2. Обнаружено 53 точки входа функций (по операндам CALL/JMP из MCP).
3. Программа использует собственный образ как RAM-переменные (0x08xx, 0x0Bxx) и внешнюю RAM 0x5000–0x7FFF.
4. RDB заполнена (64 объекта, 17 связей) и сохранена на диск.

**Inferences:**
1. Ядро вывода текста: func_print_string → func_print_char_at_ptr → func_0800/func_print_char(0803).
2. Ввод: ISR сканирует матрицу в 0x08D3; func_read_keybuf/func_check_modkeys читают её — основа ожидания клавиш (Stage 6).
3. Константные таблицы 0x2700–0x3700 и 0x3E00–0x4400 — данные (глифы/спрайты/уровни).

**Unknowns:** 40 функций с неизвестным назначением; точные границы и содержимое константных таблиц.
