; Данные: data_music_init
; Адрес: 0x383A
; Размер: 30 байт
; Описание: Инициализационный блоб музыкального секвенсора (RAM-скоуп зоны кода).
;           Жил verbatim-хвостом гэпа после упакованного шрифта; выделен в именованный
;           emit-файл для свободной конкатенации (Stage-4). Указатели потоков нот —
;           символьные DEFW на вышележащие таблицы (data_music_track_01 / data_music_scores),
;           поэтому переносится без побайтовой патч-машинery (POINTER_SITES).
;           Имена якорей (var_music_tick / var_music_stream_base_0N / data_voice_param_buf /
;           var_music_track_ptr/base) — РЕАЛЬНЫЕ метки на байтах этого блока (были EQU в
;           var_reloc_anchors.asm; на Stage-4 переведены в метки, чтобы ехали за блоком).
data_music_init:
var_music_tick:            DEFB 04h                       ; 0x383A
var_music_ptr_01:          DEFB 028h                      ; 0x383B
var_music_ptr_02:          DEFB 028h                      ; 0x383C
var_music_ptr_03:          DEFB 028h                      ; 0x383D
                           DEFB 020h                      ; 0x383E
var_music_stream_base_01:  DEFW data_music_track_01       ; 0x383F -> 3E29h
var_music_stream_base_02:  DEFW data_music_track_01+00A0h ; 0x3841 -> 3EC9h
var_music_stream_base_03:  DEFW data_music_track_01+0140h ; 0x3843 -> 3F69h
data_voice_param_buf:      DEFB 07Fh, 00h, 0FDh, 00h, 0C3h, 01h, 01Fh, 069h ; 0x3845..0x384C (инит)
                           DEFB 0Fh, 00h, 00h, 00h, 03h, 02h ; 0x384D..0x3852
                           DEFB 038h                      ; 0x3853 (конец voice_param-инита)
var_music_track_ptr:       DEFW data_music_scores         ; 0x3854 -> 3E1Ah
var_music_track_base:      DEFW data_music_track_01       ; 0x3856 -> 3E29h
