; БАЗА КАРТ УРОВНЕЙ (Stage 7). Один адрес — один объект: база совпадает с картой уровня 1, поэтому data_level_01 НЕ заведён; первые 278 байт (0x3594..0x36A9) = упакованная карта уровня 1. АДРЕСАЦИЯ: func_level_loader @0x24CF — HL=[0x253B] (base=0x3594) + слово [0x253D+2·(var_level−1)], т.е. адрес = base + offset_table[level−1]. ПОСТОЯННОГО STRIDE НЕТ: длины карт 179..376 байт (см. data_level_map_offsets). ГРАНИЦЫ: старт i-й карты = base+offset[i] (i=0..19), конец последней = base+5480+235 = 0x4BE7. ТОЖДЕСТВО: Σ len_i = 5715 = 0x1653 = data_next_addr(0x4BE7) − data_level_maps_addr(0x3594) — подтверждено чтением памяти и runtime (BP 0x253A: var_level=20 ⇒ DE=0x4BE7; var_level=13 ⇒ DE=0x4460; обе величины = прогноз модели). ФОРМАТ КАРТЫ: RLE-пары по 1 байту — мл. ниббл = длина повтора (0 ⇒ 256), ст. ниббл = код тайла; тайл → глиф 0x60+код; код 0x6F → 0x20 (пусто). Развёрнутая карта = ровно 704 байта = 22 ряда × 32 клетки (шаг ряда 0x20), пишется в буфер поля 0x7040..0x72FF; выход цикла по HL=0x7300. Для всех 20 уровней развёртка даёт ровно 704 клетки без переполнения (модель + runtime L1/L13/L20). СПЕЦ-ТАЙЛЫ: 0x60 — маркер старта игрока (стирается, координаты → 0x7C00/0x7C01, func_find_player_start @0x2034); 0x64 — целевая клетка (стирается, координаты → 0x7C21/0x7C22 → 0x7D11/0x7D12 и 0x7D31/0x7D32, func_find_scroll_target_cell @0x2136; счётчик целей 0x7C55 = 1 или 2); 0x20 — пусто. КАРТА L01: старт col=2,row=0; цель (15,1), целей 1; частоты тайлов: e(0x65)×122, a(0x61)×107, k(0x6B)×67, b(0x62)×54, n(0x6E)×15, h(0x68)×14.
data_level_maps:
data_level_01:
        defb    52h,01h,51h,2Fh,29h,0B1h,21h,54h
        defb    0F1h,51h,0FBh,41h,0FCh,0B1h,0F1h,54h
        defb    0F1h,51h,0B1h,12h,0F2h,0B1h,22h,0F7h
        defb    0B1h,25h,0F3h,0B1h,0F1h,54h,0F1h,51h
        defb    0B1h,22h,0F2h,0B1h,12h,0E1h,11h,0B1h
        defb    1Ah,0E1h,12h,0B1h,11h,54h,0F1h,51h
        defb    0B1h,12h,0E1h,11h,0B1h,0F4h,0B1h,0F9h
        defb    71h,0F3h,0B1h,0F1h,54h,0F1h,51h,0B1h
        defb    0F4h,0B1h,0F3h,0D1h,0B1h,0F7h,0B1h,16h
        defb    0F1h,54h,0F1h,51h,0B1h,0F4h,0B1h,0F3h
        defb    19h,0B1h,0F5h,0B1h,0F1h,54h,0F1h,51h
        defb    0B1h,0F4h,0B1h,0FBh,23h,0B1h,0F3h,0B1h
        defb    0F1h,54h,0F1h,51h,0B1h,0F1h,13h,0B1h
        defb    12h,0E1h,12h,0F2h,91h,0F6h,0B1h,0E3h
        defb    0B1h,0F1h,54h,0F1h,51h,0B1h,0F4h,0B1h
        defb    0F4h,28h,0F2h,0B1h,0F3h,0B1h,0F1h,54h
        defb    0F1h,51h,0B1h,0F4h,0B1h,0F7h,0D1h,0F1h
        defb    0D1h,0F4h,0B1h,0F3h,0B1h,0F1h,54h,0F1h
        defb    51h,0B1h,0F2h,15h,0E1h,12h,0B1h,12h
        defb    0F1h,14h,0F1h,0B1h,0F3h,0B1h,0F1h,54h
        defb    0F1h,51h,0B1h,0FAh,0B1h,0F8h,0B1h,0F3h
        defb    0B1h,0F1h,54h,0F1h,51h,11h,0E2h,12h
        defb    0B1h,0F5h,0B1h,0F3h,23h,0F2h,0B1h,0F2h
        defb    0B1h,11h,0F1h,54h,0F1h,51h,0F5h,0B1h
        defb    0F5h,0B1h,12h,0E1h,13h,0E1h,12h,0F2h
        defb    0B1h,0F2h,54h,0F1h,51h,0A1h,0F3h,16h
        defb    0E1h,0B1h,0FBh,0B1h,0F1h,0D1h,54h,0F1h
        defb    51h,12h,0F9h,0B1h,0F7h,11h,0B1h,11h
        defb    0F1h,0B1h,22h,54h,0F1h,51h,0D1h,0F3h
        defb    11h,0B1h,18h,0E1h,12h,0F3h,0B1h,0F2h
        defb    0B1h,0F1h,11h,54h,0F1h,51h,13h,0F2h
        defb    0B1h,0FCh,12h,0B1h,13h,0F1h,21h,54h
        defb    0F1h,51h,0F5h,0B1h,18h,0E1h,11h,0F4h
        defb    0B1h,0F3h,0D1h,11h,54h,0F7h,0B1h,0FEh
        defb    0B1h,0F2h,23h,5Ch,8Eh,58h
