; Данные: data_rst75_vector
; Адрес: 0x003C
; Размер: 3 байта
; Описание: RST 7.5 interrupt vector at 0x003C. NOT configured by clrs.rom.
;           RAM data — content is zero at startup, unpredictable at runtime.
;           The program relies on RST 7 (VBlank) as its only interrupt source.

    org 003Ch

data_rst75_vector:
    defs 3                        ; Не инициализируется clrs.rom
