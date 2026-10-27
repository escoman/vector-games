; ===========================================================================
; SOUNDEMO.ROM boot loader (loaded at origin 0x0100)
; 9344-byte self-extracting ROM by "shilin d.w" (Шилин Д.В.), (C) 1994
; ===========================================================================
; Boot copies:
;   * unpacker source (mem 0x150..0x1EF, 160 bytes)  -> RAM 0xFF50
;   * compressed stream (mem 0x200..0x267F, 9344 B)  -> RAM 0xDA80
; then JMPs to 0xFF50 to run the unpacker.
;
; Unpacker decompresses 0xDA80.. to 0x0100.., then PCHL to the stored entry
; (0x0100). The decompressed image installs its own vectors at 0x0000/0x0038
; and executes the melody player from func_main_entry (0x37A8).
; ===========================================================================
        .area CODE_BOOT (ABS)
        .org 0x0100

func_boot:
    DI                  ; 0100: F3
    LXI SP, 0000h       ; 0101: 31 00 00    SP=0 wraps -> grows down from 0xFFFF
    XRA  A              ; 0104: AF
    OUT  10h            ; 0105: D3 10       port 0x10 = soft reset / init
    LXI  DE, 0FF50h     ; 0107: 11 50 FF    dest: unpacker routine
    LXI  HL, 0150h      ; 010A: 21 50 01    src : boot file bytes 0x50..0xEF
    LXI  BC, 00A0h      ; 010D: 01 A0 00    len : 160 bytes
    CALL func_memcpy    ; 0110: CD 22 01
    LXI  DE, 0DA80h     ; 0113: 11 80 DA    dest: compressed stream
    LXI  HL, 0200h      ; 0116: 21 00 02    src : file offset 0x100
    LXI  BC, 2480h      ; 0119: 01 80 24    len : 9344 bytes
    CALL func_memcpy    ; 011C: CD 22 01
    JMP  0FF50h         ; 011F: C3 50 FF    enter unpacker

; ---------------------------------------------------------------------------
; func_memcpy: BC bytes at (HL) -> (DE), loop while BC != 0
; ---------------------------------------------------------------------------
func_memcpy:
    MOV  A, M           ; 0122: 7E
    STAX D              ; 0123: 12
    INX  H              ; 0124: 23
    INX  D              ; 0125: 13
    DCX  B              ; 0126: 0B
    MOV  A, B           ; 0127: 78
    ORA  C              ; 0128: B1
    JNZ  func_memcpy    ; 0129: C2 22 01
    RET                 ; 012C: C9

; ---------------------------------------------------------------------------
; dead code after JMP 0xFF50 -- never reached from boot path. Would patch
; the reset vector to JMP 0x0100 if it were ever executed.
; ---------------------------------------------------------------------------
    MVI  A, 0C3h        ; 012D: 3E C3       JMP opcode
    STA  0000h          ; 0130: 32 00 00    patch reset vector
    LXI  HL, 0100h      ; 0133: 21 00 01
    SHLD 0001h          ; 0136: 22 01 00    low half of JMP target = 0x0100
    RET                 ; 0139: C9

; ---------------------------------------------------------------------------
; Signature at file offset 0x38 (= mem 0x0138)
;   "shilin d.w (C)" 0xE0 0x2E 0x27 0x39 0x34 0x21 0x07 0x00 0x7E 0x3D
; Decoded CP-866 tail: "Д.В'94" -> "Д.В. Шилин, 1994"
;   0x21 0x07 0x00 0x7E 0x3D -- unused / padding
; ---------------------------------------------------------------------------
    .ascii "shilin d.w (C)"                ; 013A..0147
    .db 0xE0h, 0x2Eh, 0x27h, 0x39h, 0x34h  ; 0148..014C
    .db 0x21h, 0x07h, 0x00h, 0x7Eh, 0x3Dh  ; 014D..0x51
