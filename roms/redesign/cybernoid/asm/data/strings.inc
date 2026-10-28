; strings.inc — B-viewStage 9 (только чтение).
; Источник: data/data.asm (v06c-asm-export). Байты дословно из RDB-объектов,
; без переформатирования. В сборку НЕ включается: main.asm знает только
; layout.asm (Stage 6.23 §2.2). Список объектов и их комментарии — в RDB
; (cybernoid_unpacked.rdb); здесь — только human-readable срез по классу.
; Покрытые гэпы (gap_*) сюда не переносим — они живут только в мастере.


; str_screen: экранный текст (транслит/ASCII, разделитель слов '%'): «THE%FEDERATION%WILL%REWARD» → «Федерация вознаградит». Хедер записи display-list 70 E3 (позиция/команда). Рендерится func_display_list_interp@0x11D8 → func_render_glyph@0x114D (data_glyph_block@0x3780).
str_screen_0b96:
	defb	00h,00h,00h,00h,00h,00h,00h,00h
	defb	00h,00h,00h,00h,00h,00h,00h,00h
	defb	00h,00h,00h,00h,00h,00h,00h,00h
	defb	00h,00h,00h,00h

; str_screen: экранный текст (% -разделитель): «ENTER%<FREEMAN>%IN%HISCORE» → «Введите <FREEMAN> в таблицу рекордов». Хедер записи 60 A3. str_screen_* — вывод на экран (func_display_list_interp@0x11D8).
str_screen_0bb5:
	defb	00h,00h,00h,00h,00h,00h,00h,00h
	defb	00h,00h,00h,00h,00h,00h,00h,00h
	defb	00h,00h,00h,00h,00h,00h,00h,00h
	defb	00h,00h

; str_screen: экранный текст (% -разделитель): «PLEASE%ENTER%YOUR%NAME» → «Пожалуйста, введите Ваше имя» (ввод имени в таблицу рекордов). В том же блоке 0x0B96..0x0C40: «NO%DRIVE%A», «ENTER%LEVEL%NAME», «NOT %…». func_display_list_interp@0x11D8.
str_screen_0bd7:
	defb	00h,00h,00h,00h,00h,00h,00h,00h
	defb	00h,00h,00h,00h,00h,00h,00h,00h
	defb	00h,00h,00h,00h,00h,00h,00h

; str_screen: экранный текст (% -разделитель): «CONGRATULATIONS%%» → «Поздравляем» (двойной %% = пустое слово/конец). func_display_list_interp@0x11D8.
str_screen_0c39:
	defb	00h,0FFh,00h,00h,00h,00h,00h,70h
	defb	0E3h,54h,48h,45h,25h,46h,45h,44h
	defb	45h,52h
