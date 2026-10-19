; Функция: func_music_trampoline
; Адрес: 0x3DC5
; Размер: 8 байт (0x3DC5..0x3DCC)
; Описание: Тонкая обёртка копирования музыкального вектора + сам модифицируемый
;          	payload-байткод. func_music_init (0x3D4E) подготавливает HL= адрес
;          	payload, DE=03F8h (слот музыкального тика в ISR-векторе ОЗУ), BC=3 и
;          	переходит (JMP) на func_memcpy_trampoline: CALL func_memcpy_keep_psw
;          	копирует 3 байта payload в 03F8h, затем EI/RET. Payload (data_pad_3DCA)
;          	= байткод `CALL func_music_tick`, который компоновщик прописывает через
;          	ссылку на метку, чтобы при релокации (Фаза 2) адрес тика обновился
;          	автоматически.

func_memcpy_trampoline:
    CALL func_memcpy_keep_psw   ; 0x3DC5
    EI                          ; 0x3DC8
    RET                         ; 0x3DC9
data_pad_3DCA:
    DEFB 0CDh                   ; 0x3DCA  опкод CALL
    DW func_music_tick          ; 0x3DCB  адрес цели тика (reloc-ссылка)
