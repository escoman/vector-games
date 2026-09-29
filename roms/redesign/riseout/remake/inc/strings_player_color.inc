; Текстовый регион вынесен из layout.asm дословно (адреса сохранены):
; строки + таблицы записей func_copy_record_entries/func_draw_text_records.
; Запись [x=0D,y=01,D0 CC C1 D9 C5 D2 DE B1..00] 0x2029..0x2033: коды ASCII+0x80 дают глифы PLAYER^1; вызов MVI B,01 / LXI H,2029 / CALL 2D1B @0x2014 в func_start_new_level; размер = заголовок записи
data_records_player_color:
	defb	0Dh,01h

; «PLAYER^1» в цветном регистре: коды D0 CC C1 D9 C5 D2 DE B1 = ASCII+0x80 (9 с 00); запись x=0D,y=01 в data_records_player_color; глифы — копия шрифта в RAM 0x6400 (создаётся только игровым инициалом); рисует func_start_new_level через func_draw_text_records @0x2014
str_color_player_one:
	defb	0D0h,0CCh,0C1h,0D9h,0C5h,0D2h,0DEh,0B1h
	defb	00h
