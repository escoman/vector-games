; Текстовый регион вынесен из layout.asm дословно (адреса сохранены):
; строки + таблицы записей func_copy_record_entries/func_draw_text_records.
; Строка статуса «SCORE: 00 MEN: 5 LEVEL: 1» (28+00, лежит в потоке кода после RET @0x24B1); рисуется напрямую: LXI H,24B2; LXI D,0002; CALL func_draw_text_record @0x249E в func_init_title_screen; значения позже затираются побайтово
str_hud_status:
	defb	53h,43h,4Fh,52h,45h,3Ah,20h,20h
	defb	20h,20h,30h,30h,20h,4Dh,45h,4Eh
	defb	3Ah,20h,35h,20h,4Ch,45h,56h,45h
	defb	4Ch,3Ah,20h,31h,00h
