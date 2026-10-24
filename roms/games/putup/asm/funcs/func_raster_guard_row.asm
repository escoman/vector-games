; Функция: func_raster_guard_row
; Адрес: 0x1BCA
; Размер: ~80 байт
; Описание: Raster-safe страж ОДНОГО ряда скана флипа (func_render_all).
;           Гарантирует, что запись глифа флипаемой клетки (огонь 75h<->0FEh,
;           выход 16h..19h<->12h..15h; func_draw_char_at_hl -> func_render_glyph
;           пишет 4 биплоскости ПОСЛЕДОВАТЕЛЬНО и неатомарно, ~6-9 строк развёртки)
;           НЕ выполняется, пока луч ЭЛТ проходит по полосе ЭТОГО ряда — иначе луч
;           захватывает глиф между записями плоскостей -> пиксель собирается из
;           плоскостей двух фаз (зелёно-розовый артефакт на шве смены фазы огня).
;
;           Вход: HL = адрес клетки в data_text_buffer (row-major, COLS=32).
;           Строка ряда = (HL - data_text_buffer) / 32. Вычет базы через уже
;           существующую константу textbuf_to_vram (= 0 - база = 9A00h): offset =
;           HL + 9A00h (16-бит, carry отбрасывается, offset 0..0x2FF). row = offset>>5
;           = offset_hi*8 + offset_lo>>5 (offset_hi = H в 0..2, смещение <0x400).
;
;           Полоса ОДНОГО глиф-ряда = 8 строк (GLYPH_LINES):
;             elapsed_top = (48 + 8*row) * 96 = 0x1200 + (row*3)<<8
;             elapsed_bot = elapsed_top + 7*96 = + 0x2A0  (низ того же ряда)
;           Пороги пишутся в var_raster_top/bot (слова), антизацикливатель в
;           var_raster_cap — ТЕ ЖЕ scratch-ячейки, что у func_raster_guard_hero/enemy,
;           но те вызываются ПОЗЖЕ в кадре (hero render / chaser apply), пересечений нет.
;
;           Решение (elapsed = 0x7500 - count, растёт сверху вниз по кадру).
;           РАЗДЕЛЕНО по типу клетки (бит6 кода-замены A: 1=огонь 75h/FEh, 0=выход):
;             * elapsed >= elapsed_bot -> луч УЖЕ ниже ряда => рисуем сейчас
;               (и этот, и все следующие глифы ряда — позади луча, одной фазой);
;             * ОГОНЬ (широкий ряд, ~24-28 клеток): иначе (луч не прошёл ряд) => ВСЕГДА
;               крутимся до elapsed>=elapsed_bot и рисуем ПОЗАДИ луча. Никакой ветки
;               «успеем до луча»: широкий ряд физически не влезает в окно до луча
;               (~190 строк при цене ряда ~190-250), а per-cell «опережение» делит ряд
;               на две фазы (видимый шов). Целостность ряда важнее 1 кадра задержки.
;             * ВЫХОД 2x2 (узкий, бит6=0): если elapsed < elapsed_top и зазор
;               (elapsed_top-elapsed) >= MARGIN=0x800 (~21 строка, при цене глифа ~6-9)
;               => рисуем сейчас (2 глифа влезут до луча); иначе => вейт до прохода.
;           Цена огня-вейта: на кадре, где чанк скана попал на ряд огня, ожидание
;           ~до 190 строк (луч проходит ряд) => этот кадр удлинняется (Этап 2 —
;           перенести запись огня в окно конца кадра, где луч уже внизу, чтобы убрать
;           удлинение). На ЭТАПЕ 1 цель — убрать видимый шов/разрыв, что и делает
;           ряд-атомарность: весь ряд огня пишется целиком после луча, одной фазой.
;
;           Антизацикливатель var_raster_cap (0FFh итераций) — при исчерпании выходим
;           (fail-safe: рисуем как раньше, без вейта) — защищает и от случая, когда
;           секундомер растра не идёт (не должно быть: флипаемые клетки есть только
;           на уровне в игровом цикле, на заставке флипа нет).
;
;           Прозрачность: регистры/флаги вызывающего СОХРАНЯЮЩИ — PUSH/POP PSW,B,D,H
;           покрывают A/F, BC, DE, HL. Это критично для func_render_all: тот держит
;           курсор клетки в HL, код-замену в A, счётчик чанка в B и СТАРШИЙ байт DE
;           = база таблицы флипа (XCHG-идиом на следующей итерации читает H из DE).
;           func_beam_count затирает DE — поэтому DE обязательно восстанавливаем.
;           Внутренне трогает C,L,D,E,H,A (все сохранены парными PUSH B/PUSH D/PUSH H).
;           Вызывается ИЗ скана func_render_all перед CALL func_draw_char_at_hl.

func_raster_guard_row:
    PUSH PSW                    ; A/F (код-замена для draw_char) — сохранить
    PUSH B                      ; B — счётчик чанка render_all; C — scratch
    PUSH D                      ; D/E — DE.H = база таблицы флипа (нужен render_all)
    PUSH H                      ; H/L — курсор клетки (нужен draw_char)
    ; --- строка ряда: offset = HL + textbuf_to_vram (9A00h) = HL - база ---------
    LXI D, textbuf_to_vram      ; DE = 9A00h (0 - data_text_buffer)
    DAD D                       ; HL = offset клетки (0..0x2FF), carry отброшен
    ; row = offset >> 5 = offset_hi*8 + offset_lo>>5
    MOV A, H                    ; A = offset_hi (0..2)
    ADD A                       ; *2
    ADD A                       ; *4
    ADD A                       ; *8  -> offset_hi*8 (0..16)
    MOV C, A                    ; C = offset_hi*8
    MOV A, L                    ; A = offset_lo (0..0xFF)
    ORA A                       ; CY=0 (логический сдвиг)
    RAR
    ORA A
    RAR
    ORA A
    RAR
    ORA A
    RAR
    ORA A
    RAR                         ; A = offset_lo >> 5 (младш. 5 бит = row-доля внутри ряда)
    ADD C                       ; A = row (0..23)
    ; --- пороги полосы: elapsed_top = 0x1200 + (row*3)<<8 ------------------------
    MOV C, A                    ; C = row
    ADD A                       ; *2
    ADD C                       ; *3  -> row*3 (0..69)
    ADI 12h                     ; + (48*96)>>8 = 0x12  => старш. байт elapsed_top
    MOV H, A
    MVI L, 00h
    SHLD var_raster_top         ; elapsed_top (слово)
    ADI 02h                     ; elapsed_bot = top + 0x2A0: ст. байт +2
    MOV H, A
    MVI L, 0A0h                 ; низ = 0x2A0 & 0FFh = 0A0h
    SHLD var_raster_bot         ; elapsed_bot (слово)
    ; антизацикливатель
    MVI A, 0FFh
    STA var_raster_cap
loc_grr_loop:
    CALL func_beam_count        ; DE = count (триггерит DI/EI внутри; A,D,E scratch)
    ; elapsed(HL) = 0x7500 - count
    LXI H, 7500h
    MOV A, L
    SUB E
    MOV L, A
    MOV A, H
    SBB D
    MOV H, A                    ; HL = elapsed
    ; (1) elapsed >= elapsed_bot ?  -> луч прошёл ряд -> рисуем сейчас
    LDA var_raster_bot
    MOV E, A
    LDA var_raster_bot+1        ; A = bot_hi
    MOV D, A                    ; DE = bot (HL = elapsed сохранён)
    MOV A, L
    SUB E
    MOV A, H
    SBB D
    JNC loc_grr_ret             ; без займа => elapsed>=bot => луч УЖЕ ниже ряда => рисуем
    ; РЯД-АТОМАРНОСТЬ Этап 1: огонь 75h/FEh (бит6 кода=1) рисуем ВСЕГДА ПОЗАДИ луча.
    ; Не даём широкому ряду опередить луч: иначе луч догоняет запись на середине
    ; ряда и делит его на две фазы (видимый шов). Ключ: решение не где начался ряд,
    ; а луч уже ниже конца ряда (bot) - тогда и первый, и все следующие глифы ряда
    ; дописываются позади луча в этом же проходе -> весь ряд одной фазой. Первый
    ; fire-глиф крутится до elapsed>=bot; следующие видят луч прошедшим -> JNC ret.
    ; Выход 2x2 (бит6=0) узкий, безопасно опережает луч - оставляем margin-ветку.
    ; A (код-замена) сохранён в PSW на входе, не трогался с loc_grr_loop.
    ANI 40h                     ; бит6 кода: 1 = огонь (75h/FEh)
    JNZ loc_grr_wait            ; огонь -> вейт до прохода луча (пропускаем успех-до-луча)
    ; (2) elapsed >= elapsed_top ?  -> внутри [top,bot) -> ждать
    LDA var_raster_top
    MOV E, A
    LDA var_raster_top+1        ; A = top_hi
    MOV D, A                    ; DE = top (HL = elapsed)
    MOV A, L
    SUB E
    MOV A, H
    SBB D
    JC  loc_grr_below           ; заём => elapsed<top => возможно далеко сверху
    JMP loc_grr_wait            ; top<=elapsed<bot => луч в полосе ряда -> ждать
loc_grr_below:
    ; gap = elapsed_top - elapsed ; если gap >= MARGIN -> далеко -> рисуем сейчас
    ; HL = elapsed, DE = top (уже загружен на шаге 2)
    MOV A, E
    SUB L
    MOV C, A                    ; gap_lo
    MOV A, D
    SBB H
    MOV B, A                    ; gap_hi  (BC = gap = top - elapsed > 0)
    LXI D, 0800h                ; MARGIN = 21*96 (окно записи одного глифа + запас)
    MOV A, C
    SUB E
    MOV A, B
    SBB D
    JNC loc_grr_ret             ; gap>=MARGIN => безопасно нарисовать до прихода луча
loc_grr_wait:
    LXI H, var_raster_cap
    DCR M
    JZ  loc_grr_ret             ; cap исчерпан => bail (рисуем как раньше)
    JMP loc_grr_loop
loc_grr_ret:
    POP H                       ; восстановить HL (курсор клетки)
    POP D                       ; восстановить DE (база таблицы флипа — ст. байт!)
    POP B                       ; восстановить BC (счётчик чанка B)
    POP PSW                     ; восстановить A (код-замена) + F
    RET
