; Таблица сообщений 0x1CE2..0x1DA5: 12 записей [dst_lo,dst_hi,len] + строка len байт.
; dst = ram_hud_buffer+смещение (строка HUD, шаг 0x20); len = метка_end-метка —
; пересчитывается ассемблером: при правке строки длина записи обновляется сама.
; Читатель — func_copy_record_entries @0x1E5D (код берёт записи через data_msg_rec_*).
; Таблица сообщений 0x1CE2..0x1DA5: 12 записей [dst_lo,dst_hi,len,текст], первая dst=0x7321 len=16; выбираются по одной через func_copy_record_entries @0x1E5D (например LXI H,1D13 / MVI B,01 / CALL 1E5D @0x1C47); размер = заголовок первой записи
; Запись 0: dst = ram_hud_buffer+021h
data_msg_records:
        defb    (ram_hud_buffer+021h)&0ffh,(ram_hud_buffer+021h)>>8,str_msg_level_complete_end-str_msg_level_complete
; Сообщение «^LEVEL COMPLETE^» (16, без 00, длина в записи); запись 0 в data_msg_records @0x1CE2, dst=0x7321; переносит func_copy_record_entries @0x1E5D
str_msg_level_complete:
        defb    5Eh,4Ch,45h,56h,45h,4Ch,20h,43h
        defb    4Fh,4Dh,50h,4Ch,45h,54h,45h,5Eh
str_msg_level_complete_end:

; Запись 1: dst = ram_hud_buffer+063h
data_msg_rec_bonus:
        defb    (ram_hud_buffer+063h)&0ffh,(ram_hud_buffer+063h)>>8,str_msg_bonus_end-str_msg_bonus
; Сообщение «BONUS: 000» (11, без 00); запись 1 в data_msg_records, dst=0x7363; разряды бонуса затираются кодом уровня; переносит func_copy_record_entries
str_msg_bonus:
        defb    42h,4Fh,4Eh,55h,53h,3Ah,20h,20h
        defb    30h,30h,30h
str_msg_bonus_end:

; Запись 2: dst = ram_hud_buffer+0A2h
data_msg_rec_next_scene:
        defb    (ram_hud_buffer+0A2h)&0ffh,(ram_hud_buffer+0A2h)>>8,str_msg_next_scene_end-str_msg_next_scene
; Сообщение «NEXT SCENE IS» (13, без 00); запись 2 в data_msg_records, dst=0x73A2; переносит func_copy_record_entries
str_msg_next_scene:
        defb    4Eh,45h,58h,54h,20h,53h,43h,45h
        defb    4Eh,45h,20h,49h,53h
str_msg_next_scene_end:

; Запись 3: dst = ram_hud_buffer+122h
data_msg_rec_keyword_label:
        defb    (ram_hud_buffer+122h)&0ffh,(ram_hud_buffer+122h)>>8,str_msg_keyword_label_end-str_msg_keyword_label
; Сообщение «KEYWORD:"» (9, без 00, кавычка — открывающая); запись 3 в data_msg_records, dst=0x7422; печатается 1 записью из 0x1D13 (@0x1C47, B=01)
str_msg_keyword_label:
        defb    4Bh,45h,59h,57h,4Fh,52h,44h,3Ah
        defb    22h
str_msg_keyword_label_end:

; Запись 4: dst = ram_hud_buffer+122h
data_msg_rec_good_luck:
        defb    (ram_hud_buffer+122h)&0ffh,(ram_hud_buffer+122h)>>8,str_msg_good_luck_end-str_msg_good_luck
; Сообщение «^ GOOD LUCK ^» (14, без 00); запись 4 в data_msg_records, dst=0x7422; печатается 1 записью из 0x1D1F (@0x1C6A, B=01)
str_msg_good_luck:
        defb    5Eh,20h,47h,4Fh,4Fh,44h,20h,20h
        defb    4Ch,55h,43h,4Bh,20h,5Eh
str_msg_good_luck_end:

; Запись 5: dst = ram_hud_buffer+021h
data_msg_rec_all_patterns:
        defb    (ram_hud_buffer+021h)&0ffh,(ram_hud_buffer+021h)>>8,str_msg_all_patterns_end-str_msg_all_patterns
; Сообщение «^ALL PATTERNS» (13, без 00); запись 5 в data_msg_records, dst=0x7321; склеивается на экране со str_msg_completed; входит в блок B=07 из 0x1D30 (@0x1C75)
str_msg_all_patterns:
        defb    5Eh,41h,4Ch,4Ch,20h,50h,41h,54h
        defb    54h,45h,52h,4Eh,53h
str_msg_all_patterns_end:

; Запись 6: dst = ram_hud_buffer+047h
data_msg_rec_completed:
        defb    (ram_hud_buffer+047h)&0ffh,(ram_hud_buffer+047h)>>8,str_msg_completed_end-str_msg_completed
; Сообщение «COMPLETED^» (10, без 00, длина в записи); запись 6 в data_msg_records @0x1CE2, dst=0x7347; склеивается на экране со str_msg_all_patterns; переносит func_copy_record_entries @0x1E5D (блок B=07 от 0x1D30)
str_msg_completed:
        defb    43h,4Fh,4Dh,50h,4Ch,45h,54h,45h
        defb    44h,5Eh
str_msg_completed_end:

; Запись 7: dst = ram_hud_buffer+081h
data_msg_rec_secret_keys:
        defb    (ram_hud_buffer+081h)&0ffh,(ram_hud_buffer+081h)>>8,str_msg_secret_keys_end-str_msg_secret_keys
; Сообщение «* SECRET KEYS *» (16, без 00); запись 7 в data_msg_records @0x1CE2, dst=0x7381; переносит func_copy_record_entries @0x1E5D в буфер сообщений
str_msg_secret_keys:
        defb    2Ah,20h,53h,45h,43h,52h,45h,54h
        defb    20h,4Bh,45h,59h,53h,20h,20h,2Ah
str_msg_secret_keys_end:

; Запись 8: dst = ram_hud_buffer+0A1h
data_msg_rec_level_inc:
        defb    (ram_hud_buffer+0A1h)&0ffh,(ram_hud_buffer+0A1h)>>8,str_msg_level_inc_end-str_msg_level_inc
; Сообщение «LEVEL INC:CTRL^#» (16, без 00); запись 8 в data_msg_records @0x1CE2, dst=0x73A1; коды 23 и 01..06 — глифы символов из data_glyph_block, не управляющие байты
str_msg_level_inc:
        defb    4Ch,45h,56h,45h,4Ch,20h,49h,4Eh
        defb    43h,3Ah,43h,54h,52h,4Ch,5Eh,23h
str_msg_level_inc_end:

; Запись 9: dst = ram_hud_buffer+0C1h
data_msg_rec_men_inc:
        defb    (ram_hud_buffer+0C1h)&0ffh,(ram_hud_buffer+0C1h)>>8,str_msg_men_inc_end-str_msg_men_inc
; Сообщение «MEN INC:CTRL^» + код 22 (16, без 00); запись 9 в data_msg_records @0x1CE2, dst=0x73C1; переносит func_copy_record_entries @0x1E5D
str_msg_men_inc:
        defb    4Dh,45h,4Eh,20h,20h,20h,49h,4Eh
        defb    43h,3Ah,43h,54h,52h,4Ch,5Eh,22h
str_msg_men_inc_end:

; Запись 10: dst = ram_hud_buffer+102h
data_msg_rec_more_levels:
        defb    (ram_hud_buffer+102h)&0ffh,(ram_hud_buffer+102h)>>8,str_msg_more_levels_end-str_msg_more_levels
; Сообщение «MORE LEVELS IN» (14, без 00); запись 10 в data_msg_records @0x1CE2, dst=0x7402; переносит func_copy_record_entries @0x1E5D
str_msg_more_levels:
        defb    4Dh,4Fh,52h,45h,20h,4Ch,45h,56h
        defb    45h,4Ch,53h,20h,49h,4Eh
str_msg_more_levels_end:

; Запись 11: dst = ram_hud_buffer+123h
data_msg_rec_rise_out:
        defb    (ram_hud_buffer+123h)&0ffh,(ram_hud_buffer+123h)>>8,str_msg_rise_out_end-str_msg_rise_out
; Сообщение «RISE OUT^2!!» (12, без 00); запись 11 в data_msg_records @0x1CE2, dst=0x7423; завершает таблицу (следующий байт E5 уже не запись); TZ cite RISE OUT^2!! @0x1C9A = смещение, реальный адрес 0x1D9A
str_msg_rise_out:
        defb    52h,49h,53h,45h,20h,4Fh,55h,54h
        defb    5Eh,32h,21h,21h
str_msg_rise_out_end:

