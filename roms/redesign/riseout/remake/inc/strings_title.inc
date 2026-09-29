; Текстовый регион вынесен из layout.asm дословно (адреса сохранены):
; строки + таблицы записей func_copy_record_entries/func_draw_text_records.
; Таблица записей заставки 0x2B8B..0x2C03: 7 записей формата [x,y,текст..00]; размер = заголовок первой записи x=0A,y=08; вызов MVI B,07 / LXI H,2B8B / CALL 2D1B @0x2B61
data_title_records:
	defb	0Ah,08h

; Титул заставки «FROM DUNGEONS» (13+00); запись x=0A,y=08 в data_title_records @0x2B8B; рисует func_attract_draw_title через func_draw_text_records @0x2B66
str_title_from_dungeons:
	defb	46h,52h,4Fh,4Dh,20h,44h,55h,4Eh
	defb	47h,45h,4Fh,4Eh,53h,00h

; Uncovered ROM bytes — neither code nor an RDB object
gap_2B9B:
	defb	05h,0Bh

; Титул заставки «HIT BUTTON OR SPACE KEY» (23+00); запись x=05,y=0B в data_title_records; рисует func_attract_draw_title через func_draw_text_records @0x2B66
str_title_hit_button:
	defb	48h,49h,54h,20h,42h,55h,54h,54h
	defb	4Fh,4Eh,20h,4Fh,52h,20h,53h,50h
	defb	41h,43h,45h,20h,4Bh,45h,59h,00h

; Uncovered ROM bytes — neither code nor an RDB object
gap_2BB5:
	defb	09h,0Eh

; Титул заставки «UP TO 4 PLAYERS» (15+00); запись x=09,y=0E в data_title_records; рисует func_attract_draw_title через func_draw_text_records @0x2B66
str_title_up_to_players:
	defb	55h,50h,20h,54h,4Fh,20h,34h,20h
	defb	50h,4Ch,41h,59h,45h,52h,53h,00h

; Uncovered ROM bytes — neither code nor an RDB object
gap_2BC7:
	defb	0Fh,10h

; Титул заставки «AND» (3+00); запись x=0F,y=10 в data_title_records; рисует func_attract_draw_title через func_draw_text_records @0x2B66
str_title_and:
	defb	41h,4Eh,44h,00h

; Uncovered ROM bytes — neither code nor an RDB object
gap_2BCD:
	defb	0Ah,12h

; Титул заставки «3 SPEED LEVEL» (13+00); запись x=0A,y=12 в data_title_records; рисует func_attract_draw_title через func_draw_text_records @0x2B66
str_title_speed_level:
	defb	33h,20h,53h,50h,45h,45h,44h,20h
	defb	4Ch,45h,56h,45h,4Ch,00h

; Uncovered ROM bytes — neither code nor an RDB object
gap_2BDD:
	defb	11h,15h

; Титульная строка служебных знаков: коды 0B 0C 0D 0E 0F +00 (5 глифов); запись x=11,y=15 в data_title_records; глифы из data_glyph_block @0x316C; рисует func_attract_draw_title
str_title_symbol_row:
	defb	0Bh,0Ch,0Dh,0Eh,0Fh,00h

; Uncovered ROM bytes — neither code nor an RDB object
gap_2BE5:
	defb	02h,16h

; Титул COPYRIGHT 1983 + коды +,-./, и 01..06 (28+00); запись x=02,y=16 в data_title_records; глифы 01..06 лежат в data_glyph_block по формуле 0x3114+8*код (0x311C..0x314B); рисует func_attract_draw_title
str_title_copyright:
	defb	43h,4Fh,50h,59h,52h,49h,47h,48h
	defb	54h,20h,31h,39h,38h,33h,20h,2Bh
	defb	2Ch,2Dh,2Eh,2Fh,3Ch,20h,01h,02h
	defb	03h,04h,05h,06h,00h

; Коды глифов кредит-полосы E0..FD (30 байт); две строки по 15 глифов в текстовые позиции 0x5709 и 0x5729, цикл MVI B,0F / LDAX D / CALL 0551 в func_attract_draw_title @0x2B69
data_logo_strip_codes:
	defb	0E0h,0E1h,0E2h,0E3h,0E4h,0E5h,0E6h,0E7h
	defb	0E8h,0E9h,0EAh,0EBh,0ECh,0EDh,0EEh,0EFh
	defb	0F0h,0F1h,0F2h,0F3h,0F4h,0F5h,0F6h,0F7h
	defb	0F8h,0F9h,0FAh,0FBh,0FCh,0FDh
