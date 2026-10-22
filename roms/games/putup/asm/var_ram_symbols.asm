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

; --- Raster-sync: КР580ВИ53 (клон i8253) как «секундомер растра» --------------
; Счётчик 1 (порт 0Ah) на уровне переключается с музыки (на уровне мелодии нет,
; SFX сидят на ch2/09h) на режим 0 и перезагружается длиной кадра в конце VBlank
; ISR -> count убывает от 0x7500 (кадр) к 0, давая положение луча в отсчётах.
; Такт счётчика 1.5МГц = 768 v_cycle(12МГц)/8 -> 96 отсчётов/строку, 312 строк =
; 29952 = 0x7500 отсчётов/кадр. elapsed = 0x7500 - count = строка_луча * 96.
raster_ctrl_port:   EQU 08h   ; порт управляющего слова ВИ53
raster_cnt1_port:   EQU 0Ah   ; порт счётчика 1 (ch1) — наш секундомер
raster_w_latch1:    EQU 40h   ; SC=cnt1(01),RL=latch(00): заморозить для чтения
raster_w_load1:     EQU 70h   ; SC=cnt1(01),RL=load lo+hi(11),M=mode0(000): старт
raster_frame_hi:    EQU 75h   ; 0x7500 = 29952 отсчётов (выс. байт)
raster_frame_lo:    EQU 00h   ; низ. байт длины кадра

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
; --- Raster-sync героя (func_raster_guard_hero). Зона 0x6A0B.. свободна --------
var_raster_flag:        EQU 6A0Bh   ; байт: 1 = секундомер активен (на уровне); 0 = заставка (ch1 отдан музыке)
var_raster_top:         EQU 6A0Ch   ; слово: порог elapsed для ВЕРХА полосы героя (в отсчётах)
var_raster_bot:         EQU 6A0Eh   ; слово: порог elapsed ДЛЯ НИЗА полосы героя (в отсчётах)
var_raster_cap:         EQU 6A10h   ; байт: антизацикливатель ожидания прохода луча
; --- Step 0: кад-синхрон + чанк-скан огня (func_render_all + lbl_main_game_loop).
; Зона 0x6A11.. свободна (or_mask 8Б кончается на 6A0A, raster-структура на 6A10).
var_frame_sub:          EQU 6A11h   ; байт: досчётчик кадра в 12-окне (1..12; проход на 6 и 12)
var_scan_ptr:           EQU 6A12h   ; слово: курсор чанка скана огня в data_text_buffer
; --- Step 2a/2b: суб-пиксельный твин отрисовки героя (вертикаль + горизонталь). -
; var_glyph_voff — ВЕРТИКАЛЬНЫЙ суб-сдвиг masked-blit героя в func_render_glyph_or,
; в пикселях (0..4). Младший байт адреса VRAM = позиция по вертикали в столбце
; (ст. байт = колонка+плоскость), но адрес растёт ВВЕРХ (L = screen_mode - rowbits),
; поэтому сдвиг ВНИЗ применяется как L -= voff (H не тронут).
; 0 = спрайт выровнен по клетке (канон). Меняется ТОЛЬКО вокруг отрисовки героя;
; скан огня/erase/фон идут при voff=0 (горячий func_render_glyph не затронут).
; var_glyph_hoff (Step 2b) — ГОРИЗОНТАЛЬНЫЙ суб-сдвиг, но сдвиг по горизонтали =
; биты внутри байта + перелив в соседний VRAM-столбец, поэтому он реализуется НЕ
; адресной арифметикой, а precompute-кэшем сдвинутых ±4px композитных колонок
; (data_hero_shift_cache, см. ниже и func_build_hero_shift_cache). 0=выровненно,
; 1=сдвиг на 4px в col+1, 2=сдвиг на 4px в col-1.
var_glyph_voff:         EQU 6A14h   ; байт: вертикальный суб-сдвиг OR-глифа героя (пиксели)
var_glyph_hoff:         EQU 6A1Ch   ; байт: горизонтальный режим (0=нет,1=в col+1 на 4px,2=в col-1)
; --- Step 2a (Вариант A): scratch easing-машины func_hero_render. -------------
; Отображаемая позиция героя живёт в var_enemy_rc(lo=row,hi=col)+var_glyph_voff.
; Func_hero_render каждый кадр сравнивает её с целью (var_player_row/col) и делает
; шаг 4px. Здесь — снимок СТАРОГО отображения (для erase-прямоугольника), пара
; координат для func_draw_tile_at_ptr и цель после решения. Зона 0x6A15.. свободна.
var_hero_orow:          EQU 6A15h   ; байт: старая отображаемая строка (var_enemy_rc.lo до обновления)
var_hero_ocv:           EQU 6A16h   ; байт: старый суб-сдвиг (var_glyph_voff до обновления; >0 => footprint 3 строки)
var_hero_ocow:          EQU 6A17h   ; байт: старая отображаемая колонка (var_enemy_rc.hi до обновления)
var_hero_erow:          EQU 6A18h   ; байт: координата erase (row) — func_draw_tile_at_ptr читает (HL)=row
var_hero_ecol:          EQU 6A19h   ; байт: координата erase (col) — (HL+1)=col (смежно с erow)
var_hero_newr:          EQU 6A1Ah   ; байт: новая отображаемая строка (после easing-решения)
var_hero_newc:          EQU 6A1Bh   ; байт: новая отображаемая колонка
; --- Step 2b: scratch горизонтального easing'а. Зона 0x6A1D.. свободна. --------
var_hero_ohoff:         EQU 6A1Dh   ; байт: старый hoff (var_glyph_hoff до обновления; !=0 => footprint 3 колонки)
var_hero_newidx:        EQU 6A1Eh   ; байт: предлагаемый индекс тайла-героя (кадр/направление); детект смены кадра в покое
; --- Step 2a temps: scratch func_build_hero_shift_cache (только при init). ------
; Зона 0x6A20..0x6BFF свободна (кэш начинается 0x6C00). Указатели хранятся
; младш.байт по низшему адресу (малый endian, как LHLD/SHLD).
gsc_tile:     EQU 6A20h   ; байт: текущий тайл-герой (0..7)
gsc_row:      EQU 6A21h   ; байт: строка внутри тайла (0=верх TL/TR, 1=низ BL/BR)
gsc_plane:    EQU 6A22h   ; байт: текущая плоскость (0..3; 3=П0/маска)
gsc_byte:     EQU 6A23h   ; байт: позиция байта в плоскости (0..7)
gsc_fill0:    EQU 6A24h   ; байт: OR-зполнение вакуолёй frag0 (0 или 0F0h для маски)
gsc_fill2:    EQU 6A25h   ; байт: OR-заполнение вакуолёй frag2 (0 или 00Fh для маски)
gsc_TL:       EQU 6A26h   ; байт: код глифа записи тайла [0]
gsc_TR:       EQU 6A27h   ;   [1]
gsc_BL:       EQU 6A28h   ;   [2]
gsc_BR:       EQU 6A29h   ;   [3]
gsc_pL:       EQU 6A2Ah   ; 2 байта: указатель на текущий байт-источник L
gsc_pR:       EQU 6A2Ch   ; 2 байта: источник R
gsc_pD0:      EQU 6A2Eh   ; 2 байта: приёмник frag0 (base-колонка)
gsc_pD1:      EQU 6A30h   ; 2 байта: приёмник frag1 (средняя)
gsc_pD2:      EQU 6A32h   ; 2 байта: приёмник frag2 (правая)
; --- Step 3 scratch: draw/erase-диспатчер func_hero_render. -------------------
var_hero_idx:   EQU 6A34h ; байт: индекс тайла-героя (0..7) для draw/erase
var_hero_ebase: EQU 6A35h ; байт: базовая колонка erase-footprint (oldcol или oldcol-1)
; --- Async SFX (Stage: звуки на прерывании). Зона 0x6A36.. свободна. -----------
; var_sfx_len — счётчик кадров VBlank, оставшихся до выключения тона канала 2.
; Пишет ОДИН байт: основная программа (func_sound_init) задаёт длительность ЗАПУСКА
; тона и НЕ ждёт (нет func_delay); func_vblank_isr каждый кадр decrement-ит и на
; 0 выдаёт gate-off (OP [10] E=00h). 0 = тон не звучит (idle). Инициализируется 0
; в func_main_init до первого VBlank (ISR работает уже на заставке).
var_sfx_len:      EQU 6A36h ; байт: кадров до gate-off канала 2 (0=idle)
; Прежние var_sfx_gap (0x6A37) / var_sfx_nom (0x6A38) / sfx_gap_frames выведены из
; проекта: они вводили рефрактерную паузу и слияние запросов по ложной гипотезе
; «бипы сливаются». Настоящая причина долгого звука ключа — арифметический баг
; B/2 через RRC в func_sound_init (RRC зациклирует bit0 в bit7: для B=05h давал
; 130 кадров вместо 2). 0x6A37..0x6A38 снова свободны.
; --- Step 2b: RAM-кэш сдвинутых ±4px композитных колонок героя (precompute). ----
; Генерируется ОДИН раз при инициализации (func_build_hero_shift_cache) до первого
; кадра; арт героя статична -> инвалидации нет. В горячем пути midpoint — обычный
; выровненный OR-blit (func_render_tile_vram_or3) по этим заготовкам, без побитовой
; математики на кадр. Зона 0x6C00..0x77FF свободна (текст-буфер кончается 0x6A00,
; var-зона 0x6A1E; стек LXI SP,0100h растёт вниз от 0x0100 — сюда не достаёт;
; мёртвая зона спрайтов 0x7418 не читается).
; Разметка: для каждого тайла-героя records[0..7] храним широкий композит
; 3 колонки x 2 строки = 6 фрагментов; фрагмент = обычный raw-глиф 4 плоскости x 8
; байт (П3 +0, П2 +8, П1 +16, П0/маска +24) = 32 байта. Итого 8 x 6 x 32 = 1536
; байт (0x600): 0x6C00..0x71FF.
; ВАЖНО (Step 2b): содержимое 3 фрагментов НЕ зависит от направления сдвига —
; hoff=1 (вправо) и hoff=2 (влево) дают ОДИНАКОВЫЕ байты, различается лишь базовая
; колонка приёмника (hoff=1: base=curcol; hoff=2: base=curcol-1), которую передаёт
; вызывающий в func_render_tile_vram_or3. Поэтому ось направления в кэше НЕ хранится.
; Индекс фрагмента (порядок обхода = TL,TR,правый / BL,BR,правый; row=0 верх,1 низ;
; colpos=0 base-колонка, 1 средняя, 2 правая):
;   addr = data_hero_shift_cache + (tile*6 + row*3 + colpos) * 32
data_hero_shift_cache:  EQU 6C00h   ; 1536 байт: кэш сдвинутых композитов героя (±4px одинаковы)
; data_glyph_block — МЕТКА на распакованном блоке, определена в
; data_glyph_block_unpacked.asm (этап B: адрес задаёт компоновщик GLYPH_BASE).
data_glyph_block_end:   EQU 8000h   ; конец read-only окна (нижние 32КБ RAM)
; data_ram_sprites_7418 (0x7418) не определён: копир спрайтов в func_main_init
; выведен из исполнения (вестигиальный остаток распаковщика) — reader у 0x7418
; отсутствует (grep + capture_A), а его источник (хвост data_gfx_2761) обнулён.
