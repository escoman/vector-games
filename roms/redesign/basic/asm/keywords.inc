; Данные: data_keyword_table  (таблица ключевых слов BASIC)
; Адрес: 0x256E..0x26D6 (361 байт, 101 слов)
; Формат: байт = символ слова; bit7 последнего байта = конец слова.
; Токен = 0x80 + номер слова (func_tok_tokenize: MOV A,B / ORI 80).
; Потребитель: токенизатор (0x256E, LXI D,256D) и детокенизация LIST.
; Сверено с tools/tokens.md и Basic_Vector-06C.pdf (Приложение 1).

data_keyword_table:
    DEFB 43h, 4Ch, 0D3h         ; 0x80  #0        CLS
    DEFB 46h, 4Fh, 0D2h         ; 0x81  #1        FOR
    DEFB 4Eh, 45h, 58h, 0D4h    ; 0x82  #2        NEXT
    DEFB 44h, 41h, 54h, 0C1h    ; 0x83  #3        DATA
    DEFB 49h, 4Eh, 50h, 55h, 0D4h ; 0x84  #4        INPUT
    DEFB 44h, 49h, 0CDh         ; 0x85  #5        DIM
    DEFB 52h, 45h, 41h, 0C4h    ; 0x86  #6        READ
    DEFB 43h, 55h, 0D2h         ; 0x87  #7        CUR
    DEFB 47h, 4Fh, 54h, 0CFh    ; 0x88  #8        GOTO
    DEFB 52h, 55h, 0CEh         ; 0x89  #9        RUN
    DEFB 49h, 0C6h              ; 0x8A  #10       IF
    DEFB 52h, 45h, 53h, 54h, 4Fh, 52h, 0C5h ; 0x8B  #11       RESTORE
    DEFB 47h, 4Fh, 53h, 55h, 0C2h ; 0x8C  #12       GOSUB
    DEFB 52h, 45h, 54h, 55h, 52h, 0CEh ; 0x8D  #13       RETURN
    DEFB 52h, 45h, 0CDh         ; 0x8E  #14       REM
    DEFB 53h, 54h, 4Fh, 0D0h    ; 0x8F  #15       STOP
    DEFB 4Fh, 55h, 0D4h         ; 0x90  #16       OUT
    DEFB 4Fh, 0CEh              ; 0x91  #17       ON
    DEFB 50h, 4Ch, 4Fh, 0D4h    ; 0x92  #18       PLOT
    DEFB 4Ch, 49h, 4Eh, 0C5h    ; 0x93  #19       LINE
    DEFB 50h, 4Fh, 4Bh, 0C5h    ; 0x94  #20       POKE
    DEFB 50h, 52h, 49h, 4Eh, 0D4h ; 0x95  #21       PRINT
    DEFB 44h, 45h, 0C6h         ; 0x96  #22       DEF
    DEFB 43h, 4Fh, 4Eh, 0D4h    ; 0x97  #23       CONT
    DEFB 4Ch, 49h, 53h, 0D4h    ; 0x98  #24       LIST
    DEFB 43h, 4Ch, 45h, 41h, 0D2h ; 0x99  #25       CLEAR
    DEFB 43h, 4Ch, 4Fh, 41h, 0C4h ; 0x9A  #26       CLOAD
    DEFB 43h, 53h, 41h, 56h, 0C5h ; 0x9B  #27       CSAVE
    DEFB 4Eh, 45h, 0D7h         ; 0x9C  #28       NEW
    DEFB 54h, 41h, 42h, 0A8h    ; 0x9D  #29       TAB(
    DEFB 54h, 0CFh              ; 0x9E  #30       TO
    DEFB 53h, 50h, 43h, 0A8h    ; 0x9F  #31       SPC(
    DEFB 46h, 0CEh              ; 0xA0  #32       FN
    DEFB 54h, 48h, 45h, 0CEh    ; 0xA1  #33       THEN
    DEFB 4Eh, 4Fh, 0D4h         ; 0xA2  #34       NOT
    DEFB 53h, 54h, 45h, 0D0h    ; 0xA3  #35       STEP
    DEFB 0ABh                   ; 0xA4  #36       +
    DEFB 0ADh                   ; 0xA5  #37       -
    DEFB 0AAh                   ; 0xA6  #38       *
    DEFB 0AFh                   ; 0xA7  #39       /
    DEFB 0DEh                   ; 0xA8  #40       ^
    DEFB 41h, 4Eh, 0C4h         ; 0xA9  #41       AND
    DEFB 4Fh, 0D2h              ; 0xAA  #42       OR
    DEFB 0BEh                   ; 0xAB  #43       >
    DEFB 0BDh                   ; 0xAC  #44       =
    DEFB 0BCh                   ; 0xAD  #45       <
    DEFB 53h, 47h, 0CEh         ; 0xAE  #46       SGN
    DEFB 49h, 4Eh, 0D4h         ; 0xAF  #47       INT
    DEFB 41h, 42h, 0D3h         ; 0xB0  #48       ABS
    DEFB 55h, 53h, 0D2h         ; 0xB1  #49       USR
    DEFB 46h, 52h, 0C5h         ; 0xB2  #50       FRE
    DEFB 49h, 4Eh, 0D0h         ; 0xB3  #51       INP
    DEFB 50h, 4Fh, 0D3h         ; 0xB4  #52       POS
    DEFB 53h, 51h, 0D2h         ; 0xB5  #53       SQR
    DEFB 52h, 4Eh, 0C4h         ; 0xB6  #54       RND
    DEFB 4Ch, 4Fh, 0C7h         ; 0xB7  #55       LOG
    DEFB 45h, 58h, 0D0h         ; 0xB8  #56       EXP
    DEFB 43h, 4Fh, 0D3h         ; 0xB9  #57       COS
    DEFB 53h, 49h, 0CEh         ; 0xBA  #58       SIN
    DEFB 54h, 41h, 0CEh         ; 0xBB  #59       TAN
    DEFB 41h, 54h, 0CEh         ; 0xBC  #60       ATN
    DEFB 50h, 45h, 45h, 0CBh    ; 0xBD  #61       PEEK
    DEFB 4Ch, 45h, 0CEh         ; 0xBE  #62       LEN
    DEFB 53h, 54h, 52h, 0A4h    ; 0xBF  #63       STR$
    DEFB 56h, 41h, 0CCh         ; 0xC0  #64       VAL
    DEFB 41h, 53h, 0C3h         ; 0xC1  #65       ASC
    DEFB 43h, 48h, 52h, 0A4h    ; 0xC2  #66       CHR$
    DEFB 4Ch, 45h, 46h, 54h, 0A4h ; 0xC3  #67       LEFT$
    DEFB 52h, 49h, 47h, 48h, 54h, 0A4h ; 0xC4  #68       RIGHT$
    DEFB 4Dh, 49h, 44h, 0A4h    ; 0xC5  #69       MID$
    DEFB 50h, 4Fh, 49h, 4Eh, 0D4h ; 0xC6  #70       POINT
    DEFB 49h, 4Eh, 4Bh, 45h, 59h, 0A4h ; 0xC7  #71       INKEY$
    DEFB 41h, 0D4h              ; 0xC8  #72       AT
    DEFB 0A6h                   ; 0xC9  #73       &
    DEFB 42h, 45h, 45h, 0D0h    ; 0xCA  #74       BEEP
    DEFB 50h, 41h, 55h, 53h, 0C5h ; 0xCB  #75       PAUSE
    DEFB 56h, 45h, 52h, 49h, 46h, 0D9h ; 0xCC  #76       VERIFY
    DEFB 48h, 4Fh, 4Dh, 0C5h    ; 0xCD  #77       HOME
    DEFB 45h, 44h, 49h, 0D4h    ; 0xCE  #78       EDIT
    DEFB 44h, 45h, 4Ch, 45h, 54h, 0C5h ; 0xCF  #79       DELETE
    DEFB 4Dh, 45h, 52h, 47h, 0C5h ; 0xD0  #80       MERGE
    DEFB 41h, 55h, 54h, 0CFh    ; 0xD1  #81       AUTO
    DEFB 48h, 49h, 4Dh, 45h, 0CDh ; 0xD2  #82       HIMEM
    DEFB 0C0h                   ; 0xD3  #83       @
    DEFB 41h, 53h, 0CEh         ; 0xD4  #84       ASN
    DEFB 41h, 44h, 44h, 0D2h    ; 0xD5  #85       ADDR
    DEFB 50h, 0C9h              ; 0xD6  #86       PI
    DEFB 52h, 45h, 4Eh, 55h, 0CDh ; 0xD7  #87       RENUM
    DEFB 41h, 43h, 0D3h         ; 0xD8  #88       ACS
    DEFB 4Ch, 0C7h              ; 0xD9  #89       LG
    DEFB 4Ch, 50h, 52h, 49h, 4Eh, 0D4h ; 0xDA  #90       LPRINT
    DEFB 4Ch, 4Ch, 49h, 53h, 0D4h ; 0xDB  #91       LLIST
    DEFB 53h, 43h, 52h, 45h, 45h, 0CEh ; 0xDC  #92       SCREEN
    DEFB 43h, 4Fh, 4Ch, 4Fh, 0D2h ; 0xDD  #93       COLOR
    DEFB 47h, 45h, 0D4h         ; 0xDE  #94       GET
    DEFB 50h, 55h, 0D4h         ; 0xDF  #95       PUT
    DEFB 42h, 53h, 41h, 56h, 0C5h ; 0xE0  #96       BSAVE
    DEFB 42h, 4Ch, 4Fh, 41h, 0C4h ; 0xE1  #97       BLOAD
    DEFB 50h, 4Ch, 41h, 0D9h    ; 0xE2  #98       PLAY
    DEFB 50h, 41h, 49h, 4Eh, 0D4h ; 0xE3  #99       PAINT
    DEFB 43h, 49h, 52h, 43h, 4Ch, 0C5h ; 0xE4  #100      CIRCLE
