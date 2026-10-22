; Функция: func_clear_vram
; Адрес: 0x0B5B (выделена из func_main_init; физическое размещение в Stage-4
;         конкатенации определяется tools/order.json — стоит СРАЗУ ПОСЛЕ
;         lbl_title_key_poll, а не буквально после func_main_init, потому что
;         func_main_init заканчивается FALL-THROUGH в lbl_title_key_poll (нет
;         RET), и любая вставка между ними потеряла бы этот переход)
; Размер: 45 байт тело + 2 байта локальная переменная = 47 Б (эмит-блок
;         целиком; было 12 Б медленной петли MVI M+INX H, ~16 T/байт)
; Описание: Быстрая очистка всей VRAM Vector-06C (0x8000..0xFFFF = 32 КБ)
;           через SP-hijack + PUSH H. Порт lib/gfx/clr.asm _gfx_fill_planes
;           (mask=0Fh, fill=00h) под 8080_strict, с КОРРЕКТНЫМ сохранением
;           SP вызывающего — функция пригодна к вызову из ЛЮБОГО места, а не
;           только из boot-секвенции.
;
;           Сохранение/восстановление SP: LXI H,0000h + DAD SP (8080) перекладывает
;           SP в HL; SHLD var_clear_vram_saved_sp пишет его в локальную переменную
;           (RAM по адресу ROM-образа — ROM грузится в RAM на 0x0100, паттерн
;           совпадает с var_palette_ptr/data_ram_init_image_08C3). В конце
;           LHLD читает обратно, SPHL (F9) возвращает SP. Никаких предположений
;           о layout caller'а — SP восстанавливается ровно тем, каким был на входе.
;
;           Механика: DI; SP := 0x0000 (первый PUSH обернётся в 0xFFFE/0xFFFF);
;           HL := 0x0000 (fill-слово). Каждый PUSH H пишет 2 байта и decrement-
;           ит SP. Все 4 плоскости идут ПОДРЯД без перезагрузки SP: plane0
;           (E000..FFFF), plane1 (C000..DFFF), plane2 (A000..BFFF), plane3
;           (8000..9FFF) — после plane0 SP=0xE000 и далее естественно стекает.
;           Итого 4×16×32×8 PUSH H = 16384 PUSH H = 32768 байт.
;
;           Регистры на выходе: B=C=D=H=L=0, A и E не затронуты. Вызывающие:
;           func_main_init (загрузка, затем func_hw_init, начинающийся с XRA A)
;           и func_level_loader на loc_19A0 (шаг E3: CLS перед сборкой уровня,
;           чтобы пустые клетки 0x20 не хранили пиксели врага — func_put_char
;           делает CMP M / RZ и не перерисовывает клетку, чей код уже лежит в
;           буфере, а clear_textbuf на этом пути стоит РАНЬШЕ рисовки карты).
;           В func_level_loader сразу после вызова идёт EI: функция делает DI и
;           обратно прерывания не включает. DI держится только время самой
;           очистки (~4 hw-кадра), а не весь загрузчик.

func_clear_vram:
    DI                          ; защита от IRQ во время SP-hijack
    LXI H, 0000h                ; HL = 0 — основа для DAD SP
    DAD SP                      ; HL = 0 + SP = SP вызывающего (8080-safe)
    SHLD var_clear_vram_saved_sp ; saved_sp := HL (16-bit little-endian)
    LXI H, 0000h                ; HL := fill-слово (0x0000 — два нуля за PUSH)
    LXI SP, 0000h               ; hijack SP: старт сверху (первый PUSH → FFFE)
    MVI D, 04h                  ; 4 плоскости
fcv_planes:
    MVI B, 10h                  ; 16 страниц по 512 Б
fcv_page:
    MVI C, 20h                  ; 32 блока по 8 PUSH = 256 PUSH = 512 Б
fcv_inner:
    PUSH H
    PUSH H
    PUSH H
    PUSH H
    PUSH H
    PUSH H
    PUSH H
    PUSH H
    DCR C
    JNZ fcv_inner
    DCR B
    JNZ fcv_page
    DCR D
    JNZ fcv_planes
    LHLD var_clear_vram_saved_sp ; HL := сохранённый SP вызывающего
    SPHL                         ; SP := HL (8080 SPHL, опкод F9)
    RET

; Локальный scratch функции — 16-битная переменная для хранения SP вызывающего.
; Идёт сразу за func_clear_vram в том же emit-блоке, поэтому физический адрес
; определяется tools/order.json вместе с самой функцией (Stage-4 свободная
; конкатенация). ROM грузится в RAM на 0x0100, запись/чтение легальны.
var_clear_vram_saved_sp:
    DEFW 0
