; ------------------------------------------------------------
; void graph_fill_stride(unsigned int addr,
;                  unsigned char val,
;                  unsigned int step,
;                  unsigned char count)
;
; sccz80 __CALLEE__ linkage.
;
; Параметры sccz80 передаёт слева направо.
; char занимает слово на стеке.
;
; На входе:
;
;   SP -> return address
;          count       (word)
;          step        (word)
;          val         (word)
;          addr        (word)
;
; После извлечения:
;
;   HL = addr
;   DE = step
;   A  = val
;   C  = count
;   SP -> return address
;
; Все параметры удаляются самой процедурой.
; ------------------------------------------------------------

        SECTION code_clib
        PUBLIC  _graph_fill_stride

_graph_fill_stride:

        DI

        ; ----------------------------------------------------
        ; Получить return address.
        ; ----------------------------------------------------
        POP     H

        ; ----------------------------------------------------
        ; BC = count
        ; DE = step
        ; ----------------------------------------------------
        POP     B
        POP     D

        ; ----------------------------------------------------
        ; На вершине стека находится val.
        ;
        ; HL содержит return address.
        ;
        ; XTHL:
        ;   HL <- val
        ;   [SP] <- return address
        ; ----------------------------------------------------
        XTHL

        ; val -- младший байт слова
        MOV     A,L

        ; ----------------------------------------------------
        ; Забрать return address.
        ; После POP:
        ;
        ;   HL = return address
        ;   SP -> addr
        ; ----------------------------------------------------
        POP     H

        ; ----------------------------------------------------
        ; Получить addr и одновременно вернуть return address
        ; на вершину стека.
        ;
        ; После XTHL:
        ;
        ;   HL = addr
        ;   SP -> return address
        ; ----------------------------------------------------
        XTHL

        ; ----------------------------------------------------
        ; Сейчас:
        ;
        ;   HL = addr
        ;   DE = step
        ;   A  = val
        ;   C  = count
        ;   SP -> return address
        ; ----------------------------------------------------

        ; count == 0 ?
        MOV     B,A          ; сохранить val
        MOV     A,C
        ORA     A
        JZ      graph_fill_stride_zero

        MOV     A,B          ; восстановить val

graph_fill_stride_loop:

        ; *p = val
        MOV     M,A

        ; p += step
        DAD     D

        ; --count
        DCR     C
        JNZ     graph_fill_stride_loop

graph_fill_stride_zero:

        EI
        RET
