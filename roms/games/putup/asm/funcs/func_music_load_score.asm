; Функция: func_music_load_score
; Адрес: 0x3DEB
; Размер: 47 байт (0x3DEB-0x3E1A)
; Описание: Загрузка текущего score: индекс дорожки -> выбор записи из
;   data_music_scores (шаг 0x0F, цикл DCR B), установка var_music_track_ptr/
;   var_music_track_base, CALL 3888h (возврат в func_music_tick). Хвост 0x3E13
;   (SHLD/CALL/RET) — DEFB (пост-RET, в RDB не размечен).

func_music_load_score:
    MVI   A, 01h              ; 0x3DEB
    LXI   H, data_music_scores; 0x3DED
    ANA   A                   ; 0x3DF0
    CPI   00h                 ; 0x3DF1
    RZ                        ; 0x3DF3
    CPI   06h                 ; 0x3DF4
    RNC                       ; 0x3DF6
    DCR   A                   ; 0x3DF7
    CPI   00h                 ; 0x3DF8
    JZ    loc_3E0C            ; 0x3DFA
    MOV   B, A                ; 0x3DFD
    LXI   D, 030Fh            ; 0x3DFE
loc_3E01:
    DAD   D                   ; 0x3E01
    PUSH  PSW                 ; 0x3E02
    DCR   B                   ; 0x3E03
    JZ    loc_3E0B            ; 0x3E04
    POP   PSW                 ; 0x3E07
    JMP   loc_3E01            ; 0x3E08
loc_3E0B:
    POP   PSW                 ; 0x3E0B
loc_3E0C:
    SHLD  var_music_track_ptr ; 0x3E0C
    LXI   B, 000Fh            ; 0x3E0F
    DAD   B                   ; 0x3E12
    ; --- хвост 0x3E13..0x3E19 (SHLD/CALL/RET) ---
    DEFB 022h, 056h, 038h, 0CDh, 088h, 038h, 0C9h
