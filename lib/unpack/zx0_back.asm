; ZX0 backward-декодер (forward -> назад) для самораспаковки ROM Вектора-06Ц.
;
; Порт эталонного 8080-декодера DeZX (Ivan Gorodetsky, z88dk:
; libsrc/_DEVELOPMENT/compress/zx0/8080/dzx0.asm) с включённой веткой
; BACKWARD=1. Поток соответствует режиму компрессора ``zx0 -b``: его даёт
; utils/zx0.py::compress_backwards (reverse -> forward-сжатие -> reverse).
;
; Ключевое отличие от forward (lib/unpack/zx0.asm): распаковка идёт ЗАДОМ НАПЁРЁД.
; Указатели чтения источника и записи приёмника стартуют с последних адресов и
; идут вниз. Это позволяет распаковывать оригинал «по себе» — сжатый поток
; лежит в НИЗЕЙ области назначения, распакованный ростет вверх; write-указатель
; всегда не ниже непрочитанного read, поэтому остаток потока не затирается и
; отдельная staging-память под поток не нужна.
;
; Контракт входа (голое ядро, без C-обёртки и без BSS — только регистры и стек):
;   HL = последний адрес источника (конец сжатого потока)
;   DE = последний адрес назначения (конец оригинала)
;   в стеке под these регистрами лежит адрес возврата — ядро на EOF делает RZ,
;   снимая его (т.е. entering CALL-подобно: push ret; jmp zx0_back).
;
; Только 8080-инструкции, Intel-мнемоника пар (inx/dcx), чтобы файл собирались
; и z88dk-z80asm -m=8080_strict, и встроенным ассемблером эмулятора
; (utils/emulator). Регрессия: utils/emulator/test_zx0_back.py.

        SECTION code_user

        PUBLIC  zx0_back

; ---------------------------------------------------------------------------
; Ядро dzx0_standard (backward). Вход: HL = последний src, DE = последний dst.
; ---------------------------------------------------------------------------
zx0_back:
        MOV     B,D
        MOV     C,E             ; BC = DE = назначение (последний байт)
        LXI     D,1
        PUSH    D               ; last_offset = 0x0001
        DCR     E               ; DE = 0x0000 (нужно для elias: INR E -> 1)
        MVI     A,080h          ; битовый аккумулятор: часовой бит

zx0s_literals:
        CALL    zx0s_elias      ; DE = длина блока литералов
        CALL    zx0s_ldir       ; скопировать литералы с (HL) вниз в (BC)
        ADD     A               ; следующий бит
        JC      zx0s_new_offset ; 1 -> новое смещение
        CALL    zx0s_elias      ; 0 -> повтор с последним смещением, DE = длина

zx0s_copy:
        XTHL                    ; HL <-> (SP): HL = last_offset, (SP) = src
        PUSH    H               ; вернуть last_offset в стек
        DAD     B               ; HL = last_offset + BC (повтор — выше BC)
        CALL    zx0s_ldir       ; скопировать DE байт (с перекрытием)
        POP     H               ; HL = last_offset
        XTHL                    ; HL = src, (SP) = last_offset
        ADD     A               ; следующий бит
        JNC     zx0s_literals   ; 0 -> литералы
                                ; 1 -> новое смещение (проваливаемся)

zx0s_new_offset:
        CALL    zx0s_elias      ; DE = значение (младший байт = e_v)
        INX     SP              ; снять last_offset (2 байта) — дальше не нужен
        INX     SP
        DCR     D               ; backward EOF-тест старшего байта значения
        RZ                      ; -> конец потока (RZ снимает адрес возврата)
        DCR     E
        MOV     D,E             ; подготовка нового смещения (backward-ветка)
        PUSH    B
        MOV     B,A             ; B = битовый аккумулятор (сохранить)
        MOV     A,D             ; A = a_sub
        RAR                     ; A = (a_sub>>1)|0x80; carry = a_sub&1
        MOV     D,A             ; D = старший байт нового смещения
        MOV     A,M             ; A = байт смещения M из (HL)
        RAR                     ; A = (M>>1)|(carry<<7); carry = M&1 (interlace)
        MOV     E,A             ; E = младший байт нового смещения
        MOV     A,B             ; A = битовый аккумулятор (восстановить)
        POP     B
        DCX     H               ; пропустить байт смещения M (источник вниз)
        INX     D               ; backward-подстройка базы
        PUSH    D               ; last_offset = DE (новое смещение)
        LXI     D,1             ; DE = 1 (база длины)
        CC      zx0s_elias_backtrack ; carry==1 (M&1==1) -> дочитать длину
        INX     D               ; DE = длина
        JMP     zx0s_copy

; Elias-gamma (interlaced). backward: источник читается вниз (DCX H),
; возврат по отсутствию переноса (RNC), а не по переносу (RC) как в forward.
zx0s_elias:
        INR     E               ; DE = 1
zx0s_elias_loop:
        ADD     A               ; getbit -> carry
        JNZ     zx0s_elias_skip ; A != 0 -> бит ещё есть в аккумуляторе
        MOV     A,M             ; иначе подгрузить байт из (HL)
        DCX     H               ; источник идёт вниз (backward)
        RAL                     ; A = (A<<1)|carry; carry = бит7 байта
zx0s_elias_skip:
        RNC                     ; backward: бит == 0 -> вернуть DE
zx0s_elias_backtrack:
        XCHG                    ; бит == 1: DE <<= 1
        DAD     H
        XCHG
        ADD     A               ; getbit (бит данных)
        JNC     zx0s_elias_loop ; 0 -> продолжить
        INR     E               ; 1 -> DE += 1
        JMP     zx0s_elias_loop

; Копировать DE байт с (HL) в (BC), ОБА указателя идут ВНИЗ (backward).
zx0s_ldir:
        PUSH    PSW
zx0s_ldir_loop:
        MOV     A,M             ; прочитать из (HL)
        STAX    B               ; записать в (BC)
        DCX     H               ; HL-- (backward)
        DCX     B               ; BC-- (backward)
        DCX     D               ; DE-- (счётчик)
        MOV     A,D
        ORA     E
        JNZ     zx0s_ldir_loop
        POP     PSW
        RET

        .end
