; ============================================================================
; Данные (RAM): var_ram_symbols.asm
; Адрес:  — (диапазон ОЗУ, не входит в образ ROM)
; Размер: — (это определения адресов, без байтового содержимого)
; Назначение: сводный заголовок символьных адресов ОЗУ. Все объекты, которые в
;   ROM не хранятся (переменные var_, рантайм-буферы, векторы прерываний) выгружены
;   ТОЛЬКО как символические EQU-метки по TZ Stage 10 п.2 — байтовое содержимое в
;   образ ROM не входит и генерируется программой в рантайме.
; ПРИМЕЧАНИЕ (отклонение от п.1): вместо 44 отдельных файлов-заглушек собрано в один
;   include-заголовок (удобно для Stage 11). Перечень и адреса взяты из RDB.
; Формат: имя: EQU  <адрес>; для буферов дан <имя>_end = адрес+размер.
; ============================================================================

; --- Векторы прерываний i8080 (перехваты, program-observable) -----------------
data_int_vector_reset:  EQU 0000h   ; RST 0x00 / RESET-вектор (JMP в точку входа)
data_int_vector_rst7:   EQU 0038h   ; RST 0x38 / VBlank ISR-вектор (JMP 0x03A4)

; --- Звук VI53 (каналы) -------------------------------------------------------
var_snd_period_ch0:     EQU data_snd_init   ; слово: период канала 0
var_snd_period_ch1:     EQU data_snd_init+02h   ; слово: период канала 1
var_snd_period_ch2:     EQU data_snd_init+04h   ; слово: период канала 2
var_snd_state:          EQU data_snd_init+06h   ; байт: состояние звукового генератора

; --- Видео / палитра / экран -------------------------------------------------
var_palette_timer:      EQU data_ram_init_image_08C3   ; байт: таймер палитры (обновление по кадру)
var_portb_mode:         EQU data_ram_init_image_08C3+01h   ; байт: тень режима порта B (ВВ55)
var_scroll:             EQU data_ram_init_image_08C3+0Ch   ; байт: значение скролла (порт A тень)
var_screen_mode:        EQU data_ram_init_image_08C3+0Dh   ; байт: режим экрана
var_palette_ptr:        EQU data_ram_init_image_08C3+18h   ; слово: 2-байтный указатель палитры (OUT 0Ch)
var_saved_sp:           EQU data_ram_init_image_08C3+1Ah   ; слово: сохранённый stack pointer
var_frame_counter:      EQU data_ram_init_image_08C3+1Ch   ; байт: счётчик кадров (INR в VBlank ISR)

; --- Клавиатура (результат матричного сканирования 8x8 в ISR) -----------------
data_kbd_matrix:        EQU data_ram_init_image_08C3+10h   ; 8 байт: состояние столбцов 0x08D3..0x08DA
data_kbd_matrix_end:    EQU data_ram_init_image_08C3+18h

; --- Игровое состояние --------------------------------------------------------
var_num_leading_zero_flag: EQU data_ram_init_image_08C3+1Fh ; байт: флаг ведущих нулей (формат чисел)
var_score:              EQU data_ram_init_image_08C3+30h   ; слово: очки
var_level:              EQU data_ram_init_image_08C3+32h   ; байт: номер текущего уровня (1..15)
var_page_flip:          EQU data_ram_init_image_08C3+36h   ; слово: переключение страниц буфера
var_bonus_counter:      EQU data_ram_init_image_08C3+38h   ; байт: счётчик бонуса
var_bonus_threshold:    EQU data_ram_init_image_08C3+39h   ; слово: порог бонуса
var_game_state:         EQU data_ram_init_image_08C3+3Dh   ; байт: состояние игры
var_player_row:         EQU data_ram_init_image_08C3+3Eh   ; байт: строка игрока
var_player_col:         EQU data_ram_init_image_08C3+3Fh   ; байт: колонка игрока
var_player_bufaddr:     EQU data_ram_init_image_08C3+40h   ; слово: адрес игрока в буфере
var_collision_flag:     EQU data_ram_init_image_08C3+42h   ; байт: флаг коллизии
var_work_const:         EQU data_ram_init_image_08C3+44h   ; байт: рабочая константа
var_entity_index:       EQU data_ram_init_image_08C3+4Bh   ; байт: индекс сущности

; --- Временные движка (кэш позиций объектов/яиц, 0x08E3..0x091C) -------------
; Именование по роли в func_game_update/func_score_and_redraw/func_draw_game_objects.
; Слово rc: lo=строка, hi=колонка.
var_enemy_rc:           EQU data_ram_init_image_08C3+20h   ; слово: позиция врага (prev cache)
var_bonus_rc:           EQU data_ram_init_image_08C3+22h   ; слово: позиция бонуса
var_egg_rc:             EQU data_ram_init_image_08C3+24h   ; слово: позиция яйца
var_blink_cell:         EQU data_ram_init_image_08C3+26h   ; слово: текущая мигающая клетка (erase)
var_blink_type:         EQU data_ram_init_image_08C3+27h   ; байт: тип символа в мигающей клетке
var_item_cost_table:    EQU data_ram_init_image_08C3+2Ah   ; таблица стоимости предмета (base+type)
var_egg_hist_prev:      EQU data_ram_init_image_08C3+34h   ; байт: пред. позиция яйца (история)
var_egg_hist_cur:       EQU data_ram_init_image_08C3+35h   ; байт: текущая позиция яйца
var_page_flip_hi:       EQU data_ram_init_image_08C3+37h   ; байт: старш. байт var_page_flip
var_draw_row:           EQU data_ram_init_image_08C3+3Bh   ; байт: строка курсора вывода (restore)
var_draw_col:           EQU data_ram_init_image_08C3+3Ch   ; байт: колонка курсора вывода
var_obj_type_idx:       EQU data_ram_init_image_08C3+49h   ; байт: индекс типа объекта (×4 → тайл)
var_move_dir:           EQU data_ram_init_image_08C3+4Ah   ; байт: флаг/направление движения
var_egg_counter:        EQU data_ram_init_image_08C3+4Ch   ; байт: счётчик яиц
var_egg_seq:            EQU data_ram_init_image_08C3+4Dh   ; байт: порядковый счётчик спавна
var_egg_slot:           EQU data_ram_init_image_08C3+59h   ; байт: выбранный слот яйца (spawn)
var_score_delta:        EQU data_ram_init_image_08C3+28h   ; слово: дельта счёта (scratch collision-death)
var_score_scratch:      EQU data_game_object_init+01h   ; байт: перенос/scratch (collision-death)
var_prng_seed:          EQU var_prng_seed_init   ; слово: сид PRNG (иниц. в ROM, правится in-place)

; --- Scratch-байты островка data_ram_init_image_08C3 (0x08C3..0x0924). -------
; Роль точно не установлена — именованы нейтрально по адресу, чтобы emit-код
; не содержал абсолютных литералов в кодовую зону (требование свободной
; конкатенации, Stage-4). На Stage-3B их значения перепривяжутся к
; data_ram_init_image_08C3+смещение, чтобы ехать вместе с островком.
var_scr_08EE:           EQU data_ram_init_image_08C3+2Bh   ; иниц. =01h в func_main_init
var_scr_08EF:           EQU data_ram_init_image_08C3+2Ch   ; иниц. =03h в func_main_init
var_scr_08F0:           EQU data_ram_init_image_08C3+2Dh   ; иниц. =05h в func_main_init
var_scr_08F1:           EQU data_ram_init_image_08C3+2Eh   ; иниц. =08h в func_main_init
var_scr_0906:           EQU data_ram_init_image_08C3+43h   ; обнуляется в func_game_update/func_gamestate_handlers
var_scr_0909:           EQU data_ram_init_image_08C3+46h   ; scratch-пара (в game_update <- var_player_col)
var_scr_090A:           EQU data_ram_init_image_08C3+47h   ; scratch-пара (в game_update <- var_player_row)
var_scr_091D:           EQU data_ram_init_image_08C3+5Ah   ; HUD-счётчик (обрезка бонуса до 6 в func_draw_level_hud)
; --- ROM-тайлы глифов (byte-exact зона <0x2761) ------------------------------
data_tile_2706:         EQU data_tile_graphics   ; глиф-тайл (spawn fallback)
data_tile_empty:        EQU data_tile_graphics+04h   ; глиф пустой клетки
data_tile_2716:         EQU data_tile_graphics+10h   ; глиф-тайл (spawn variant B)
data_tile_272A:         EQU data_tile_graphics+24h   ; глиф-тайл (bonus draw)

; --- Буфер параметров текущего уровня (копия записи data_level_params) --------
data_level_param_buf:   EQU data_ram_init_image_08C3+4Eh   ; 8 байт: 0x0911..0x0918
data_level_param_buf_end: EQU data_ram_init_image_08C3+56h

; --- Сущности ---------------------------------------------------------------
var_entity1_state:      EQU data_ram_init_image_08C3+57h   ; байт: состояние сущности 1
var_entity2_state:      EQU data_ram_init_image_08C3+58h   ; байт: состояние сущности 2
var_lives_icons:        EQU data_ram_init_image_08C3+5Bh   ; байт: счётчик/иконки жизней
data_entity_xcoords:    EQU data_ram_init_image_08C3+5Ch   ; 3 байта: X-координаты сущностей
data_entity_xcoords_end: EQU data_ram_init_image_08C3+5Fh
data_entity_ycoords:    EQU data_ram_init_image_08C3+5Fh   ; 3 байта: Y-координаты сущностей
data_entity_ycoords_end: EQU data_ram_init_image_08C3+62h

; --- Текст / указатели ------------------------------------------------------
var_music_work_ptr:     EQU data_game_object_init+05h   ; слово: рабочий указатель музыки
var_text_ptr:           EQU data_game_object_init+17h   ; слово: указатель текста

; --- Музыкальный секвенсор --------------------------------------------------
; var_music_* / data_voice_param_buf / var_music_voice2_flag(_hi) живут в
; перемещаемой зоне образа (>= 0x2761): их инициализированные значения — часть
; ROM, и при компакции (Фаза 2) они сдвигаются вместе с кодом. Поэтому их
; адреса — НЕ литералы здесь, а РЕАЛЬНЫЕ метки на байтах emit-файлов данных
; (data_music_init.asm @0x383A.. / var_music_voice2_flag_init.asm @0x3BC8): метка
; едет за блоком автоматически (verbatim = исходный адрес; compact = reloc).
; var_music_work_ptr (0B41h) ниже 0x2761 — не двигается, определён выше.

; --- Крупные рантайм-буферы (вне ROM-образa, ОЗУ) ---------------------------
; Текстовый back-буфер 32x32 кодов символов. Исторически лежал на 0x5000
; (имя data_ram_buffer_5000). Фаза 1: перенесён на 0x6600 — окно выше
; глиф-блока (0x4600..0x65FF), чтобы read-only блок не наезжал на write-RAM
; и дыра 0x4600..0x55FF схлопнулась. База — единственная константа
; переноса: все позиции курсора в коде — как data_text_buffer+смещение, а
; func_render_glyph использует textbuf_to_vram (= 0 - база, перевод в VRAM).
data_text_buffer:       EQU 6600h   ; 1024 байта: текстовый/символьный back-буфер
data_text_buffer_end:   EQU 6A00h
textbuf_to_vram:        EQU 0 - data_text_buffer   ; 9A00h: HL(буфер)+константа = смещение клетки
; --- Мигание выхода (Фаза 4) — 3 байта сразу за текстовым буфером ------------
; Зона 0x6A00.. свободна: буфер заполняется только 0x400 байтами от 0x6600,
; координаты курсора не превышают 31*32+31=0x3FF. Иниц. в func_main_init
; (var_exit_phase=0FFh) и сброс в func_level_loader на каждом уровне.
var_exit_phase:         EQU 6A00h   ; байт: 0FFh=выкл; 0=светлый нарисован, 1=тёмный
var_exit_rc:            EQU 6A01h   ; слово: lo=строка, hi=колонка выхода (как var_bonus_rc)
; --- Масочный scratch OR-композита (func_render_glyph_or) --------------------
; 8 байт плоскости 0 (маски) текущего глифа: копятся сюда один раз, чтобы
; указатель приёмника (HL), указатель цвета (DE) и указатель маски (BC) шли
; независимо по 4 плоскостям. Реентрансно: scratch живёт только внутри одного
; вызова glyph_or (стек сохранён PUSH H). Зона 0x6A03.. свободна (см. выше).
var_or_mask_scratch:    EQU 6A03h   ; 8 байт: маска P0 для masked-blit оверлея героя
; data_glyph_block — МЕТКА на распакованном блоке, определена в
; data_glyph_block_unpacked.asm (этап B: адрес задаёт компоновщик GLYPH_BASE).
data_glyph_block_end:   EQU 8000h   ; конец read-only окна (нижние 32КБ RAM)
; data_ram_sprites_7418 (0x7418) не определён: копир спрайтов в func_main_init
; выведен из исполнения (вестигиальный остаток распаковщика) — reader у 0x7418
; отсутствует (grep + capture_A), а его источник (хвост data_gfx_2761) обнулён.
