; Функция: func_game_update_handlers
; Адрес: 0x0F39
; Размер: 490 байт (0x0F39-0x1122, непрерывное тело)
; Описание: Обработчики событий кадра движка (6 точек входа из func_game_update:
;   0x0F39 сбор бонуса, 0x0F63 таймер бонуса, 0x0F6D/0x0FD4/0x1017/0x1042
;   движение игрока и коллизии). Возврат в func_score_and_redraw (0F25/0F28)
;   и в общий перерисов loc_0D68 game_update.

func_item_bonus_collect:
    LHLD  var_score           ; 0x0F39
    LXI   B, 0064h            ; 0x0F3C
    DAD   B                   ; 0x0F3F
    SHLD  var_score           ; 0x0F40
    LXI   H, var_egg_counter  ; 0x0F43
    INR   M                   ; 0x0F46
    MOV   A, M                ; 0x0F47
    RLC                       ; 0x0F48
    ADI   017h                ; 0x0F49
    STA   var_draw_row        ; 0x0F4B
    MVI   A, 018h             ; 0x0F4E
    STA   var_draw_col        ; 0x0F50
    CALL  func_restore_cursor ; 0x0F53
    MVI   A, 072h             ; 0x0F56
    CALL  func_print_char_at_ptr; 0x0F58
    MVI   A, 06Dh             ; 0x0F5B
    CALL  func_print_char_at_ptr; 0x0F5D
    JMP   loc_0F25            ; 0x0F60
func_item_bonus_timer:
    LXI   H, var_bonus_counter; 0x0F63
    INR   M                   ; 0x0F66
    CALL  func_play_sfx       ; 0x0F67
    JMP   loc_0F28            ; 0x0F6A
func_player_move_a:
    MVI   A, 06h              ; 0x0F6D
    STA   var_obj_type_idx    ; 0x0F6F
    LXI   H, var_enemy_rc     ; 0x0F72
    LDA   var_player_row      ; 0x0F75
    CMP   M                   ; 0x0F78
    JNZ   loc_0F85            ; 0x0F79
    INX   H                   ; 0x0F7C
    LDA   var_player_col      ; 0x0F7D
    CMP   M                   ; 0x0F80
    DCX   H                   ; 0x0F81
    JZ    loc_0F88            ; 0x0F82
loc_0F85:
    CALL  func_draw_tile_at_ptr; 0x0F85
loc_0F88:
    LDA   var_player_row      ; 0x0F88
    MOV   L, A                ; 0x0F8B
    LDA   var_player_col      ; 0x0F8C
    MOV   H, A                ; 0x0F8F
    SHLD  var_enemy_rc        ; 0x0F90
    XCHG                      ; 0x0F93
    LDA   var_obj_type_idx    ; 0x0F94
    ADD   A                   ; 0x0F97
    ADD   A                   ; 0x0F98
    LXI   H, data_tile_table_26DE; 0x0F99
    CALL  func_hl_add_a       ; 0x0F9C
    CALL  func_render_tile_vram; 0x0F9F
loc_0FA2:
    LHLD  var_blink_cell      ; 0x0FA2
    INX   H                   ; 0x0FA5
    MOV   A, L                ; 0x0FA6
    ANI   01Fh                ; 0x0FA7
    SHLD  var_blink_cell      ; 0x0FA9
    JNZ   loc_0FD1            ; 0x0FAC
    MVI   B, 0002h            ; 0x0FAF
    CALL  func_sound_init     ; 0x0FB1
    CALL  func_erase_char_08E9; 0x0FB4
    ; Пауза на шарик = ВРЕМЯ АНИМАЦИИ, а не звука. В оригинале итерация стоила
    ; func_delay(2) внутри блокирующего func_sound_init + func_delay(1) здесь,
    ; т.е. 3 единицы (~7.5 кадров). После перехода на async-SFX звук больше не
    ; держит цикл, поэтому его доля паузы переехала сюда: B=3 сохраняет прежний
    ; темп пересчёта очков за оставшееся время (шарики исчезают не мгновенно).
    MVI   B, 0003h            ; 0x0FB7 (было 0001h)
    CALL  func_delay          ; 0x0FB9
    LHLD  var_score           ; 0x0FBC
    LXI   B, 000Ah            ; 0x0FBF
    DAD   B                   ; 0x0FC2
    SHLD  var_score           ; 0x0FC3
    CALL  func_draw_score_hud ; 0x0FC6
    LDA   var_blink_type      ; 0x0FC9
    CPI   02h                 ; 0x0FCC
    JZ    func_level_loader   ; 0x0FCE
loc_0FD1:
    JMP   loc_0FA2            ; 0x0FD1
func_player_move_b:
    LXI   H, var_player_col   ; 0x0FD4
    INR   M                   ; 0x0FD7
    XRA   A                   ; 0x0FD8
    STA   var_move_dir        ; 0x0FD9
    MOV   D, M                ; 0x0FDC
    LDA   var_player_row      ; 0x0FDD
    MOV   E, A                ; 0x0FE0
    CALL  func_coords_to_textbuf; 0x0FE1
    SHLD  var_player_bufaddr  ; 0x0FE4
    INX   H                   ; 0x0FE7
    MOV   A, M                ; 0x0FE8
    CPI   077h                ; 0x0FE9
    JNC   loc_0FF8            ; 0x0FEB
    LXI   B, 0020h            ; 0x0FEE
    DAD   B                   ; 0x0FF1
    MOV   A, M                ; 0x0FF2
    CPI   077h                ; 0x0FF3
    JC    loc_0FFC            ; 0x0FF5
loc_0FF8:
    LXI   H, var_player_col   ; 0x0FF8
    DCR   M                   ; 0x0FFB
loc_0FFC:
    LDA   var_egg_hist_cur    ; 0x0FFC
    MOV   B, A                ; 0x0FFF
    LDA   var_egg_hist_prev   ; 0x1000
    STA   var_egg_hist_cur    ; 0x1003
    MOV   A, B                ; 0x1006
    STA   var_egg_hist_prev   ; 0x1007
    ORA   A                   ; 0x100A
    JNZ   loc_0D68            ; 0x100B
    LDA   var_page_flip       ; 0x100E
    STA   var_work_const      ; 0x1011
    JMP   loc_0D6D            ; 0x1014
func_player_move_c:
    LXI   H, var_player_col   ; 0x1017
    DCR   M                   ; 0x101A
    MVI   A, 01h              ; 0x101B
    STA   var_move_dir        ; 0x101D
    MOV   D, M                ; 0x1020
    LDA   var_player_row      ; 0x1021
    MOV   E, A                ; 0x1024
    CALL  func_coords_to_textbuf; 0x1025
    SHLD  var_player_bufaddr  ; 0x1028
    MOV   A, M                ; 0x102B
    CPI   077h                ; 0x102C
    JNC   loc_103B            ; 0x102E
    LXI   B, 0020h            ; 0x1031
    DAD   B                   ; 0x1034
    MOV   A, M                ; 0x1035
    CPI   077h                ; 0x1036
    JC    loc_103F            ; 0x1038
loc_103B:
    LXI   H, var_player_col   ; 0x103B
    INR   M                   ; 0x103E
loc_103F:
    JMP   loc_0FFC            ; 0x103F
func_player_move_d:
    LHLD  var_player_row      ; 0x1042
    XCHG                      ; 0x1045
    CALL  func_coords_to_textbuf; 0x1046
    SHLD  var_player_bufaddr  ; 0x1049
    LXI   B, 0040h            ; 0x104C
    DAD   B                   ; 0x104F
    MOV   A, M                ; 0x1050
    CPI   07Eh                ; 0x1051
    JZ    loc_111A            ; 0x1053
    CPI   07Dh                ; 0x1056
    JZ    loc_1188            ; 0x1058
    LDA   var_egg_counter     ; 0x105B
    CPI   01h                 ; 0x105E
    JZ    loc_106B            ; 0x1060
    CPI   02h                 ; 0x1063
    JZ    loc_106B            ; 0x1065
    JMP   loc_0D68            ; 0x1068
loc_106B:
    LHLD  var_player_bufaddr  ; 0x106B
    LXI   B, 0040h            ; 0x106E
    DAD   B                   ; 0x1071
    MOV   A, M                ; 0x1072
    CPI   079h                ; 0x1073
    JNZ   loc_0D68            ; 0x1075
    MVI   B, 0005h            ; 0x1078
    CALL  func_sound_init     ; 0x107A
    LDA   var_player_col      ; 0x107D
    STA   var_draw_row        ; 0x1080
    LDA   var_player_row      ; 0x1083
    ADI   02h                 ; 0x1086
    STA   var_draw_col        ; 0x1088
    CALL  func_restore_cursor ; 0x108B
    MVI   A, 07Bh             ; 0x108E
    CALL  func_print_char_at_ptr; 0x1090
    MVI   A, 07Ch             ; 0x1093
    CALL  func_print_char_at_ptr; 0x1095
    LDA   var_egg_counter     ; 0x1098
    DCR   A                   ; 0x109B
    STA   var_egg_counter     ; 0x109C
    RLC                       ; 0x109F
    ADI   019h                ; 0x10A0
    STA   var_draw_row        ; 0x10A2
    MVI   A, 018h             ; 0x10A5
    STA   var_draw_col        ; 0x10A7
    CALL  func_restore_cursor ; 0x10AA
    MVI   A, 020h             ; 0x10AD
    CALL  func_print_char_at_ptr; 0x10AF
    CALL  func_print_char_at_ptr; 0x10B2
    LDA   var_egg_seq         ; 0x10B5
    INR   A                   ; 0x10B8
    STA   var_egg_seq         ; 0x10B9
    LDA   var_level           ; 0x10BC
    CPI   0Ah                 ; 0x10BF
    MVI   B, 0001h            ; 0x10C1
    JC    loc_10C8            ; 0x10C3
    MVI   B, 0002h            ; 0x10C6
loc_10C8:
    LDA   var_egg_seq         ; 0x10C8
    CMP   B                   ; 0x10CB
    JNZ   loc_0D68            ; 0x10CC
    LDA   data_level_param_buf; 0x10CF
    MOV   D, A                ; 0x10D2
    LDA   data_level_param_buf+1; 0x10D3
    MOV   E, A                ; 0x10D6
    LXI   H, data_tile_272A   ; 0x10D7
    CALL  func_draw_tile_to_buf; 0x10DA
    MVI   B, 0005h            ; 0x10DD
    CALL  func_sound_init     ; 0x10DF
    MVI   A, 07h              ; 0x10E2
    STA   var_obj_type_idx    ; 0x10E4
    LXI   H, var_bonus_rc     ; 0x10E7
    LDA   data_level_param_buf+1; 0x10EA
    CMP   M                   ; 0x10ED
    JNZ   loc_10FA            ; 0x10EE
    INX   H                   ; 0x10F1
    LDA   data_level_param_buf; 0x10F2
    CMP   M                   ; 0x10F5
    DCX   H                   ; 0x10F6
    JZ    loc_10FD            ; 0x10F7
loc_10FA:
    CALL  func_draw_tile_at_ptr; 0x10FA
loc_10FD:
    LDA   data_level_param_buf+1; 0x10FD
    MOV   L, A                ; 0x1100
    LDA   data_level_param_buf; 0x1101
    MOV   H, A                ; 0x1104
    SHLD  var_bonus_rc        ; 0x1105
    ; (Фаза 4) запомнить позицию выхода и включить мигание (скан в func_game_update)
    SHLD  var_exit_rc         ; lo=строка, hi=колонка — тот же кэш
    XRA   A
    STA   var_exit_phase      ; светлый нарисован, следующий проход — тёмный
    XCHG                      ; 0x1108
    LDA   var_obj_type_idx    ; 0x1109
    ADD   A                   ; 0x110C
    ADD   A                   ; 0x110D
    LXI   H, data_tile_table_26DE; 0x110E
    CALL  func_hl_add_a       ; 0x1111
    CALL  func_render_tile_vram; 0x1114
    JMP   loc_0D68            ; 0x1117
loc_111A:
    LHLD  var_player_row      ; 0x111A
    XCHG                      ; 0x111D
    INR   E                   ; 0x111E
    INR   E                   ; 0x111F
loc_1120:
    JMP   func_spawn_egg      ; 0x1120
