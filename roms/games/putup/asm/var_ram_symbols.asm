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
var_snd_period_ch0:     EQU 031Ah   ; слово: период канала 0
var_snd_period_ch1:     EQU 031Ch   ; слово: период канала 1
var_snd_period_ch2:     EQU 031Eh   ; слово: период канала 2
var_snd_state:          EQU 0320h   ; байт: состояние звукового генератора

; --- Видео / палитра / экран -------------------------------------------------
var_palette_timer:      EQU 08C3h   ; байт: таймер палитры (обновление по кадру)
var_portb_mode:         EQU 08C4h   ; байт: тень режима порта B (ВВ55)
var_scroll:             EQU 08CFh   ; байт: значение скролла (порт A тень)
var_screen_mode:        EQU 08D0h   ; байт: режим экрана
var_palette_ptr:        EQU 08DBh   ; слово: 2-байтный указатель палитры (OUT 0Ch)
var_saved_sp:           EQU 08DDh   ; слово: сохранённый stack pointer
var_frame_counter:      EQU 08DFh   ; байт: счётчик кадров (INR в VBlank ISR)

; --- Клавиатура (результат матричного сканирования 8x8 в ISR) -----------------
data_kbd_matrix:        EQU 08D3h   ; 8 байт: состояние столбцов 0x08D3..0x08DA
data_kbd_matrix_end:    EQU 08DBh

; --- Игровое состояние --------------------------------------------------------
var_num_leading_zero_flag: EQU 08E2h ; байт: флаг ведущих нулей (формат чисел)
var_score:              EQU 08F3h   ; слово: очки
var_level:              EQU 08F5h   ; байт: номер текущего уровня (1..15)
var_page_flip:          EQU 08F9h   ; слово: переключение страниц буфера
var_bonus_counter:      EQU 08FBh   ; байт: счётчик бонуса
var_bonus_threshold:    EQU 08FCh   ; слово: порог бонуса
var_game_state:         EQU 0900h   ; байт: состояние игры
var_player_row:         EQU 0901h   ; байт: строка игрока
var_player_col:         EQU 0902h   ; байт: колонка игрока
var_player_bufaddr:     EQU 0903h   ; слово: адрес игрока в буфере
var_collision_flag:     EQU 0905h   ; байт: флаг коллизии
var_work_const:         EQU 0907h   ; байт: рабочая константа
var_entity_index:       EQU 090Eh   ; байт: индекс сущности

; --- Временные движка (кэш позиций объектов/яиц, 0x08E3..0x091C) -------------
; Именование по роли в func_game_update/func_score_and_redraw/func_draw_game_objects.
; Слово rc: lo=строка, hi=колонка.
var_enemy_rc:           EQU 08E3h   ; слово: позиция врага (prev cache)
var_bonus_rc:           EQU 08E5h   ; слово: позиция бонуса
var_egg_rc:             EQU 08E7h   ; слово: позиция яйца
var_blink_cell:         EQU 08E9h   ; слово: текущая мигающая клетка (erase)
var_blink_type:         EQU 08EAh   ; байт: тип символа в мигающей клетке
var_item_cost_table:    EQU 08EDh   ; таблица стоимости предмета (base+type)
var_egg_hist_prev:      EQU 08F7h   ; байт: пред. позиция яйца (история)
var_egg_hist_cur:       EQU 08F8h   ; байт: текущая позиция яйца
var_page_flip_hi:       EQU 08FAh   ; байт: старш. байт var_page_flip
var_draw_row:           EQU 08FEh   ; байт: строка курсора вывода (restore)
var_draw_col:           EQU 08FFh   ; байт: колонка курсора вывода
var_obj_type_idx:       EQU 090Ch   ; байт: индекс типа объекта (×4 → тайл)
var_move_dir:           EQU 090Dh   ; байт: флаг/направление движения
var_egg_counter:        EQU 090Fh   ; байт: счётчик яиц
var_egg_seq:            EQU 0910h   ; байт: порядковый счётчик спавна
var_egg_slot:           EQU 091Ch   ; байт: выбранный слот яйца (spawn)
var_score_delta:        EQU 08EBh   ; слово: дельта счёта (scratch collision-death)
var_score_scratch:      EQU 0B3Dh   ; байт: перенос/scratch (collision-death)
var_prng_seed:          EQU 1155h   ; слово: сид PRNG (иниц. в ROM, правится in-place)

; --- Scratch-байты островка data_ram_init_image_08C3 (0x08C3..0x0924). -------
; Роль точно не установлена — именованы нейтрально по адресу, чтобы emit-код
; не содержал абсолютных литералов в кодовую зону (требование свободной
; конкатенации, Stage-4). На Stage-3B их значения перепривяжутся к
; data_ram_init_image_08C3+смещение, чтобы ехать вместе с островком.
var_scr_08EE:           EQU 08EEh   ; иниц. =01h в func_main_init
var_scr_08EF:           EQU 08EFh   ; иниц. =03h в func_main_init
var_scr_08F0:           EQU 08F0h   ; иниц. =05h в func_main_init
var_scr_08F1:           EQU 08F1h   ; иниц. =08h в func_main_init
var_scr_0906:           EQU 0906h   ; обнуляется в func_game_update/func_gamestate_handlers
var_scr_0909:           EQU 0909h   ; scratch-пара (в game_update <- var_player_col)
var_scr_090A:           EQU 090Ah   ; scratch-пара (в game_update <- var_player_row)
var_scr_091D:           EQU 091Dh   ; HUD-счётчик (обрезка бонуса до 6 в func_draw_level_hud)
; --- ROM-тайлы глифов (byte-exact зона <0x2761) ------------------------------
data_tile_2706:         EQU 2706h   ; глиф-тайл (spawn fallback)
data_tile_empty:        EQU 270Ah   ; глиф пустой клетки
data_tile_2716:         EQU 2716h   ; глиф-тайл (spawn variant B)
data_tile_272A:         EQU 272Ah   ; глиф-тайл (bonus draw)

; --- Буфер параметров текущего уровня (копия записи data_level_params) --------
data_level_param_buf:   EQU 0911h   ; 8 байт: 0x0911..0x0918
data_level_param_buf_end: EQU 0919h

; --- Сущности ---------------------------------------------------------------
var_entity1_state:      EQU 091Ah   ; байт: состояние сущности 1
var_entity2_state:      EQU 091Bh   ; байт: состояние сущности 2
var_lives_icons:        EQU 091Eh   ; байт: счётчик/иконки жизней
data_entity_xcoords:    EQU 091Fh   ; 3 байта: X-координаты сущностей
data_entity_xcoords_end: EQU 0922h
data_entity_ycoords:    EQU 0922h   ; 3 байта: Y-координаты сущностей
data_entity_ycoords_end: EQU 0925h

; --- Текст / указатели ------------------------------------------------------
var_music_work_ptr:     EQU 0B41h   ; слово: рабочий указатель музыки
var_text_ptr:           EQU 0B53h   ; слово: указатель текста

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
; data_glyph_block — МЕТКА на распакованном блоке, определена в
; data_glyph_block_unpacked.asm (этап B: адрес задаёт компоновщик GLYPH_BASE).
data_glyph_block_end:   EQU 8000h   ; конец read-only окна (нижние 32КБ RAM)
; data_ram_sprites_7418 (0x7418) не определён: копир спрайтов в func_main_init
; выведен из исполнения (вестигиальный остаток распаковщика) — reader у 0x7418
; отсутствует (grep + capture_A), а его источник (хвост data_gfx_2761) обнулён.
