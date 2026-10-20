; Данные: data_ram_init_image_08C3
; Адрес: 0x08C3
; Размер: 98 байт
; Описание: Иниц. образ блока переменных ОЗУ (var_palette_timer..data_entity_ycoords): статичные стартовые значения игрового состояния, загружаемые в ОЗУ при старте. RDB мапит этот ROM-диапазон на RAM-переменные; линейный де코д даёт рассинхрон (данные, не код).
data_ram_init_image_08C3:
    DEFB 03h, 00h, 0Ch, 00h, 022h, 05Eh, 019h, 022h
    DEFB 020h, 01Ah, 022h, 0EEh, 019h, 021h, 00h, 01h
    DEFB 031h, 01Eh, 01Ah, 0E5h, 021h, 02h, 00h, 0E5h
    DEFB 02Bh, 02Bh, 022h, 01Eh, 01h, 0E5h, 00h, 022h
    DEFB 00h, 00h, 00h, 00h, 00h, 00h, 00h, 021h
    DEFB 079h, 06h, 022h, 029h, 00h, 03Ah, 05Dh, 00h
    DEFB 0FEh, 020h, 00h, 00h, 06h, 021h, 00h, 00h
    DEFB 0C3h, 0E5h, 0Dh, 031h, 016h, 01Ah, 0CDh, 04Eh
    DEFB 012h, 0Eh, 01h, 0C4h, 097h, 06h, 0CDh, 044h
    DEFB 012h, 03Eh, 023h, 0CDh, 0EFh, 011h, 0CDh, 0DEh
    DEFB 011h, 0CDh, 06h, 012h, 0FEh, 0Dh, 0CAh, 0FEh
    DEFB 06h, 021h, 045h, 019h, 036h, 00h, 0FEh, 02Dh
    DEFB 0C2h, 02Ah
