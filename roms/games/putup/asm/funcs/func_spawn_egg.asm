; Функция: func_spawn_egg
; Адрес: 0x1157
; Размер: 64 байт (0x1157-0x1196, непрерывное тело)
; Описание: Спавн яйца: CALL func_prng -> выбор колонки, отбор по чётности,
;   расчёт тайла из data_tile_2706/2716, CALL func_draw_tile_to_buf,
;   JMP loc_0D68 (перерис). Вход 0x1188 — вариант B. Retry via loc_1120.

func_spawn_egg:
    CALL  func_prng           ; 0x1157
    ANI   07h                 ; 0x115A
    CPI   05h                 ; 0x115C
    JNC   loc_1120            ; 0x115E
    STA   var_egg_slot        ; 0x1161
    LDA   var_egg_slot        ; 0x1164
    CPI   04h                 ; 0x1167
    JNZ   loc_1174            ; 0x1169
    CALL  func_prng           ; 0x116C
    ANI   01h                 ; 0x116F
    JNZ   loc_111A            ; 0x1171
loc_1174:
    LDA   var_egg_slot        ; 0x1174
    ADI   0Ah                 ; 0x1177
    MOV   L, A                ; 0x1179
    MVI   H, 0000h            ; 0x117A
    DAD   H                   ; 0x117C
    DAD   H                   ; 0x117D
    LXI   B, data_tile_2706   ; 0x117E
    DAD   B                   ; 0x1181
    CALL  func_draw_tile_to_buf; 0x1182
    JMP   loc_0D68            ; 0x1185
loc_1188:
    LHLD  var_player_row      ; 0x1188
    XCHG                      ; 0x118B
    INR   E                   ; 0x118C
    INR   E                   ; 0x118D
    LXI   H, data_tile_2716   ; 0x118E
    CALL  func_draw_tile_to_buf; 0x1191
    JMP   loc_0D68            ; 0x1194
