;
; vi53out.asm — прямая запись в порты ВИ53. Маппинг подтверждён двумя
; независимыми источниками: исходниками эмулятора (vio.h: addr =
; ~port & 3) и рабочей игрой OldTower для Вектора-06Ц:
; управление = 0x08, канал 0 = 0x0B, канал 1 = 0x0A, канал 2 = 0x09.
;
; В отличие от v06_out(), здесь нет самомодификации байта порта и
; di/ei — только инструкция out (n), a с немедленным адресом, поэтому
; кадровое прерывание не может подменить порт.
;
;   void v06_vi53_ctrl(unsigned char v);  — регистр управления
;   void v06_vi53_ch0(unsigned char v);   — данные канала 0
;   void v06_vi53_ch1(unsigned char v);   — данные канала 1
;   void v06_vi53_ch2(unsigned char v);   — данные канала 2
;
; Только 8080-инструкции. Аргумент (unsigned char) передаётся в стеке
; по соглашению z88dk cdecl: читаем его по SP+2, стек НЕ трогаем —
; очистку делает вызывающий.
;

        SECTION code_clib
        PUBLIC  _v06_vi53_ctrl
        PUBLIC  _v06_vi53_ch0
        PUBLIC  _v06_vi53_ch1
        PUBLIC  _v06_vi53_ch2

_v06_vi53_ctrl:
        ld      hl, 2           ; младший байт аргумента над адресом
        add     hl, sp          ; возврата
        ld      a, (hl)
        out     (0x08), a
        ret

_v06_vi53_ch0:
        ld      hl, 2
        add     hl, sp
        ld      a, (hl)
        out     (0x0B), a
        ret

_v06_vi53_ch1:
        ld      hl, 2
        add     hl, sp
        ld      a, (hl)
        out     (0x0A), a
        ret

_v06_vi53_ch2:
        ld      hl, 2
        add     hl, sp
        ld      a, (hl)
        out     (0x09), a
        ret
