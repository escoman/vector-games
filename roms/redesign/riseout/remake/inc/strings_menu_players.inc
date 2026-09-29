; Текстовый регион вынесен из layout.asm дословно (адреса сохранены):
; строки + таблицы записей func_copy_record_entries/func_draw_text_records.
; Запись [x=08,y=0B,HOW MANY PLAYERS?..00] 0x2C89..0x2C9C; вызов MVI B,01 / LXI H,2C89 / CALL 2D1B @0x2C2C
data_records_players_count:
	defb	08h,0Bh

; Меню «HOW MANY PLAYERS?» (17+00); запись x=08,y=0B в data_records_players_count @0x2C89; рисует func @0x2C22 (lbl_2c22, вход по JZ из func_attract_menu_key_handler) через func_draw_text_records @0x2C31 (B=01)
str_menu_how_many_players:
	defb	48h,4Fh,57h,20h,4Dh,41h,4Eh,59h
	defb	20h,50h,4Ch,41h,59h,45h,52h,53h
	defb	3Fh,00h

; Меню «PLAYER» (6+00); печатается 4 раза в столбец: LXI D,0D0E; LXI H,2C9D; MVI B,04; цикл CALL func_draw_text_record_safe @0x2C3C с INR D INR D (шаг по строке +2); цифры игроков — func_put_char_glyph кодами 31..34 в 0x55AC
str_menu_player:
	defb	50h,4Ch,41h,59h,45h,52h,00h
