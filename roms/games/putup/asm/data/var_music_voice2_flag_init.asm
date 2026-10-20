; Данные: var_music_voice2_flag_init
; Адрес: 0x3BC8
; Размер: 2 байт
; Описание: Иниц. 2 байта RAM-переменных var_music_voice2_flag(0x3BC8)+var_pad_3BC9(0x3BC9): байты инициализации флага голоса 2 (значения 35h/29h в ROM-образе).
;           Имена var_music_voice2_flag / _hi — РЕАЛЬНЫЕ метки на байтах (были EQU в
;           var_reloc_anchors.asm; на Stage-4 переведены в метки, чтобы ехали за блоком).
var_music_voice2_flag_init:
var_music_voice2_flag:     DEFB 035h   ; 0x3BC8
var_music_voice2_flag_hi:  DEFB 029h   ; 0x3BC9
