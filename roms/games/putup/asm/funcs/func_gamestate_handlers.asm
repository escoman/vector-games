; Функция: func_gamestate_handlers
; Адрес: 0x1252
; Размер: 184 байт (0x1252-0x1309, непрерывное тело)
; Описание: Обработчики исходов кадра (3 входа из func_game_update):
;   0x1252 пойманное яйцо (продвижение), 0x12B3 game_state==1 (ловушка),
;   0x12F6 game_state==2 (уклонение). 0x1296 — site релокации textbuf (500Ah).

func_egg_caught:
    LXI   H, 00E0h            ; 0x1252  переставить курсор скана мигания
    SHLD  var_blink_cell      ; 0x1255
    MVI   A, TIME_BAR_HURRYUP ; 0x1258  укоротить шкалу TIME (с 10h до 07h)
    STA   var_time_bar_ticks  ; 0x125A
    CALL  func_draw_status_hud; 0x125D
    CALL  func_prng           ; 0x1260
    ANI   03h                 ; 0x1263
    ADI   0Ah                 ; 0x1265
    STA   var_egg_slot        ; 0x1267
    MOV   L, A                ; 0x126A
    MVI   H, 0000h            ; 0x126B
    DAD   H                   ; 0x126D
    DAD   H                   ; 0x126E
    LDA   data_entity_xcoords+1; 0x126F
    MOV   D, A                ; 0x1272
    LDA   data_entity_ycoords+1; 0x1273
    MOV   E, A                ; 0x1276
    LXI   B, data_tile_2706   ; 0x1277
    DAD   B                   ; 0x127A
    PUSH  H                   ; 0x127B
    CALL  func_draw_tile_to_buf; 0x127C
    POP   H                   ; 0x127F
    LDA   data_entity_xcoords+2; 0x1280
    MOV   D, A                ; 0x1283
    LDA   data_entity_ycoords+2; 0x1284
    MOV   E, A                ; 0x1287
    CALL  func_draw_tile_to_buf; 0x1288
    LDA   var_player_col      ; 0x128B
    STA   data_entity_xcoords+1; 0x128E
    MVI   A, 023h             ; 0x1291
    STA   data_entity_ycoords+1; 0x1293
    LXI   H, data_text_buffer+000Ah; 0x1296
    CALL  func_set_text_ptr   ; 0x1299
    LXI   H, str_hurry_up      ; 0x129C
    CALL  func_print_string   ; 0x129F
    MVI   B, 0008h            ; 0x12A2
    CALL  func_sound_init     ; 0x12A4
    MVI   A, 09h              ; 0x12A7
    STA   var_entity1_state   ; 0x12A9
    INR   A                   ; 0x12AC
    STA   var_entity2_state   ; 0x12AD
    JMP   loc_0E4A            ; 0x12B0
func_gamestate_catch:
    LXI   H, var_player_row   ; 0x12B3
    DCR   M                   ; 0x12B6
    MOV   E, M                ; 0x12B7
    LDA   var_player_col      ; 0x12B8
    MOV   D, A                ; 0x12BB
    CALL  func_coords_to_textbuf; 0x12BC
    SHLD  var_player_bufaddr  ; 0x12BF
    LHLD  var_player_bufaddr  ; 0x12C2
    MOV   A, M                ; 0x12C5
    CPI   077h                ; 0x12C6
    JNC   loc_12D2            ; 0x12C8
    INX   H                   ; 0x12CB
    MOV   A, M                ; 0x12CC
    CPI   077h                ; 0x12CD
    JC    loc_12E0            ; 0x12CF
loc_12D2:
    XRA   A                   ; 0x12D2
    STA   var_game_state                ; 0x12D3
    STA   var_scr_0906                ; 0x12D6
    LXI   H, var_player_row   ; 0x12D9
    INR   M                   ; 0x12DC
    JMP   loc_0D41            ; 0x12DD
loc_12E0:
    LXI   H, var_scr_0906             ; 0x12E0
    INR   M                   ; 0x12E3
    MOV   A, M                ; 0x12E4
    CPI   04h                 ; 0x12E5
    JC    loc_12F3            ; 0x12E7
    XRA   A                   ; 0x12EA
    STA   var_scr_0906                ; 0x12EB
    MVI   A, GAME_STATE_EVADE ; 0x12EE  = 2: счётчик доехал -> режим evade
    STA   var_game_state                ; 0x12F0
loc_12F3:
    JMP   loc_0D41            ; 0x12F3
func_gamestate_evade:
    LXI   H, var_scr_0906             ; 0x12F6
    INR   M                   ; 0x12F9
    MOV   A, M                ; 0x12FA
    CPI   03h                 ; 0x12FB
    JC    loc_1307            ; 0x12FD
    XRA   A                   ; 0x1300
    STA   var_scr_0906                ; 0x1301
    STA   var_game_state                ; 0x1304
loc_1307:
    JMP   loc_0D41            ; 0x1307
