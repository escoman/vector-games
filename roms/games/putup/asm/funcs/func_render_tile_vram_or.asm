; Функция: func_render_tile_vram_or
; Адрес: 0x1BC9
; Размер: ~34 байта (тело) + func_render_glyph_or + хелперы loc_mov8 / loc_blit8 / loc_or_nextplane
; Описание: MASKED-BLIT тайла 2x2 поверх уже нарисованного в VRAM (оверлей героя).
;           Вход: HL = указатель графики тайла (4 байта-глифа), D = колонка,
;           E = строка — тот же контракт, что у func_render_tile_vram.
;
;           СМЫСЛ (схема lib/gfx/plane.asm «плоскость сегментов»): у глифа героя
;           плоскость 0 (P0) хранит СИЛУЭТ-маску: 1 = фон (за пределами героя),
;           0 = сам герой. Наложение для каждой из 4 экраных плоскостей i:
;                 Plane_i = (Plane_i AND mask) OR color_i
;           где mask = P0 глифа, color_i = i-я плоскость глифа (КЛАДЁТСЯ ЦЕЛИКОМ,
;           НЕ маскируется!). То есть:
;             * где mask=1 (фон) — экранный пиксель СОХРАНЯЕТСЯ (фрукт/стена под
;               «пустой» частью клетки героя не затираются), но цвет героя поверх
;               всё равно OR-ится (color_i);
;             * где mask=0 (герой) — фон ВЫТИРАЕТСЯ и заменяется цветом героя.
;           ВАЖНО: цвет НЕ обнуляется инверсной маской. Прежний вариант
;           (color AND ~mask) стирал биты цвета в области mask=1 -> герой почти
;           полностью исчезал. Правильно: зачистка фона маской (AND), затем OR
;           всего цвета глифа напрямую.
;
;           Плоскость 0: color_0 = mask, поэтому (Plane0 AND mask) OR mask = mask,
;           т.е. Plane0 = P0 (то же, что писал оригинальный verbatim-рендер).
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
; (Tier-2: бит0 слова = тег compact; raw = 4 плоскости по 8 байт подряд, P0 идёт
; первой => P0 = маска). Запись (см. шапку):
;   * space (20h) -> no-op (пустая клетка оверлея ничего не трогает);
;   * маска P0 (8 байт) грузится в var_or_mask_scratch, DE уходит на color P1;
;   * плоскость 0: Plane0 = mask (loc_mov8 == (Plane0 AND mask) OR mask);
;   * compact (тег=1): плоскостей 1..3 нет -> стоп после P0 (герой всегда raw);
;   * raw плоскости 1..3: Plane_i = (Plane_i AND mask) OR color_i (loc_blit8),
;     приёмник шагает на +0x2000 (loc_or_nextplane), цвет идёт последовательно.
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
    MOV A, E                    ; снять тег компактности
    ANI 01h
    MOV C, A                    ; C = тег (0 raw / 1 compact)
    MOV A, E
    SUB C
    MOV E, A                    ; DE = база записи (P0 = маска, далее цвета)
    ; --- загрузка маски (P0, 8 байт из (DE)) в scratch; DE уйдёт на color P1 ---
    PUSH H                      ; сохранить базу приёмника (плоскость 0)
    LXI H, var_or_mask_scratch
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
    ; DE = entry+8 (цвет P1); маска в var_or_mask_scratch; HL = scratch+8
    POP H                       ; HL = база приёмника (плоскость 0)
    ; --- Тег compact проверяем ДО LXI B: loc_mov8/loc_blit8 используют BC как
    ;     указатель маски и затирают C (тег). Иначе после plane0 C=низ scratch,
    ;     ORA A != 0 -> ложный уход, и плоскости 1..3 не рисуются (герой только
    ;     на 0x8000). ---
    MOV A, C                    ; C = тег (0 raw / 1 compact), ещё цел
    ORA A
    JNZ loc_compact             ; compact: только плоскость 0
    ; --- raw: плоскость 0 = mask, затем blit плоскостей 1..3 ---
    LXI B, var_or_mask_scratch
    CALL loc_mov8               ; dest0 = маска; HL = dest0+8, DE не тронут (=entry+8)
    CALL loc_or_nextplane       ; HL -> база плоскости 1
    LXI B, var_or_mask_scratch
    CALL loc_blit8              ; P1: (dest&mask)|color1; DE->entry+16
    CALL loc_or_nextplane
    LXI B, var_or_mask_scratch
    CALL loc_blit8              ; P2; DE->entry+24
    CALL loc_or_nextplane
    LXI B, var_or_mask_scratch
    CALL loc_blit8              ; P3; DE->entry+32
    JMP loc_or_done
loc_compact:
    LXI B, var_or_mask_scratch
    CALL loc_mov8               ; compact: plane0 = mask, плоскостей 1..3 нет
loc_or_done:
    POP H
    POP D
    POP B
    POP PSW
    RET

; Копия: 8 байт. Вход HL=приёмник, BC=источник. dest = (BC). Оба +8. Не трогает D/E.
; (Для плоскости 0 источника-маски: Plane0 = mask.)
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
