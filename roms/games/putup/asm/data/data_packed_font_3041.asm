; Данные: data_packed_font_3041
; Адрес: 0x3041
; Размер: 2041 байт (0x3041..0x3839; следующий объект var_music_tick@0x383A)
; Назначение: УПАКОВАННЫЙ ИСТОЧНИК ШРИФТА/ГЛИФОВ. Читается ПО УБЫВАНИЮ четырьмя
;   писателями битовых плоскостей func_load_glyph_block(0x0401) для построения блока
;   глифов @0x6000 (data_glyph_block). Указатель источника DE=0x3041; DE+=8 на глиф,
;   всего 256 глифов. 4 плоскости глифа разворачиваются из пар битов источника
;   {7,3},{6,2},{5,1},{4,0}. VERIFIED: источник глифа-0 = 0x61 x8 -> glyph0=[00x24,FFx8].
;   Точная схема упаковки/RLE полностью не расшифрована (Unknown) — выгружен сырым блоком.
; ВЫГРУЗКА: бинарный блок —  по-байтовая копия — побайтовые DEFB в этом файле (без bin-артефактов).
;   putup.rom (SHA256 = ROM в MCP). Начало (0x61 x16) сверено с debug_read_memory_range(0x3041,16).

data_packed_font_3041:
    DEFB 061h, 061h, 061h, 061h, 061h, 061h, 061h, 061h, 061h, 061h, 061h, 061h, 061h, 061h, 061h, 061h
    DEFB 061h, 061h, 061h, 061h, 061h, 061h, 061h, 061h, 061h, 061h, 061h, 061h, 061h, 061h, 061h, 061h
    DEFB 061h, 061h, 061h, 061h, 061h, 061h, 061h, 061h, 061h, 061h, 061h, 061h, 061h, 061h, 061h, 061h
    DEFB 061h, 061h, 061h, 061h, 061h, 061h, 061h, 061h, 061h, 061h, 061h, 061h, 061h, 061h, 061h, 061h
    DEFB 061h, 061h, 061h, 061h, 061h, 061h, 061h, 061h, 061h, 061h, 061h, 061h, 061h, 061h, 061h, 061h
    DEFB 061h, 061h, 061h, 061h, 061h, 061h, 061h, 061h, 061h, 061h, 061h, 061h, 061h, 061h, 061h, 061h
    DEFB 061h, 061h, 061h, 061h, 061h, 061h, 061h, 061h, 061h, 000h, 000h, 000h, 000h, 000h, 000h, 000h
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h
    DEFB 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h
    DEFB 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h
    DEFB 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h
    DEFB 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h
    DEFB 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h
    DEFB 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h
    DEFB 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h
    DEFB 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h
    DEFB 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h
    DEFB 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h
    DEFB 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h
    DEFB 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h
    DEFB 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h
    DEFB 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h
    DEFB 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h
    DEFB 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h
    DEFB 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h
    DEFB 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h
    DEFB 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h
    DEFB 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h
    DEFB 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h
    DEFB 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h
    DEFB 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h
    DEFB 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h
    DEFB 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h
    DEFB 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h
    DEFB 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h
    DEFB 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h
    DEFB 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h
    DEFB 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h
    DEFB 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h
    DEFB 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h
    DEFB 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 000h, 000h, 000h, 000h, 000h, 000h, 000h
    DEFB 000h, 000h, 000h, 000h, 0F0h, 060h, 080h, 090h, 0F0h, 0F0h, 070h, 070h, 050h, 070h, 050h, 050h
    DEFB 040h, 000h, 020h, 0C0h, 0C0h, 080h, 080h, 0F8h, 0F8h, 000h, 000h, 000h, 000h, 080h, 060h, 060h
    DEFB 060h, 060h, 060h, 060h, 060h, 060h, 0A0h, 0A0h, 030h, 030h, 030h, 020h, 020h, 0C0h, 0C0h, 0C0h
    DEFB 0F0h, 030h, 020h, 0C0h, 03Ch, 0C0h, 030h, 020h, 0C0h, 0C0h, 0A0h, 060h, 0A0h, 000h, 000h, 000h
    DEFB 000h, 000h, 070h, 050h, 050h, 040h, 0C0h, 030h, 0C0h, 030h, 01Ch, 0C1h, 0C1h, 031h, 0C1h, 0C1h
    DEFB 0C0h, 000h, 000h, 000h, 030h, 020h, 020h, 020h, 0C0h, 020h, 0C0h, 0C0h, 0F0h, 090h, 090h, 080h
    DEFB 060h, 000h, 000h, 000h, 060h, 060h, 080h, 080h, 090h, 000h, 000h, 0C0h, 0F0h, 090h, 080h, 080h
    DEFB 060h, 0F8h, 068h, 068h, 060h, 060h, 060h, 0A0h, 0A0h, 0B0h, 0B0h, 06Bh, 0ABh, 06Ah, 0AAh, 06Ah
    DEFB 0A0h, 000h, 030h, 030h, 0C0h, 0C1h, 030h, 0C0h, 0C0h, 000h, 000h, 000h, 060h, 0F0h, 0F0h, 060h
    DEFB 080h, 070h, 050h, 0F0h, 0F0h, 070h, 070h, 070h, 050h, 000h, 000h, 000h, 000h, 000h, 000h, 000h
    DEFB 000h, 000h, 060h, 060h, 060h, 086h, 068h, 089h, 089h, 08Ah, 08Ah, 08Ah, 08Ah, 0FAh, 0FAh, 0FAh
    DEFB 0FFh, 031h, 032h, 032h, 032h, 032h, 032h, 032h, 0C1h, 031h, 0C2h, 0C2h, 0C2h, 0C2h, 0C2h, 0C2h
    DEFB 0C1h, 031h, 012h, 012h, 012h, 012h, 012h, 0C2h, 0C1h, 031h, 012h, 012h, 0C2h, 0C2h, 0C2h, 0C2h
    DEFB 0C1h, 031h, 062h, 0F2h, 0F2h, 062h, 082h, 0C2h, 0C1h, 031h, 062h, 062h, 082h, 082h, 092h, 0C2h
    DEFB 0C1h, 030h, 032h, 032h, 032h, 032h, 032h, 032h, 0C1h, 0A0h, 0BAh, 0B4h, 0B4h, 0B4h, 0B4h, 0B4h
    DEFB 0B4h, 0F0h, 0FBh, 0F6h, 0F6h, 0F6h, 0B8h, 0F8h, 0B8h, 0A0h, 0BAh, 0B4h, 0B4h, 0B4h, 0B4h, 0B4h
    DEFB 0B4h, 0B4h, 0B4h, 0B4h, 0B4h, 0B4h, 0B4h, 0BAh, 0A0h, 0B4h, 0B4h, 0B4h, 0B4h, 0B4h, 0B4h, 0ABh
    DEFB 0A0h, 071h, 0F1h, 0F1h, 071h, 071h, 051h, 051h, 041h, 0F0h, 040h, 0F0h, 070h, 0B0h, 0B0h, 0B0h
    DEFB 0B0h, 0F0h, 040h, 070h, 040h, 0B0h, 0B0h, 0B0h, 0B0h, 0B0h, 0B0h, 0B0h, 0B0h, 0B0h, 0B0h, 0B0h
    DEFB 0B0h, 0B0h, 0B0h, 0B0h, 0B0h, 0B0h, 0B0h, 0B0h, 0B0h, 0F4h, 040h, 0F0h, 070h, 0B0h, 0B0h, 0B0h
    DEFB 0B0h, 047h, 040h, 070h, 040h, 0B0h, 0B0h, 0B0h, 0B0h, 0F0h, 0F0h, 0F0h, 0F0h, 0E0h, 0F0h, 0F0h
    DEFB 000h, 0F0h, 0F0h, 0F0h, 0F0h, 070h, 070h, 070h, 070h, 0F0h, 0F0h, 0F0h, 0F0h, 070h, 040h, 040h
    DEFB 040h, 047h, 047h, 047h, 060h, 080h, 080h, 000h, 000h, 040h, 040h, 040h, 060h, 080h, 080h, 080h
    DEFB 080h, 0F0h, 0F0h, 0F0h, 0F0h, 070h, 070h, 070h, 070h, 0F0h, 0F0h, 0F0h, 0F0h, 070h, 040h, 040h
    DEFB 040h, 070h, 070h, 070h, 040h, 060h, 080h, 080h, 080h, 040h, 040h, 040h, 040h, 000h, 000h, 000h
    DEFB 000h, 000h, 0F0h, 0F0h, 0F0h, 070h, 0F0h, 070h, 070h, 000h, 0F0h, 0F0h, 070h, 0F0h, 070h, 070h
    DEFB 070h, 070h, 070h, 070h, 070h, 070h, 070h, 040h, 040h, 070h, 070h, 040h, 070h, 040h, 040h, 040h
    DEFB 000h, 000h, 0F0h, 0F0h, 0F0h, 070h, 0F0h, 070h, 070h, 000h, 0F0h, 0F0h, 070h, 0F0h, 070h, 070h
    DEFB 070h, 070h, 070h, 070h, 070h, 070h, 040h, 040h, 000h, 070h, 070h, 040h, 070h, 040h, 040h, 040h
    DEFB 040h, 061h, 061h, 0F6h, 0F6h, 068h, 068h, 080h, 080h, 014h, 014h, 015h, 011h, 014h, 014h, 015h
    DEFB 011h, 074h, 074h, 07Fh, 07Fh, 07Fh, 07Fh, 0F5h, 071h, 0F4h, 0F4h, 0FAh, 0A1h, 064h, 0F4h, 0FAh
    DEFB 0FAh, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 0F1h, 0F1h, 0F1h, 0F1h, 0F1h, 0F1h, 0F1h
    DEFB 0F1h, 0F1h, 0F1h, 0F1h, 0F1h, 0F1h, 0F1h, 0F1h, 0F1h, 0F1h, 0F1h, 0F1h, 0F1h, 0F1h, 0F1h, 0F1h
    DEFB 0F1h, 0F1h, 0F1h, 0F1h, 0F1h, 0F1h, 0F1h, 0F1h, 0F1h, 0F1h, 0F1h, 0F1h, 0F1h, 0F1h, 0F1h, 0F1h
    DEFB 0F1h, 0F1h, 0F1h, 0F1h, 0F1h, 0F1h, 0F1h, 0F1h, 0F1h, 0F1h, 0F1h, 0F1h, 0F1h, 0F1h, 0F1h, 0F1h
    DEFB 0F1h, 0F1h, 0F1h, 0F1h, 0F1h, 0F1h, 0F1h, 0F1h, 0F1h, 0F1h, 0F1h, 0F1h, 0F1h, 0F1h, 0F1h, 0F1h
    DEFB 0F1h, 0F1h, 0F1h, 0F1h, 0F1h, 0F1h, 0F1h, 0F1h, 0F1h, 0F1h, 0F1h, 0F1h, 0F1h, 0F1h, 0F1h, 0F1h
    DEFB 0F1h, 0F1h, 0F1h, 0F1h, 0F1h, 0F1h, 0F1h, 0F1h, 0F1h, 0F1h, 0F1h, 0F1h, 0F1h, 0F1h, 0F1h, 0F1h
    DEFB 0F1h, 0F1h, 0F1h, 0F1h, 0F1h, 0F1h, 0F1h, 0F1h, 0F1h, 0F1h, 0F1h, 0F1h, 0F1h, 0F1h, 0F1h, 0F1h
    DEFB 0F1h, 0F1h, 0F1h, 0F1h, 0F1h, 0F1h, 0F1h, 0F1h, 0F1h, 0F1h, 0F1h, 0F1h, 0F1h, 0F1h, 0F1h, 0F1h
    DEFB 0F1h, 0F1h, 0F1h, 0F1h, 0F1h, 0F1h, 0F1h, 0F1h, 0F1h, 0F1h, 0F1h, 0F1h, 0F1h, 0F1h, 0F1h, 0F1h
    DEFB 0F1h, 0F1h, 0F1h, 0F1h, 0F1h, 0F1h, 0F1h, 0F1h, 0F1h, 0F1h, 0F1h, 0F1h, 0F1h, 0F1h, 0F1h, 0F1h
    DEFB 0F1h, 0F1h, 0F1h, 0F1h, 0F1h, 0F1h, 0F1h, 0F1h, 0F1h, 0F1h, 0F1h, 0F1h, 0F1h, 0F1h, 0F1h, 0F1h
    DEFB 0F1h, 0F1h, 0F1h, 0F1h, 0F1h, 0F1h, 0F1h, 0F1h, 0F1h, 0F1h, 0F1h, 0F1h, 0F1h, 0F1h, 0F1h, 0F1h
    DEFB 0F1h, 0F1h, 0F1h, 0F1h, 0F1h, 0F1h, 0F1h, 0F1h, 0F1h, 0F1h, 0F1h, 0F1h, 0F1h, 0F1h, 0F1h, 0F1h
    DEFB 0F1h, 0F1h, 0F1h, 0F1h, 0F1h, 0F1h, 0F1h, 0F1h, 0F1h, 071h, 071h, 071h, 071h, 071h, 071h, 071h
    DEFB 071h, 071h, 071h, 071h, 071h, 071h, 071h, 071h, 071h, 071h, 071h, 071h, 071h, 071h, 071h, 071h
    DEFB 071h, 071h, 071h, 071h, 071h, 071h, 071h, 071h, 071h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h
    DEFB 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h
    DEFB 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h
    DEFB 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h
    DEFB 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h
    DEFB 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h
    DEFB 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h
    DEFB 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h
    DEFB 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h
    DEFB 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h
    DEFB 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h
    DEFB 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h
    DEFB 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h
    DEFB 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h
    DEFB 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h
    DEFB 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h
    DEFB 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h
    DEFB 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h
    DEFB 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h
    DEFB 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h
    DEFB 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h
    DEFB 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h
    DEFB 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h
    DEFB 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h
    DEFB 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h
    DEFB 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h
    DEFB 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h
    DEFB 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h
    DEFB 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h
    DEFB 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h
    DEFB 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h
    DEFB 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 060h, 060h, 060h, 060h, 060h, 068h, 068h
    DEFB 068h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h, 0E1h
