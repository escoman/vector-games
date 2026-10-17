; equates.asm — аппаратные и структурные константы образа (ветвь A).
; Только EQU (байт не эмитит) -> включение в мастер не сдвигает адреса.
; Источники: docs/VECTOR_VERIFIED.md (VERIFIED_BY_CODE) и карта RDB.
; Метки var_*/data_*/func_* уже определены в code.asm — здесь их нет,
; чтобы не было коллизий имён при сборке.

PORT_PIA_CW    equ 0000h   ; КР580ВВ55 управляющее слово: D7=1 режим, D7=0 BSR порта C
PORT_PIA_PC    equ 0001h   ; Port C: служебные клавиши (ст. биты); бит0 = магнитофон/бипер
PORT_PIA_PB    equ 0002h   ; Port B: out бит0-3 бордюр, бит4 режим 512px; in — клавиатура
PORT_PIA_PA    equ 0003h   ; Port A: вертикальный скролл + маска строк клавиатуры
PORT_VI53_CW   equ 0008h   ; КР580ВИ53 управляющее слово таймера
PORT_VI53_C2   equ 0009h   ; ВИ53 счётчик канала 2 (тон/звук)
PORT_VI53_C1   equ 000Ah   ; ВИ53 счётчик канала 1
PORT_VI53_C0   equ 000Bh   ; ВИ53 счётчик канала 0
PORT_PALETTE   equ 000Ch   ; запись физ. цвета в палитру (адрес = 4 бита пикселя); зеркала 0D..0F
PORT_BANK      equ 0010h   ; банковая память
PLANE3_BASE    equ 8000h   ; VRAM плоскость 3 (бит 3 цвета)
PLANE2_BASE    equ 0A000h   ; VRAM плоскость 2 (бит 2 цвета)
PLANE1_BASE    equ 0C000h   ; VRAM плоскость 1 (бит 1 цвета)
PLANE0_BASE    equ 0E000h   ; VRAM плоскость 0 (бит 0 цвета)
STACK_TOP      equ 7FFFh   ; вершина стека при boot (LXI SP,7FFFh в func_0000)
GLYPH_BASE     equ 379Fh   ; data_glyph_block — знакогенератор 128x5 (Stage 7)
KEYWORD_BASE   equ 256Eh   ; data_keyword_table — 101 слово (Stage 8)
MSGPOOL_BASE   equ 2465h   ; data_error_messages — пул 23 строк (Stage 8)
AUTOLOAD_BASE  equ 4012h   ; str_autoload — COLOR15,0,1:CLS (Stage 8)

; ---- зеркала порта палитры ----
PORT_PALETTE1 equ 000Dh   ; зеркало 0Ch
PORT_PALETTE2 equ 000Eh   ; зеркало 0Ch
PORT_PALETTE3 equ 000Fh   ; зеркало 0Ch

; ---- размер образа ----
RAM_IMAGE_SIZE equ 4300h   ; 17152 байт (0x0000..0x42FF)
