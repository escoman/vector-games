; Данные: data_music_init
; Адрес: 0x383A
; Размер: 30 байт
; Описание: Инициализационный блоб музыкального секвенсора (RAM-скоуп зоны кода).
;           Жил verbatim-хвостом гэпа после упакованного шрифта; выделен в именованный
;           emit-файл для свободной конкатенации (Stage-4). Указатели потоков нот —
;           символьные DEFW на вышележащие таблицы (data_music_track_01 / data_music_scores),
;           поэтому переносится без побайтовой патч-машинery (POINTER_SITES).
;           Имена якорей (var_music_tick / var_music_stream_base_0N / data_voice_param_buf /
;           var_music_track_ptr/base) — EQU в var_reloc_anchors.asm, численно = адрес в этом блоке.
data_music_init:
    DEFB 04h, 028h, 028h, 028h, 020h            ; 0x383A tick/ptr-иниты (var_music_tick, ptr_01..03)
    DEFW data_music_track_01                    ; 0x383F stream_base_01 -> 3E29h
    DEFW data_music_track_01+00A0h              ; 0x3841 stream_base_02 -> 3EC9h
    DEFW data_music_track_01+0140h              ; 0x3843 stream_base_03 -> 3F69h
    DEFB 07Fh, 00h, 0FDh, 00h, 0C3h, 01h, 01Fh, 069h ; 0x3845 data_voice_param_buf (инит)
    DEFB 0Fh, 00h, 00h, 00h, 03h, 02h, 038h          ; 0x384D ..0x3853 (до data_voice_param_buf_end)
    DEFW data_music_scores                      ; 0x3854 var_music_track_ptr -> 3E1Ah
    DEFW data_music_track_01                    ; 0x3856 var_music_track_base -> 3E29h
