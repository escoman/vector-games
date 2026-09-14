; Данные: data_rst55_vector
; Адрес: 0x002C
; Размер: 3 байта
; Описание: RST 5.5 interrupt vector at 0x002C. NOT configured by clrs.rom.
;           RAM data — content is zero at startup, unpredictable at runtime.
;           The program relies on RST 7 (VBlank) as its only interrupt source.

    org 002Ch

data_rst55_vector:
    defs 3                        ; Не инициализируется clrs.rom
