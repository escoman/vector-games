; passwords.inc — B-viewStage 9 (только чтение).
; Источник: data/data.asm (v06c-asm-export). Байты дословно из RDB-объектов,
; без переформатирования. В сборку НЕ включается: main.asm знает только
; layout.asm (Stage 6.23 §2.2). Список объектов и их комментарии — в RDB
; (cybernoid_unpacked.rdb); здесь — только human-readable срез по классу.
; Покрытые гэпы (gap_*) сюда не переносим — они живут только в мастере.


; data_password_table: таблица паролей/имён уровней экрана 3.PASS (exec 0x264D). Строки: "START" (0x264D), "ROOM%%" (0x2653), "KISS%%" (0x265A), "LEFT%%" (0x2661), "CLEAR%%" (0x2668). Каждая запись 0-терминирована, разделитель '%' (0x25). Используется обработчиком screen_pass@0x020A (LXI B,264D @0x020F).
data_password_table:
	defb	53h,54h,41h,52h,54h,00h,52h,4Fh
	defb	4Fh,4Dh,25h,25h,00h,4Bh,49h,53h
	defb	53h,25h,25h,00h,4Ch,45h,46h,54h
	defb	25h,25h,00h,43h,4Ch,45h,41h,52h
	defb	25h,26h,26h,00h
