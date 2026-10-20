; Функция: func_print_digit_tail
; Адрес: 0x0364
; Размер: 31 байт (0x0364-0x0382, непрерывное тело)
; Описание: Хвост func_print_uint16: вывод цифры (A|=30h), подача ведущих
;   нулей через var_num_leading_zero_flag, печать пробелом/func_print_char_at_ptr.
;   Вход из func_print_uint16 (JMP 0x0364).

func_print_digit_tail:
    ORI   030h                ; 0x0364
    PUSH  PSW                 ; 0x0366
    CPI   030h                ; 0x0367
    JZ    loc_0371            ; 0x0369
    MVI   A, 01h              ; 0x036C
    STA   var_num_leading_zero_flag; 0x036E
loc_0371:
    LDA   var_num_leading_zero_flag; 0x0371
    ORA   A                   ; 0x0374
    JNZ   loc_037F            ; 0x0375
    MVI   A, 020h             ; 0x0378
    CALL  func_print_char_at_ptr; 0x037A
    POP   PSW                 ; 0x037D
    RET                       ; 0x037E
loc_037F:
    POP   PSW                 ; 0x037F
    JMP   func_print_char_at_ptr; 0x0380
