; Данные: data_glyph_block_unpacked
; Адрес: 0x6000 (этап A; переносится константой GLYPH_BASE в gen_layout.py)
; Размер: 5048 байт (Tier 2: 131 одноплоскостных глифов сжаты 32->8 Б, 125 raw)
; Tier 2 (поверх Стадии 1): глифы с ненулевой ТОЛЬКО плоскостью 0x8000
;   (буквы) хранятся 8-байтной маской; ptr_table bit0=1 = признак compact.
;   func_render_glyph по тегу пишет маску в 0x8000 и нули в A000/C000/E000,
;   raw-глифы копируются 32Б как прежде -> VRAM побайтово идентичен.
; Предыдущие осознанные отхождения (Фаза 3 инверсия E000, Стадия 1 15<->8)
;   сохранены внутри масок/сырых записей.
; Фаза 4 (мигание выхода): в placeholder-слотах глифов 18..21 (@+528..+655)
;   записаны тёмно-синие варианты глифов выхода 188..191: маска в A000+E000,
;   C000=0 -> физ. индекс 5 -> слот палитры 0C9h (тёмно-синий).
; SHA256 этого компактного блока = aafc14a4c0594732631e83ca837e8eb639c31c23d695264e5a6b8eaa03276318
;   (до OR-реформата погонщика (глифы 2..5: П3=0, П2=П1=S, маска ¬S в П0/0xE000 —
;    вывод как у героя через func_render_tile_vram_or) — 817bb59fea764c85730c08d97c7768d87177db82abbbe95e7a490380d49317f7;
;    до плоской маски погонщика (глифы 2..5, plane0:=¬plane1, flat-blit) — 5355ccfd77328793fc8920eddae5a9f26350f67ae0226bb0ad75436f8ab9c1a2;
;    до Фазы 4 — a489876c896c53efbbdbf57c87b840ca9a0e920e36790668fc7dc77416e8ff2a;
;    исходный снимок оригинала — 45919a36b3fed08b6a81d58ae26f17dc4f274fb603608915239a283036ef55b5;
;    после Стадии 1 (полный 8192) — 6fd358ad5dff6e8865eeaf9a8840167dbf4b5d6e2a69a5efae05843b5d5c3879).

data_glyph_block:
data_glyph_block_unpacked:
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h   ; глиф 0 @+0 [compact]
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 0BDh, 0B3h, 05Fh, 05Fh, 02Fh, 017h, 00Ch, 003h   ; глиф 2 (OR-формат как у героя: П3=0, П2=S, П1=S, П0/маска=¬S)
    DEFB 0BDh, 0B3h, 05Fh, 05Fh, 02Fh, 017h, 00Ch, 003h, 042h, 04Ch, 0A0h, 0A0h, 0D0h, 0E8h, 0F3h, 0FCh
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 003h, 00Ch, 017h, 02Fh, 05Ch, 050h, 0BCh, 0BFh   ; глиф 3
    DEFB 003h, 00Ch, 017h, 02Fh, 05Ch, 050h, 0BCh, 0BFh, 0FCh, 0F3h, 0E8h, 0D0h, 0A3h, 0AFh, 043h, 040h
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 0BDh, 0CDh, 0FAh, 0FAh, 0F4h, 0E8h, 030h, 0C0h   ; глиф 4
    DEFB 0BDh, 0CDh, 0FAh, 0FAh, 0F4h, 0E8h, 030h, 0C0h, 042h, 032h, 005h, 005h, 00Bh, 017h, 0CFh, 03Fh
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 0C0h, 030h, 0E8h, 0F4h, 03Ah, 00Ah, 03Dh, 0FDh   ; глиф 5
    DEFB 0C0h, 030h, 0E8h, 0F4h, 03Ah, 00Ah, 03Dh, 0FDh, 03Fh, 0CFh, 017h, 00Bh, 0C5h, 0F5h, 0C2h, 002h
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 038h, 010h, 0D6h, 0FEh, 0FEh, 038h, 07Ch, 038h
    DEFB 038h, 010h, 0D6h, 0FEh, 0FEh, 038h, 07Ch, 038h, 038h, 010h, 0D6h, 0FEh, 0FEh, 038h, 07Ch, 038h
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 038h, 010h, 07Ch, 0FEh, 07Ch, 038h, 010h, 010h
    DEFB 038h, 010h, 07Ch, 0FEh, 07Ch, 038h, 010h, 010h, 038h, 010h, 07Ch, 0FEh, 07Ch, 038h, 010h, 010h
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 018h, 03Ch, 03Ch, 018h, 000h, 000h
    DEFB 000h, 000h, 018h, 03Ch, 03Ch, 018h, 000h, 000h, 000h, 000h, 018h, 03Ch, 03Ch, 018h, 000h, 000h
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 0FFh, 0FFh, 0E7h, 0C3h, 0C3h, 0E7h, 0FFh, 0FFh
    DEFB 0FFh, 0FFh, 0E7h, 0C3h, 0C3h, 0E7h, 0FFh, 0FFh, 0FFh, 0FFh, 0E7h, 0C3h, 0C3h, 0E7h, 0FFh, 0FFh
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 03Ch, 066h, 042h, 042h, 066h, 03Ch, 000h
    DEFB 000h, 03Ch, 066h, 042h, 042h, 066h, 03Ch, 000h, 000h, 03Ch, 066h, 042h, 042h, 066h, 03Ch, 000h
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 0FFh, 0C3h, 099h, 0BDh, 0BDh, 099h, 0C3h, 0FFh
    DEFB 0FFh, 0C3h, 099h, 0BDh, 0BDh, 099h, 0C3h, 0FFh, 0FFh, 0C3h, 099h, 0BDh, 0BDh, 099h, 0C3h, 0FFh
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 078h, 0CCh, 0CCh, 0CCh, 07Dh, 00Fh, 007h, 00Fh
    DEFB 078h, 0CCh, 0CCh, 0CCh, 07Dh, 00Fh, 007h, 00Fh, 078h, 0CCh, 0CCh, 0CCh, 07Dh, 00Fh, 007h, 00Fh
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 018h, 07Eh, 018h, 03Ch, 066h, 066h, 066h, 03Ch
    DEFB 018h, 07Eh, 018h, 03Ch, 066h, 066h, 066h, 03Ch, 018h, 07Eh, 018h, 03Ch, 066h, 066h, 066h, 03Ch
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 072h, 045h, 075h, 000h, 0FFh, 080h, 080h, 0FFh   ; глиф 18 @+528 [raw] тёмный 188 (Фаза 4)
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 072h, 045h, 075h, 000h, 0FFh, 080h, 080h, 0FFh
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 0FFh, 080h, 080h, 0FFh, 000h, 075h, 045h   ; глиф 19 @+560 [raw] тёмный 189 (Фаза 4)
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 0FFh, 080h, 080h, 0FFh, 000h, 075h, 045h
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 048h, 048h, 05Ch, 000h, 0FFh, 001h, 001h, 0FFh   ; глиф 20 @+592 [raw] тёмный 190 (Фаза 4)
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 048h, 048h, 05Ch, 000h, 0FFh, 001h, 001h, 0FFh
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 0FFh, 001h, 001h, 0FFh, 000h, 048h, 048h   ; глиф 21 @+624 [raw] тёмный 191 (Фаза 4)
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 0FFh, 001h, 001h, 0FFh, 000h, 048h, 048h
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh
    DEFB 001h, 002h, 004h, 008h, 010h, 020h, 040h, 080h, 000h, 000h, 010h, 010h, 0FFh, 010h, 010h, 000h
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 030h, 000h, 030h, 030h, 078h, 078h, 030h   ; глиф 32 @+928 [compact]
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 06Ch, 06Ch, 000h, 06Ch, 06Ch, 0FEh, 06Ch, 0FEh, 06Ch, 06Ch
    DEFB 000h, 0C3h, 03Ch, 066h, 066h, 03Ch, 0C3h, 000h, 000h, 0C6h, 066h, 030h, 018h, 0CCh, 0C6h, 000h   ; глиф 36 @+960 [compact]
    DEFB 000h, 076h, 0CCh, 0DCh, 076h, 038h, 06Ch, 038h, 000h, 000h, 000h, 000h, 000h, 0C0h, 060h, 060h
    DEFB 000h, 018h, 030h, 060h, 060h, 060h, 030h, 018h, 000h, 060h, 030h, 018h, 018h, 018h, 030h, 060h   ; глиф 40 @+992 [compact]
    DEFB 000h, 000h, 066h, 03Ch, 0FFh, 03Ch, 066h, 000h, 000h, 000h, 030h, 030h, 0FCh, 030h, 030h, 000h
    DEFB 060h, 030h, 030h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 0FCh, 000h, 000h, 000h   ; глиф 44 @+1024 [compact]
    DEFB 000h, 030h, 030h, 000h, 000h, 000h, 000h, 000h, 000h, 080h, 0C0h, 060h, 030h, 018h, 00Ch, 006h
    DEFB 000h, 07Ch, 0C6h, 0E6h, 0D6h, 0CEh, 0C6h, 07Ch, 000h, 0FCh, 030h, 030h, 030h, 030h, 070h, 030h   ; глиф 48 @+1056 [compact]
    DEFB 000h, 0FCh, 0CCh, 060h, 038h, 00Ch, 0CCh, 078h, 000h, 078h, 0CCh, 00Ch, 038h, 00Ch, 0CCh, 078h
    DEFB 000h, 01Eh, 00Ch, 0FEh, 0CCh, 06Ch, 03Ch, 01Ch, 000h, 078h, 0CCh, 00Ch, 00Ch, 0F8h, 0C0h, 0FCh   ; глиф 52 @+1088 [compact]
    DEFB 000h, 078h, 0CCh, 0CCh, 0F8h, 0C0h, 060h, 038h, 000h, 030h, 030h, 030h, 018h, 00Ch, 0CCh, 0FCh
    DEFB 000h, 078h, 0CCh, 0CCh, 078h, 0CCh, 0CCh, 078h, 000h, 070h, 018h, 00Ch, 07Ch, 0CCh, 0CCh, 078h   ; глиф 56 @+1120 [compact]
    DEFB 000h, 030h, 030h, 000h, 000h, 030h, 030h, 000h, 060h, 030h, 030h, 000h, 000h, 030h, 030h, 000h
    DEFB 000h, 018h, 030h, 060h, 0C0h, 060h, 030h, 018h, 000h, 000h, 0FCh, 000h, 000h, 0FCh, 000h, 000h   ; глиф 60 @+1152 [compact]
    DEFB 000h, 0C0h, 060h, 030h, 018h, 030h, 060h, 0C0h, 000h, 030h, 000h, 030h, 018h, 00Ch, 0CCh, 078h
    DEFB 000h, 078h, 0C0h, 0C0h, 0DEh, 0DEh, 0C6h, 07Ch, 000h, 0CCh, 0CCh, 0FCh, 0CCh, 0CCh, 078h, 030h   ; глиф 64 @+1184 [compact]
    DEFB 000h, 0FCh, 066h, 066h, 07Ch, 066h, 066h, 0FCh, 000h, 03Ch, 066h, 0C0h, 0C0h, 0C0h, 066h, 03Ch
    DEFB 000h, 0F8h, 06Ch, 066h, 066h, 066h, 06Ch, 0F8h, 000h, 0FEh, 062h, 068h, 078h, 068h, 062h, 0FEh   ; глиф 68 @+1216 [compact]
    DEFB 000h, 0F0h, 060h, 068h, 078h, 068h, 062h, 0FEh, 000h, 03Eh, 066h, 0CEh, 0C0h, 0C0h, 066h, 03Ch
    DEFB 000h, 0CCh, 0CCh, 0CCh, 0FCh, 0CCh, 0CCh, 0CCh, 000h, 078h, 030h, 030h, 030h, 030h, 030h, 078h   ; глиф 72 @+1248 [compact]
    DEFB 000h, 078h, 0CCh, 0CCh, 00Ch, 00Ch, 00Ch, 01Eh, 000h, 0E6h, 066h, 06Ch, 078h, 06Ch, 066h, 0E6h
    DEFB 000h, 0FEh, 066h, 062h, 060h, 060h, 060h, 0F0h, 000h, 0C6h, 0C6h, 0C6h, 0D6h, 0FEh, 0EEh, 0C6h   ; глиф 76 @+1280 [compact]
    DEFB 000h, 0C6h, 0C6h, 0CEh, 0DEh, 0F6h, 0E6h, 0C6h, 000h, 038h, 06Ch, 0C6h, 0C6h, 0C6h, 06Ch, 038h
    DEFB 000h, 0F0h, 060h, 060h, 07Ch, 066h, 066h, 0FCh, 000h, 01Ch, 078h, 0DCh, 0CCh, 0CCh, 0CCh, 078h   ; глиф 80 @+1312 [compact]
    DEFB 000h, 0E6h, 066h, 06Ch, 07Ch, 064h, 066h, 0FCh, 000h, 078h, 0CCh, 018h, 030h, 060h, 0CCh, 078h
    DEFB 000h, 078h, 030h, 030h, 030h, 030h, 0B4h, 0FCh, 000h, 0FCh, 0CCh, 0CCh, 0CCh, 0CCh, 0CCh, 0CCh   ; глиф 84 @+1344 [compact]
    DEFB 000h, 030h, 078h, 0CCh, 0CCh, 0CCh, 0CCh, 0CCh, 000h, 0C6h, 0EEh, 0FEh, 0D6h, 0C6h, 0C6h, 0C6h
    DEFB 000h, 0C6h, 06Ch, 038h, 038h, 06Ch, 0C6h, 0C6h, 000h, 078h, 030h, 030h, 078h, 0CCh, 0CCh, 0CCh   ; глиф 88 @+1376 [compact]
    DEFB 000h, 0FEh, 066h, 032h, 018h, 08Ch, 0C6h, 0FEh, 000h, 078h, 060h, 060h, 060h, 060h, 060h, 078h
    DEFB 000h, 002h, 006h, 00Ch, 018h, 030h, 060h, 0C0h, 000h, 078h, 018h, 018h, 018h, 018h, 018h, 078h   ; глиф 92 @+1408 [compact]
    DEFB 000h, 000h, 000h, 000h, 0C6h, 06Ch, 038h, 010h, 0FFh, 000h, 000h, 000h, 000h, 000h, 000h, 000h
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h   ; глиф 96 @+1440 [raw]
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh
    DEFB 003h, 03Ch, 03Fh, 000h, 00Eh, 000h, 000h, 000h, 003h, 03Ch, 000h, 01Fh, 00Eh, 000h, 000h, 000h   ; глиф 97 @+1472 [raw]
    DEFB 003h, 03Ch, 000h, 01Fh, 00Eh, 000h, 000h, 000h, 0FCh, 0FFh, 0FFh, 0FFh, 0F1h, 0FFh, 0FFh, 0FFh
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 060h, 0E0h, 0F0h, 038h, 018h, 018h, 038h, 070h, 060h   ; глиф 98 @+1504 [raw]
    DEFB 000h, 000h, 000h, 018h, 000h, 038h, 070h, 060h, 0FFh, 00Fh, 0C7h, 0E7h, 0E7h, 0C7h, 08Fh, 09Fh
    DEFB 0FFh, 0FFh, 07Fh, 03Fh, 002h, 003h, 000h, 000h, 030h, 030h, 000h, 000h, 002h, 003h, 000h, 000h   ; глиф 99 @+1536 [raw]
    DEFB 030h, 030h, 000h, 000h, 000h, 000h, 003h, 000h, 0CFh, 0CFh, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh
    DEFB 000h, 000h, 000h, 0E0h, 000h, 000h, 000h, 000h, 0F8h, 0F8h, 0F0h, 000h, 000h, 000h, 000h, 000h   ; глиф 100 @+1568 [raw]
    DEFB 0F8h, 0F8h, 0F0h, 000h, 000h, 000h, 000h, 000h, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh
    DEFB 000h, 0E0h, 0E0h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 0F0h, 0F0h, 0F8h, 0F8h, 0F8h   ; глиф 101 @+1600 [raw]
    DEFB 0C0h, 0E0h, 0E0h, 0F0h, 0F0h, 0F8h, 0F8h, 0F8h, 03Fh, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh
    DEFB 00Eh, 001h, 003h, 003h, 000h, 000h, 000h, 000h, 00Eh, 001h, 003h, 003h, 000h, 000h, 000h, 000h   ; глиф 102 @+1632 [raw]
    DEFB 00Eh, 000h, 000h, 000h, 007h, 00Eh, 01Dh, 003h, 0F1h, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh, 0E2h, 0FCh
    DEFB 0C6h, 000h, 000h, 0ADh, 0E1h, 0D8h, 000h, 000h, 0C6h, 000h, 000h, 0ADh, 0E1h, 0D8h, 000h, 000h   ; глиф 103 @+1664 [raw]
    DEFB 000h, 07Ch, 038h, 000h, 01Eh, 000h, 0D8h, 08Ch, 0FFh, 0FFh, 0C7h, 0FFh, 0E1h, 0FFh, 0FFh, 073h
    DEFB 000h, 000h, 000h, 000h, 080h, 000h, 080h, 002h, 000h, 000h, 000h, 000h, 000h, 080h, 000h, 002h   ; глиф 104 @+1696 [raw]
    DEFB 000h, 000h, 000h, 000h, 080h, 080h, 080h, 000h, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh
    DEFB 0F6h, 000h, 060h, 000h, 000h, 000h, 000h, 000h, 0F6h, 000h, 060h, 00Ah, 00Eh, 01Ch, 030h, 000h   ; глиф 105 @+1728 [raw]
    DEFB 000h, 0F0h, 000h, 000h, 000h, 000h, 030h, 000h, 0FFh, 00Fh, 0FFh, 0FFh, 0F1h, 0E3h, 0CFh, 0FFh
    DEFB 030h, 0BAh, 0BBh, 000h, 0C6h, 0E1h, 0EFh, 000h, 030h, 0BAh, 0BBh, 000h, 0C6h, 0E1h, 0EFh, 000h   ; глиф 106 @+1760 [raw]
    DEFB 000h, 000h, 000h, 037h, 000h, 000h, 000h, 0CFh, 0FFh, 0BAh, 0BBh, 000h, 0C6h, 0E1h, 0EFh, 030h
    DEFB 048h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 048h, 000h, 000h, 000h, 000h, 000h, 000h, 000h   ; глиф 107 @+1792 [raw]
    DEFB 000h, 050h, 050h, 020h, 060h, 000h, 000h, 000h, 0FFh, 0FFh, 0FFh, 0FFh, 09Fh, 0FFh, 0FFh, 0FFh
    DEFB 000h, 07Ch, 07Ch, 07Ch, 038h, 008h, 088h, 000h, 038h, 000h, 07Ch, 07Ch, 038h, 008h, 088h, 000h   ; глиф 108 @+1824 [raw]
    DEFB 038h, 000h, 07Ch, 07Ch, 038h, 000h, 000h, 048h, 0FFh, 0FFh, 0FFh, 0FFh, 0C7h, 0FFh, 0FFh, 0FFh
    DEFB 0C0h, 0E0h, 0E0h, 000h, 000h, 000h, 000h, 000h, 0C0h, 000h, 000h, 0E0h, 0C0h, 000h, 000h, 000h   ; глиф 109 @+1856 [raw]
    DEFB 0C0h, 000h, 000h, 0E0h, 0C0h, 000h, 000h, 000h, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh
    DEFB 000h, 01Fh, 01Fh, 01Fh, 00Eh, 001h, 000h, 000h, 00Eh, 000h, 000h, 01Fh, 00Eh, 001h, 000h, 000h   ; глиф 110 @+1888 [raw]
    DEFB 00Eh, 000h, 000h, 01Fh, 00Eh, 000h, 000h, 000h, 0FFh, 0FFh, 0FFh, 0FFh, 0F1h, 0FFh, 0FFh, 0FFh
    DEFB 01Fh, 03Fh, 000h, 000h, 000h, 07Ch, 0FEh, 0FFh, 000h, 000h, 03Fh, 07Fh, 07Fh, 083h, 001h, 020h   ; глиф 111 @+1920 [raw]
    DEFB 01Fh, 03Fh, 03Fh, 07Fh, 07Fh, 083h, 001h, 020h, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh, 0DFh
    DEFB 078h, 056h, 0FFh, 055h, 0FFh, 055h, 07Fh, 035h, 000h, 0A9h, 000h, 0AAh, 000h, 0AAh, 000h, 000h   ; глиф 112 @+1952 [raw]
    DEFB 078h, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh, 07Fh, 035h, 0FFh, 0FFh, 0FFh, 0FFh, 01Fh, 0AAh, 080h, 0CAh
    DEFB 063h, 0F7h, 000h, 06Bh, 01Eh, 000h, 000h, 000h, 063h, 0F7h, 000h, 06Bh, 01Eh, 000h, 000h, 000h   ; глиф 113 @+1984 [raw]
    DEFB 000h, 000h, 0F7h, 000h, 000h, 00Dh, 001h, 000h, 0FFh, 0FFh, 008h, 06Bh, 0FFh, 0F2h, 0FEh, 0FFh
    DEFB 001h, 000h, 002h, 003h, 000h, 000h, 000h, 000h, 000h, 003h, 002h, 003h, 001h, 000h, 000h, 000h   ; глиф 114 @+2016 [raw]
    DEFB 000h, 003h, 002h, 003h, 001h, 000h, 000h, 000h, 0FFh, 0FFh, 0FDh, 0FCh, 0FFh, 0FFh, 0FFh, 0FFh
    DEFB 000h, 000h, 000h, 000h, 00Ch, 008h, 000h, 000h, 003h, 007h, 00Eh, 00Ch, 00Ch, 008h, 006h, 00Fh   ; глиф 115 @+2048 [raw]
    DEFB 000h, 007h, 00Eh, 00Ch, 00Ch, 008h, 000h, 00Fh, 0FCh, 0F8h, 0F1h, 0F3h, 0F3h, 0F7h, 0F9h, 0F0h
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h   ; глиф 116 @+2080 [raw]
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh
    DEFB 0FFh, 0FFh, 0EEh, 023h, 000h, 000h, 000h, 000h, 0F7h, 0CCh, 011h, 0DCh, 067h, 043h, 026h, 000h   ; глиф 117 @+2112 [raw]
    DEFB 0F7h, 0CCh, 011h, 0DCh, 067h, 043h, 026h, 000h, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh
    DEFB 0FFh, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh, 026h, 0ACh, 082h, 000h, 000h, 000h, 000h   ; глиф 118 @+2144 [raw]
    DEFB 0FFh, 0FFh, 0FFh, 0FFh, 0EFh, 0B2h, 099h, 002h, 000h, 0D9h, 053h, 07Dh, 0FFh, 0FFh, 0FFh, 0FFh
    DEFB 07Fh, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 07Fh, 000h, 000h, 000h, 000h, 000h, 000h, 000h   ; глиф 119 @+2176 [raw]
    DEFB 000h, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh, 07Fh, 07Fh, 07Fh, 07Fh, 07Fh, 07Fh, 07Fh, 03Fh, 000h
    DEFB 0FEh, 003h, 001h, 001h, 001h, 001h, 001h, 000h, 0FEh, 003h, 001h, 001h, 001h, 001h, 001h, 000h   ; глиф 120 @+2208 [raw]
    DEFB 000h, 0FCh, 0FEh, 0FEh, 0FEh, 0FEh, 0FEh, 0FEh, 0FEh, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh, 000h
    DEFB 07Fh, 080h, 000h, 000h, 000h, 000h, 000h, 000h, 07Fh, 080h, 000h, 000h, 000h, 000h, 000h, 000h   ; глиф 121 @+2240 [raw]
    DEFB 000h, 07Fh, 0FEh, 0FCh, 0FCh, 0FCh, 0FEh, 07Fh, 07Fh, 0FFh, 0FEh, 0FCh, 0FCh, 0FCh, 0FEh, 000h
    DEFB 0FEh, 003h, 0C0h, 0E0h, 0E0h, 000h, 000h, 000h, 0FEh, 003h, 0C0h, 0E0h, 0E0h, 000h, 000h, 000h   ; глиф 122 @+2272 [raw]
    DEFB 000h, 0FCh, 03Fh, 01Fh, 01Fh, 01Fh, 03Fh, 0FEh, 0FEh, 0FFh, 0FFh, 0FFh, 0FFh, 01Fh, 03Fh, 000h
    DEFB 07Fh, 080h, 001h, 000h, 003h, 003h, 000h, 000h, 07Fh, 080h, 000h, 003h, 003h, 003h, 001h, 000h   ; глиф 123 @+2304 [raw]
    DEFB 000h, 07Fh, 0FEh, 0FFh, 0FFh, 0FFh, 0FFh, 07Fh, 07Fh, 0FFh, 0FFh, 0FFh, 0FCh, 0FCh, 0FFh, 000h
    DEFB 0FEh, 003h, 0C0h, 0E0h, 0E0h, 000h, 000h, 000h, 0FEh, 003h, 0C0h, 000h, 000h, 0E0h, 0C0h, 000h   ; глиф 124 @+2336 [raw]
    DEFB 000h, 0FCh, 0FFh, 01Fh, 01Fh, 0FFh, 0FFh, 0FEh, 0FEh, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh, 000h
    DEFB 07Fh, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 07Fh, 000h, 000h, 000h, 000h, 000h, 000h, 000h   ; глиф 125 @+2368 [raw]
    DEFB 000h, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh, 07Fh, 07Fh, 07Fh, 07Fh, 07Fh, 07Fh, 07Fh, 03Fh, 080h
    DEFB 0CCh, 0CCh, 0CCh, 0C7h, 0C0h, 0C0h, 0FFh, 07Fh, 033h, 033h, 033h, 038h, 03Fh, 03Fh, 000h, 000h   ; глиф 126 @+2400 [raw]
    DEFB 0CCh, 0CCh, 0CCh, 0C7h, 0C0h, 0C0h, 0FFh, 07Fh, 033h, 033h, 033h, 038h, 03Fh, 03Fh, 03Fh, 0FFh
    DEFB 0FFh, 0FFh, 0FFh, 0D7h, 0D8h, 0C0h, 0FFh, 07Fh, 000h, 0CCh, 000h, 0FFh, 0FFh, 0FFh, 0C0h, 07Fh   ; глиф 127 @+2432 [raw]
    DEFB 0CCh, 0CCh, 0CCh, 0FFh, 0FFh, 0FFh, 0FFh, 07Fh, 033h, 033h, 033h, 028h, 027h, 03Fh, 000h, 080h
    DEFB 033h, 033h, 033h, 0E3h, 003h, 003h, 0FFh, 0FEh, 0CCh, 0CCh, 0CCh, 01Ch, 0FCh, 0FCh, 000h, 000h   ; глиф 128 @+2464 [raw]
    DEFB 033h, 033h, 033h, 0E3h, 003h, 003h, 0FFh, 0FEh, 0CCh, 0CCh, 0CCh, 01Ch, 0FCh, 0FCh, 003h, 0FFh
    DEFB 07Fh, 0FFh, 0C0h, 0C1h, 0C0h, 0C1h, 0C1h, 0C0h, 000h, 000h, 03Fh, 03Eh, 03Fh, 03Eh, 03Eh, 03Fh   ; глиф 129 @+2496 [raw]
    DEFB 07Fh, 0FFh, 0C0h, 0C1h, 0C0h, 0C1h, 0C1h, 0C0h, 0FFh, 03Fh, 03Fh, 03Eh, 03Fh, 03Eh, 03Eh, 03Fh
    DEFB 0FEh, 0FFh, 003h, 083h, 003h, 083h, 083h, 0E3h, 000h, 000h, 0FCh, 07Ch, 0FCh, 07Ch, 07Ch, 01Ch   ; глиф 130 @+2528 [raw]
    DEFB 0FEh, 0FFh, 003h, 083h, 003h, 083h, 083h, 0E3h, 0FFh, 0FCh, 0FCh, 07Ch, 0FCh, 07Ch, 07Ch, 01Ch
    DEFB 000h, 000h, 000h, 000h, 000h, 074h, 0E8h, 000h, 01Ah, 0DCh, 0ECh, 074h, 074h, 074h, 0E8h, 0C0h   ; глиф 131 @+2560 [raw]
    DEFB 000h, 000h, 000h, 074h, 074h, 074h, 0E8h, 0C0h, 01Ah, 000h, 000h, 000h, 000h, 000h, 000h, 000h
    DEFB 03Fh, 03Fh, 01Fh, 007h, 000h, 001h, 000h, 003h, 000h, 000h, 000h, 000h, 003h, 001h, 001h, 003h   ; глиф 132 @+2592 [raw]
    DEFB 03Fh, 03Fh, 01Fh, 007h, 003h, 001h, 000h, 003h, 0C0h, 0C0h, 0E0h, 0F8h, 0FCh, 0FEh, 0FFh, 0FCh
    DEFB 0FCh, 0FCh, 0F8h, 0E0h, 000h, 000h, 000h, 0C0h, 000h, 000h, 000h, 000h, 0C0h, 080h, 080h, 0C0h   ; глиф 133 @+2624 [raw]
    DEFB 0FCh, 0FCh, 0F8h, 0E0h, 000h, 080h, 000h, 0C0h, 003h, 003h, 007h, 01Fh, 0FFh, 07Fh, 0FFh, 03Fh
    DEFB 007h, 01Fh, 03Fh, 038h, 07Eh, 07Fh, 07Dh, 073h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h   ; глиф 134 @+2656 [raw]
    DEFB 007h, 01Fh, 03Fh, 038h, 07Eh, 07Fh, 07Dh, 073h, 0F8h, 0E0h, 0C0h, 0C7h, 081h, 080h, 082h, 08Ch
    DEFB 0E0h, 0F8h, 0FCh, 01Ch, 07Eh, 0FEh, 0BEh, 0CEh, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h   ; глиф 135 @+2688 [raw]
    DEFB 0E0h, 0F8h, 0FCh, 01Ch, 07Eh, 0FEh, 0BEh, 0CEh, 01Fh, 007h, 003h, 0E3h, 081h, 001h, 041h, 031h
    DEFB 03Fh, 03Fh, 01Fh, 007h, 000h, 001h, 000h, 07Dh, 000h, 000h, 000h, 000h, 003h, 001h, 001h, 0FFh   ; глиф 136 @+2720 [raw]
    DEFB 03Fh, 03Fh, 01Fh, 007h, 003h, 001h, 000h, 07Dh, 0C0h, 0C0h, 0E0h, 0F8h, 0FCh, 0FEh, 0FFh, 082h
    DEFB 0FCh, 0FCh, 0F8h, 0E0h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 0C0h, 080h, 080h, 0FFh   ; глиф 137 @+2752 [raw]
    DEFB 0FCh, 0FCh, 0F8h, 0E0h, 000h, 080h, 000h, 0BEh, 003h, 003h, 007h, 01Fh, 0FFh, 07Fh, 0FFh, 041h
    DEFB 000h, 0EEh, 07Ch, 07Ch, 0D6h, 0D6h, 07Ch, 038h, 000h, 0EEh, 07Ch, 000h, 0D6h, 0D6h, 07Ch, 038h   ; глиф 138 @+2784 [raw]
    DEFB 000h, 0EEh, 07Ch, 000h, 0D6h, 0D6h, 07Ch, 038h, 0FFh, 011h, 083h, 083h, 029h, 029h, 083h, 0C7h
    DEFB 000h, 000h, 000h, 000h, 00Ch, 01Eh, 016h, 00Ch, 07Fh, 07Fh, 03Fh, 00Fh, 00Ch, 01Eh, 016h, 00Ch   ; глиф 139 @+2816 [raw]
    DEFB 07Fh, 07Fh, 03Fh, 00Fh, 00Ch, 01Eh, 016h, 00Ch, 080h, 080h, 0C0h, 0F0h, 0F3h, 0E1h, 0E9h, 0F3h
    DEFB 000h, 000h, 000h, 000h, 060h, 0F0h, 0B0h, 060h, 0FCh, 0FCh, 0F8h, 0E0h, 060h, 0F0h, 0B0h, 060h   ; глиф 140 @+2848 [raw]
    DEFB 000h, 000h, 000h, 0E0h, 060h, 0F0h, 0B0h, 060h, 0FFh, 0FFh, 0FFh, 01Fh, 09Fh, 00Fh, 04Fh, 09Fh
    DEFB 000h, 000h, 001h, 001h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 001h, 0FFh, 0FFh, 0FFh   ; глиф 141 @+2880 [raw]
    DEFB 000h, 000h, 000h, 000h, 001h, 0E0h, 0FCh, 0FEh, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh, 01Fh, 003h, 001h
    DEFB 060h, 0C0h, 080h, 080h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 080h, 0FEh, 0FEh, 0FEh   ; глиф 142 @+2912 [raw]
    DEFB 000h, 000h, 000h, 000h, 080h, 000h, 000h, 000h, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh
    DEFB 000h, 000h, 000h, 000h, 00Ch, 01Eh, 01Ah, 00Ch, 01Fh, 00Fh, 00Fh, 007h, 00Ch, 01Eh, 01Ah, 00Ch   ; глиф 143 @+2944 [raw]
    DEFB 01Fh, 00Fh, 00Fh, 007h, 00Ch, 01Eh, 01Ah, 00Ch, 0E0h, 0F0h, 0F0h, 0F8h, 0F3h, 0E1h, 0E5h, 0F3h
    DEFB 000h, 000h, 000h, 000h, 060h, 0F0h, 0D0h, 060h, 0F0h, 0E0h, 0E0h, 0C0h, 060h, 0F0h, 0D0h, 060h   ; глиф 144 @+2976 [raw]
    DEFB 000h, 000h, 000h, 0C0h, 060h, 0F0h, 0D0h, 060h, 0FFh, 0FFh, 0FFh, 03Fh, 09Fh, 00Fh, 02Fh, 09Fh
    DEFB 00Ch, 006h, 003h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 003h, 01Fh, 01Fh, 01Fh, 01Fh   ; глиф 145 @+3008 [raw]
    DEFB 000h, 000h, 000h, 003h, 000h, 01Fh, 01Fh, 01Fh, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh, 0E0h, 0E0h, 0E0h
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 0F0h, 0F0h, 0F0h, 0F0h   ; глиф 146 @+3040 [raw]
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh
    DEFB 000h, 000h, 038h, 000h, 01Eh, 007h, 001h, 000h, 079h, 078h, 038h, 03Ch, 01Eh, 007h, 001h, 000h   ; глиф 147 @+3072 [raw]
    DEFB 079h, 078h, 038h, 03Ch, 01Eh, 007h, 001h, 000h, 086h, 087h, 0C7h, 0C3h, 0E1h, 0F8h, 0FEh, 0FFh
    DEFB 000h, 000h, 000h, 07Ch, 000h, 01Eh, 0C7h, 000h, 0F0h, 0F8h, 0F8h, 07Ch, 03Ch, 01Eh, 0C7h, 000h   ; глиф 148 @+3104 [raw]
    DEFB 0F0h, 0F8h, 0F8h, 07Ch, 03Ch, 01Eh, 0C7h, 000h, 00Fh, 007h, 007h, 083h, 0C3h, 0E1h, 038h, 0FFh
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 01Fh, 03Fh, 03Fh, 05Bh, 05Bh, 05Bh, 05Bh, 07Fh   ; глиф 149 @+3136 [raw]
    DEFB 000h, 000h, 03Fh, 05Bh, 05Bh, 05Bh, 05Bh, 07Fh, 0FFh, 0FFh, 0C0h, 0A4h, 0A4h, 0A4h, 0A4h, 080h
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 0C0h, 0E0h, 0E0h, 0E0h, 0F0h, 0F0h, 0F0h   ; глиф 150 @+3168 [raw]
    DEFB 000h, 000h, 000h, 000h, 0E0h, 000h, 0F0h, 0F0h, 0FFh, 0FFh, 0FFh, 0FFh, 01Fh, 0FFh, 00Fh, 00Fh
    DEFB 000h, 000h, 01Fh, 000h, 03Ch, 078h, 0E3h, 000h, 00Fh, 01Fh, 01Fh, 03Eh, 03Ch, 078h, 0E3h, 000h   ; глиф 151 @+3200 [raw]
    DEFB 00Fh, 01Fh, 01Fh, 03Eh, 03Ch, 078h, 0E3h, 000h, 0F0h, 0E0h, 0E0h, 0C1h, 0C3h, 087h, 01Ch, 0FFh
    DEFB 000h, 000h, 000h, 03Ch, 000h, 0E0h, 080h, 000h, 09Eh, 01Eh, 01Ch, 03Ch, 078h, 0E0h, 080h, 000h   ; глиф 152 @+3232 [raw]
    DEFB 09Eh, 01Eh, 01Ch, 03Ch, 078h, 0E0h, 080h, 000h, 061h, 0E1h, 0E3h, 0C3h, 087h, 01Fh, 07Fh, 0FFh
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 003h, 007h, 007h, 007h, 00Fh, 00Fh, 00Fh   ; глиф 153 @+3264 [raw]
    DEFB 000h, 000h, 000h, 007h, 007h, 00Fh, 00Fh, 00Fh, 0FFh, 0FFh, 0FFh, 0F8h, 0F8h, 0F0h, 0F0h, 0F0h
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 0F8h, 0FCh, 0FCh, 0DAh, 0DAh, 0DAh, 0DAh, 0FEh   ; глиф 154 @+3296 [raw]
    DEFB 000h, 000h, 000h, 000h, 0DAh, 000h, 0DAh, 0FEh, 0FFh, 0FFh, 0FFh, 0FFh, 025h, 0FFh, 025h, 001h
    DEFB 03Ch, 07Eh, 0FCh, 0F0h, 006h, 006h, 000h, 000h, 000h, 000h, 003h, 00Fh, 0FFh, 0FFh, 07Eh, 03Ch   ; глиф 155 @+3328 [raw]
    DEFB 000h, 000h, 003h, 00Fh, 0FFh, 0FFh, 07Eh, 03Ch, 0FFh, 0FFh, 0FFh, 0FFh, 0F9h, 0F9h, 07Eh, 03Ch
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 0DFh, 0DFh, 0DFh, 000h, 0FBh, 0FBh, 0FBh   ; глиф 156 @+3360 [raw]
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 0DFh, 0DFh, 000h, 000h, 0FBh, 0FBh
    DEFB 000h, 07Eh, 07Eh, 07Eh, 07Eh, 03Ch, 000h, 000h, 03Ch, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh   ; глиф 157 @+3392 [raw]
    DEFB 03Ch, 07Eh, 0FFh, 0FFh, 0FFh, 0FFh, 07Eh, 03Ch, 000h, 000h, 000h, 000h, 000h, 000h, 081h, 0C3h
    DEFB 0FFh, 0FFh, 07Eh, 000h, 07Eh, 0FFh, 099h, 099h, 00Ch, 00Ch, 0FFh, 0FFh, 000h, 01Eh, 0FFh, 0FFh   ; глиф 158 @+3424 [raw]
    DEFB 0FFh, 0FFh, 07Eh, 03Ch, 07Eh, 0FFh, 099h, 099h, 0F3h, 0F3h, 081h, 0FFh, 07Eh, 0E1h, 066h, 066h
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h   ; глиф 159 @+3456 [raw]
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh
    DEFB 07Fh, 07Fh, 07Fh, 03Fh, 03Fh, 01Fh, 00Fh, 003h, 01Fh, 01Fh, 01Fh, 01Fh, 00Fh, 00Fh, 007h, 003h   ; глиф 160 @+3488 [raw]
    DEFB 01Fh, 01Fh, 01Fh, 01Fh, 00Fh, 00Fh, 007h, 003h, 080h, 080h, 080h, 0C0h, 0C0h, 0E0h, 0F0h, 0FCh
    DEFB 00Eh, 00Dh, 00Bh, 007h, 03Fh, 03Fh, 007h, 03Fh, 000h, 000h, 000h, 001h, 001h, 031h, 000h, 00Fh   ; глиф 161 @+3520 [raw]
    DEFB 000h, 000h, 000h, 001h, 001h, 031h, 000h, 00Fh, 0F1h, 0F2h, 0F4h, 0F8h, 0C0h, 0C0h, 0F8h, 0C0h
    DEFB 0B6h, 0B6h, 0B6h, 0B4h, 0FCh, 0F8h, 0F0h, 0C0h, 0B6h, 0B6h, 0B6h, 0B4h, 0FCh, 0F8h, 0F0h, 0C0h   ; глиф 162 @+3552 [raw]
    DEFB 0B6h, 0B6h, 0B6h, 0B4h, 0FCh, 0F8h, 0F0h, 0C0h, 001h, 001h, 001h, 003h, 003h, 007h, 00Fh, 03Fh
    DEFB 0F0h, 0F8h, 0FCh, 0FCh, 0F8h, 0FCh, 0FEh, 0FCh, 020h, 070h, 0D8h, 0ECh, 0F0h, 0F4h, 002h, 0FCh   ; глиф 163 @+3584 [raw]
    DEFB 020h, 070h, 0D8h, 0ECh, 0F0h, 0F4h, 002h, 0FCh, 00Fh, 007h, 003h, 003h, 007h, 003h, 001h, 003h
    DEFB 07Fh, 07Fh, 07Fh, 03Fh, 03Fh, 01Fh, 00Fh, 003h, 01Fh, 01Fh, 01Fh, 01Fh, 00Fh, 00Fh, 007h, 003h   ; глиф 164 @+3616 [raw]
    DEFB 01Fh, 01Fh, 01Fh, 01Fh, 00Fh, 00Fh, 007h, 003h, 080h, 080h, 080h, 0C0h, 0C0h, 0E0h, 0F0h, 0FCh
    DEFB 01Fh, 03Eh, 03Fh, 00Fh, 01Fh, 01Fh, 00Fh, 03Fh, 007h, 00Eh, 000h, 006h, 00Eh, 00Dh, 000h, 00Fh   ; глиф 165 @+3648 [raw]
    DEFB 007h, 00Eh, 000h, 006h, 00Eh, 00Dh, 000h, 00Fh, 0E0h, 0C1h, 0C0h, 0F0h, 0E0h, 0E0h, 0F0h, 0C0h
    DEFB 0B6h, 0B6h, 0B6h, 0B4h, 0FCh, 0F8h, 0F0h, 0C0h, 0B6h, 0B6h, 0B6h, 0B4h, 0FCh, 0F8h, 0F0h, 0C0h   ; глиф 166 @+3680 [raw]
    DEFB 0B6h, 0B6h, 0B6h, 0B4h, 0FCh, 0F8h, 0F0h, 0C0h, 001h, 001h, 001h, 003h, 003h, 007h, 00Fh, 03Fh
    DEFB 038h, 07Ch, 0FEh, 0F6h, 0F0h, 0F0h, 0F0h, 0FCh, 000h, 038h, 01Ch, 0E6h, 0F0h, 0F0h, 000h, 0FCh   ; глиф 167 @+3712 [raw]
    DEFB 000h, 038h, 01Ch, 0E6h, 0F0h, 0F0h, 000h, 0FCh, 0C7h, 083h, 001h, 009h, 00Fh, 00Fh, 00Fh, 003h
    DEFB 07Fh, 07Fh, 07Fh, 03Fh, 03Fh, 01Fh, 00Fh, 003h, 01Fh, 01Fh, 01Fh, 01Fh, 00Fh, 00Fh, 007h, 003h   ; глиф 168 @+3744 [raw]
    DEFB 01Fh, 01Fh, 01Fh, 01Fh, 00Fh, 00Fh, 007h, 003h, 080h, 080h, 080h, 0C0h, 0C0h, 0E0h, 0F0h, 0FCh
    DEFB 00Fh, 00Fh, 007h, 01Fh, 01Fh, 01Fh, 00Fh, 03Fh, 003h, 003h, 001h, 00Bh, 00Bh, 007h, 000h, 00Fh   ; глиф 169 @+3776 [raw]
    DEFB 003h, 003h, 001h, 00Bh, 00Bh, 007h, 000h, 00Fh, 0F0h, 0F0h, 0F8h, 0E0h, 0E0h, 0E0h, 0F0h, 0C0h
    DEFB 0B6h, 0B6h, 0B6h, 0B4h, 0FCh, 0F8h, 0F0h, 0C0h, 0B6h, 0B6h, 0B6h, 0B4h, 0FCh, 0F8h, 0F0h, 0C0h   ; глиф 170 @+3808 [raw]
    DEFB 0B6h, 0B6h, 0B6h, 0B4h, 0FCh, 0F8h, 0F0h, 0C0h, 001h, 001h, 001h, 003h, 003h, 007h, 00Fh, 03Fh
    DEFB 0FCh, 0F8h, 0F8h, 0FCh, 0FCh, 0FCh, 0F8h, 0FCh, 0ECh, 0D8h, 000h, 0E4h, 0F4h, 0F4h, 000h, 0FCh   ; глиф 171 @+3840 [raw]
    DEFB 0ECh, 0D8h, 000h, 0E4h, 0F4h, 0F4h, 000h, 0FCh, 003h, 007h, 007h, 003h, 003h, 003h, 007h, 003h
    DEFB 06Dh, 06Dh, 06Dh, 02Dh, 03Fh, 01Fh, 00Fh, 003h, 06Dh, 06Dh, 06Dh, 02Dh, 03Fh, 01Fh, 00Fh, 003h   ; глиф 172 @+3872 [raw]
    DEFB 06Dh, 06Dh, 06Dh, 02Dh, 03Fh, 01Fh, 00Fh, 003h, 080h, 080h, 080h, 0C0h, 0C0h, 0E0h, 0F0h, 0FCh
    DEFB 00Fh, 01Fh, 03Fh, 03Fh, 01Fh, 03Fh, 07Fh, 03Fh, 004h, 00Eh, 01Bh, 037h, 00Fh, 02Fh, 040h, 03Fh   ; глиф 173 @+3904 [raw]
    DEFB 004h, 00Eh, 01Bh, 037h, 00Fh, 02Fh, 040h, 03Fh, 0F0h, 0E0h, 0C0h, 0C0h, 0E0h, 0C0h, 080h, 0C0h
    DEFB 0FEh, 0FEh, 0FEh, 0FCh, 0FCh, 0F8h, 0F0h, 0C0h, 0F8h, 0F8h, 0F8h, 0F8h, 0F0h, 0F0h, 0E0h, 0C0h   ; глиф 174 @+3936 [raw]
    DEFB 0F8h, 0F8h, 0F8h, 0F8h, 0F0h, 0F0h, 0E0h, 0C0h, 001h, 001h, 001h, 003h, 003h, 007h, 00Fh, 03Fh
    DEFB 070h, 0F0h, 0F0h, 0FCh, 0FCh, 0F8h, 0F0h, 0FCh, 000h, 000h, 000h, 080h, 080h, 088h, 000h, 0F0h   ; глиф 175 @+3968 [raw]
    DEFB 000h, 000h, 000h, 080h, 080h, 088h, 000h, 0F0h, 08Fh, 00Fh, 00Fh, 003h, 003h, 007h, 00Fh, 003h
    DEFB 06Dh, 06Dh, 06Dh, 02Dh, 03Fh, 01Fh, 00Fh, 003h, 06Dh, 06Dh, 06Dh, 02Dh, 03Fh, 01Fh, 00Fh, 003h   ; глиф 176 @+4000 [raw]
    DEFB 06Dh, 06Dh, 06Dh, 02Dh, 03Fh, 01Fh, 00Fh, 003h, 080h, 080h, 080h, 0C0h, 0C0h, 0E0h, 0F0h, 0FCh
    DEFB 01Ch, 03Eh, 07Fh, 06Fh, 00Fh, 00Fh, 00Fh, 03Fh, 000h, 01Ch, 038h, 067h, 00Fh, 00Fh, 000h, 03Fh   ; глиф 177 @+4032 [raw]
    DEFB 000h, 01Ch, 038h, 067h, 00Fh, 00Fh, 000h, 03Fh, 0E3h, 0C1h, 080h, 090h, 0F0h, 0F0h, 0F0h, 0C0h
    DEFB 0FEh, 0FEh, 0FEh, 0FCh, 0FCh, 0F8h, 0F0h, 0C0h, 0F8h, 0F8h, 0F8h, 0F8h, 0F0h, 0F0h, 0E0h, 0C0h   ; глиф 178 @+4064 [raw]
    DEFB 0F8h, 0F8h, 0F8h, 0F8h, 0F0h, 0F0h, 0E0h, 0C0h, 001h, 001h, 001h, 003h, 003h, 007h, 00Fh, 03Fh
    DEFB 0F8h, 07Ch, 0FCh, 0F0h, 0F8h, 0F8h, 0F0h, 0FCh, 0E0h, 070h, 000h, 060h, 070h, 0B0h, 0B0h, 0F0h   ; глиф 179 @+4096 [raw]
    DEFB 0E0h, 070h, 000h, 060h, 070h, 0B0h, 0B0h, 0F0h, 007h, 083h, 003h, 00Fh, 007h, 007h, 00Fh, 003h
    DEFB 06Dh, 06Dh, 06Dh, 02Dh, 03Fh, 01Fh, 00Fh, 003h, 06Dh, 06Dh, 06Dh, 02Dh, 03Fh, 01Fh, 00Fh, 003h   ; глиф 180 @+4128 [raw]
    DEFB 06Dh, 06Dh, 06Dh, 02Dh, 03Fh, 01Fh, 00Fh, 003h, 080h, 080h, 080h, 0C0h, 0C0h, 0E0h, 0F0h, 0FCh
    DEFB 03Fh, 01Fh, 00Fh, 03Fh, 03Fh, 03Fh, 01Fh, 03Fh, 037h, 01Bh, 000h, 027h, 02Fh, 02Fh, 000h, 03Fh   ; глиф 181 @+4160 [raw]
    DEFB 037h, 01Bh, 000h, 027h, 02Fh, 02Fh, 000h, 03Fh, 0C0h, 0E0h, 0F0h, 0C0h, 0C0h, 0C0h, 0E0h, 0C0h
    DEFB 0FEh, 0FEh, 0FEh, 0FCh, 0FCh, 0F8h, 0F0h, 0C0h, 0F8h, 0F8h, 0F8h, 0F8h, 0F0h, 0F0h, 0E0h, 0C0h   ; глиф 182 @+4192 [raw]
    DEFB 0F8h, 0F8h, 0F8h, 0F8h, 0F0h, 0F0h, 0E0h, 0C0h, 001h, 001h, 001h, 003h, 003h, 007h, 00Fh, 03Fh
    DEFB 0F0h, 0F0h, 0E0h, 0F8h, 0F8h, 0F8h, 0F0h, 0FCh, 0C0h, 0C0h, 080h, 0D0h, 0D0h, 0E0h, 000h, 0F0h   ; глиф 183 @+4224 [raw]
    DEFB 0C0h, 0C0h, 080h, 0D0h, 0D0h, 0E0h, 000h, 0F0h, 00Fh, 00Fh, 01Fh, 007h, 007h, 007h, 00Fh, 003h
    DEFB 07Dh, 07Dh, 07Dh, 03Dh, 03Fh, 01Fh, 00Fh, 003h, 07Dh, 07Dh, 07Dh, 03Dh, 03Fh, 01Fh, 00Fh, 003h   ; глиф 184 @+4256 [raw]
    DEFB 07Dh, 07Dh, 07Dh, 03Dh, 03Fh, 01Fh, 00Fh, 003h, 082h, 082h, 082h, 0C2h, 0C0h, 0E0h, 0F0h, 0FCh
    DEFB 07Eh, 03Eh, 00Fh, 00Fh, 07Fh, 03Fh, 00Fh, 03Fh, 07Ch, 03Ch, 000h, 007h, 04Fh, 02Fh, 000h, 03Fh   ; глиф 185 @+4288 [raw]
    DEFB 07Ch, 03Ch, 000h, 007h, 04Fh, 02Fh, 000h, 03Fh, 081h, 0C1h, 0F0h, 0F0h, 080h, 0C0h, 0F0h, 0C0h
    DEFB 0BEh, 0BEh, 0BEh, 0BCh, 0FCh, 0F8h, 0F0h, 0C0h, 0B8h, 0B8h, 0B8h, 0B8h, 0F0h, 0F0h, 0E0h, 0C0h   ; глиф 186 @+4320 [raw]
    DEFB 0B8h, 0B8h, 0B8h, 0B8h, 0F0h, 0F0h, 0E0h, 0C0h, 041h, 041h, 041h, 043h, 003h, 007h, 00Fh, 03Fh
    DEFB 07Eh, 07Ch, 0F0h, 0F0h, 0FEh, 0FCh, 0F0h, 0FCh, 038h, 030h, 000h, 080h, 0C0h, 0CCh, 000h, 0F0h   ; глиф 187 @+4352 [raw]
    DEFB 038h, 030h, 000h, 080h, 0C0h, 0CCh, 000h, 0F0h, 081h, 083h, 00Fh, 00Fh, 001h, 003h, 00Fh, 003h
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 072h, 045h, 075h, 000h, 0FFh, 080h, 080h, 0FFh   ; глиф 188 @+4384 [raw]
    DEFB 072h, 045h, 075h, 000h, 0FFh, 080h, 080h, 0FFh, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 0FFh, 080h, 080h, 0FFh, 000h, 075h, 045h   ; глиф 189 @+4416 [raw]
    DEFB 000h, 0FFh, 080h, 080h, 0FFh, 000h, 075h, 045h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 048h, 048h, 05Ch, 000h, 0FFh, 001h, 001h, 0FFh   ; глиф 190 @+4448 [raw]
    DEFB 048h, 048h, 05Ch, 000h, 0FFh, 001h, 001h, 0FFh, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h
    DEFB 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 0FFh, 001h, 001h, 0FFh, 000h, 048h, 048h   ; глиф 191 @+4480 [raw]
    DEFB 000h, 0FFh, 001h, 001h, 0FFh, 000h, 048h, 048h, 000h, 000h, 000h, 000h, 000h, 000h, 000h, 000h
    DEFB 000h, 0CEh, 0DBh, 0FBh, 0DBh, 0CEh, 000h, 000h, 000h, 07Eh, 0CCh, 07Ch, 00Ch, 078h, 000h, 000h   ; глиф 192 @+4512 [compact]
    DEFB 000h, 078h, 0CCh, 0CCh, 0F8h, 0C0h, 078h, 004h, 006h, 0FEh, 0CCh, 0CCh, 0CCh, 0CCh, 000h, 000h
    DEFB 0C3h, 0FFh, 066h, 066h, 066h, 07Eh, 000h, 000h, 000h, 07Ch, 0C0h, 0FCh, 0CCh, 078h, 000h, 000h   ; глиф 196 @+4544 [compact]
    DEFB 018h, 018h, 07Eh, 0DBh, 0DBh, 07Eh, 018h, 000h, 000h, 0C0h, 0C0h, 0C0h, 0C0h, 0FCh, 000h, 000h
    DEFB 000h, 0C6h, 06Ch, 038h, 06Ch, 0C6h, 000h, 000h, 000h, 0CCh, 0ECh, 0DCh, 0CCh, 0CCh, 000h, 000h   ; глиф 200 @+4576 [compact]
    DEFB 000h, 0CCh, 0ECh, 0DCh, 0CCh, 0CCh, 000h, 030h, 000h, 0CCh, 0CCh, 0F0h, 0D8h, 0CCh, 000h, 000h
    DEFB 000h, 0C6h, 066h, 036h, 01Eh, 00Eh, 000h, 000h, 000h, 0C6h, 0C6h, 0D6h, 0EEh, 0C6h, 000h, 000h   ; глиф 204 @+4608 [compact]
    DEFB 000h, 0CCh, 0CCh, 0FCh, 0CCh, 0CCh, 000h, 000h, 000h, 078h, 0CCh, 0CCh, 0CCh, 078h, 000h, 000h
    DEFB 000h, 0CCh, 0CCh, 0CCh, 0CCh, 0FCh, 000h, 000h, 000h, 0CCh, 06Ch, 07Ch, 0CCh, 07Ch, 000h, 000h   ; глиф 208 @+4640 [compact]
    DEFB 0C0h, 0C0h, 0F8h, 0CCh, 0CCh, 0F8h, 000h, 000h, 000h, 078h, 0CCh, 0C0h, 0CCh, 078h, 000h, 000h
    DEFB 000h, 030h, 030h, 030h, 030h, 0FCh, 000h, 000h, 078h, 0CCh, 00Ch, 07Ch, 0CCh, 0CCh, 000h, 000h   ; глиф 212 @+4672 [compact]
    DEFB 000h, 0DBh, 07Eh, 018h, 07Eh, 0DBh, 000h, 000h, 000h, 0FCh, 0C6h, 0F8h, 0CCh, 0F8h, 000h, 000h
    DEFB 000h, 0F8h, 0CCh, 0F8h, 0C0h, 0C0h, 000h, 000h, 000h, 0F2h, 0DAh, 0F2h, 0C2h, 0C2h, 000h, 000h   ; глиф 216 @+4704 [compact]
    DEFB 000h, 078h, 0CCh, 018h, 0CCh, 078h, 000h, 000h, 000h, 0FEh, 0D6h, 0D6h, 0D6h, 0D6h, 000h, 000h
    DEFB 000h, 07Ch, 0C6h, 01Eh, 0C6h, 07Ch, 000h, 000h, 003h, 0FFh, 0D6h, 0D6h, 0D6h, 0D6h, 000h, 000h   ; глиф 220 @+4736 [compact]
    DEFB 000h, 00Ch, 00Ch, 07Ch, 0CCh, 0CCh, 000h, 000h, 000h, 03Eh, 033h, 03Eh, 030h, 0F0h, 000h, 000h
    DEFB 000h, 0CEh, 0DBh, 0DBh, 0FBh, 0DBh, 0DBh, 0CEh, 000h, 0C6h, 0C6h, 0FEh, 066h, 036h, 01Eh, 00Eh   ; глиф 224 @+4768 [compact]
    DEFB 000h, 0FCh, 0C6h, 0C6h, 0FCh, 0C0h, 0C0h, 0FCh, 006h, 0FEh, 0CCh, 0CCh, 0CCh, 0CCh, 0CCh, 0CCh
    DEFB 0C3h, 0FFh, 066h, 066h, 066h, 066h, 066h, 07Eh, 000h, 0FEh, 0C0h, 0C0h, 0F8h, 0C0h, 0C0h, 0FCh   ; глиф 228 @+4800 [compact]
    DEFB 000h, 018h, 07Eh, 0DBh, 0DBh, 0DBh, 07Eh, 018h, 000h, 0C0h, 0C0h, 0C0h, 0C0h, 0C0h, 0C0h, 0FCh
    DEFB 000h, 0C3h, 066h, 03Ch, 018h, 03Ch, 066h, 0C3h, 000h, 0C6h, 0E6h, 0F6h, 0DEh, 0CEh, 0C6h, 0C6h   ; глиф 232 @+4832 [compact]
    DEFB 000h, 0C6h, 0E6h, 0F6h, 0DEh, 0CEh, 0C6h, 0D6h, 000h, 0C6h, 0C6h, 0CCh, 0F8h, 0D8h, 0CCh, 0C6h
    DEFB 000h, 0C6h, 0C6h, 066h, 036h, 01Eh, 00Eh, 006h, 000h, 0C6h, 0C6h, 0C6h, 0D6h, 0FEh, 0EEh, 0C6h   ; глиф 236 @+4864 [compact]
    DEFB 000h, 0C6h, 0C6h, 0C6h, 0FEh, 0C6h, 0C6h, 0C6h, 000h, 07Ch, 0C6h, 0C6h, 0C6h, 0C6h, 0C6h, 07Ch
    DEFB 000h, 0C6h, 0C6h, 0C6h, 0C6h, 0C6h, 0C6h, 0FEh, 000h, 0C6h, 066h, 036h, 07Eh, 0C6h, 0C6h, 07Eh   ; глиф 240 @+4896 [compact]
    DEFB 000h, 0C0h, 0C0h, 0C0h, 0FCh, 0C6h, 0C6h, 0FCh, 000h, 07Ch, 0C6h, 0C0h, 0C0h, 0C0h, 0C6h, 07Ch
    DEFB 000h, 030h, 030h, 030h, 030h, 030h, 030h, 0FCh, 000h, 07Ch, 0C6h, 006h, 07Eh, 0C6h, 0C6h, 0C6h   ; глиф 244 @+4928 [compact]
    DEFB 000h, 0DBh, 0DBh, 07Eh, 018h, 07Eh, 0DBh, 0DBh, 000h, 0FCh, 0C6h, 0C6h, 0FCh, 0CCh, 0CCh, 0F8h
    DEFB 000h, 0FCh, 0C6h, 0C6h, 0FCh, 0C0h, 0C0h, 0C0h, 000h, 0F2h, 0DAh, 0DAh, 0F2h, 0C2h, 0C2h, 0C2h   ; глиф 248 @+4960 [compact]
    DEFB 000h, 07Ch, 0C6h, 006h, 03Ch, 006h, 066h, 03Ch, 000h, 0FEh, 0D6h, 0D6h, 0D6h, 0D6h, 0D6h, 0D6h
    DEFB 000h, 07Ch, 0C6h, 006h, 01Eh, 006h, 0C6h, 07Ch, 003h, 0FFh, 0D6h, 0D6h, 0D6h, 0D6h, 0D6h, 0D6h   ; глиф 252 @+4992 [compact]
    DEFB 0EFh, 07Dh, 032h, 000h, 000h, 000h, 000h, 000h, 010h, 082h, 0CDh, 07Fh, 03Ah, 0B0h, 010h, 008h
    DEFB 010h, 082h, 0CDh, 07Fh, 03Ah, 0B0h, 010h, 008h, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh, 0FFh
    DEFB 000h, 03Eh, 033h, 033h, 03Eh, 030h, 030h, 0F0h
