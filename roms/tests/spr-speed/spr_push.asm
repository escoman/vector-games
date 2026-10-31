; spr_push.asm — «хардкорное» ядро вывода спрайтов: PUSH прямо в видеопамять.
;
; СГЕНЕРИРОВАН gen_push.py из mario_old.inc — руками не править: правки
; вносить в генератор и пересобирать (файл уже в SRCS Makefile).
;
; Каждый спрайт — самостоятельная функция:
;   * данные спрайта лежат ПРЯМО В ЕЁ КОДЕ: пара строк столбца — это
;     `lxi b, imm16`, отдельного блока данных и указателя нет вообще;
;   * на время вывода SP уводится в видеопамять (sphl), строки выплёвываются
;     через `push b`: 8080 кладёт пару по убывающим адресам, а внутри
;     столбца экрана адрес убывает вниз — один PUSH пишет ДВЕ соседние
;     строки, B (старший) — верхняя, C — нижняя;
;   * поэтому SP ставится в «верх столбца + 1», а прогон из 16 PUSH пишет
;     ровно 32 строки столбца; следующий столбец = HL += 0x100 и sphl.
;
; Цена: lxi b (10 тактов) + push b (11) = 21 такт на 2 байта (10.5 на байт)
; против 24 тактов на байт у «лесенки» SMC. Обратная сторона — `di` на весь
; вывод: SP стоит в VRAM, а кадровое прерывание (isr_frame в
; lib/sys/startup.asm) толкает в стек af/bc/de/hl. SP сохраняется через
; DAD SP / SHLD и восстанавливается до EI, так что стык с ISR честный.
;
; Запись ПЛОТНАЯ — весь прямоугольник 8*COLS x 32, включая прозрачные нули,
; поэтому erase_sprite_box под спрайтом не нужен: нули затирают фон сами.
;
; Раскладка адресов: П3 = 8000h, П2 = A000h, П1 = C000h, П0 = E000h;
; строка r столбца c = база + 256*c + (255-y-r), то есть вниз по экрану
; адрес УБЫВАЕТ.
;
; Внешний вид (как у прочих движков): void spr_push_marioN(unsigned char x,
; unsigned int y) __z88dk_callee — x кратен 8, y — верх спрайта.


        SECTION code_clib

        PUBLIC  _spr_push_mario1
        PUBLIC  _spr_push_mario2
        PUBLIC  _spr_push_mario3

; ---------------------------------------------------------------
; фаза 0 (ноги вместе)
; 3 столбца x 32 строк, плоскости П1 + П0
; ---------------------------------------------------------------
_spr_push_mario1:
        pop     d               ; ret
        pop     h
        mov     a, l
        sta     pu_y            ; y — верх спрайта
        pop     h
        mov     a, l
        sta     pu_x            ; x — левый край (кратен 8)
        push    d               ; ret обратно на стек: дальше SP уедет в VRAM

        di                      ; SP в VRAM — кадровое прерывание трогать стек не должно
        lxi     h, 0
        dad     sp              ; 8080 не умеет ld (nn),sp
        shld    pu_sp           ; SP на входе в функцию

        ; HL = 0x8000 + (x/8)*256 + (255-y) — верх левого столбца П3
        lda     pu_x
        ora     a               ; CY=0, иначе rar вставит бит переноса в H
        rar
        rar
        rar
        mov     h, a
        mvi     l, 0
        mov     a, h
        adi     80h
        mov     h, a
        lda     pu_y
        cma
        mov     l, a            ; L = 255-y — строка 0 столбца

        ; --- П1 (C000h) ---
        mov     a, h
        adi     40h             ; база плоскости (HL = верх П3)
        mov     h, a

        ; ------- П1, столбец 0 -------
        inx     h               ; SP = верх столбца + 1
        sphl
        lxi     b, 0000h        ; строки 0-1
        push    b
        lxi     b, 0000h
        push    b
        lxi     b, 0C0Fh
        push    b
        lxi     b, 1110h
        push    b
        lxi     b, 7FFFh        ; строки 8-9
        push    b
        lxi     b, 3F1Fh
        push    b
        lxi     b, 7FFFh
        push    b
        lxi     b, 0FF7Fh
        push    b
        lxi     b, 3F1Fh        ; строки 16-17
        push    b
        lxi     b, 0F1Fh
        push    b
        lxi     b, 3F3Fh
        push    b
        lxi     b, 7F7Fh
        push    b
        lxi     b, 7F7Fh        ; строки 24-25
        push    b
        lxi     b, 3F3Fh
        push    b
        lxi     b, 1F04h
        push    b
        lxi     b, 080Fh
        push    b

        ; ------- П1, столбец 1 -------
        inr     h               ; +0x100 — следующий столбец
        sphl
        lxi     b, 0000h        ; строки 0-1
        push    b
        lxi     b, 0000h
        push    b
        lxi     b, 60E0h
        push    b
        lxi     b, 0E0F0h
        push    b
        lxi     b, 68C8h        ; строки 8-9
        push    b
        lxi     b, 0E4FCh
        push    b
        lxi     b, 0FCFCh
        push    b
        lxi     b, 0FCF8h
        push    b
        lxi     b, 0F0F8h       ; строки 16-17
        push    b
        lxi     b, 0C884h
        push    b
        lxi     b, 8484h
        push    b
        lxi     b, 0F1Bh
        push    b
        lxi     b, 0FFFEh       ; строки 24-25
        push    b
        lxi     b, 0FEF9h
        push    b
        lxi     b, 0F010h
        push    b
        lxi     b, 10F0h
        push    b

        ; ------- П1, столбец 2 -------
        inr     h               ; +0x100 — следующий столбец
        sphl
        lxi     b, 0000h        ; строки 0-1
        push    b
        lxi     b, 0000h
        push    b
        lxi     b, 0000h
        push    b
        lxi     b, 0000h
        push    b
        lxi     b, 0000h        ; строки 8-9
        push    b
        lxi     b, 0000h
        push    b
        lxi     b, 0000h
        push    b
        lxi     b, 0000h
        push    b
        lxi     b, 0000h        ; строки 16-17
        push    b
        lxi     b, 0000h
        push    b
        lxi     b, 0000h
        push    b
        lxi     b, 00C0h
        push    b
        lxi     b, 6070h        ; строки 24-25
        push    b
        lxi     b, 0F8C8h
        push    b
        lxi     b, 8898h
        push    b
        lxi     b, 7000h
        push    b

        ; --- П0 (E000h) ---
        mov     a, h
        adi     1Eh             ; база плоскости минус уже пройденные столбцы
        mov     h, a

        ; ------- П0, столбец 0 -------
        ; HL уже = верх столбца + 1 (осталось от прошлой плоскости)
        sphl
        lxi     b, 0000h        ; строки 0-1
        push    b
        lxi     b, 0000h
        push    b
        lxi     b, 0C0Fh
        push    b
        lxi     b, 1F1Fh
        push    b
        lxi     b, 7FFFh        ; строки 8-9
        push    b
        lxi     b, 3014h
        push    b
        lxi     b, 7480h
        push    b
        lxi     b, 8247h
        push    b
        lxi     b, 3C10h        ; строки 16-17
        push    b
        lxi     b, 0F11h
        push    b
        lxi     b, 2020h
        push    b
        lxi     b, 715Fh
        push    b
        lxi     b, 597Fh        ; строки 24-25
        push    b
        lxi     b, 3F3Fh
        push    b
        lxi     b, 1F07h
        push    b
        lxi     b, 0F0Fh
        push    b

        ; ------- П0, столбец 1 -------
        inr     h               ; +0x100 — следующий столбец
        sphl
        lxi     b, 0000h        ; строки 0-1
        push    b
        lxi     b, 0000h
        push    b
        lxi     b, 60A0h
        push    b
        lxi     b, 2030h
        push    b
        lxi     b, 0B8F8h       ; строки 8-9
        push    b
        lxi     b, 0FC7Ch
        push    b
        lxi     b, 64E4h
        push    b
        lxi     b, 4408h
        push    b
        lxi     b, 3078h        ; строки 16-17
        push    b
        lxi     b, 0F8FCh
        push    b
        lxi     b, 0FCFCh
        push    b
        lxi     b, 0FFFCh
        push    b
        lxi     b, 0F8FDh       ; строки 24-25
        push    b
        lxi     b, 0FFF9h
        push    b
        lxi     b, 0F0F0h
        push    b
        lxi     b, 0F0F0h
        push    b

        ; ------- П0, столбец 2 -------
        inr     h               ; +0x100 — следующий столбец
        sphl
        lxi     b, 0000h        ; строки 0-1
        push    b
        lxi     b, 0000h
        push    b
        lxi     b, 0000h
        push    b
        lxi     b, 0000h
        push    b
        lxi     b, 0000h        ; строки 8-9
        push    b
        lxi     b, 0000h
        push    b
        lxi     b, 0000h
        push    b
        lxi     b, 0000h
        push    b
        lxi     b, 0000h        ; строки 16-17
        push    b
        lxi     b, 0000h
        push    b
        lxi     b, 0000h
        push    b
        lxi     b, 00C0h
        push    b
        lxi     b, 0E0B0h       ; строки 24-25
        push    b
        lxi     b, 1838h
        push    b
        lxi     b, 0F8F8h
        push    b
        lxi     b, 7000h
        push    b

        lhld    pu_sp           ; SP ровно как был на входе
        sphl
        ei
        ret

; ---------------------------------------------------------------
; фаза 1 (шаг вперёд)
; 3 столбца x 32 строк, плоскости П1 + П0
; ---------------------------------------------------------------
_spr_push_mario2:
        pop     d               ; ret
        pop     h
        mov     a, l
        sta     pu_y            ; y — верх спрайта
        pop     h
        mov     a, l
        sta     pu_x            ; x — левый край (кратен 8)
        push    d               ; ret обратно на стек: дальше SP уедет в VRAM

        di                      ; SP в VRAM — кадровое прерывание трогать стек не должно
        lxi     h, 0
        dad     sp              ; 8080 не умеет ld (nn),sp
        shld    pu_sp           ; SP на входе в функцию

        ; HL = 0x8000 + (x/8)*256 + (255-y) — верх левого столбца П3
        lda     pu_x
        ora     a               ; CY=0, иначе rar вставит бит переноса в H
        rar
        rar
        rar
        mov     h, a
        mvi     l, 0
        mov     a, h
        adi     80h
        mov     h, a
        lda     pu_y
        cma
        mov     l, a            ; L = 255-y — строка 0 столбца

        ; --- П1 (C000h) ---
        mov     a, h
        adi     40h             ; база плоскости (HL = верх П3)
        mov     h, a

        ; ------- П1, столбец 0 -------
        inx     h               ; SP = верх столбца + 1
        sphl
        lxi     b, 0000h        ; строки 0-1
        push    b
        lxi     b, 0000h
        push    b
        lxi     b, 0C0Fh
        push    b
        lxi     b, 0808h
        push    b
        lxi     b, 3F7Fh        ; строки 8-9
        push    b
        lxi     b, 3F1Fh
        push    b
        lxi     b, 3F7Fh
        push    b
        lxi     b, 7FFFh
        push    b
        lxi     b, 3F0Fh        ; строки 16-17
        push    b
        lxi     b, 072Ch
        push    b
        lxi     b, 7973h
        push    b
        lxi     b, 333Fh
        push    b
        lxi     b, 3F3Fh        ; строки 24-25
        push    b
        lxi     b, 7F9Fh
        push    b
        lxi     b, 8E44h
        push    b
        lxi     b, 2418h
        push    b

        ; ------- П1, столбец 1 -------
        inr     h               ; +0x100 — следующий столбец
        sphl
        lxi     b, 0000h        ; строки 0-1
        push    b
        lxi     b, 0000h
        push    b
        lxi     b, 3070h
        push    b
        lxi     b, 0F070h
        push    b
        lxi     b, 38C4h        ; строки 8-9
        push    b
        lxi     b, 0E4FEh
        push    b
        lxi     b, 0FEFEh
        push    b
        lxi     b, 0FEFCh
        push    b
        lxi     b, 0F8FCh       ; строки 16-17
        push    b
        lxi     b, 0E2E2h
        push    b
        lxi     b, 0F1F9h
        push    b
        lxi     b, 0F9F3h
        push    b
        lxi     b, 0FFFFh       ; строки 24-25
        push    b
        lxi     b, 0FFFAh
        push    b
        lxi     b, 0FA72h
        push    b
        lxi     b, 84F8h
        push    b

        ; ------- П1, столбец 2 -------
        inr     h               ; +0x100 — следующий столбец
        sphl
        lxi     b, 0000h        ; строки 0-1
        push    b
        lxi     b, 0000h
        push    b
        lxi     b, 0000h
        push    b
        lxi     b, 0000h
        push    b
        lxi     b, 0000h        ; строки 8-9
        push    b
        lxi     b, 0000h
        push    b
        lxi     b, 0000h
        push    b
        lxi     b, 0000h
        push    b
        lxi     b, 0000h        ; строки 16-17
        push    b
        lxi     b, 0000h
        push    b
        lxi     b, 0000h
        push    b
        lxi     b, 0E038h
        push    b
        lxi     b, 2C24h        ; строки 24-25
        push    b
        lxi     b, 64CCh
        push    b
        lxi     b, 3800h
        push    b
        lxi     b, 0000h
        push    b

        ; --- П0 (E000h) ---
        mov     a, h
        adi     1Eh             ; база плоскости минус уже пройденные столбцы
        mov     h, a

        ; ------- П0, столбец 0 -------
        ; HL уже = верх столбца + 1 (осталось от прошлой плоскости)
        sphl
        lxi     b, 0000h        ; строки 0-1
        push    b
        lxi     b, 0000h
        push    b
        lxi     b, 0C0Bh
        push    b
        lxi     b, 0F0Fh
        push    b
        lxi     b, 3F7Fh        ; строки 8-9
        push    b
        lxi     b, 301Ah
        push    b
        lxi     b, 3A40h
        push    b
        lxi     b, 41E7h
        push    b
        lxi     b, 3E08h        ; строки 16-17
        push    b
        lxi     b, 072Fh
        push    b
        lxi     b, 5F5Eh
        push    b
        lxi     b, 3E2Dh
        push    b
        lxi     b, 2C3Fh        ; строки 24-25
        push    b
        lxi     b, 7FFFh
        push    b
        lxi     b, 0FE7Ch
        push    b
        lxi     b, 3C18h
        push    b

        ; ------- П0, столбец 1 -------
        inr     h               ; +0x100 — следующий столбец
        sphl
        lxi     b, 0000h        ; строки 0-1
        push    b
        lxi     b, 0000h
        push    b
        lxi     b, 3050h
        push    b
        lxi     b, 9090h
        push    b
        lxi     b, 0D8FCh       ; строки 8-9
        push    b
        lxi     b, 7C3Eh
        push    b
        lxi     b, 3272h
        push    b
        lxi     b, 2284h
        push    b
        lxi     b, 183Ch        ; строки 16-17
        push    b
        lxi     b, 0FEFEh
        push    b
        lxi     b, 1F0Fh
        push    b
        lxi     b, 0F1Fh
        push    b
        lxi     b, 0FEFEh       ; строки 24-25
        push    b
        lxi     b, 0FFFEh
        push    b
        lxi     b, 0FE7Eh
        push    b
        lxi     b, 0FCF8h
        push    b

        ; ------- П0, столбец 2 -------
        inr     h               ; +0x100 — следующий столбец
        sphl
        lxi     b, 0000h        ; строки 0-1
        push    b
        lxi     b, 0000h
        push    b
        lxi     b, 0000h
        push    b
        lxi     b, 0000h
        push    b
        lxi     b, 0000h        ; строки 8-9
        push    b
        lxi     b, 0000h
        push    b
        lxi     b, 0000h
        push    b
        lxi     b, 0000h
        push    b
        lxi     b, 0000h        ; строки 16-17
        push    b
        lxi     b, 0000h
        push    b
        lxi     b, 0000h
        push    b
        lxi     b, 0E0D8h
        push    b
        lxi     b, 0DCDCh       ; строки 24-25
        push    b
        lxi     b, 9CFCh
        push    b
        lxi     b, 3800h
        push    b
        lxi     b, 0000h
        push    b

        lhld    pu_sp           ; SP ровно как был на входе
        sphl
        ei
        ret

; ---------------------------------------------------------------
; фаза 2 (широкий шаг)
; 3 столбца x 32 строк, плоскости П1 + П0
; ---------------------------------------------------------------
_spr_push_mario3:
        pop     d               ; ret
        pop     h
        mov     a, l
        sta     pu_y            ; y — верх спрайта
        pop     h
        mov     a, l
        sta     pu_x            ; x — левый край (кратен 8)
        push    d               ; ret обратно на стек: дальше SP уедет в VRAM

        di                      ; SP в VRAM — кадровое прерывание трогать стек не должно
        lxi     h, 0
        dad     sp              ; 8080 не умеет ld (nn),sp
        shld    pu_sp           ; SP на входе в функцию

        ; HL = 0x8000 + (x/8)*256 + (255-y) — верх левого столбца П3
        lda     pu_x
        ora     a               ; CY=0, иначе rar вставит бит переноса в H
        rar
        rar
        rar
        mov     h, a
        mvi     l, 0
        mov     a, h
        adi     80h
        mov     h, a
        lda     pu_y
        cma
        mov     l, a            ; L = 255-y — строка 0 столбца

        ; --- П1 (C000h) ---
        mov     a, h
        adi     40h             ; база плоскости (HL = верх П3)
        mov     h, a

        ; ------- П1, столбец 0 -------
        inx     h               ; SP = верх столбца + 1
        sphl
        lxi     b, 0000h        ; строки 0-1
        push    b
        lxi     b, 0000h
        push    b
        lxi     b, 181Fh
        push    b
        lxi     b, 1808h
        push    b
        lxi     b, 3F7Fh        ; строки 8-9
        push    b
        lxi     b, 3F1Fh
        push    b
        lxi     b, 1F3Fh
        push    b
        lxi     b, 3F7Fh
        push    b
        lxi     b, 1F0Fh        ; строки 16-17
        push    b
        lxi     b, 6FF9h
        push    b
        lxi     b, 0F1E3h
        push    b
        lxi     b, 677Fh
        push    b
        lxi     b, 9F8Fh        ; строки 24-25
        push    b
        lxi     b, 8F8Fh
        push    b
        lxi     b, 0C870h
        push    b
        lxi     b, 0000h
        push    b

        ; ------- П1, столбец 1 -------
        inr     h               ; +0x100 — следующий столбец
        sphl
        lxi     b, 0000h        ; строки 0-1
        push    b
        lxi     b, 0000h
        push    b
        lxi     b, 1CBCh
        push    b
        lxi     b, 7C3Ch
        push    b
        lxi     b, 1CC4h        ; строки 8-9
        push    b
        lxi     b, 0F4FEh
        push    b
        lxi     b, 0FEFFh
        push    b
        lxi     b, 0FFFEh
        push    b
        lxi     b, 0FCF8h       ; строки 16-17
        push    b
        lxi     b, 0C482h
        push    b
        lxi     b, 71F9h
        push    b
        lxi     b, 0FDFFh
        push    b
        lxi     b, 0FFF3h       ; строки 24-25
        push    b
        lxi     b, 0FBF9h
        push    b
        lxi     b, 0F919h
        push    b
        lxi     b, 0600h
        push    b

        ; ------- П1, столбец 2 -------
        inr     h               ; +0x100 — следующий столбец
        sphl
        lxi     b, 0000h        ; строки 0-1
        push    b
        lxi     b, 0000h
        push    b
        lxi     b, 0000h
        push    b
        lxi     b, 0000h
        push    b
        lxi     b, 0000h        ; строки 8-9
        push    b
        lxi     b, 0000h
        push    b
        lxi     b, 0000h
        push    b
        lxi     b, 0000h
        push    b
        lxi     b, 0000h        ; строки 16-17
        push    b
        lxi     b, 0000h
        push    b
        lxi     b, 0000h
        push    b
        lxi     b, 0FC36h
        push    b
        lxi     b, 3232h        ; строки 24-25
        push    b
        lxi     b, 36FCh
        push    b
        lxi     b, 0000h
        push    b
        lxi     b, 0000h
        push    b

        ; --- П0 (E000h) ---
        mov     a, h
        adi     1Eh             ; база плоскости минус уже пройденные столбцы
        mov     h, a

        ; ------- П0, столбец 0 -------
        ; HL уже = верх столбца + 1 (осталось от прошлой плоскости)
        sphl
        lxi     b, 0000h        ; строки 0-1
        push    b
        lxi     b, 0000h
        push    b
        lxi     b, 1817h
        push    b
        lxi     b, 170Fh
        push    b
        lxi     b, 3F7Fh        ; строки 8-9
        push    b
        lxi     b, 3015h
        push    b
        lxi     b, 1520h
        push    b
        lxi     b, 2073h
        push    b
        lxi     b, 1F08h        ; строки 16-17
        push    b
        lxi     b, 6F9Fh
        push    b
        lxi     b, 0BFBFh
        push    b
        lxi     b, 7F59h
        push    b
        lxi     b, 0F9FFh       ; строки 24-25
        push    b
        lxi     b, 0FFFFh
        push    b
        lxi     b, 0F870h
        push    b
        lxi     b, 0000h
        push    b

        ; ------- П0, столбец 1 -------
        inr     h               ; +0x100 — следующий столбец
        sphl
        lxi     b, 0000h        ; строки 0-1
        push    b
        lxi     b, 0000h
        push    b
        lxi     b, 1CA4h
        push    b
        lxi     b, 0C4C4h
        push    b
        lxi     b, 0E4FCh       ; строки 8-9
        push    b
        lxi     b, 3C1Eh
        push    b
        lxi     b, 1A39h
        push    b
        lxi     b, 91C2h
        push    b
        lxi     b, 0C38h        ; строки 16-17
        push    b
        lxi     b, 0FCFEh
        push    b
        lxi     b, 0FF8Fh
        push    b
        lxi     b, 0707h
        push    b
        lxi     b, 8CFEh        ; строки 24-25
        push    b
        lxi     b, 0FFFFh
        push    b
        lxi     b, 0FF1Fh
        push    b
        lxi     b, 0600h
        push    b

        ; ------- П0, столбец 2 -------
        inr     h               ; +0x100 — следующий столбец
        sphl
        lxi     b, 0000h        ; строки 0-1
        push    b
        lxi     b, 0000h
        push    b
        lxi     b, 0000h
        push    b
        lxi     b, 0000h
        push    b
        lxi     b, 0000h        ; строки 8-9
        push    b
        lxi     b, 0000h
        push    b
        lxi     b, 0000h
        push    b
        lxi     b, 0000h
        push    b
        lxi     b, 0000h        ; строки 16-17
        push    b
        lxi     b, 0000h
        push    b
        lxi     b, 0000h
        push    b
        lxi     b, 0FCCEh
        push    b
        lxi     b, 0CECEh       ; строки 24-25
        push    b
        lxi     b, 0CEFCh
        push    b
        lxi     b, 0000h
        push    b
        lxi     b, 0000h
        push    b

        lhld    pu_sp           ; SP ровно как был на входе
        sphl
        ei
        ret

        SECTION bss_compiler
pu_x:     defb    0               ; x — пиксельная координата (кратна 8)
pu_y:     defb    0               ; y — верх спрайта
pu_sp:    defw    0               ; SP функции на входе (DAD SP / SHLD)
