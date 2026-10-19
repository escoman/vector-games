; Данные: data_music_period_table
; Адрес: 0x421A
; Размер: 192 байт (0x421A..0x42D9; следующий объект data_note_names_42DA@0x42DA)
; Назначение: таблица периодов (частот) нот, 16-битные little-endian значения;
;   индексируется в func_music_process_voice (LXI H, смещение = индекс*2).
;   Фаза 2: промоутнута из гэп-verbatim в именованный объект, чтобы ссылки
;   LXI H,421Ah стали символичными (data_music_period_table) и переехали при релокации.
;   Содержимое — данные (периоды), побайтовые DEFB, НЕ патчится при релокации.

data_music_period_table:
    DEFB 0EEh, 0Eh, 018h, 0Eh, 04Dh, 0Dh, 08Eh, 0Ch, 0DAh, 0Bh, 02Fh, 0Bh, 08Fh, 0Ah, 0F7h, 09h   ; 0x421A
    DEFB 068h, 09h, 0E1h, 08h, 061h, 08h, 0E9h, 07h, 077h, 07h, 0Ch, 07h, 0A7h, 06h, 047h, 06h   ; 0x422A
    DEFB 0EDh, 05h, 098h, 05h, 048h, 05h, 0FCh, 04h, 0B4h, 04h, 071h, 04h, 031h, 04h, 0F5h, 03h   ; 0x423A
    DEFB 0BCh, 03h, 086h, 03h, 053h, 03h, 024h, 03h, 0F7h, 02h, 0CCh, 02h, 0A4h, 02h, 07Eh, 02h   ; 0x424A
    DEFB 05Ah, 02h, 038h, 02h, 018h, 02h, 0FAh, 01h, 0DEh, 01h, 0C3h, 01h, 0AAh, 01h, 092h, 01h   ; 0x425A
    DEFB 07Bh, 01h, 066h, 01h, 052h, 01h, 03Fh, 01h, 02Dh, 01h, 01Ch, 01h, 0Ch, 01h, 0FDh, 00h   ; 0x426A
    DEFB 0EFh, 00h, 0E2h, 00h, 0D5h, 00h, 0C9h, 00h, 0BEh, 00h, 0B3h, 00h, 0A9h, 00h, 09Fh, 00h   ; 0x427A
    DEFB 097h, 00h, 08Eh, 00h, 086h, 00h, 07Fh, 00h, 077h, 00h, 071h, 00h, 06Ah, 00h, 064h, 00h   ; 0x428A
    DEFB 05Fh, 00h, 059h, 00h, 054h, 00h, 050h, 00h, 04Bh, 00h, 047h, 00h, 043h, 00h, 03Fh, 00h   ; 0x429A
    DEFB 03Ch, 00h, 038h, 00h, 035h, 00h, 032h, 00h, 02Fh, 00h, 02Dh, 00h, 02Ah, 00h, 028h, 00h   ; 0x42AA
    DEFB 026h, 00h, 024h, 00h, 022h, 00h, 020h, 00h, 01Eh, 00h, 01Ch, 00h, 01Bh, 00h, 019h, 00h   ; 0x42BA
    DEFB 018h, 00h, 016h, 00h, 015h, 00h, 014h, 00h, 013h, 00h, 012h, 00h, 011h, 00h, 010h, 00h   ; 0x42CA