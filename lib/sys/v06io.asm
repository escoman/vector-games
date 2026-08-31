;
; v06io.asm — примитивы портов ввода-вывода Вектора-06Ц (КР580ВМ80).
;
; У процессора 8080 инструкции IN/OUT принимают только непосредственный
; номер порта, поэтому номер порта вписывается самоmodификацией в операнд.
;
; Соглашение вызова z88dk classic: аргументы в стеке, первый сверху.
;
;   void v06_out(unsigned char port, unsigned char val);
;   unsigned char v06_in(unsigned char port);
;

        SECTION code_clib
        PUBLIC  v06_out
        PUBLIC  _v06_out
        PUBLIC  v06_in
        PUBLIC  _v06_in

; Функции вызываются и из основного цикла, и из кадрового прерывания,
; поэтому окно самоmodификации прикрывается di/ei: иначе прерывание,
; вклинившееся между вписыванием номера порта и OUT, подменит порт.

; void v06_out(unsigned char port, unsigned char val)
v06_out:
_v06_out:
        pop     hl              ; адрес возврата
        pop     de              ; port -> e
        pop     bc              ; val  -> c
        push    bc
        push    de
        push    hl

        di
        ld      a, e
        ld      (outpatch+1), a ; вписать номер порта
        ld      a, c
outpatch:
        out     (0), a
        ei
        ret

; unsigned char v06_in(unsigned char port) — результат в L
v06_in:
_v06_in:
        pop     hl              ; адрес возврата
        pop     de              ; port -> e
        push    de
        push    hl

        di
        ld      a, e
        ld      (inpatch+1), a  ; вписать номер порта
inpatch:
        in      a, (0)
        ei
        ld      l, a
        ret
