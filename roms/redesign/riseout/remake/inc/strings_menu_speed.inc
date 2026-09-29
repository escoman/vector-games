; Текстовый регион вынесен из layout.asm дословно (адреса сохранены):
; строки + таблицы записей func_copy_record_entries/func_draw_text_records.
; Таблица записей меню скорости 0x2CDB..0x2D14: 5 записей [x,y,текст..00], первая x=08,y=0B; вызов MVI B,05 / LXI H,2CDB / CALL 2D1B @0x2CA7
data_records_speed_menu:
	defb	08h,0Bh

; Меню «SELECT SPEED LEVEL» (18+00); запись x=08,y=0B в data_records_speed_menu @0x2CDB; рисует func @0x2CA4 (lbl_2ca4) через func_draw_text_records @0x2CAC (B=05)
str_menu_select_speed:
	defb	53h,45h,4Ch,45h,43h,54h,20h,53h
	defb	50h,45h,45h,44h,20h,4Ch,45h,56h
	defb	45h,4Ch,00h

; Uncovered ROM bytes — neither code nor an RDB object
gap_2CF0:
	defb	0Ah,0Dh

; Меню «^ PLAYER^1 ^» (12+00); запись x=0A,y=0D в data_records_speed_menu; символ ^ (0x5E) — обычный глиф, не управляющий маркер
str_menu_player_one:
	defb	5Eh,20h,50h,4Ch,41h,59h,45h,52h
	defb	5Eh,31h,20h,5Eh,00h

; Uncovered ROM bytes — neither code nor an RDB object
gap_2CFF:
	defb	0Bh,0Fh

; Меню «LOW» (3+00); запись x=0B,y=0F в data_records_speed_menu @0x2CDB
str_menu_low:
	defb	4Ch,4Fh,57h,00h

; Uncovered ROM bytes — neither code nor an RDB object
gap_2D05:
	defb	0Bh,11h

; Меню «NORMAL» (6+00); запись x=0B,y=11 в data_records_speed_menu @0x2CDB
str_menu_normal:
	defb	4Eh,4Fh,52h,4Dh,41h,4Ch,00h

; Uncovered ROM bytes — neither code nor an RDB object
gap_2D0E:
	defb	0Bh,13h

; Меню «HIGH» (4+00); запись x=0B,y=13 в data_records_speed_menu @0x2CDB
str_menu_high:
	defb	48h,49h,47h,48h,00h

; Меню «SPEED» (5+00); печатается 3 раза: LXI D,0F12; LXI H,2D15; MVI B,03; цикл CALL func_draw_text_record_safe @0x2CB7 (шаг по строке +2)
str_menu_speed:
	defb	53h,50h,45h,45h,44h,00h
