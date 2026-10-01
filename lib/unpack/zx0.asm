; zx0.asm — распаковщик ZX0 «standard» для Вектора-06Ц (KR580VM80A / 8080).
;
; Порт эталонного 8080-декодера DeZX dzx0_standard (Einar Saukas /
; Ivan Gorodetsky, z88dk: _DEVELOPMENT/compress/zx0/8080/dzx0.asm) под
; соглашение вызова z88dk classic этого проекта. Формат потока в точности
; совпадает с тем, что выдаёт сборочный компрессор utils/zx0.py (его
; Python-модель dzx0_standard() побайтово повторяет этот ассемблер).
;
; C-интерфейс (стандартное соглашение, стек чистит вызывающий):
;     void zx0_decompress(const unsigned char *src, unsigned char *dst);
; src — сжатый поток ZX0 (без заголовка), dst — куда распаковывать. Длину
; результата декодер не знает: поток завершается маркером EOF (Elias(256)),
; поэтому длина хранится вызывающим отдельно.
;
; Распаковка идёт «вперёд» (forward): src < dst, области не перекрываются.
; Декодер активно использует стек (хранит там «последнее смещение»), но
; к моменту возврата (EOF) стек сбалансирован: POP PSW снимает слот
; смещения непосредственно перед RZ.
;
; Аргументы (по выводу zcc -S, как в rle.asm): правый аргумент ближе к SP,
; т.е. dst @ sp+2, src @ sp+4. Функция НЕ чистит стек и просто делает RET.
;
; Только 8080-инструкции. Мнемоника пар — inc/dec (inc hl, dec de): даёт те
; же байты, что Intel inx/dcx, но собирается и z88dk-z80asm -m8080, и
; встроенным ассемблером эмулятора (utils/emulator), что позволяет гонять
; регрессию utils/emulator/test_zx0.py против эталона utils/zx0.py.

        SECTION code_user

        PUBLIC  _zx0_decompress

; ---------------------------------------------------------------------------
; void zx0_decompress(const unsigned char *src, unsigned char *dst)
; ---------------------------------------------------------------------------
_zx0_decompress:
        LXI     H,2
        DAD     SP              ; HL -> dst (sp+2)
        MOV     A,M
        STA     zx0_dst
        INC     HL
        MOV     A,M
        STA     zx0_dst+1
        INC     HL               ; HL -> src (sp+4)
        MOV     A,M
        STA     zx0_src
        INC     HL
        MOV     A,M
        STA     zx0_src+1

        LHLD    zx0_dst
        XCHG                    ; DE = dst
        LHLD    zx0_src         ; HL = src
        CALL    zx0_standard
        RET

; ---------------------------------------------------------------------------
; Ядро dzx0_standard (forward).
; Вход: HL = источник (сжатые данные), DE = назначение.
; Выход: данные распакованы, поток прочитан до EOF.
; Регистры: A — битовый аккумулятор (часовой бит 0x80), BC — указатель
; назначения, DE — длина/смещение (рабочий), (SP) — «последнее смещение»
; как обратное (0x10000 - distance).
; ---------------------------------------------------------------------------
zx0_standard:
        MOV     B,D
        MOV     C,E             ; BC = DE = назначение
        LXI     D,0FFFFh
        PUSH    D               ; last_offset = 0xFFFF (обратное смещение)
        INC     DE               ; DE = 0 (нужно для dzx0s_elias: INR E -> 1)
        MVI     A,080h          ; битовый аккумулятор: часовой бит

zx0s_literals:
        CALL    zx0s_elias      ; DE = длина блока литералов
        CALL    zx0s_ldir       ; скопировать литералы из (HL) в (BC)
        ADD     A               ; следующий бит
        JC      zx0s_new_offset ; 1 -> новое смещение
        CALL    zx0s_elias      ; 0 -> повтор с последним смещением, DE = длина

zx0s_copy:
        XTHL                    ; HL <-> (SP): HL = last_offset, (SP) = src
        PUSH    H               ; вернуть last_offset в стек
        DAD     B               ; HL = last_offset + BC = BC - distance
        CALL    zx0s_ldir       ; скопировать DE байт (с перекрытием)
        POP     H               ; HL = last_offset
        XTHL                    ; HL = src, (SP) = last_offset
        ADD     A               ; следующий бит
        JNC     zx0s_literals   ; 0 -> литералы
                                ; 1 -> новое смещение (проваливаемся)

zx0s_new_offset:
        CALL    zx0s_elias      ; DE = значение (младший байт = e_v)
        MOV     D,A             ; D = A (сохранить битовый аккумулятор)
        POP     PSW             ; снять last_offset; A = его старший байт
        XRA     A
        SUB     E               ; A = 0 - e_v; carry = 1 (e_v != 0)
        RZ                      ; e_v == 0 -> EOF (конец потока)
        MOV     E,D             ; E = битовый аккумулятор
        MOV     D,A             ; D = a_sub = 256 - e_v
        MOV     A,E             ; A = битовый аккумулятор
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
        INC     HL               ; пропустить байт смещения M
        PUSH    D               ; last_offset = DE (новое обратное смещение)
        LXI     D,1             ; DE = 1 (база длины)
        CNC     zx0s_elias_backtrack ; carry==0 (M&1==0) -> дочитать длину
        INC     DE               ; DE = длина (value + 1)
        JMP     zx0s_copy

; Elias-gamma (interlaced). На входе DE = 0 (или 1 для backtrack).
; Читает биты из аккумулятора A, подгружая байты из (HL).
zx0s_elias:
        INR     E               ; DE = 1
zx0s_elias_loop:
        ADD     A               ; getbit -> carry
        JNZ     zx0s_elias_skip ; A != 0 -> бит ещё есть в аккумуляторе
        MOV     A,M             ; иначе подгрузить байт из (HL)
        INC     HL
        RAL                     ; A = (A<<1)|carry; carry = бит7 байта
zx0s_elias_skip:
        RC                      ; бит == 1 -> вернуть DE
zx0s_elias_backtrack:
        XCHG                    ; бит == 0: DE <<= 1
        DAD     H
        XCHG
        ADD     A               ; getbit (бит данных)
        JNC     zx0s_elias_loop ; 0 -> продолжить
        INR     E               ; 1 -> DE += 1
        JMP     zx0s_elias_loop

; Копировать DE байт из (HL) в (BC), продвигая оба указателя.
zx0s_ldir:
        PUSH    PSW
zx0s_ldir_loop:
        MOV     A,M
        STAX    B
        INC     HL
        INC     BC
        DEC     DE
        MOV     A,D
        ORA     E
        JNZ     zx0s_ldir_loop
        POP     PSW
        RET

        SECTION bss_user

zx0_dst:        DEFS 2
zx0_src:        DEFS 2
