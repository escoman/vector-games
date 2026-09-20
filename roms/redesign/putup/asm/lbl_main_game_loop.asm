; Метка: lbl_main_game_loop
; Адрес: 0x0E85
; Размер: 114 байт (0x0E85-0x0EF6)
; Описание: Главный игровой цикл. Проход по сущностям 1..3 (BC=1..3):
;           var_entity_index=C; HL=0919h+index -> A=состояние сущности;
;           диспетчер CZ по состоянию 1..10 -> func_entity_state1..10.
;           После обхода: CALL func_game_update (кадровое обновление);
;           MVI B,02h; CALL func_delay (пауза); INX B; пока C<3 (JC loc_0E88).
;           Затем обмен var_page_flip <-> 08FAh (переключение экранной страницы)
;           и JMP lbl_main_game_loop (бесконечный цикл). Fall-through сюда из
;           func_game_update (0x0E84).

lbl_main_game_loop:
    LXI B, 0001h                ; 0x0E85
loc_0E88:
    PUSH B                      ; 0x0E88
    MOV A, C                    ; 0x0E89
    STA var_entity_index        ; 0x0E8A
    LXI H, 0919h                ; 0x0E8D
    DAD B                       ; 0x0E90
    MOV A, M                    ; 0x0E91
    CPI 01h                     ; 0x0E92
    PUSH PSW                    ; 0x0E94
    CZ func_entity_state1       ; 0x0E95
    POP PSW                     ; 0x0E98
    CPI 02h                     ; 0x0E99
    PUSH PSW                    ; 0x0E9B
    CZ func_entity_state2       ; 0x0E9C
    POP PSW                     ; 0x0E9F
    CPI 03h                     ; 0x0EA0
    PUSH PSW                    ; 0x0EA2
    CZ func_entity_state3       ; 0x0EA3
    POP PSW                     ; 0x0EA6
    CPI 04h                     ; 0x0EA7
    PUSH PSW                    ; 0x0EA9
    CZ func_entity_state4       ; 0x0EAA
    POP PSW                     ; 0x0EAD
    CPI 05h                     ; 0x0EAE
    PUSH PSW                    ; 0x0EB0
    CZ func_entity_state5       ; 0x0EB1
    POP PSW                     ; 0x0EB4
    CPI 06h                     ; 0x0EB5
    PUSH PSW                    ; 0x0EB7
    CZ func_entity_state6       ; 0x0EB8
    POP PSW                     ; 0x0EBB
    CPI 07h                     ; 0x0EBC
    PUSH PSW                    ; 0x0EBE
    CZ func_entity_state7       ; 0x0EBF
    POP PSW                     ; 0x0EC2
    CPI 08h                     ; 0x0EC3
    PUSH PSW                    ; 0x0EC5
    CZ func_entity_state8       ; 0x0EC6
    POP PSW                     ; 0x0EC9
    CPI 09h                     ; 0x0ECA
    PUSH PSW                    ; 0x0ECC
    CZ func_entity_state9       ; 0x0ECD
    POP PSW                     ; 0x0ED0
    CPI 0Ah                     ; 0x0ED1
    CZ func_entity_state10      ; 0x0ED3
    CALL func_game_update       ; 0x0ED6
    MVI B, 02h                  ; 0x0ED9
    CALL func_delay             ; 0x0EDB
    POP B                       ; 0x0EDE
    INX B                       ; 0x0EDF
    MOV A, C                    ; 0x0EE0
    CPI 03h                     ; 0x0EE1
    JC loc_0E88                 ; 0x0EE3
    LDA var_page_flip           ; 0x0EE6
    MOV B, A                    ; 0x0EE9
    LDA 08FAh                   ; 0x0EEA
    STA var_page_flip           ; 0x0EED
    MOV A, B                    ; 0x0EF0
    STA 08FAh                   ; 0x0EF1
    JMP lbl_main_game_loop      ; 0x0EF4
