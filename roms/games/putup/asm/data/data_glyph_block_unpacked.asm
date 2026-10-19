; Данные: data_glyph_block_unpacked
; Адрес: 0x6000 (этап A; в этапе B переносится константой GLYPH_BASE в gen_layout.py)
; Размер: 8192 байт (0x6000..0x7FFF; 256 глифов x 32 Б)
; Назначение: РАСПАКОВАННЫЙ БЛОК ГЛИФОВ — снимок RAM пост-инициализации оригинала
;   (debug_read_memory_range(0x6000,8192) через MCP после ~4 с работы: загрузка
;   глифов func_load_glyph_block, seed глифа-0 из func_load_gfx_2761, копир
;   спрайтов 0x2F61→0x7418 внутри func_main_init). В новом ROM исполняется
;   read-only; единственные писатели в этом диапазоне в оригинале — init-рутины,
;   патчем NOP на 0x0B83 загрузка выключена. VERIFIED: снимки на 4 с и 6 с
;   идентичны (0 расхождений).
; ОСОЗНАННОЕ ОТХОЖДЕНИЕ от оригинала: чанк плоскости E000 (байты 24..31 каждого
;   32-байтного глифа; вес бита цвета 1 = LSB) инвертирован (XOR 0xFF) во ВСЕХ
;   256 глифах — фон E000 стал чистым 0x00 вместо 0xFF. Компенсация в палитре
;   (func_render_glyph.asm, 0x08A3..0x08B2): перестановка соседних пар слотов
;   PAL'[j]=PAL[j^1], итоговая РАСКРАШЕННАЯ картинка побайтово идентична оригиналу
;   (гейт: tools/compare_color.py, 0 расхождений цвета на title/play1/play2).
;   Глиф 0 после инверсии = [00x24, 00x8].
; Стадия 1 (поверх Фазы 3): цветовой индекс 15 <-> 8 перемаркирован во всех глифах
;   с компенсацией свапом слотов палитры 8<->15 — картинка та же, но текст (бывш.
;   idx15 во всех 4 плоскостях) теперь пишется ТОЛЬКО в плоскость 0x8000 (idx8),
;   плоскости A000/C000/E000 у букв = 0. Это открывает компакцию 1-битного шрифта.
;   SHA256 этого (изменённого) блока
;   = 6fd358ad5dff6e8865eeaf9a8840167dbf4b5d6e2a69a5efae05843b5d5c3879
;   (после Фазы 3 было b5c8aee246df3d946b4aa207ae1515f507069e2ec570f670870798e49b4b55fc;
;   исходный снимок оригинала — 45919a36b3fed08b6a81d58ae26f17dc4f274fb603608915239a283036ef55b5).
; ВЫГРУЗКА: бинарный блок —  вербатим — побайтовые DEFB в этом файле (без bin-артефактов).
;   ответа MCP (без дешифровки), получен tools/get_glyph_block.py.

data_glyph_block:                  ; историческое имя (ptr_table, стр. заставки)
data_glyph_block_unpacked:
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h   ; глиф 0 @0x6000
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h   ; глиф 1 @0x6020
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 0BDh, 0B3h, 05Fh, 05Fh, 02Fh, 017h, 00Ch, 003h   ; глиф 2 @0x6040
    DEFB 0BDh, 0B3h, 05Fh, 05Fh, 02Fh, 017h, 00Ch, 003h, 0BDh, 0B3h, 05Fh, 05Fh, 02Fh, 017h, 00Ch, 003h
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 003h, 00Ch, 017h, 02Fh, 05Ch, 050h, 0BCh, 0BFh   ; глиф 3 @0x6060
    DEFB 003h, 00Ch, 017h, 02Fh, 05Ch, 050h, 0BCh, 0BFh, 003h, 00Ch, 017h, 02Fh, 05Ch, 050h, 0BCh, 0BFh
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 0BDh, 0CDh, 0FAh, 0FAh, 0F4h, 0E8h, 030h, 0C0h   ; глиф 4 @0x6080
    DEFB 0BDh, 0CDh, 0FAh, 0FAh, 0F4h, 0E8h, 030h, 0C0h, 0BDh, 0CDh, 0FAh, 0FAh, 0F4h, 0E8h, 030h, 0C0h
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 0C0h, 030h, 0E8h, 0F4h, 03Ah, 00Ah, 03Dh, 0FDh   ; глиф 5 @0x60A0
    DEFB 0C0h, 030h, 0E8h, 0F4h, 03Ah, 00Ah, 03Dh, 0FDh, 0C0h, 030h, 0E8h, 0F4h, 03Ah, 00Ah, 03Dh, 0FDh
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 038h, 010h, 0D6h, 0FEh, 0FEh, 038h, 07Ch, 038h   ; глиф 6 @0x60C0
    DEFB 038h, 010h, 0D6h, 0FEh, 0FEh, 038h, 07Ch, 038h, 038h, 010h, 0D6h, 0FEh, 0FEh, 038h, 07Ch, 038h
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 038h, 010h, 07Ch, 0FEh, 07Ch, 038h, 010h, 010h   ; глиф 7 @0x60E0
    DEFB 038h, 010h, 07Ch, 0FEh, 07Ch, 038h, 010h, 010h, 038h, 010h, 07Ch, 0FEh, 07Ch, 038h, 010h, 010h
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 018h, 03Ch, 03Ch, 018h, 000h, 000h   ; глиф 8 @0x6100
    DEFB 000h, 000h, 018h, 03Ch, 03Ch, 018h, 000h, 000h, 000h, 000h, 018h, 03Ch, 03Ch, 018h, 000h, 000h
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 0FFh, 0FFh, 0E7h, 0C3h, 0C3h, 0E7h, 0FFh, 0FFh   ; глиф 9 @0x6120
    DEFB 0FFh, 0FFh, 0E7h, 0C3h, 0C3h, 0E7h, 0FFh, 0FFh, 0FFh, 0FFh, 0E7h, 0C3h, 0C3h, 0E7h, 0FFh, 0FFh
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 03Ch, 066h, 042h, 042h, 066h, 03Ch, 000h   ; глиф 10 @0x6140
    DEFB 000h, 03Ch, 066h, 042h, 042h, 066h, 03Ch, 000h, 000h, 03Ch, 066h, 042h, 042h, 066h, 03Ch, 000h
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 0FFh, 0C3h, 099h, 0BDh, 0BDh, 099h, 0C3h, 0FFh   ; глиф 11 @0x6160
    DEFB 0FFh, 0C3h, 099h, 0BDh, 0BDh, 099h, 0C3h, 0FFh, 0FFh, 0C3h, 099h, 0BDh, 0BDh, 099h, 0C3h, 0FFh
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 078h, 0CCh, 0CCh, 0CCh, 07Dh, 00Fh, 007h, 00Fh   ; глиф 12 @0x6180
    DEFB 078h, 0CCh, 0CCh, 0CCh, 07Dh, 00Fh, 007h, 00Fh, 078h, 0CCh, 0CCh, 0CCh, 07Dh, 00Fh, 007h, 00Fh
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 018h, 07Eh, 018h, 03Ch, 066h, 066h, 066h, 03Ch   ; глиф 13 @0x61A0
    DEFB 018h, 07Eh, 018h, 03Ch, 066h, 066h, 066h, 03Ch, 018h, 07Eh, 018h, 03Ch, 066h, 066h, 066h, 03Ch
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h   ; глиф 14 @0x61C0
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h   ; глиф 15 @0x61E0
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h   ; глиф 16 @0x6200
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h   ; глиф 17 @0x6220
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h   ; глиф 18 @0x6240
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h   ; глиф 19 @0x6260
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h   ; глиф 20 @0x6280
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h   ; глиф 21 @0x62A0
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h   ; глиф 22 @0x62C0
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h   ; глиф 23 @0x62E0
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h   ; глиф 24 @0x6300
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h   ; глиф 25 @0x6320
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h   ; глиф 26 @0x6340
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h   ; глиф 27 @0x6360
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h   ; глиф 28 @0x6380
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h   ; глиф 29 @0x63A0
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh
    DEFB 001h, 002h, 004h, 008h, 010h, 020h, 040h, 080h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h   ; глиф 30 @0x63C0
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h
    DEFB 000h, 000h, 010h, 010h, 0FFh, 010h, 010h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h   ; глиф 31 @0x63E0
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h   ; глиф 32 @0x6400
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h
    DEFB 000h, 030h, 000h, 030h, 030h, 078h, 078h, 030h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h   ; глиф 33 @0x6420
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 06Ch, 06Ch, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h   ; глиф 34 @0x6440
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h
    DEFB 000h, 06Ch, 06Ch, 0FEh, 06Ch, 0FEh, 06Ch, 06Ch, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h   ; глиф 35 @0x6460
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h
    DEFB 000h, 0C3h, 03Ch, 066h, 066h, 03Ch, 0C3h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h   ; глиф 36 @0x6480
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h
    DEFB 000h, 0C6h, 066h, 030h, 018h, 0CCh, 0C6h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h   ; глиф 37 @0x64A0
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h
    DEFB 000h, 076h, 0CCh, 0DCh, 076h, 038h, 06Ch, 038h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h   ; глиф 38 @0x64C0
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h
    DEFB 000h, 000h, 000h, 000h, 000h, 0C0h, 060h, 060h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h   ; глиф 39 @0x64E0
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h
    DEFB 000h, 018h, 030h, 060h, 060h, 060h, 030h, 018h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h   ; глиф 40 @0x6500
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h
    DEFB 000h, 060h, 030h, 018h, 018h, 018h, 030h, 060h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h   ; глиф 41 @0x6520
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h
    DEFB 000h, 000h, 066h, 03Ch, 0FFh, 03Ch, 066h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h   ; глиф 42 @0x6540
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h
    DEFB 000h, 000h, 030h, 030h, 0FCh, 030h, 030h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h   ; глиф 43 @0x6560
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h
    DEFB 060h, 030h, 030h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h   ; глиф 44 @0x6580
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h
    DEFB 000h, 000h, 000h, 000h, 0FCh, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h   ; глиф 45 @0x65A0
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h
    DEFB 000h, 030h, 030h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h   ; глиф 46 @0x65C0
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h
    DEFB 000h, 080h, 0C0h, 060h, 030h, 018h, 00Ch, 006h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h   ; глиф 47 @0x65E0
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h
    DEFB 000h, 07Ch, 0C6h, 0E6h, 0D6h, 0CEh, 0C6h, 07Ch, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h   ; глиф 48 @0x6600
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h
    DEFB 000h, 0FCh, 030h, 030h, 030h, 030h, 070h, 030h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h   ; глиф 49 @0x6620
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h
    DEFB 000h, 0FCh, 0CCh, 060h, 038h, 00Ch, 0CCh, 078h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h   ; глиф 50 @0x6640
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h
    DEFB 000h, 078h, 0CCh, 00Ch, 038h, 00Ch, 0CCh, 078h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h   ; глиф 51 @0x6660
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h
    DEFB 000h, 01Eh, 00Ch, 0FEh, 0CCh, 06Ch, 03Ch, 01Ch, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h   ; глиф 52 @0x6680
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h
    DEFB 000h, 078h, 0CCh, 00Ch, 00Ch, 0F8h, 0C0h, 0FCh, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h   ; глиф 53 @0x66A0
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h
    DEFB 000h, 078h, 0CCh, 0CCh, 0F8h, 0C0h, 060h, 038h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h   ; глиф 54 @0x66C0
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h
    DEFB 000h, 030h, 030h, 030h, 018h, 00Ch, 0CCh, 0FCh, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h   ; глиф 55 @0x66E0
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h
    DEFB 000h, 078h, 0CCh, 0CCh, 078h, 0CCh, 0CCh, 078h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h   ; глиф 56 @0x6700
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h
    DEFB 000h, 070h, 018h, 00Ch, 07Ch, 0CCh, 0CCh, 078h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h   ; глиф 57 @0x6720
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h
    DEFB 000h, 030h, 030h, 000h, 000h, 030h, 030h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h   ; глиф 58 @0x6740
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h
    DEFB 060h, 030h, 030h, 000h, 000h, 030h, 030h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h   ; глиф 59 @0x6760
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h
    DEFB 000h, 018h, 030h, 060h, 0C0h, 060h, 030h, 018h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h   ; глиф 60 @0x6780
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h
    DEFB 000h, 000h, 0FCh, 000h, 000h, 0FCh, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h   ; глиф 61 @0x67A0
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h
    DEFB 000h, 0C0h, 060h, 030h, 018h, 030h, 060h, 0C0h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h   ; глиф 62 @0x67C0
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h
    DEFB 000h, 030h, 000h, 030h, 018h, 00Ch, 0CCh, 078h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h   ; глиф 63 @0x67E0
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h
    DEFB 000h, 078h, 0C0h, 0C0h, 0DEh, 0DEh, 0C6h, 07Ch, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h   ; глиф 64 @0x6800
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h
    DEFB 000h, 0CCh, 0CCh, 0FCh, 0CCh, 0CCh, 078h, 030h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h   ; глиф 65 @0x6820
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h
    DEFB 000h, 0FCh, 066h, 066h, 07Ch, 066h, 066h, 0FCh, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h   ; глиф 66 @0x6840
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h
    DEFB 000h, 03Ch, 066h, 0C0h, 0C0h, 0C0h, 066h, 03Ch, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h   ; глиф 67 @0x6860
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h
    DEFB 000h, 0F8h, 06Ch, 066h, 066h, 066h, 06Ch, 0F8h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h   ; глиф 68 @0x6880
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h
    DEFB 000h, 0FEh, 062h, 068h, 078h, 068h, 062h, 0FEh, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h   ; глиф 69 @0x68A0
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h
    DEFB 000h, 0F0h, 060h, 068h, 078h, 068h, 062h, 0FEh, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h   ; глиф 70 @0x68C0
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h
    DEFB 000h, 03Eh, 066h, 0CEh, 0C0h, 0C0h, 066h, 03Ch, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h   ; глиф 71 @0x68E0
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h
    DEFB 000h, 0CCh, 0CCh, 0CCh, 0FCh, 0CCh, 0CCh, 0CCh, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h   ; глиф 72 @0x6900
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h
    DEFB 000h, 078h, 030h, 030h, 030h, 030h, 030h, 078h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h   ; глиф 73 @0x6920
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h
    DEFB 000h, 078h, 0CCh, 0CCh, 00Ch, 00Ch, 00Ch, 01Eh, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h   ; глиф 74 @0x6940
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h
    DEFB 000h, 0E6h, 066h, 06Ch, 078h, 06Ch, 066h, 0E6h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h   ; глиф 75 @0x6960
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h
    DEFB 000h, 0FEh, 066h, 062h, 060h, 060h, 060h, 0F0h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h   ; глиф 76 @0x6980
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h
    DEFB 000h, 0C6h, 0C6h, 0C6h, 0D6h, 0FEh, 0EEh, 0C6h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h   ; глиф 77 @0x69A0
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h
    DEFB 000h, 0C6h, 0C6h, 0CEh, 0DEh, 0F6h, 0E6h, 0C6h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h   ; глиф 78 @0x69C0
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h
    DEFB 000h, 038h, 06Ch, 0C6h, 0C6h, 0C6h, 06Ch, 038h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h   ; глиф 79 @0x69E0
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h
    DEFB 000h, 0F0h, 060h, 060h, 07Ch, 066h, 066h, 0FCh, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h   ; глиф 80 @0x6A00
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h
    DEFB 000h, 01Ch, 078h, 0DCh, 0CCh, 0CCh, 0CCh, 078h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h   ; глиф 81 @0x6A20
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h
    DEFB 000h, 0E6h, 066h, 06Ch, 07Ch, 064h, 066h, 0FCh, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h   ; глиф 82 @0x6A40
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h
    DEFB 000h, 078h, 0CCh, 018h, 030h, 060h, 0CCh, 078h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h   ; глиф 83 @0x6A60
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h
    DEFB 000h, 078h, 030h, 030h, 030h, 030h, 0B4h, 0FCh, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h   ; глиф 84 @0x6A80
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h
    DEFB 000h, 0FCh, 0CCh, 0CCh, 0CCh, 0CCh, 0CCh, 0CCh, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h   ; глиф 85 @0x6AA0
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h
    DEFB 000h, 030h, 078h, 0CCh, 0CCh, 0CCh, 0CCh, 0CCh, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h   ; глиф 86 @0x6AC0
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h
    DEFB 000h, 0C6h, 0EEh, 0FEh, 0D6h, 0C6h, 0C6h, 0C6h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h   ; глиф 87 @0x6AE0
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h
    DEFB 000h, 0C6h, 06Ch, 038h, 038h, 06Ch, 0C6h, 0C6h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h   ; глиф 88 @0x6B00
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h
    DEFB 000h, 078h, 030h, 030h, 078h, 0CCh, 0CCh, 0CCh, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h   ; глиф 89 @0x6B20
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h
    DEFB 000h, 0FEh, 066h, 032h, 018h, 08Ch, 0C6h, 0FEh, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h   ; глиф 90 @0x6B40
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h
    DEFB 000h, 078h, 060h, 060h, 060h, 060h, 060h, 078h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h   ; глиф 91 @0x6B60
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h
    DEFB 000h, 002h, 006h, 00Ch, 018h, 030h, 060h, 0C0h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h   ; глиф 92 @0x6B80
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h
    DEFB 000h, 078h, 018h, 018h, 018h, 018h, 018h, 078h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h   ; глиф 93 @0x6BA0
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h
    DEFB 000h, 000h, 000h, 000h, 0C6h, 06Ch, 038h, 010h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h   ; глиф 94 @0x6BC0
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h
    DEFB 0FFh, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h   ; глиф 95 @0x6BE0
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h   ; глиф 96 @0x6C00
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh
    DEFB 003h, 03Ch, 03Fh, 000h, 00Eh, 000h, 000h, 000h, 003h, 03Ch, 000h, 01Fh, 00Eh, 000h, 000h, 000h   ; глиф 97 @0x6C20
    DEFB 003h, 03Ch, 000h, 01Fh, 00Eh, 000h, 000h, 000h, 0FCh, 0FFh, 0FFh, 0FFh, 0F1h, 0FFh, 0FFh, 0FFh
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 060h, 0E0h, 0F0h, 038h, 018h, 018h, 038h, 070h, 060h   ; глиф 98 @0x6C40
    DEFB 000h, 000h, 000h, 018h, 000h, 038h, 070h, 060h, 0FFh, 00Fh, 0C7h, 0E7h, 0E7h, 0C7h, 08Fh, 09Fh
    DEFB 0FFh, 0FFh, 07Fh, 03Fh, 002h, 003h, 000h, 000h, 030h, 030h, 000h, 000h, 002h, 003h, 000h, 000h   ; глиф 99 @0x6C60
    DEFB 030h, 030h, 000h, 000h, 000h, 000h, 003h, 000h, 0CFh, 0CFh, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh
    DEFB 000h, 000h, 000h, 0E0h, 000h, 000h, 000h, 000h, 0F8h, 0F8h, 0F0h, 000h, 000h, 000h, 000h, 000h   ; глиф 100 @0x6C80
    DEFB 0F8h, 0F8h, 0F0h, 000h, 000h, 000h, 000h, 000h, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh
    DEFB 000h, 0E0h, 0E0h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 0F0h, 0F0h, 0F8h, 0F8h, 0F8h   ; глиф 101 @0x6CA0
    DEFB 0C0h, 0E0h, 0E0h, 0F0h, 0F0h, 0F8h, 0F8h, 0F8h, 03Fh, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh
    DEFB 00Eh, 001h, 003h, 003h, 000h, 000h, 000h, 000h, 00Eh, 001h, 003h, 003h, 000h, 000h, 000h, 000h   ; глиф 102 @0x6CC0
    DEFB 00Eh, 000h, 000h, 000h, 007h, 00Eh, 01Dh, 003h, 0F1h, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh, 0E2h, 0FCh
    DEFB 0C6h, 000h, 000h, 0ADh, 0E1h, 0D8h, 000h, 000h, 0C6h, 000h, 000h, 0ADh, 0E1h, 0D8h, 000h, 000h   ; глиф 103 @0x6CE0
    DEFB 000h, 07Ch, 038h, 000h, 01Eh, 000h, 0D8h, 08Ch, 0FFh, 0FFh, 0C7h, 0FFh, 0E1h, 0FFh, 0FFh, 073h
    DEFB 000h, 000h, 000h, 000h, 080h, 000h, 080h, 002h, 000h, 000h, 000h, 000h, 000h, 080h, 000h, 002h   ; глиф 104 @0x6D00
    DEFB 000h, 000h, 000h, 000h, 080h, 080h, 080h, 000h, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh
    DEFB 0F6h, 000h, 060h, 000h, 000h, 000h, 000h, 000h, 0F6h, 000h, 060h, 00Ah, 00Eh, 01Ch, 030h, 000h   ; глиф 105 @0x6D20
    DEFB 000h, 0F0h, 000h, 000h, 000h, 000h, 030h, 000h, 0FFh, 00Fh, 0FFh, 0FFh, 0F1h, 0E3h, 0CFh, 0FFh
    DEFB 030h, 0BAh, 0BBh, 000h, 0C6h, 0E1h, 0EFh, 000h, 030h, 0BAh, 0BBh, 000h, 0C6h, 0E1h, 0EFh, 000h   ; глиф 106 @0x6D40
    DEFB 000h, 000h, 000h, 037h, 000h, 000h, 000h, 0CFh, 0FFh, 0BAh, 0BBh, 000h, 0C6h, 0E1h, 0EFh, 030h
    DEFB 048h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 048h, 000h, 000h, 000h, 000h, 000h, 000h, 000h   ; глиф 107 @0x6D60
    DEFB 000h, 050h, 050h, 020h, 060h, 000h, 000h, 000h, 0FFh, 0FFh, 0FFh, 0FFh, 09Fh, 0FFh, 0FFh, 0FFh
    DEFB 000h, 07Ch, 07Ch, 07Ch, 038h, 008h, 088h, 000h, 038h, 000h, 07Ch, 07Ch, 038h, 008h, 088h, 000h   ; глиф 108 @0x6D80
    DEFB 038h, 000h, 07Ch, 07Ch, 038h, 000h, 000h, 048h, 0FFh, 0FFh, 0FFh, 0FFh, 0C7h, 0FFh, 0FFh, 0FFh
    DEFB 0C0h, 0E0h, 0E0h, 000h, 000h, 000h, 000h, 000h, 0C0h, 000h, 000h, 0E0h, 0C0h, 000h, 000h, 000h   ; глиф 109 @0x6DA0
    DEFB 0C0h, 000h, 000h, 0E0h, 0C0h, 000h, 000h, 000h, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh
    DEFB 000h, 01Fh, 01Fh, 01Fh, 00Eh, 001h, 000h, 000h, 00Eh, 000h, 000h, 01Fh, 00Eh, 001h, 000h, 000h   ; глиф 110 @0x6DC0
    DEFB 00Eh, 000h, 000h, 01Fh, 00Eh, 000h, 000h, 000h, 0FFh, 0FFh, 0FFh, 0FFh, 0F1h, 0FFh, 0FFh, 0FFh
    DEFB 01Fh, 03Fh, 000h, 000h, 000h, 07Ch, 0FEh, 0FFh, 000h, 000h, 03Fh, 07Fh, 07Fh, 083h, 001h, 020h   ; глиф 111 @0x6DE0
    DEFB 01Fh, 03Fh, 03Fh, 07Fh, 07Fh, 083h, 001h, 020h, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh, 0DFh
    DEFB 078h, 056h, 0FFh, 055h, 0FFh, 055h, 07Fh, 035h, 000h, 0A9h, 000h, 0AAh, 000h, 0AAh, 000h, 000h   ; глиф 112 @0x6E00
    DEFB 078h, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh, 07Fh, 035h, 0FFh, 0FFh, 0FFh, 0FFh, 01Fh, 0AAh, 080h, 0CAh
    DEFB 063h, 0F7h, 000h, 06Bh, 01Eh, 000h, 000h, 000h, 063h, 0F7h, 000h, 06Bh, 01Eh, 000h, 000h, 000h   ; глиф 113 @0x6E20
    DEFB 000h, 000h, 0F7h, 000h, 000h, 00Dh, 001h, 000h, 0FFh, 0FFh, 008h, 06Bh, 0FFh, 0F2h, 0FEh, 0FFh
    DEFB 001h, 000h, 002h, 003h, 000h, 000h, 000h, 000h, 000h, 003h, 002h, 003h, 001h, 000h, 000h, 000h   ; глиф 114 @0x6E40
    DEFB 000h, 003h, 002h, 003h, 001h, 000h, 000h, 000h, 0FFh, 0FFh, 0FDh, 0FCh, 0FFh, 0FFh, 0FFh, 0FFh
    DEFB 000h, 000h, 000h, 000h, 00Ch, 008h, 000h, 000h, 003h, 007h, 00Eh, 00Ch, 00Ch, 008h, 006h, 00Fh   ; глиф 115 @0x6E60
    DEFB 000h, 007h, 00Eh, 00Ch, 00Ch, 008h, 000h, 00Fh, 0FCh, 0F8h, 0F1h, 0F3h, 0F3h, 0F7h, 0F9h, 0F0h
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h   ; глиф 116 @0x6E80
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh
    DEFB 0FFh, 0FFh, 0EEh, 023h, 000h, 000h, 000h, 000h, 0F7h, 0CCh, 011h, 0DCh, 067h, 043h, 026h, 000h   ; глиф 117 @0x6EA0
    DEFB 0F7h, 0CCh, 011h, 0DCh, 067h, 043h, 026h, 000h, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh
    DEFB 0FFh, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh, 026h, 0ACh, 082h, 000h, 000h, 000h, 000h   ; глиф 118 @0x6EC0
    DEFB 0FFh, 0FFh, 0FFh, 0FFh, 0EFh, 0B2h, 099h, 002h, 000h, 0D9h, 053h, 07Dh, 0FFh, 0FFh, 0FFh, 0FFh
    DEFB 07Fh, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 07Fh, 000h, 000h, 000h, 000h, 000h, 000h, 000h   ; глиф 119 @0x6EE0
    DEFB 000h, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh, 07Fh, 07Fh, 07Fh, 07Fh, 07Fh, 07Fh, 07Fh, 03Fh, 000h
    DEFB 0FEh, 003h, 001h, 001h, 001h, 001h, 001h, 000h, 0FEh, 003h, 001h, 001h, 001h, 001h, 001h, 000h   ; глиф 120 @0x6F00
    DEFB 000h, 0FCh, 0FEh, 0FEh, 0FEh, 0FEh, 0FEh, 0FEh, 0FEh, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh, 000h
    DEFB 07Fh, 080h, 000h, 000h, 000h, 000h, 000h, 000h, 07Fh, 080h, 000h, 000h, 000h, 000h, 000h, 000h   ; глиф 121 @0x6F20
    DEFB 000h, 07Fh, 0FEh, 0FCh, 0FCh, 0FCh, 0FEh, 07Fh, 07Fh, 0FFh, 0FEh, 0FCh, 0FCh, 0FCh, 0FEh, 000h
    DEFB 0FEh, 003h, 0C0h, 0E0h, 0E0h, 000h, 000h, 000h, 0FEh, 003h, 0C0h, 0E0h, 0E0h, 000h, 000h, 000h   ; глиф 122 @0x6F40
    DEFB 000h, 0FCh, 03Fh, 01Fh, 01Fh, 01Fh, 03Fh, 0FEh, 0FEh, 0FFh, 0FFh, 0FFh, 0FFh, 01Fh, 03Fh, 000h
    DEFB 07Fh, 080h, 001h, 000h, 003h, 003h, 000h, 000h, 07Fh, 080h, 000h, 003h, 003h, 003h, 001h, 000h   ; глиф 123 @0x6F60
    DEFB 000h, 07Fh, 0FEh, 0FFh, 0FFh, 0FFh, 0FFh, 07Fh, 07Fh, 0FFh, 0FFh, 0FFh, 0FCh, 0FCh, 0FFh, 000h
    DEFB 0FEh, 003h, 0C0h, 0E0h, 0E0h, 000h, 000h, 000h, 0FEh, 003h, 0C0h, 000h, 000h, 0E0h, 0C0h, 000h   ; глиф 124 @0x6F80
    DEFB 000h, 0FCh, 0FFh, 01Fh, 01Fh, 0FFh, 0FFh, 0FEh, 0FEh, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh, 000h
    DEFB 07Fh, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 07Fh, 000h, 000h, 000h, 000h, 000h, 000h, 000h   ; глиф 125 @0x6FA0
    DEFB 000h, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh, 07Fh, 07Fh, 07Fh, 07Fh, 07Fh, 07Fh, 07Fh, 03Fh, 080h
    DEFB 0CCh, 0CCh, 0CCh, 0C7h, 0C0h, 0C0h, 0FFh, 07Fh, 033h, 033h, 033h, 038h, 03Fh, 03Fh, 000h, 000h   ; глиф 126 @0x6FC0
    DEFB 0CCh, 0CCh, 0CCh, 0C7h, 0C0h, 0C0h, 0FFh, 07Fh, 033h, 033h, 033h, 038h, 03Fh, 03Fh, 03Fh, 0FFh
    DEFB 0FFh, 0FFh, 0FFh, 0D7h, 0D8h, 0C0h, 0FFh, 07Fh, 000h, 0CCh, 000h, 0FFh, 0FFh, 0FFh, 0C0h, 07Fh   ; глиф 127 @0x6FE0
    DEFB 0CCh, 0CCh, 0CCh, 0FFh, 0FFh, 0FFh, 0FFh, 07Fh, 033h, 033h, 033h, 028h, 027h, 03Fh, 000h, 080h
    DEFB 033h, 033h, 033h, 0E3h, 003h, 003h, 0FFh, 0FEh, 0CCh, 0CCh, 0CCh, 01Ch, 0FCh, 0FCh, 000h, 000h   ; глиф 128 @0x7000
    DEFB 033h, 033h, 033h, 0E3h, 003h, 003h, 0FFh, 0FEh, 0CCh, 0CCh, 0CCh, 01Ch, 0FCh, 0FCh, 003h, 0FFh
    DEFB 07Fh, 0FFh, 0C0h, 0C1h, 0C0h, 0C1h, 0C1h, 0C0h, 000h, 000h, 03Fh, 03Eh, 03Fh, 03Eh, 03Eh, 03Fh   ; глиф 129 @0x7020
    DEFB 07Fh, 0FFh, 0C0h, 0C1h, 0C0h, 0C1h, 0C1h, 0C0h, 0FFh, 03Fh, 03Fh, 03Eh, 03Fh, 03Eh, 03Eh, 03Fh
    DEFB 0FEh, 0FFh, 003h, 083h, 003h, 083h, 083h, 0E3h, 000h, 000h, 0FCh, 07Ch, 0FCh, 07Ch, 07Ch, 01Ch   ; глиф 130 @0x7040
    DEFB 0FEh, 0FFh, 003h, 083h, 003h, 083h, 083h, 0E3h, 0FFh, 0FCh, 0FCh, 07Ch, 0FCh, 07Ch, 07Ch, 01Ch
    DEFB 000h, 000h, 000h, 000h, 000h, 074h, 0E8h, 000h, 01Ah, 0DCh, 0ECh, 074h, 074h, 074h, 0E8h, 0C0h   ; глиф 131 @0x7060
    DEFB 000h, 000h, 000h, 074h, 074h, 074h, 0E8h, 0C0h, 01Ah, 000h, 000h, 000h, 000h, 000h, 000h, 000h
    DEFB 03Fh, 03Fh, 01Fh, 007h, 000h, 001h, 000h, 003h, 000h, 000h, 000h, 000h, 003h, 001h, 001h, 003h   ; глиф 132 @0x7080
    DEFB 03Fh, 03Fh, 01Fh, 007h, 003h, 001h, 000h, 003h, 0C0h, 0C0h, 0E0h, 0F8h, 0FCh, 0FEh, 0FFh, 0FCh
    DEFB 0FCh, 0FCh, 0F8h, 0E0h, 000h, 000h, 000h, 0C0h, 000h, 000h, 000h, 000h, 0C0h, 080h, 080h, 0C0h   ; глиф 133 @0x70A0
    DEFB 0FCh, 0FCh, 0F8h, 0E0h, 000h, 080h, 000h, 0C0h, 003h, 003h, 007h, 01Fh, 0FFh, 07Fh, 0FFh, 03Fh
    DEFB 007h, 01Fh, 03Fh, 038h, 07Eh, 07Fh, 07Dh, 073h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h   ; глиф 134 @0x70C0
    DEFB 007h, 01Fh, 03Fh, 038h, 07Eh, 07Fh, 07Dh, 073h, 0F8h, 0E0h, 0C0h, 0C7h, 081h, 080h, 082h, 08Ch
    DEFB 0E0h, 0F8h, 0FCh, 01Ch, 07Eh, 0FEh, 0BEh, 0CEh, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h   ; глиф 135 @0x70E0
    DEFB 0E0h, 0F8h, 0FCh, 01Ch, 07Eh, 0FEh, 0BEh, 0CEh, 01Fh, 007h, 003h, 0E3h, 081h, 001h, 041h, 031h
    DEFB 03Fh, 03Fh, 01Fh, 007h, 000h, 001h, 000h, 07Dh, 000h, 000h, 000h, 000h, 003h, 001h, 001h, 0FFh   ; глиф 136 @0x7100
    DEFB 03Fh, 03Fh, 01Fh, 007h, 003h, 001h, 000h, 07Dh, 0C0h, 0C0h, 0E0h, 0F8h, 0FCh, 0FEh, 0FFh, 082h
    DEFB 0FCh, 0FCh, 0F8h, 0E0h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 0C0h, 080h, 080h, 0FFh   ; глиф 137 @0x7120
    DEFB 0FCh, 0FCh, 0F8h, 0E0h, 000h, 080h, 000h, 0BEh, 003h, 003h, 007h, 01Fh, 0FFh, 07Fh, 0FFh, 041h
    DEFB 000h, 0EEh, 07Ch, 07Ch, 0D6h, 0D6h, 07Ch, 038h, 000h, 0EEh, 07Ch, 000h, 0D6h, 0D6h, 07Ch, 038h   ; глиф 138 @0x7140
    DEFB 000h, 0EEh, 07Ch, 000h, 0D6h, 0D6h, 07Ch, 038h, 0FFh, 011h, 083h, 083h, 029h, 029h, 083h, 0C7h
    DEFB 000h, 000h, 000h, 000h, 00Ch, 01Eh, 016h, 00Ch, 07Fh, 07Fh, 03Fh, 00Fh, 00Ch, 01Eh, 016h, 00Ch   ; глиф 139 @0x7160
    DEFB 07Fh, 07Fh, 03Fh, 00Fh, 00Ch, 01Eh, 016h, 00Ch, 080h, 080h, 0C0h, 0F0h, 0F3h, 0E1h, 0E9h, 0F3h
    DEFB 000h, 000h, 000h, 000h, 060h, 0F0h, 0B0h, 060h, 0FCh, 0FCh, 0F8h, 0E0h, 060h, 0F0h, 0B0h, 060h   ; глиф 140 @0x7180
    DEFB 000h, 000h, 000h, 0E0h, 060h, 0F0h, 0B0h, 060h, 0FFh, 0FFh, 0FFh, 01Fh, 09Fh, 00Fh, 04Fh, 09Fh
    DEFB 000h, 000h, 001h, 001h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 001h, 0FFh, 0FFh, 0FFh   ; глиф 141 @0x71A0
    DEFB 000h, 000h, 000h, 000h, 001h, 0E0h, 0FCh, 0FEh, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh, 01Fh, 003h, 001h
    DEFB 060h, 0C0h, 080h, 080h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 080h, 0FEh, 0FEh, 0FEh   ; глиф 142 @0x71C0
    DEFB 000h, 000h, 000h, 000h, 080h, 000h, 000h, 000h, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh
    DEFB 000h, 000h, 000h, 000h, 00Ch, 01Eh, 01Ah, 00Ch, 01Fh, 00Fh, 00Fh, 007h, 00Ch, 01Eh, 01Ah, 00Ch   ; глиф 143 @0x71E0
    DEFB 01Fh, 00Fh, 00Fh, 007h, 00Ch, 01Eh, 01Ah, 00Ch, 0E0h, 0F0h, 0F0h, 0F8h, 0F3h, 0E1h, 0E5h, 0F3h
    DEFB 000h, 000h, 000h, 000h, 060h, 0F0h, 0D0h, 060h, 0F0h, 0E0h, 0E0h, 0C0h, 060h, 0F0h, 0D0h, 060h   ; глиф 144 @0x7200
    DEFB 000h, 000h, 000h, 0C0h, 060h, 0F0h, 0D0h, 060h, 0FFh, 0FFh, 0FFh, 03Fh, 09Fh, 00Fh, 02Fh, 09Fh
    DEFB 00Ch, 006h, 003h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 003h, 01Fh, 01Fh, 01Fh, 01Fh   ; глиф 145 @0x7220
    DEFB 000h, 000h, 000h, 003h, 000h, 01Fh, 01Fh, 01Fh, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh, 0E0h, 0E0h, 0E0h
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 0F0h, 0F0h, 0F0h, 0F0h   ; глиф 146 @0x7240
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh
    DEFB 000h, 000h, 038h, 000h, 01Eh, 007h, 001h, 000h, 079h, 078h, 038h, 03Ch, 01Eh, 007h, 001h, 000h   ; глиф 147 @0x7260
    DEFB 079h, 078h, 038h, 03Ch, 01Eh, 007h, 001h, 000h, 086h, 087h, 0C7h, 0C3h, 0E1h, 0F8h, 0FEh, 0FFh
    DEFB 000h, 000h, 000h, 07Ch, 000h, 01Eh, 0C7h, 000h, 0F0h, 0F8h, 0F8h, 07Ch, 03Ch, 01Eh, 0C7h, 000h   ; глиф 148 @0x7280
    DEFB 0F0h, 0F8h, 0F8h, 07Ch, 03Ch, 01Eh, 0C7h, 000h, 00Fh, 007h, 007h, 083h, 0C3h, 0E1h, 038h, 0FFh
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 01Fh, 03Fh, 03Fh, 05Bh, 05Bh, 05Bh, 05Bh, 07Fh   ; глиф 149 @0x72A0
    DEFB 000h, 000h, 03Fh, 05Bh, 05Bh, 05Bh, 05Bh, 07Fh, 0FFh, 0FFh, 0C0h, 0A4h, 0A4h, 0A4h, 0A4h, 080h
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 0C0h, 0E0h, 0E0h, 0E0h, 0F0h, 0F0h, 0F0h   ; глиф 150 @0x72C0
    DEFB 000h, 000h, 000h, 000h, 0E0h, 000h, 0F0h, 0F0h, 0FFh, 0FFh, 0FFh, 0FFh, 01Fh, 0FFh, 00Fh, 00Fh
    DEFB 000h, 000h, 01Fh, 000h, 03Ch, 078h, 0E3h, 000h, 00Fh, 01Fh, 01Fh, 03Eh, 03Ch, 078h, 0E3h, 000h   ; глиф 151 @0x72E0
    DEFB 00Fh, 01Fh, 01Fh, 03Eh, 03Ch, 078h, 0E3h, 000h, 0F0h, 0E0h, 0E0h, 0C1h, 0C3h, 087h, 01Ch, 0FFh
    DEFB 000h, 000h, 000h, 03Ch, 000h, 0E0h, 080h, 000h, 09Eh, 01Eh, 01Ch, 03Ch, 078h, 0E0h, 080h, 000h   ; глиф 152 @0x7300
    DEFB 09Eh, 01Eh, 01Ch, 03Ch, 078h, 0E0h, 080h, 000h, 061h, 0E1h, 0E3h, 0C3h, 087h, 01Fh, 07Fh, 0FFh
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 003h, 007h, 007h, 007h, 00Fh, 00Fh, 00Fh   ; глиф 153 @0x7320
    DEFB 000h, 000h, 000h, 007h, 007h, 00Fh, 00Fh, 00Fh, 0FFh, 0FFh, 0FFh, 0F8h, 0F8h, 0F0h, 0F0h, 0F0h
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 0F8h, 0FCh, 0FCh, 0DAh, 0DAh, 0DAh, 0DAh, 0FEh   ; глиф 154 @0x7340
    DEFB 000h, 000h, 000h, 000h, 0DAh, 000h, 0DAh, 0FEh, 0FFh, 0FFh, 0FFh, 0FFh, 025h, 0FFh, 025h, 001h
    DEFB 03Ch, 07Eh, 0FCh, 0F0h, 006h, 006h, 000h, 000h, 000h, 000h, 003h, 00Fh, 0FFh, 0FFh, 07Eh, 03Ch   ; глиф 155 @0x7360
    DEFB 000h, 000h, 003h, 00Fh, 0FFh, 0FFh, 07Eh, 03Ch, 0FFh, 0FFh, 0FFh, 0FFh, 0F9h, 0F9h, 07Eh, 03Ch
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 0DFh, 0DFh, 0DFh, 000h, 0FBh, 0FBh, 0FBh   ; глиф 156 @0x7380
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 0DFh, 0DFh, 000h, 000h, 0FBh, 0FBh
    DEFB 000h, 07Eh, 07Eh, 07Eh, 07Eh, 03Ch, 000h, 000h, 03Ch, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh   ; глиф 157 @0x73A0
    DEFB 03Ch, 07Eh, 0FFh, 0FFh, 0FFh, 0FFh, 07Eh, 03Ch, 000h, 000h, 000h, 000h, 000h, 000h, 081h, 0C3h
    DEFB 0FFh, 0FFh, 07Eh, 000h, 07Eh, 0FFh, 099h, 099h, 00Ch, 00Ch, 0FFh, 0FFh, 000h, 01Eh, 0FFh, 0FFh   ; глиф 158 @0x73C0
    DEFB 0FFh, 0FFh, 07Eh, 03Ch, 07Eh, 0FFh, 099h, 099h, 0F3h, 0F3h, 081h, 0FFh, 07Eh, 0E1h, 066h, 066h
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h   ; глиф 159 @0x73E0
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh
    DEFB 07Fh, 07Fh, 07Fh, 03Fh, 03Fh, 01Fh, 00Fh, 003h, 01Fh, 01Fh, 01Fh, 01Fh, 00Fh, 00Fh, 007h, 003h   ; глиф 160 @0x7400
    DEFB 01Fh, 01Fh, 01Fh, 01Fh, 00Fh, 00Fh, 007h, 003h, 080h, 080h, 080h, 0C0h, 0C0h, 0E0h, 0F0h, 0FCh
    DEFB 00Eh, 00Dh, 00Bh, 007h, 03Fh, 03Fh, 007h, 03Fh, 000h, 000h, 000h, 001h, 001h, 031h, 000h, 00Fh   ; глиф 161 @0x7420
    DEFB 000h, 000h, 000h, 001h, 001h, 031h, 000h, 00Fh, 0F1h, 0F2h, 0F4h, 0F8h, 0C0h, 0C0h, 0F8h, 0C0h
    DEFB 0B6h, 0B6h, 0B6h, 0B4h, 0FCh, 0F8h, 0F0h, 0C0h, 0B6h, 0B6h, 0B6h, 0B4h, 0FCh, 0F8h, 0F0h, 0C0h   ; глиф 162 @0x7440
    DEFB 0B6h, 0B6h, 0B6h, 0B4h, 0FCh, 0F8h, 0F0h, 0C0h, 049h, 049h, 049h, 04Bh, 003h, 007h, 00Fh, 03Fh
    DEFB 0F0h, 0F8h, 0FCh, 0FCh, 0F8h, 0FCh, 0FEh, 0FCh, 020h, 070h, 0D8h, 0ECh, 0F0h, 0F4h, 002h, 0FCh   ; глиф 163 @0x7460
    DEFB 020h, 070h, 0D8h, 0ECh, 0F0h, 0F4h, 002h, 0FCh, 00Fh, 007h, 003h, 003h, 007h, 003h, 001h, 003h
    DEFB 07Fh, 07Fh, 07Fh, 03Fh, 03Fh, 01Fh, 00Fh, 003h, 01Fh, 01Fh, 01Fh, 01Fh, 00Fh, 00Fh, 007h, 003h   ; глиф 164 @0x7480
    DEFB 01Fh, 01Fh, 01Fh, 01Fh, 00Fh, 00Fh, 007h, 003h, 080h, 080h, 080h, 0C0h, 0C0h, 0E0h, 0F0h, 0FCh
    DEFB 01Fh, 03Eh, 03Fh, 00Fh, 01Fh, 01Fh, 00Fh, 03Fh, 007h, 00Eh, 000h, 006h, 00Eh, 00Dh, 000h, 00Fh   ; глиф 165 @0x74A0
    DEFB 007h, 00Eh, 000h, 006h, 00Eh, 00Dh, 000h, 00Fh, 0E0h, 0C1h, 0C0h, 0F0h, 0E0h, 0E0h, 0F0h, 0C0h
    DEFB 0B6h, 0B6h, 0B6h, 0B4h, 0FCh, 0F8h, 0F0h, 0C0h, 0B6h, 0B6h, 0B6h, 0B4h, 0FCh, 0F8h, 0F0h, 0C0h   ; глиф 166 @0x74C0
    DEFB 0B6h, 0B6h, 0B6h, 0B4h, 0FCh, 0F8h, 0F0h, 0C0h, 049h, 049h, 049h, 04Bh, 003h, 007h, 00Fh, 03Fh
    DEFB 038h, 07Ch, 0FEh, 0F6h, 0F0h, 0F0h, 0F0h, 0FCh, 000h, 038h, 01Ch, 0E6h, 0F0h, 0F0h, 000h, 0FCh   ; глиф 167 @0x74E0
    DEFB 000h, 038h, 01Ch, 0E6h, 0F0h, 0F0h, 000h, 0FCh, 0C7h, 083h, 001h, 009h, 00Fh, 00Fh, 00Fh, 003h
    DEFB 07Fh, 07Fh, 07Fh, 03Fh, 03Fh, 01Fh, 00Fh, 003h, 01Fh, 01Fh, 01Fh, 01Fh, 00Fh, 00Fh, 007h, 003h   ; глиф 168 @0x7500
    DEFB 01Fh, 01Fh, 01Fh, 01Fh, 00Fh, 00Fh, 007h, 003h, 080h, 080h, 080h, 0C0h, 0C0h, 0E0h, 0F0h, 0FCh
    DEFB 00Fh, 00Fh, 007h, 01Fh, 01Fh, 01Fh, 00Fh, 03Fh, 003h, 003h, 001h, 00Bh, 00Bh, 007h, 000h, 00Fh   ; глиф 169 @0x7520
    DEFB 003h, 003h, 001h, 00Bh, 00Bh, 007h, 000h, 00Fh, 0F0h, 0F0h, 0F8h, 0E0h, 0E0h, 0E0h, 0F0h, 0C0h
    DEFB 0B6h, 0B6h, 0B6h, 0B4h, 0FCh, 0F8h, 0F0h, 0C0h, 0B6h, 0B6h, 0B6h, 0B4h, 0FCh, 0F8h, 0F0h, 0C0h   ; глиф 170 @0x7540
    DEFB 0B6h, 0B6h, 0B6h, 0B4h, 0FCh, 0F8h, 0F0h, 0C0h, 049h, 049h, 049h, 04Bh, 003h, 007h, 00Fh, 03Fh
    DEFB 0FCh, 0F8h, 0F8h, 0FCh, 0FCh, 0FCh, 0F8h, 0FCh, 0ECh, 0D8h, 000h, 0E4h, 0F4h, 0F4h, 000h, 0FCh   ; глиф 171 @0x7560
    DEFB 0ECh, 0D8h, 000h, 0E4h, 0F4h, 0F4h, 000h, 0FCh, 003h, 007h, 007h, 003h, 003h, 003h, 007h, 003h
    DEFB 06Dh, 06Dh, 06Dh, 02Dh, 03Fh, 01Fh, 00Fh, 003h, 06Dh, 06Dh, 06Dh, 02Dh, 03Fh, 01Fh, 00Fh, 003h   ; глиф 172 @0x7580
    DEFB 06Dh, 06Dh, 06Dh, 02Dh, 03Fh, 01Fh, 00Fh, 003h, 092h, 092h, 092h, 0D2h, 0C0h, 0E0h, 0F0h, 0FCh
    DEFB 00Fh, 01Fh, 03Fh, 03Fh, 01Fh, 03Fh, 07Fh, 03Fh, 004h, 00Eh, 01Bh, 037h, 00Fh, 02Fh, 040h, 03Fh   ; глиф 173 @0x75A0
    DEFB 004h, 00Eh, 01Bh, 037h, 00Fh, 02Fh, 040h, 03Fh, 0F0h, 0E0h, 0C0h, 0C0h, 0E0h, 0C0h, 080h, 0C0h
    DEFB 0FEh, 0FEh, 0FEh, 0FCh, 0FCh, 0F8h, 0F0h, 0C0h, 0F8h, 0F8h, 0F8h, 0F8h, 0F0h, 0F0h, 0E0h, 0C0h   ; глиф 174 @0x75C0
    DEFB 0F8h, 0F8h, 0F8h, 0F8h, 0F0h, 0F0h, 0E0h, 0C0h, 001h, 001h, 001h, 003h, 003h, 007h, 00Fh, 03Fh
    DEFB 070h, 0F0h, 0F0h, 0FCh, 0FCh, 0F8h, 0F0h, 0FCh, 000h, 000h, 000h, 080h, 080h, 088h, 000h, 0F0h   ; глиф 175 @0x75E0
    DEFB 000h, 000h, 000h, 080h, 080h, 088h, 000h, 0F0h, 08Fh, 00Fh, 00Fh, 003h, 003h, 007h, 00Fh, 003h
    DEFB 06Dh, 06Dh, 06Dh, 02Dh, 03Fh, 01Fh, 00Fh, 003h, 06Dh, 06Dh, 06Dh, 02Dh, 03Fh, 01Fh, 00Fh, 003h   ; глиф 176 @0x7600
    DEFB 06Dh, 06Dh, 06Dh, 02Dh, 03Fh, 01Fh, 00Fh, 003h, 092h, 092h, 092h, 0D2h, 0C0h, 0E0h, 0F0h, 0FCh
    DEFB 01Ch, 03Eh, 07Fh, 06Fh, 00Fh, 00Fh, 00Fh, 03Fh, 000h, 01Ch, 038h, 067h, 00Fh, 00Fh, 000h, 03Fh   ; глиф 177 @0x7620
    DEFB 000h, 01Ch, 038h, 067h, 00Fh, 00Fh, 000h, 03Fh, 0E3h, 0C1h, 080h, 090h, 0F0h, 0F0h, 0F0h, 0C0h
    DEFB 0FEh, 0FEh, 0FEh, 0FCh, 0FCh, 0F8h, 0F0h, 0C0h, 0F8h, 0F8h, 0F8h, 0F8h, 0F0h, 0F0h, 0E0h, 0C0h   ; глиф 178 @0x7640
    DEFB 0F8h, 0F8h, 0F8h, 0F8h, 0F0h, 0F0h, 0E0h, 0C0h, 001h, 001h, 001h, 003h, 003h, 007h, 00Fh, 03Fh
    DEFB 0F8h, 07Ch, 0FCh, 0F0h, 0F8h, 0F8h, 0F0h, 0FCh, 0E0h, 070h, 000h, 060h, 070h, 0B0h, 0B0h, 0F0h   ; глиф 179 @0x7660
    DEFB 0E0h, 070h, 000h, 060h, 070h, 0B0h, 0B0h, 0F0h, 007h, 083h, 003h, 00Fh, 007h, 007h, 00Fh, 003h
    DEFB 06Dh, 06Dh, 06Dh, 02Dh, 03Fh, 01Fh, 00Fh, 003h, 06Dh, 06Dh, 06Dh, 02Dh, 03Fh, 01Fh, 00Fh, 003h   ; глиф 180 @0x7680
    DEFB 06Dh, 06Dh, 06Dh, 02Dh, 03Fh, 01Fh, 00Fh, 003h, 092h, 092h, 092h, 0D2h, 0C0h, 0E0h, 0F0h, 0FCh
    DEFB 03Fh, 01Fh, 00Fh, 03Fh, 03Fh, 03Fh, 01Fh, 03Fh, 037h, 01Bh, 000h, 027h, 02Fh, 02Fh, 000h, 03Fh   ; глиф 181 @0x76A0
    DEFB 037h, 01Bh, 000h, 027h, 02Fh, 02Fh, 000h, 03Fh, 0C0h, 0E0h, 0F0h, 0C0h, 0C0h, 0C0h, 0E0h, 0C0h
    DEFB 0FEh, 0FEh, 0FEh, 0FCh, 0FCh, 0F8h, 0F0h, 0C0h, 0F8h, 0F8h, 0F8h, 0F8h, 0F0h, 0F0h, 0E0h, 0C0h   ; глиф 182 @0x76C0
    DEFB 0F8h, 0F8h, 0F8h, 0F8h, 0F0h, 0F0h, 0E0h, 0C0h, 001h, 001h, 001h, 003h, 003h, 007h, 00Fh, 03Fh
    DEFB 0F0h, 0F0h, 0E0h, 0F8h, 0F8h, 0F8h, 0F0h, 0FCh, 0C0h, 0C0h, 080h, 0D0h, 0D0h, 0E0h, 000h, 0F0h   ; глиф 183 @0x76E0
    DEFB 0C0h, 0C0h, 080h, 0D0h, 0D0h, 0E0h, 000h, 0F0h, 00Fh, 00Fh, 01Fh, 007h, 007h, 007h, 00Fh, 003h
    DEFB 07Dh, 07Dh, 07Dh, 03Dh, 03Fh, 01Fh, 00Fh, 003h, 07Dh, 07Dh, 07Dh, 03Dh, 03Fh, 01Fh, 00Fh, 003h   ; глиф 184 @0x7700
    DEFB 07Dh, 07Dh, 07Dh, 03Dh, 03Fh, 01Fh, 00Fh, 003h, 082h, 082h, 082h, 0C2h, 0C0h, 0E0h, 0F0h, 0FCh
    DEFB 07Eh, 03Eh, 00Fh, 00Fh, 07Fh, 03Fh, 00Fh, 03Fh, 07Ch, 03Ch, 000h, 007h, 04Fh, 02Fh, 000h, 03Fh   ; глиф 185 @0x7720
    DEFB 07Ch, 03Ch, 000h, 007h, 04Fh, 02Fh, 000h, 03Fh, 081h, 0C1h, 0F0h, 0F0h, 080h, 0C0h, 0F0h, 0C0h
    DEFB 0BEh, 0BEh, 0BEh, 0BCh, 0FCh, 0F8h, 0F0h, 0C0h, 0B8h, 0B8h, 0B8h, 0B8h, 0F0h, 0F0h, 0E0h, 0C0h   ; глиф 186 @0x7740
    DEFB 0B8h, 0B8h, 0B8h, 0B8h, 0F0h, 0F0h, 0E0h, 0C0h, 041h, 041h, 041h, 043h, 003h, 007h, 00Fh, 03Fh
    DEFB 07Eh, 07Ch, 0F0h, 0F0h, 0FEh, 0FCh, 0F0h, 0FCh, 038h, 030h, 000h, 080h, 0C0h, 0CCh, 000h, 0F0h   ; глиф 187 @0x7760
    DEFB 038h, 030h, 000h, 080h, 0C0h, 0CCh, 000h, 0F0h, 081h, 083h, 00Fh, 00Fh, 001h, 003h, 00Fh, 003h
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 072h, 045h, 075h, 000h, 0FFh, 080h, 080h, 0FFh   ; глиф 188 @0x7780
    DEFB 072h, 045h, 075h, 000h, 0FFh, 080h, 080h, 0FFh, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 0FFh, 080h, 080h, 0FFh, 000h, 075h, 045h   ; глиф 189 @0x77A0
    DEFB 000h, 0FFh, 080h, 080h, 0FFh, 000h, 075h, 045h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 048h, 048h, 05Ch, 000h, 0FFh, 001h, 001h, 0FFh   ; глиф 190 @0x77C0
    DEFB 048h, 048h, 05Ch, 000h, 0FFh, 001h, 001h, 0FFh, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 0FFh, 001h, 001h, 0FFh, 000h, 048h, 048h   ; глиф 191 @0x77E0
    DEFB 000h, 0FFh, 001h, 001h, 0FFh, 000h, 048h, 048h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h
    DEFB 000h, 0CEh, 0DBh, 0FBh, 0DBh, 0CEh, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h   ; глиф 192 @0x7800
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h
    DEFB 000h, 07Eh, 0CCh, 07Ch, 00Ch, 078h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h   ; глиф 193 @0x7820
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h
    DEFB 000h, 078h, 0CCh, 0CCh, 0F8h, 0C0h, 078h, 004h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h   ; глиф 194 @0x7840
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h
    DEFB 006h, 0FEh, 0CCh, 0CCh, 0CCh, 0CCh, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h   ; глиф 195 @0x7860
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h
    DEFB 0C3h, 0FFh, 066h, 066h, 066h, 07Eh, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h   ; глиф 196 @0x7880
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h
    DEFB 000h, 07Ch, 0C0h, 0FCh, 0CCh, 078h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h   ; глиф 197 @0x78A0
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h
    DEFB 018h, 018h, 07Eh, 0DBh, 0DBh, 07Eh, 018h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h   ; глиф 198 @0x78C0
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h
    DEFB 000h, 0C0h, 0C0h, 0C0h, 0C0h, 0FCh, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h   ; глиф 199 @0x78E0
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h
    DEFB 000h, 0C6h, 06Ch, 038h, 06Ch, 0C6h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h   ; глиф 200 @0x7900
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h
    DEFB 000h, 0CCh, 0ECh, 0DCh, 0CCh, 0CCh, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h   ; глиф 201 @0x7920
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h
    DEFB 000h, 0CCh, 0ECh, 0DCh, 0CCh, 0CCh, 000h, 030h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h   ; глиф 202 @0x7940
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h
    DEFB 000h, 0CCh, 0CCh, 0F0h, 0D8h, 0CCh, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h   ; глиф 203 @0x7960
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h
    DEFB 000h, 0C6h, 066h, 036h, 01Eh, 00Eh, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h   ; глиф 204 @0x7980
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h
    DEFB 000h, 0C6h, 0C6h, 0D6h, 0EEh, 0C6h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h   ; глиф 205 @0x79A0
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h
    DEFB 000h, 0CCh, 0CCh, 0FCh, 0CCh, 0CCh, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h   ; глиф 206 @0x79C0
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h
    DEFB 000h, 078h, 0CCh, 0CCh, 0CCh, 078h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h   ; глиф 207 @0x79E0
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h
    DEFB 000h, 0CCh, 0CCh, 0CCh, 0CCh, 0FCh, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h   ; глиф 208 @0x7A00
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h
    DEFB 000h, 0CCh, 06Ch, 07Ch, 0CCh, 07Ch, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h   ; глиф 209 @0x7A20
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h
    DEFB 0C0h, 0C0h, 0F8h, 0CCh, 0CCh, 0F8h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h   ; глиф 210 @0x7A40
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h
    DEFB 000h, 078h, 0CCh, 0C0h, 0CCh, 078h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h   ; глиф 211 @0x7A60
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h
    DEFB 000h, 030h, 030h, 030h, 030h, 0FCh, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h   ; глиф 212 @0x7A80
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h
    DEFB 078h, 0CCh, 00Ch, 07Ch, 0CCh, 0CCh, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h   ; глиф 213 @0x7AA0
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h
    DEFB 000h, 0DBh, 07Eh, 018h, 07Eh, 0DBh, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h   ; глиф 214 @0x7AC0
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h
    DEFB 000h, 0FCh, 0C6h, 0F8h, 0CCh, 0F8h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h   ; глиф 215 @0x7AE0
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h
    DEFB 000h, 0F8h, 0CCh, 0F8h, 0C0h, 0C0h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h   ; глиф 216 @0x7B00
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h
    DEFB 000h, 0F2h, 0DAh, 0F2h, 0C2h, 0C2h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h   ; глиф 217 @0x7B20
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h
    DEFB 000h, 078h, 0CCh, 018h, 0CCh, 078h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h   ; глиф 218 @0x7B40
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h
    DEFB 000h, 0FEh, 0D6h, 0D6h, 0D6h, 0D6h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h   ; глиф 219 @0x7B60
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h
    DEFB 000h, 07Ch, 0C6h, 01Eh, 0C6h, 07Ch, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h   ; глиф 220 @0x7B80
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h
    DEFB 003h, 0FFh, 0D6h, 0D6h, 0D6h, 0D6h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h   ; глиф 221 @0x7BA0
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h
    DEFB 000h, 00Ch, 00Ch, 07Ch, 0CCh, 0CCh, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h   ; глиф 222 @0x7BC0
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h
    DEFB 000h, 03Eh, 033h, 03Eh, 030h, 0F0h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h   ; глиф 223 @0x7BE0
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h
    DEFB 000h, 0CEh, 0DBh, 0DBh, 0FBh, 0DBh, 0DBh, 0CEh, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h   ; глиф 224 @0x7C00
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h
    DEFB 000h, 0C6h, 0C6h, 0FEh, 066h, 036h, 01Eh, 00Eh, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h   ; глиф 225 @0x7C20
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h
    DEFB 000h, 0FCh, 0C6h, 0C6h, 0FCh, 0C0h, 0C0h, 0FCh, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h   ; глиф 226 @0x7C40
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h
    DEFB 006h, 0FEh, 0CCh, 0CCh, 0CCh, 0CCh, 0CCh, 0CCh, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h   ; глиф 227 @0x7C60
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h
    DEFB 0C3h, 0FFh, 066h, 066h, 066h, 066h, 066h, 07Eh, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h   ; глиф 228 @0x7C80
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h
    DEFB 000h, 0FEh, 0C0h, 0C0h, 0F8h, 0C0h, 0C0h, 0FCh, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h   ; глиф 229 @0x7CA0
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h
    DEFB 000h, 018h, 07Eh, 0DBh, 0DBh, 0DBh, 07Eh, 018h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h   ; глиф 230 @0x7CC0
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h
    DEFB 000h, 0C0h, 0C0h, 0C0h, 0C0h, 0C0h, 0C0h, 0FCh, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h   ; глиф 231 @0x7CE0
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h
    DEFB 000h, 0C3h, 066h, 03Ch, 018h, 03Ch, 066h, 0C3h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h   ; глиф 232 @0x7D00
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h
    DEFB 000h, 0C6h, 0E6h, 0F6h, 0DEh, 0CEh, 0C6h, 0C6h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h   ; глиф 233 @0x7D20
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h
    DEFB 000h, 0C6h, 0E6h, 0F6h, 0DEh, 0CEh, 0C6h, 0D6h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h   ; глиф 234 @0x7D40
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h
    DEFB 000h, 0C6h, 0C6h, 0CCh, 0F8h, 0D8h, 0CCh, 0C6h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h   ; глиф 235 @0x7D60
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h
    DEFB 000h, 0C6h, 0C6h, 066h, 036h, 01Eh, 00Eh, 006h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h   ; глиф 236 @0x7D80
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h
    DEFB 000h, 0C6h, 0C6h, 0C6h, 0D6h, 0FEh, 0EEh, 0C6h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h   ; глиф 237 @0x7DA0
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h
    DEFB 000h, 0C6h, 0C6h, 0C6h, 0FEh, 0C6h, 0C6h, 0C6h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h   ; глиф 238 @0x7DC0
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h
    DEFB 000h, 07Ch, 0C6h, 0C6h, 0C6h, 0C6h, 0C6h, 07Ch, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h   ; глиф 239 @0x7DE0
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h
    DEFB 000h, 0C6h, 0C6h, 0C6h, 0C6h, 0C6h, 0C6h, 0FEh, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h   ; глиф 240 @0x7E00
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h
    DEFB 000h, 0C6h, 066h, 036h, 07Eh, 0C6h, 0C6h, 07Eh, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h   ; глиф 241 @0x7E20
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h
    DEFB 000h, 0C0h, 0C0h, 0C0h, 0FCh, 0C6h, 0C6h, 0FCh, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h   ; глиф 242 @0x7E40
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h
    DEFB 000h, 07Ch, 0C6h, 0C0h, 0C0h, 0C0h, 0C6h, 07Ch, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h   ; глиф 243 @0x7E60
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h
    DEFB 000h, 030h, 030h, 030h, 030h, 030h, 030h, 0FCh, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h   ; глиф 244 @0x7E80
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h
    DEFB 000h, 07Ch, 0C6h, 006h, 07Eh, 0C6h, 0C6h, 0C6h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h   ; глиф 245 @0x7EA0
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h
    DEFB 000h, 0DBh, 0DBh, 07Eh, 018h, 07Eh, 0DBh, 0DBh, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h   ; глиф 246 @0x7EC0
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h
    DEFB 000h, 0FCh, 0C6h, 0C6h, 0FCh, 0CCh, 0CCh, 0F8h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h   ; глиф 247 @0x7EE0
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h
    DEFB 000h, 0FCh, 0C6h, 0C6h, 0FCh, 0C0h, 0C0h, 0C0h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h   ; глиф 248 @0x7F00
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h
    DEFB 000h, 0F2h, 0DAh, 0DAh, 0F2h, 0C2h, 0C2h, 0C2h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h   ; глиф 249 @0x7F20
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h
    DEFB 000h, 07Ch, 0C6h, 006h, 03Ch, 006h, 066h, 03Ch, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h   ; глиф 250 @0x7F40
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h
    DEFB 000h, 0FEh, 0D6h, 0D6h, 0D6h, 0D6h, 0D6h, 0D6h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h   ; глиф 251 @0x7F60
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h
    DEFB 000h, 07Ch, 0C6h, 006h, 01Eh, 006h, 0C6h, 07Ch, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h   ; глиф 252 @0x7F80
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h
    DEFB 003h, 0FFh, 0D6h, 0D6h, 0D6h, 0D6h, 0D6h, 0D6h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h   ; глиф 253 @0x7FA0
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h
    DEFB 0EFh, 07Dh, 032h, 000h, 000h, 000h, 000h, 000h, 010h, 082h, 0CDh, 07Fh, 03Ah, 0B0h, 010h, 008h   ; глиф 254 @0x7FC0
    DEFB 010h, 082h, 0CDh, 07Fh, 03Ah, 0B0h, 010h, 008h, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh
    DEFB 000h, 03Eh, 033h, 033h, 03Eh, 030h, 030h, 0F0h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h   ; глиф 255 @0x7FE0
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h
