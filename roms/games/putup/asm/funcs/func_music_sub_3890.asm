; Функция: func_music_sub_3890
; Адрес: 0x3890
; Размер: 114 байт
; Описание: Подпрограмма смены нот (вызывается из func_music_tick по CZ при
;           var_music_tick==0). Для трёх каналов сверяет байт длительности из
;           текущей позиции трека (var_music_track_ptr -> var_music_work_ptr) с
;           счётчиками потока var_music_ptr_01/02/03; при истечении обнуляет
;           счётчик. Затем вызывает func_music_process_voice и инкрементирует все
;           три счётчика потока. Живёт в гэп-зоне между именованными объектами;
;           Фаза 2 промоутила её в именованный слот, чтобы все abs-ссылки
;           (var_music_*, func_music_process_voice) стали символичными и
;           переехали при релокации.

func_music_sub_3890:
    PUSH H                      ; 0x3890
    LHLD var_music_track_ptr    ; 0x3891
    SHLD var_music_work_ptr     ; 0x3894
    POP H                       ; 0x3897
    PUSH H                      ; 0x3898
    LHLD var_music_work_ptr     ; 0x3899
    INX H                       ; 0x389C
    INX H                       ; 0x389D
    INX H                       ; 0x389E
    INX H                       ; 0x389F
    INX H                       ; 0x38A0
    INX H                       ; 0x38A1
    MOV A, M                    ; 0x38A2
    POP H                       ; 0x38A3
    MOV B, A                    ; 0x38A4
    LDA var_music_ptr_01        ; 0x38A5
    ANA A                       ; 0x38A8
    CMP B                       ; 0x38A9
    JC loc_38B2                 ; 0x38AA
    MVI A, 00h                  ; 0x38AD
    STA var_music_ptr_01        ; 0x38AF
loc_38B2:
    PUSH H                      ; 0x38B2
    LHLD var_music_work_ptr     ; 0x38B3
    INX H                       ; 0x38B6
    INX H                       ; 0x38B7
    INX H                       ; 0x38B8
    INX H                       ; 0x38B9
    INX H                       ; 0x38BA
    INX H                       ; 0x38BB
    INX H                       ; 0x38BC
    MOV A, M                    ; 0x38BD
    POP H                       ; 0x38BE
    MOV B, A                    ; 0x38BF
    LDA var_music_ptr_02        ; 0x38C0
    ANA A                       ; 0x38C3
    CMP B                       ; 0x38C4
    JC loc_38CD                 ; 0x38C5
    MVI A, 00h                  ; 0x38C8
    STA var_music_ptr_02        ; 0x38CA
loc_38CD:
    PUSH H                      ; 0x38CD
    LHLD var_music_work_ptr     ; 0x38CE
    INX H                       ; 0x38D1
    INX H                       ; 0x38D2
    INX H                       ; 0x38D3
    INX H                       ; 0x38D4
    INX H                       ; 0x38D5
    INX H                       ; 0x38D6
    INX H                       ; 0x38D7
    INX H                       ; 0x38D8
    MOV A, M                    ; 0x38D9
    POP H                       ; 0x38DA
    MOV B, A                    ; 0x38DB
    LDA var_music_ptr_03        ; 0x38DC
    ANA A                       ; 0x38DF
    CMP B                       ; 0x38E0
    JC loc_38E9                 ; 0x38E1
    MVI A, 00h                  ; 0x38E4
    STA var_music_ptr_03        ; 0x38E6
loc_38E9:
    CALL func_music_process_voice ; 0x38E9
    LDA var_music_ptr_01        ; 0x38EC
    INR A                       ; 0x38EF
    STA var_music_ptr_01        ; 0x38F0
    LDA var_music_ptr_02        ; 0x38F3
    INR A                       ; 0x38F6
    STA var_music_ptr_02        ; 0x38F7
    LDA var_music_ptr_03        ; 0x38FA
    INR A                       ; 0x38FD
    STA var_music_ptr_03        ; 0x38FE
    RET                         ; 0x3901
