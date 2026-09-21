; Данные: data_glyph_ptr_table
; Адрес: 0x0600
; Размер: 512 байт (256 слов)
; Назначение: таблица указателей глифов. word[N] = data_glyph_block(0x6000) + N*32 =
;             адрес 32-байтной битмапы глифа N. Читается func_render_glyph (0x0803):
;             HL=0x0600+A*2 -> DE=(HL). Все значения указывают в ОЗУ-блок глифов
;             (строится при инициализации), поэтому даны символьно как смещения от
;             data_glyph_block (адресная база). Машинный код = word в LE-порядке.

data_glyph_ptr_table:
    ; глифы 0..7 (смещения 0..224)
    DEFW data_glyph_block+0,   data_glyph_block+32,  data_glyph_block+64,  data_glyph_block+96
    DEFW data_glyph_block+128, data_glyph_block+160, data_glyph_block+192, data_glyph_block+224
    ; глифы 8..15 (256..480)
    DEFW data_glyph_block+256, data_glyph_block+288, data_glyph_block+320, data_glyph_block+352
    DEFW data_glyph_block+384, data_glyph_block+416, data_glyph_block+448, data_glyph_block+480
    ; глифы 16..23 (512..736)
    DEFW data_glyph_block+512, data_glyph_block+544, data_glyph_block+576, data_glyph_block+608
    DEFW data_glyph_block+640, data_glyph_block+672, data_glyph_block+704, data_glyph_block+736
    ; глифы 24..31 (768..992)
    DEFW data_glyph_block+768, data_glyph_block+800, data_glyph_block+832, data_glyph_block+864
    DEFW data_glyph_block+896, data_glyph_block+928, data_glyph_block+960, data_glyph_block+992
    ; глифы 32..39 (1024..1248)
    DEFW data_glyph_block+1024, data_glyph_block+1056, data_glyph_block+1088, data_glyph_block+1120
    DEFW data_glyph_block+1152, data_glyph_block+1184, data_glyph_block+1216, data_glyph_block+1248
    ; глифы 40..47 (1280..1504)
    DEFW data_glyph_block+1280, data_glyph_block+1312, data_glyph_block+1344, data_glyph_block+1376
    DEFW data_glyph_block+1408, data_glyph_block+1440, data_glyph_block+1472, data_glyph_block+1504
    ; глифы 48..55 (1536..1760)
    DEFW data_glyph_block+1536, data_glyph_block+1568, data_glyph_block+1600, data_glyph_block+1632
    DEFW data_glyph_block+1664, data_glyph_block+1696, data_glyph_block+1728, data_glyph_block+1760
    ; глифы 56..63 (1792..2016)
    DEFW data_glyph_block+1792, data_glyph_block+1824, data_glyph_block+1856, data_glyph_block+1888
    DEFW data_glyph_block+1920, data_glyph_block+1952, data_glyph_block+1984, data_glyph_block+2016
    ; глифы 64..71 (2048..2272)
    DEFW data_glyph_block+2048, data_glyph_block+2080, data_glyph_block+2112, data_glyph_block+2144
    DEFW data_glyph_block+2176, data_glyph_block+2208, data_glyph_block+2240, data_glyph_block+2272
    ; глифы 72..79 (2304..2528)
    DEFW data_glyph_block+2304, data_glyph_block+2336, data_glyph_block+2368, data_glyph_block+2400
    DEFW data_glyph_block+2432, data_glyph_block+2464, data_glyph_block+2496, data_glyph_block+2528
    ; глифы 80..87 (2560..2784)
    DEFW data_glyph_block+2560, data_glyph_block+2592, data_glyph_block+2624, data_glyph_block+2656
    DEFW data_glyph_block+2688, data_glyph_block+2720, data_glyph_block+2752, data_glyph_block+2784
    ; глифы 88..95 (2816..3040)
    DEFW data_glyph_block+2816, data_glyph_block+2848, data_glyph_block+2880, data_glyph_block+2912
    DEFW data_glyph_block+2944, data_glyph_block+2976, data_glyph_block+3008, data_glyph_block+3040
    ; глифы 96..103 (3072..3296)
    DEFW data_glyph_block+3072, data_glyph_block+3104, data_glyph_block+3136, data_glyph_block+3168
    DEFW data_glyph_block+3200, data_glyph_block+3232, data_glyph_block+3264, data_glyph_block+3296
    ; глифы 104..111 (3328..3552)
    DEFW data_glyph_block+3328, data_glyph_block+3360, data_glyph_block+3392, data_glyph_block+3424
    DEFW data_glyph_block+3456, data_glyph_block+3488, data_glyph_block+3520, data_glyph_block+3552
    ; глифы 112..119 (3584..3808)
    DEFW data_glyph_block+3584, data_glyph_block+3616, data_glyph_block+3648, data_glyph_block+3680
    DEFW data_glyph_block+3712, data_glyph_block+3744, data_glyph_block+3776, data_glyph_block+3808
    ; глифы 120..127 (3840..4064)
    DEFW data_glyph_block+3840, data_glyph_block+3872, data_glyph_block+3904, data_glyph_block+3936
    DEFW data_glyph_block+3968, data_glyph_block+4000, data_glyph_block+4032, data_glyph_block+4064
    ; глифы 128..135 (4096..4320)
    DEFW data_glyph_block+4096, data_glyph_block+4128, data_glyph_block+4160, data_glyph_block+4192
    DEFW data_glyph_block+4224, data_glyph_block+4256, data_glyph_block+4288, data_glyph_block+4320
    ; глифы 136..143 (4352..4576)
    DEFW data_glyph_block+4352, data_glyph_block+4384, data_glyph_block+4416, data_glyph_block+4448
    DEFW data_glyph_block+4480, data_glyph_block+4512, data_glyph_block+4544, data_glyph_block+4576
    ; глифы 144..151 (4608..4832)
    DEFW data_glyph_block+4608, data_glyph_block+4640, data_glyph_block+4672, data_glyph_block+4704
    DEFW data_glyph_block+4736, data_glyph_block+4768, data_glyph_block+4800, data_glyph_block+4832
    ; глифы 152..159 (4864..5088)
    DEFW data_glyph_block+4864, data_glyph_block+4896, data_glyph_block+4928, data_glyph_block+4960
    DEFW data_glyph_block+4992, data_glyph_block+5024, data_glyph_block+5056, data_glyph_block+5088
    ; глифы 160..167 (5120..5344)
    DEFW data_glyph_block+5120, data_glyph_block+5152, data_glyph_block+5184, data_glyph_block+5216
    DEFW data_glyph_block+5248, data_glyph_block+5280, data_glyph_block+5312, data_glyph_block+5344
    ; глифы 168..175 (5376..5600)
    DEFW data_glyph_block+5376, data_glyph_block+5408, data_glyph_block+5440, data_glyph_block+5472
    DEFW data_glyph_block+5504, data_glyph_block+5536, data_glyph_block+5568, data_glyph_block+5600
    ; глифы 176..183 (5632..5856)
    DEFW data_glyph_block+5632, data_glyph_block+5664, data_glyph_block+5696, data_glyph_block+5728
    DEFW data_glyph_block+5760, data_glyph_block+5792, data_glyph_block+5824, data_glyph_block+5856
    ; глифы 184..191 (5888..6112)
    DEFW data_glyph_block+5888, data_glyph_block+5920, data_glyph_block+5952, data_glyph_block+5984
    DEFW data_glyph_block+6016, data_glyph_block+6048, data_glyph_block+6080, data_glyph_block+6112
    ; глифы 192..199 (6144..6368)
    DEFW data_glyph_block+6144, data_glyph_block+6176, data_glyph_block+6208, data_glyph_block+6240
    DEFW data_glyph_block+6272, data_glyph_block+6304, data_glyph_block+6336, data_glyph_block+6368
    ; глифы 200..207 (6400..6624)
    DEFW data_glyph_block+6400, data_glyph_block+6432, data_glyph_block+6464, data_glyph_block+6496
    DEFW data_glyph_block+6528, data_glyph_block+6560, data_glyph_block+6592, data_glyph_block+6624
    ; глифы 208..215 (6656..6880)
    DEFW data_glyph_block+6656, data_glyph_block+6688, data_glyph_block+6720, data_glyph_block+6752
    DEFW data_glyph_block+6784, data_glyph_block+6816, data_glyph_block+6848, data_glyph_block+6880
    ; глифы 216..223 (6912..7136)
    DEFW data_glyph_block+6912, data_glyph_block+6944, data_glyph_block+6976, data_glyph_block+7008
    DEFW data_glyph_block+7040, data_glyph_block+7072, data_glyph_block+7104, data_glyph_block+7136
    ; глифы 224..231 (7168..7392)
    DEFW data_glyph_block+7168, data_glyph_block+7200, data_glyph_block+7232, data_glyph_block+7264
    DEFW data_glyph_block+7296, data_glyph_block+7328, data_glyph_block+7360, data_glyph_block+7392
    ; глифы 232..239 (7424..7648)
    DEFW data_glyph_block+7424, data_glyph_block+7456, data_glyph_block+7488, data_glyph_block+7520
    DEFW data_glyph_block+7552, data_glyph_block+7584, data_glyph_block+7616, data_glyph_block+7648
    ; глифы 240..247 (7680..7904)
    DEFW data_glyph_block+7680, data_glyph_block+7712, data_glyph_block+7744, data_glyph_block+7776
    DEFW data_glyph_block+7808, data_glyph_block+7840, data_glyph_block+7872, data_glyph_block+7904
    ; глифы 248..255 (7936..8160)
    DEFW data_glyph_block+7936, data_glyph_block+7968, data_glyph_block+8000, data_glyph_block+8032
    DEFW data_glyph_block+8064, data_glyph_block+8096, data_glyph_block+8128, data_glyph_block+8160
