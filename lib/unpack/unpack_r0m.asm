; unpack_r0m.asm — самораспаковывающийся bootstrap для образа .r0m Вектора-06Ц.
;
; Формат .r0m: ядро эмулятора (vector-psp/vector-debug/desktop) берёт адрес
; загрузки из предпоследнего символа имени файла: для «.r0m» это '0' → образ
; грузится в 0x0000 и исполняется с него (ResetMode::LOADROM отключает boot,
; так что 0x0000.. — обычная RAM). Точка входа — 0x0000.
;
; Идея обратной (backward) самораспаковки: сжатый поток ZX0 лежит НИЖЕ адреса
; назначения (поток начинается сразу за кодом stub, на ~0x0078, а оригинал
; распаковывается в 0x0100 и выше). Обратный декодер читает поток с конца вниз
; и пишет оригинал с конца (0x0100+len-1) вниз. Разрыв write-указателя от
; read-указателя убывает монотонно и в пределе равен (0x0100 - start_stream) > 0,
; поэтому запись никогда не настигает непрочитанный хвост потока — отдельная
; staging-память не нужна, и сам stub (код ниже 0x0100) не затирается.
;
; Stub собирается РОВНО по адресу исполнения (org 0x0000): внутренние CALL/JMP
; ядра резолвятся корректно без relocation и без второго прохода. Единственные
; параметры, которые подставляет utils/rompack.py, — это адреса конца потока и
; конца оригинала (16-битные immediates, размер кода от них не зависит):
;   -Dsrc_last = адрес последнего байта сжатого потока (stub_size + len - 1)
;   -Ddst_last = адрес последнего байта оригинала      (0x0100 + orig_len - 1)
;
; После EOF ядро делает RZ, вспопав заранее положенный сюда 0x0100, — то есть
; управление передаётся распакованному оригиналу. Вектора оригинал ставит сам
; (lib/sys/startup.asm); остаток потока в векторной странице 0x0000-0x00FF
; безвреден и частично перезаписывается инициализацией оригинала.
;
; Только 8080, Intel-мнемоники (par: inx/dcx). Тот же backward-код, что в
; lib/unpack/zx0_back.asm (регрессия: utils/emulator/test_zx0_back.py).

        org     0x0000

; --- bootstrap -------------------------------------------------------------
entry:
        di
        lxi     sp, 0FF00h              ; стек выше и dst, и потока (проверка в rompack)
        lxi     h, 0100h
        push    h                       ; «адрес возврата»: на EOF ядро вспопает 0x0100
        lxi     h, src_last             ; HL = последний байт сжатого потока
        lxi     d, dst_last             ; DE = последний байт оригинала
        jmp     zx0_back                ; распаковка; завершается RET в 0x0100

; src_last / dst_last задаются только через -D при сборке (rompack). Без -D
; символы не определёнy — файл собирается лишь с переданными значениями.

; --- ядро dzx0_standard (backward) ----------------------------------------
; Вход: HL = последний src, DE = последний dst, в стеке — адрес возврата.
zx0_back:
        mov     b,d
        mov     c,e             ; BC = DE = назначение (последний байт)
        lxi     d,1
        push    d               ; last_offset = 0x0001
        dcr     e               ; DE = 0x0000 (нужно для elias: INR E -> 1)
        mvi     a,080h          ; битовый аккумулятор: часовой бит

zx0s_literals:
        call    zx0s_elias      ; DE = длина блока литералов
        call    zx0s_ldir       ; скопировать литералы с (HL) вниз в (BC)
        add     a               ; следующий бит
        jc      zx0s_new_offset ; 1 -> новое смещение
        call    zx0s_elias      ; 0 -> повтор с последним смещением, DE = длина

zx0s_copy:
        xthl                    ; HL <-> (SP): HL = last_offset, (SP) = src
        push    h               ; вернуть last_offset в стек
        dad     b               ; HL = last_offset + BC (повтор — выше BC)
        call    zx0s_ldir       ; скопировать DE байт (с перекрытием)
        pop     h               ; HL = last_offset
        xthl                    ; HL = src, (SP) = last_offset
        add     a               ; следующий бит
        jnc     zx0s_literals   ; 0 -> литералы
                                ; 1 -> новое смещение (проваливаемся)

zx0s_new_offset:
        call    zx0s_elias      ; DE = значение (младший байт = e_v)
        inx     sp              ; снять last_offset (2 байта) — дальше не нужен
        inx     sp
        dcr     d               ; backward EOF-тест старшего байта значения
        rz                      ; -> конец потока (RZ снимает адрес возврата)
        dcr     e
        mov     d,e             ; подготовка нового смещения (backward-ветка)
        push    b
        mov     b,a             ; B = битовый аккумулятор (сохранить)
        mov     a,d             ; A = a_sub
        rar                     ; A = (a_sub>>1)|0x80; carry = a_sub&1
        mov     d,a             ; D = старший байт нового смещения
        mov     a,m             ; A = байт смещения M из (HL)
        rar                     ; A = (M>>1)|(carry<<7); carry = M&1 (interlace)
        mov     e,a             ; E = младший байт нового смещения
        mov     a,b             ; A = битовый аккумулятор (восстановить)
        pop     b
        dcx     h               ; пропустить байт смещения M (источник вниз)
        inx     d               ; backward-подстройка базы
        push    d               ; last_offset = DE (новое смещение)
        lxi     d,1             ; DE = 1 (база длины)
        cc      zx0s_elias_backtrack ; carry==1 (M&1==1) -> дочитать длину
        inx     d               ; DE = длина
        jmp     zx0s_copy

; Elias-gamma (interlaced). backward: источник читается вниз (DCX H),
; возврат по отсутствию переноса (RNC), а не по переносу (RC) как в forward.
zx0s_elias:
        inr     e               ; DE = 1
zx0s_elias_loop:
        add     a               ; getbit -> carry
        jnz     zx0s_elias_skip ; A != 0 -> бит ещё есть в аккумуляторе
        mov     a,m             ; иначе подгрузить байт из (HL)
        dcx     h               ; источник идёт вниз (backward)
        ral                     ; A = (A<<1)|carry; carry = бит7 байта
zx0s_elias_skip:
        rnc                     ; backward: бит == 0 -> вернуть DE
zx0s_elias_backtrack:
        xchg                    ; бит == 1: DE <<= 1
        dad     h
        xchg
        add     a               ; getbit (бит данных)
        jnc     zx0s_elias_loop ; 0 -> продолжить
        inr     e               ; 1 -> DE += 1
        jmp     zx0s_elias_loop

; Копировать DE байт с (HL) в (BC), ОБА указателя идут ВНИЗ (backward).
zx0s_ldir:
        push    psw
zx0s_ldir_loop:
        mov     a,m             ; прочитать из (HL)
        stax    b               ; записать в (BC)
        dcx     h               ; HL-- (backward)
        dcx     b               ; BC-- (backward)
        dcx     d               ; DE-- (счётчик)
        mov     a,d
        ora     e
        jnz     zx0s_ldir_loop
        pop     psw
        ret
