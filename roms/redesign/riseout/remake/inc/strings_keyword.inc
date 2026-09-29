; Текстовый регион вынесен из layout.asm дословно (адреса сохранены):
; строки + таблицы записей func_copy_record_entries/func_draw_text_records.
; Запись [x=0A,y=01,KEYWORD?..00] 0x16E3..0x16F2; вызов MVI B,01 / LXI H,16E3 / CALL 2D1B @0x1261 в func_probe_control_keys; размер = заголовок записи
data_records_keyword:
	defb	0Ah,01h

; Запрос ввода «KEYWORD?» с 5 пробелами (13+00); запись x=0A,y=01 в data_records_keyword @0x16E3; рисует func_probe_control_keys через func_draw_text_records @0x1261 (B=01), ввод читает func_read_keyword_input @0x1E05
str_prompt_keyword:
	defb	4Bh,45h,59h,57h,4Fh,52h,44h,3Fh
	defb	20h,20h,20h,20h,20h,00h
