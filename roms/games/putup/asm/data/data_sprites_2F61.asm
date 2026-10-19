; Данные: data_sprites_2F61
; Адрес: 0x2F61
; Размер: 224 байта (0x2F61..0x3040; следующий объект data_packed_font_3041@0x3041)
; Назначение: блок спрайтовой графики между data_gfx_2761 и упакованным шрифтом.
;   Точное предназначение в RDB не задокументировано (комментарий пуст). Начало
;   содержит паттерны 0xC0,0xF0,0xF8,0xFC... (треугольные маски спрайтов).
; ВЫГРУЗКА: бинарный блок —  по-байтовая копия — побайтовые DEFB в этом файле (без bin-артефактов).
;   putup.rom (SHA256 = ROM в MCP). Начало сверено с debug_read_memory_range(0x2F61,16).

data_sprites_2F61:
    DEFB 01Fh, 00Fh, 000h, 031h, 001h, 001h, 000h, 000h, 000h, 0C0h, 0F0h, 0F8h, 0FCh, 0B4h, 0B6h, 0B6h
    DEFB 0B6h, 0FCh, 002h, 0F4h, 0F0h, 0ECh, 0D8h, 070h, 020h, 003h, 007h, 00Fh, 00Fh, 01Fh, 01Fh, 01Fh
    DEFB 01Fh, 00Fh, 000h, 00Dh, 00Eh, 006h, 000h, 00Eh, 007h, 0C0h, 0F0h, 0F8h, 0FCh, 0B4h, 0B6h, 0B6h
    DEFB 0B6h, 0FCh, 000h, 0F0h, 0F0h, 0E6h, 01Ch, 038h, 000h, 003h, 007h, 00Fh, 00Fh, 01Fh, 01Fh, 01Fh
    DEFB 01Fh, 00Fh, 000h, 007h, 00Bh, 00Bh, 001h, 003h, 003h, 0C0h, 0F0h, 0F8h, 0FCh, 0B4h, 0B6h, 0B6h
    DEFB 0B6h, 0FCh, 000h, 0F4h, 0F4h, 0E4h, 000h, 0D8h, 0ECh, 003h, 00Fh, 01Fh, 03Fh, 02Dh, 06Dh, 06Dh
    DEFB 06Dh, 03Fh, 040h, 02Fh, 00Fh, 037h, 01Bh, 00Eh, 004h, 0C0h, 0E0h, 0F0h, 0F0h, 0F8h, 0F8h, 0F8h
    DEFB 0F8h, 0F0h, 000h, 088h, 080h, 080h, 000h, 000h, 000h, 003h, 00Fh, 01Fh, 03Fh, 02Dh, 06Dh, 06Dh
    DEFB 06Dh, 03Fh, 000h, 00Fh, 00Fh, 067h, 038h, 01Ch, 000h, 0C0h, 0E0h, 0F0h, 0F0h, 0F8h, 0F8h, 0F8h
    DEFB 0F8h, 0F0h, 0B0h, 0B0h, 070h, 060h, 000h, 070h, 0E0h, 003h, 00Fh, 01Fh, 03Fh, 02Dh, 06Dh, 06Dh
    DEFB 06Dh, 03Fh, 000h, 02Fh, 02Fh, 027h, 000h, 01Bh, 037h, 0C0h, 0E0h, 0F0h, 0F0h, 0F8h, 0F8h, 0F8h
    DEFB 0F8h, 0F0h, 000h, 0E0h, 0D0h, 0D0h, 080h, 0C0h, 0C0h, 003h, 00Fh, 01Fh, 03Fh, 03Dh, 07Dh, 07Dh
    DEFB 07Dh, 03Fh, 000h, 02Fh, 04Fh, 007h, 000h, 03Ch, 07Ch, 0C0h, 0E0h, 0F0h, 0F0h, 0B8h, 0B8h, 0B8h
    DEFB 0B8h, 0F0h, 000h, 0CCh, 0C0h, 080h, 000h, 030h, 038h, 061h, 061h, 061h, 061h, 061h, 061h, 061h
