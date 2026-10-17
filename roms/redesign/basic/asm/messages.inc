; Данные: data_error_messages  (пул сообщений об ошибках и промптов)
; Адрес: 0x2465..0x256D (265 байт, 23 строк)
; Формат: ASCII-байты; старший бит (bit7) ПОСЛЕДНЕГО байта = конец
;   строки; между строками разделителей нет (плотный пул).
; КОДИРОВКА: коды 0x60..0x7E в этом ROM — КИРИЛЛИЦА (знакогенератор
;   Stage 7), поэтому сообщения набраны русскими буквами: байты
;   62 65 7A = «БЕЗ», 6F 7B 69 62 6B 61 = «ОШИБКА». Ключевые слова
;   (NEXT/FOR/DATA/GOSUB/DEF) — латиницей A..Z (0x41..0x5A).
; Вывод: func_error_raise (0x0083): LXI H,2465 и проход пула по
;   bit7-терминаторам, индекс от кода ошибки (RAR/DCR). NEXT->строка0
;   подтверждён живым тестом (экран «NEXT БЕЗ FOR ОШИБКА»).

data_error_messages:
str_err_next_bez_for:
    DEFB 4Eh, 45h, 58h, 54h, 20h, 62h, 65h, 7Ah, 20h, 46h, 4Fh, 0D2h ; str_err_next_bez_for  @0x2465  #0  [NEXT без FOR]
    ;   текст: 'NEXT БЕЗ FOR'
str_err_sintaksi_eskaq:
    DEFB 73h, 69h, 6Eh, 74h, 61h, 6Bh, 73h, 69h, 7Eh, 65h, 73h, 6Bh, 61h, 0F1h ; str_err_sintaksi_eskaq  @0x2471  #1  [синтаксическая]
    ;   текст: 'СИНТАКСИЧЕСКАЯ'
str_err_return_bez_gosub:
    DEFB 52h, 45h, 54h, 55h, 52h, 4Eh, 20h, 62h, 65h, 7Ah, 20h, 47h, 4Fh, 53h, 55h, 0C2h ; str_err_return_bez_gosub  @0x247F  #2  [RETURN без GOSUB]
    ;   текст: 'RETURN БЕЗ GOSUB'
str_err_malo_dannyh_w_data:
    DEFB 6Dh, 61h, 6Ch, 6Fh, 20h, 64h, 61h, 6Eh, 6Eh, 79h, 68h, 20h, 77h, 20h, 44h, 41h, 54h, 0C1h ; str_err_malo_dannyh_w_data  @0x248F  #3  [мало данных в DATA]
    ;   текст: 'МАЛО ДАННЫХ В DATA'
str_err_newernyj_argument:
    DEFB 6Eh, 65h, 77h, 65h, 72h, 6Eh, 79h, 6Ah, 20h, 61h, 72h, 67h, 75h, 6Dh, 65h, 6Eh, 0F4h ; str_err_newernyj_argument  @0x24A1  #4  [неверный аргумент]
    ;   текст: 'НЕВЕРНЫЙ АРГУМЕНТ'
str_err_perepolnenie:
    DEFB 70h, 65h, 72h, 65h, 70h, 6Fh, 6Ch, 6Eh, 65h, 6Eh, 69h, 0E5h ; str_err_perepolnenie  @0x24B2  #5  [переполнение]
    ;   текст: 'ПЕРЕПОЛНЕНИЕ'
str_err_net_pamqti:
    DEFB 6Eh, 65h, 74h, 20h, 70h, 61h, 6Dh, 71h, 74h, 0E9h ; str_err_net_pamqti  @0x24BE  #6  [нет памяти]
    ;   текст: 'НЕТ ПАМЯТИ'
str_err_net_stroki:
    DEFB 6Eh, 65h, 74h, 20h, 73h, 74h, 72h, 6Fh, 6Bh, 0E9h ; str_err_net_stroki  @0x24C8  #7  [нет строки]
    ;   текст: 'НЕТ СТРОКИ'
str_err_newernyj_indeks:
    DEFB 6Eh, 65h, 77h, 65h, 72h, 6Eh, 79h, 6Ah, 20h, 69h, 6Eh, 64h, 65h, 6Bh, 0F3h ; str_err_newernyj_indeks  @0x24D2  #8  [неверный индекс]
    ;   текст: 'НЕВЕРНЫЙ ИНДЕКС'
str_err_powtornoe_opisanie:
    DEFB 70h, 6Fh, 77h, 74h, 6Fh, 72h, 6Eh, 6Fh, 65h, 20h, 6Fh, 70h, 69h, 73h, 61h, 6Eh, 69h, 0E5h ; str_err_powtornoe_opisanie  @0x24E1  #9  [повторное описание]
    ;   текст: 'ПОВТОРНОЕ ОПИСАНИЕ'
str_err_delenie_na_nolx:
    DEFB 64h, 65h, 6Ch, 65h, 6Eh, 69h, 65h, 20h, 6Eh, 61h, 20h, 6Eh, 6Fh, 6Ch, 0F8h ; str_err_delenie_na_nolx  @0x24F3  #10  [деление на ноль]
    ;   текст: 'ДЕЛЕНИЕ НА НОЛЬ'
str_err_tolxko_w_programme:
    DEFB 74h, 6Fh, 6Ch, 78h, 6Bh, 6Fh, 20h, 77h, 20h, 70h, 72h, 6Fh, 67h, 72h, 61h, 6Dh, 6Dh, 0E5h ; str_err_tolxko_w_programme  @0x2502  #11  [только в programme]
    ;   текст: 'ТОЛЬКО В ПРОГРАММЕ'
str_err_nesootw_dannyh:
    DEFB 6Eh, 65h, 73h, 6Fh, 6Fh, 74h, 77h, 2Eh, 64h, 61h, 6Eh, 6Eh, 79h, 0E8h ; str_err_nesootw_dannyh  @0x2514  #12  [несоответствие данных]
    ;   текст: 'НЕСООТВ.ДАННЫХ'
str_err_mal_bufer:
    DEFB 6Dh, 61h, 6Ch, 20h, 62h, 75h, 66h, 65h, 0F2h ; str_err_mal_bufer  @0x2522  #13  [мал буфер]
    ;   текст: 'МАЛ БУФЕР'
str_err_x_255:
    DEFB 58h, 24h, 3Eh, 32h, 35h, 0B5h ; str_err_x_255  @0x252B  #14  [X$>255]
    ;   текст: 'X$>255'
str_err_slovno:
    DEFB 73h, 6Ch, 6Fh, 76h, 6Eh, 0EFh ; str_err_slovno  @0x2531  #15  [сложно]
    ;   текст: 'СЛОЖНО'
str_err_nelxzq:
    DEFB 6Eh, 65h, 6Ch, 78h, 7Ah, 0F1h ; str_err_nelxzq  @0x2537  #16  [нельзя]
    ;   текст: 'НЕЛЬЗЯ'
str_err_net_def:
    DEFB 6Eh, 65h, 74h, 20h, 44h, 45h, 0C6h ; str_err_net_def  @0x253D  #17  [нет DEF]
    ;   текст: 'НЕТ DEF'
str_err_o_ibka:
    DEFB 20h, 6Fh, 7Bh, 69h, 62h, 6Bh, 0E1h ; str_err_o_ibka  @0x2544  #18  [ ошибка]
    ;   текст: ' ОШИБКА'
str_prompt_msg:
    DEFB 0Dh, 0Ah, 3Dh, 3Eh, 0Dh, 8Ah ; str_prompt_msg  @0x254B  #19
    ;   текст: '\\r\\n=>\\r\\n'
str_prompt_stop:
    DEFB 0Dh, 0Ah, 73h, 74h, 6Fh, 0F0h ; str_prompt_stop  @0x2551  #20
    ;   текст: '\\r\\nСТОП'
str_prompt_w_stroke:
    DEFB 20h, 77h, 20h, 73h, 74h, 72h, 6Fh, 6Bh, 65h, 0A0h ; str_prompt_w_stroke  @0x2557  #21
    ;   текст: ' В СТРОКЕ '
str_prompt_programma:
    DEFB 0Dh, 0Ah, 70h, 72h, 6Fh, 67h, 72h, 61h, 6Dh, 6Dh, 61h, 3Ah, 0A0h ; str_prompt_programma  @0x2561  #22
    ;   текст: '\\r\\nПРОГРАММА: '
