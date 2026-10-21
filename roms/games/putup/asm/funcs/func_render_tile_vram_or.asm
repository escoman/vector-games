; Функция: func_render_tile_vram_or
; Адрес: 0x1BC9
; Размер: ~34 байта (тело) + func_render_glyph_or + хелперы loc_mov8 / loc_and_de / loc_blit8 / loc_or_nextplane
; Описание: MASKED-BLIT тайла 2x2 поверх уже нарисованного в VRAM (оверлей героя).
;           Вход: HL = указатель графики тайла (4 байта-глифа), D = колонка,
;           E = строка — тот же контракт, что у func_render_tile_vram.
;
;           СМЫСЛ: глиф героя = 4 плоскости по 8 байт, идут в порядке обхода
;           (база 0x8000, шаг +0x2000), DE идёт последовательно entry+0,8,16,24:
;             entry+0  -> 0x8000 (Plane 3, П3)    entry+8  -> 0xA000 (Plane 2, П2)
;             entry+16 -> 0xC000 (Plane 1, П1)    entry+24 -> 0xE000 (Plane 0, П0)
;           МАСКА зачистки ЕДИНАЯ для всех плоскостей = П0 (entry+24), буферится в
;           var_or_mask_scratch. Композиция (Plane := ...):
;             * 0x8000 (Plane 3, П3): (Plane AND П0) OR П3   (loc_blit8, color=entry+0);
;             * 0xA000 (Plane 2, П2): (Plane AND П0) OR П2   (loc_blit8, color=entry+8);
;             * 0xC000 (Plane 1, П1): (Plane AND П0) OR П1   (loc_blit8, color=entry+16);
;             * 0xE000 (Plane 0, П0): Plane AND П0           (loc_and_de) — зачистка без
;               наложения: П0 на свою плоскость НЕ OR-ится (по требованию).
;           Где П0=1 (фон) — пиксель экрана сохраняется; П0=0 (герой) — вытирается, затем
;           поверх OR-ится цвет плоскости. ВАЖНО: цвет НЕ инвертируется (color AND ~mask
;           стирал героя); зачистка = AND, наложение = OR всего цвета напрямую.
;
;           КЛЮЧЕВОЕ (багфикс): порядок чтения 4 байт тайла обязан совпадать с
;          func_render_tile_vram байт-в-байт. Между верхним-правым глифом [1] и
;           шагом строки (LXI B,001Fh; DAD B) идёт ОТДЕЛЬНЫЙ `INX D` — источник
;           шагает к [2] ДО шага строки (шаг строки двигает только HL). Иначе
;           нижняя пара читает [1],[2] вместо [2],[3] → в BL TR-глиф, в BR BL-глиф.
;
;           Вынесено в отдельную функцию намеренно: той же схемой позже можно
;           рисовать поверх преследователя режима HURRY UP (func_entity_state10).
;
;           Регистры/флаги прозрачны, как у func_render_glyph: PUSH PSW/B/D/H на
;           входе, POP на выходе. Хелперы меняют только A/HL/DE/BC/флаги.

func_render_tile_vram_or:
    PUSH B                      ; как в func_render_tile_vram
    PUSH H                      ; сохранить указатель графики тайла
    CALL func_coords_to_textbuf ; (D=col,E=row) -> HL = адрес клетки буфера
    POP D                       ; DE = указатель графики тайла
    LDAX D
    CALL func_render_glyph_or   ; [0] -> верх-лево
    INX D
    INX H
    LDAX D
    CALL func_render_glyph_or   ; [1] -> верх-право
    INX D                       ; -> [2]: источник шагает ДО шага строки (как оригинал)
    LXI B, 001Fh
    DAD B                       ; шаг строки только по HL: col+1 +31 -> след. строка, col
    LDAX D
    CALL func_render_glyph_or   ; [2] -> низ-лево
    INX D
    INX H
    LDAX D
    CALL func_render_glyph_or   ; [3] -> низ-право
    POP B
    RET

; --- func_render_glyph_or ---------------------------------------------------
; Masked-blit одного глифа поверх VRAM. Вход: A = индекс глифа, HL = адрес
; клетки текстового буфера. Вычисление адреса приёмника (4 плоскости по +0x2000)
; и выбор слова глифа из data_glyph_ptr_table — один в один с func_render_glyph
; (Tier-2: бит0 слова = тег compact; raw = 4 плоскости по 8 байт подряд:
; entry+0=П3, entry+8=П2, entry+16=П1, entry+24=П0). Запись (см. шапку):
;   * space (20h) -> no-op (пустая клетка оверлея ничего не трогает);
;   * маска = П0 (entry+24) буферится в var_or_mask_scratch, DE возвращается на entry+0;
;   * 0x8000 (Plane 3), 0xA000 (Plane 2), 0xC000 (Plane 1): (Plane AND П0) OR color_i
;     (loc_blit8), цвет идёт последовательно entry+0/8/16, приёмник шагает +0x2000;
;   * 0xE000 (Plane 0): Plane = Plane AND П0 (loc_and_de; DE=entry+24), без OR;
;   * compact (тег=1): короткая запись -> Plane3 = entry+0 verbatim (loc_mov8), стоп.
func_render_glyph_or:
    PUSH PSW                    ; прозрачность для вызывающего
    PUSH B
    PUSH D
    PUSH H
    MOV D, A                    ; D = глиф
    LXI B, textbuf_to_vram      ; HL = смещение клетки (абс. адрес - база буфера)
    DAD B
    MOV A, L                    ; --- кол = (L & 1Fh) ---
    ANI 1Fh
    MOV C, A
    MOV A, H                    ; --- строка-биты = (H>>2)&C0 | (L>>2)&38 ---
    RRC
    RRC
    ANI 0C0h
    MOV B, A
    MOV A, L
    RRC
    RRC
    ANI 38h
    ORA B
    MOV B, A                    ; B = rowbits
    MOV A, D
    CPI 20h
    JZ loc_or_done              ; пробел: no-op (ничего не накладываем)
    ADD A                       ; DE = 2*глиф (смещение в таблице указателей)
    MOV E, A
    MVI A, 00h
    ADC A
    MOV D, A
    LXI H, data_glyph_ptr_table
    DAD D
    MOV E, M                    ; DE = слово указателя (бит0 = тег compact)
    INX H
    MOV D, M
    MVI H, 00h                  ; HL = кол
    MOV L, C
    PUSH B
    LXI B, data_vram_col_table
    DAD B
    MOV H, M                    ; H = старший байт приёмника плоскости 0 по кол-ке
    LDA var_screen_mode
    POP B                       ; B = rowbits
    SUB B
    MOV L, A                    ; HL = адрес приёмника (плоскость 0x0800)
    ; --- Step 2a: вертикальный суб-сдвиг OR-глифа (твин героя) --------------
    ; Младший байт VRAM-адреса = позиция по вертикали в столбце; ст. байт (H)
    ; = колонка+плоскость. Адрес растёт ВВЕРХ: L = var_screen_mode - rowbits
    ; (с ростом строки rowbits растёт, L падает), поэтому сдвиг ВНИЗ = ВЫЧИТАНИЕ
    ; из L: 8-байтовый столбец глифа едет строго по вертикали (плоскости: шаг
    ; +0x2000 идёт через H и не трогает смещение).
    ; voff=0 (по умолчанию) -> без изменений; вычитание трогает только A/флаги.
    LDA var_glyph_voff          ; A = суб-сдвиг героя (пиксели, 0..7)
    ORA A                       ; voff==0?
    JZ loc_or_novoff            ;   да -> рисуем выровненно по клетке (канон)
    MOV C, A                    ;   нет -> C = voff (тег в C перезапишется ниже)
    MOV A, L
    SUB C                       ;          L -= voff (сдвиг ВНИЗ, H не трогаем)
    MOV L, A
loc_or_novoff:
    MOV A, E                    ; снять тег компактности
    ANI 01h
    MOV C, A                    ; C = тег (0 raw / 1 compact)
    MOV A, E
    SUB C
    MOV E, A                    ; DE = база записи (цвета с entry+0; маска П0 = entry+24)
    ; --- Ветвление по тегу ДО всего, что трогает BC/C (тег в C должен выжить) ---
    MOV A, C                    ; C = тег (0 raw / 1 compact)
    ORA A
    JNZ loc_compact             ; compact: только плоскость 0 verbatim
    ; --- RAW: буферим П0 = entry+24 в scratch (единая маска AND для всех плоскостей) ---
    PUSH H                      ; HL = база приёмника (Plane 3 = 0x8000)
    PUSH D                      ; DE = base entry (чтобы цвета начать с entry+0)
    LXI H, 0018h                ; 24
    DAD D                       ; HL = entry+24
    XCHG                        ; DE = entry+24 (источник П0), HL = base entry
    LXI H, var_or_mask_scratch  ; HL = scratch — приёмник маски
    LDAX D
    MOV M, A
    INX D
    INX H
    LDAX D
    MOV M, A
    INX D
    INX H
    LDAX D
    MOV M, A
    INX D
    INX H
    LDAX D
    MOV M, A
    INX D
    INX H
    LDAX D
    MOV M, A
    INX D
    INX H
    LDAX D
    MOV M, A
    INX D
    INX H
    LDAX D
    MOV M, A
    INX D
    INX H
    LDAX D
    MOV M, A
    INX D
    INX H
    POP D                       ; DE = base entry (цвета начнём с entry+0)
    POP H                       ; HL = база приёмника (Plane 3 = 0x8000)
    ; --- Plane 3 (0x8000): (dest AND П0) OR П3 ---
    LXI B, var_or_mask_scratch
    CALL loc_blit8              ; mask=П0(scratch), color=П3(DE=entry+0); DE->entry+8
    CALL loc_or_nextplane       ; HL -> 0xA000 (Plane 2)
    LXI B, var_or_mask_scratch
    CALL loc_blit8              ; (dest AND П0) OR П2(entry+8); DE->entry+16
    CALL loc_or_nextplane       ; HL -> 0xC000 (Plane 1)
    LXI B, var_or_mask_scratch
    CALL loc_blit8              ; (dest AND П0) OR П1(entry+16); DE->entry+24
    CALL loc_or_nextplane       ; HL -> 0xE000 (Plane 0)
    CALL loc_and_de             ; 0xE000: dest &= П0 (DE=entry+24); П0 НЕ OR-ится
    JMP loc_or_done
loc_compact:
    ; compact: короткая 8-байтная запись -> НЕ читаем entry+24 (вне записи).
    ; Plane 3 = (entry+0..7) verbatim: BC = DE = entry; loc_mov8 пишет (BC)->(HL).
    PUSH D
    POP B
    CALL loc_mov8
loc_or_done:
    POP H
    POP D
    POP B
    POP PSW
    RET

; Копия verbatim: 8 байт. Вход HL=приёмник, BC=источник. dest = (BC). Оба +8. Не трогает D/E.
; (Теперь используется только compact-ветвью: Plane3 = короткая запись 8 байт.)
loc_mov8:
    LDAX B
    MOV M, A
    INX B
    INX H
    LDAX B
    MOV M, A
    INX B
    INX H
    LDAX B
    MOV M, A
    INX B
    INX H
    LDAX B
    MOV M, A
    INX B
    INX H
    LDAX B
    MOV M, A
    INX B
    INX H
    LDAX B
    MOV M, A
    INX B
    INX H
    LDAX B
    MOV M, A
    INX B
    INX H
    LDAX B
    MOV M, A
    INX B
    INX H
    RET

; Зачистка Plane 0xE000 СОБСТВЕННЫМ П0: 8 байт. Вход HL=приёмник, DE=П0 (entry+24).
;   dest = dest & (DE). Оба +8. Не трогает B/C. (П0 на 0xE000 НЕ OR-ится.)
loc_and_de:
    LDAX D
    ANA M
    MOV M, A
    INX D
    INX H
    LDAX D
    ANA M
    MOV M, A
    INX D
    INX H
    LDAX D
    ANA M
    MOV M, A
    INX D
    INX H
    LDAX D
    ANA M
    MOV M, A
    INX D
    INX H
    LDAX D
    ANA M
    MOV M, A
    INX D
    INX H
    LDAX D
    ANA M
    MOV M, A
    INX D
    INX H
    LDAX D
    ANA M
    MOV M, A
    INX D
    INX H
    LDAX D
    ANA M
    MOV M, A
    INX D
    INX H
    RET

; Masked-blit: 8 байт. Вход HL=приёмник, BC=маска, DE=цвет.
;   dest = (dest & mask) OR color. Все три шага +8. Не трогает B/C.
; Зачистка фона маской (AND) + OR цвета героя ЦЕЛИКОМ (цвет не инвертируется).
; На бите: A=mask&dest (HL=приёмник), XCHG -> HL=цвет, A|=цвет (это color),
; XCHG обратно -> HL=приёмник, запись. Никаких стеков/инверсий на байт.
loc_blit8:
    LDAX B                      ; A = mask
    INX B                       ; mask++
    ANA M                       ; A = mask & dest
    XCHG                        ; HL=color, DE=dest
    ORA M                       ; A = (mask&dest) | color
    XCHG                        ; HL=dest, DE=color
    MOV M, A                    ; dest = результат
    INX H
    INX D
    LDAX B
    INX B
    ANA M
    XCHG
    ORA M
    XCHG
    MOV M, A
    INX H
    INX D
    LDAX B
    INX B
    ANA M
    XCHG
    ORA M
    XCHG
    MOV M, A
    INX H
    INX D
    LDAX B
    INX B
    ANA M
    XCHG
    ORA M
    XCHG
    MOV M, A
    INX H
    INX D
    LDAX B
    INX B
    ANA M
    XCHG
    ORA M
    XCHG
    MOV M, A
    INX H
    INX D
    LDAX B
    INX B
    ANA M
    XCHG
    ORA M
    XCHG
    MOV M, A
    INX H
    INX D
    LDAX B
    INX B
    ANA M
    XCHG
    ORA M
    XCHG
    MOV M, A
    INX H
    INX D
    LDAX B
    INX B
    ANA M
    XCHG
    ORA M
    XCHG
    MOV M, A
    INX H
    INX D
    RET

; Шаг приёмника на следующую плоскость: после blit/mov HL=dest+8, добавить 0x1FF8 -> +0x2000.
; Не трогает B/C/D/E.
loc_or_nextplane:
    MOV A, L
    ADI 0F8h
    MOV L, A
    MOV A, H
    ACI 1Fh
    MOV H, A
    RET
