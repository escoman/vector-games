;
; loader_stage2.inc — сгенерировано из .scratch/loader_stage2.bin (utils/bin2inc.py), НЕ ПРАВИТЬ.
;
; Собран под ORG 0e000h: метки разрешены в абсолютные адреса этой
; области, поэтому массив копируется в память побайтово без
; релопации. docs/LOADER_TZ.MD.
;
loader_stage2:
        db      0F3h, 031h, 0F0h, 0DCh, 03Eh, 008h, 032h, 0F6h, 0DEh, 0AFh, 032h, 0F4h, 0DEh, 001h, 000h, 000h
        db      03Eh, 000h, 002h, 003h, 002h, 003h, 0B9h, 0C2h, 012h, 0E0h, 078h, 0FEh, 0E0h, 0C2h, 010h, 0E0h
        db      03Eh, 0C3h, 032h, 000h, 000h, 03Eh, 000h, 032h, 001h, 000h, 03Eh, 0E0h, 032h, 002h, 000h, 03Eh
        db      088h, 0D3h, 000h, 03Eh, 081h, 0D3h, 004h, 03Eh, 0FFh, 0D3h, 003h, 0D3h, 005h, 0D3h, 006h, 0D3h
        db      007h, 0AFh, 0D3h, 002h, 03Ah, 044h, 0E8h, 0B7h, 0CAh, 054h, 0E0h, 021h, 042h, 0E8h, 011h, 060h
        db      0E8h, 0CDh, 023h, 0E1h, 03Ah, 048h, 0E8h, 0B7h, 0CAh, 064h, 0E0h, 021h, 046h, 0E8h, 011h, 060h
        db      0F0h, 0CDh, 023h, 0E1h, 01Eh, 008h, 016h, 0C9h, 07Ah, 06Fh, 026h, 0C0h, 0CDh, 0FEh, 0E0h, 07Ah
        db      03Dh, 06Fh, 026h, 0C0h, 0CDh, 0F2h, 0E0h, 07Ah, 0D6h, 00Ah, 06Fh, 026h, 0C0h, 0CDh, 0F2h, 0E0h
        db      07Ah, 0D6h, 018h, 057h, 01Dh, 0C2h, 068h, 0E0h, 021h, 000h, 0C0h, 011h, 000h, 010h, 07Eh, 012h
        db      013h, 036h, 000h, 023h, 07Eh, 012h, 013h, 036h, 000h, 023h, 07Ch, 0FEh, 0E0h, 0C2h, 08Eh, 0E0h
        db      01Eh, 060h, 00Eh, 00Fh, 079h, 0D3h, 002h, 0E6h, 002h, 0CAh, 0B2h, 0E0h, 03Ah, 041h, 0E8h, 0C3h
        db      0B5h, 0E0h, 03Ah, 040h, 0E8h, 0D3h, 00Ch, 00Dh, 0F2h, 0A4h, 0E0h, 01Dh, 0C2h, 0A2h, 0E0h, 016h
        db      004h, 01Eh, 050h, 0AFh, 0D3h, 002h, 03Ah, 040h, 0E8h, 0D3h, 00Ch, 01Dh, 0C2h, 0C3h, 0E0h, 015h
        db      0C2h, 0C1h, 0E0h, 021h, 000h, 010h, 011h, 000h, 0C0h, 07Eh, 012h, 013h, 036h, 000h, 023h, 07Eh
        db      012h, 013h, 036h, 000h, 023h, 07Ch, 0FEh, 030h, 0C2h, 0D9h, 0E0h, 03Eh, 002h, 0D3h, 001h, 0C3h
        db      064h, 0E1h, 006h, 020h, 03Eh, 0FFh, 0B6h, 077h, 024h, 005h, 0C2h, 0F4h, 0E0h, 0C9h, 006h, 020h
        db      03Eh, 081h, 0B6h, 077h, 024h, 005h, 0C2h, 000h, 0E1h, 0C9h, 0D5h, 07Dh, 007h, 007h, 007h, 06Fh
        db      07Ch, 01Fh, 0E6h, 070h, 057h, 01Fh, 082h, 085h, 0C6h, 018h, 06Fh, 07Ch, 0E6h, 01Fh, 0C6h, 0C0h
        db      067h, 0D1h, 0C9h, 07Eh, 0B7h, 01Fh, 01Fh, 01Fh, 0C6h, 0C0h, 032h, 030h, 0E8h, 023h, 07Eh, 02Fh
        db      032h, 031h, 0E8h, 023h, 07Eh, 032h, 032h, 0E8h, 023h, 07Eh, 032h, 033h, 0E8h, 03Ah, 030h, 0E8h
        db      067h, 03Ah, 031h, 0E8h, 06Fh, 03Ah, 032h, 0E8h, 04Fh, 01Ah, 0B6h, 077h, 013h, 024h, 00Dh, 0C2h
        db      049h, 0E1h, 03Ah, 031h, 0E8h, 03Dh, 032h, 031h, 0E8h, 03Ah, 033h, 0E8h, 03Dh, 032h, 033h, 0E8h
        db      0C2h, 03Dh, 0E1h, 0C9h, 0CDh, 073h, 0E2h, 057h, 0B7h, 01Fh, 05Fh, 082h, 067h, 0CDh, 073h, 0E2h
        db      0BCh, 0DAh, 067h, 0E1h, 082h, 032h, 0F6h, 0DEh, 01Eh, 00Ch, 03Eh, 008h, 0CDh, 030h, 0E2h, 0FEh
        db      055h, 0CAh, 089h, 0E1h, 0FEh, 0AAh, 0C2h, 064h, 0E1h, 01Dh, 0C2h, 07Ah, 0E1h, 0CDh, 00Eh, 0E2h
        db      05Fh, 07Eh, 0FEh, 000h, 0C2h, 08Dh, 0E1h, 021h, 0F1h, 0DEh, 07Eh, 02Bh, 0BEh, 0C2h, 064h, 0E1h
        db      057h, 02Bh, 07Eh, 032h, 0F7h, 0DEh, 047h, 03Eh, 008h, 032h, 0F8h, 0DEh, 0CDh, 00Eh, 0E2h, 0F5h
        db      07Eh, 0FEh, 000h, 0CAh, 0F0h, 0E1h, 087h, 087h, 087h, 087h, 087h, 04Fh, 0F1h, 023h, 07Eh, 0BBh
        db      0C2h, 0ACh, 0E1h, 0D5h, 0C5h, 023h, 011h, 07Eh, 020h, 07Eh, 002h, 00Ah, 0AEh, 077h, 023h, 00Ch
        db      015h, 0C2h, 0C9h, 0E1h, 0C1h, 069h, 060h, 0CDh, 00Ah, 0E1h, 073h, 0D1h, 03Ah, 0F8h, 0DEh, 03Dh
        db      032h, 0F8h, 0DEh, 0B7h, 0C2h, 0ACh, 0E1h, 07Ah, 0FEh, 001h, 0C2h, 0ACh, 0E1h, 0C3h, 004h, 0E2h
        db      0F1h, 093h, 0CAh, 0ACh, 0E1h, 03Ch, 0C2h, 064h, 0E1h, 01Dh, 004h, 015h, 03Eh, 008h, 032h, 0F8h
        db      0DEh, 0C3h, 0ACh, 0E1h, 0AFh, 0D3h, 001h, 03Ah, 0F7h, 0DEh, 067h, 02Eh, 000h, 0E9h, 0C5h, 021h
        db      0D0h, 0DEh, 0E5h, 001h, 023h, 000h, 03Eh, 0FFh, 0CDh, 030h, 0E2h, 077h, 023h, 080h, 047h, 03Eh
        db      008h, 00Dh, 0C2h, 018h, 0E2h, 02Bh, 078h, 096h, 096h, 07Eh, 0E1h, 0C2h, 012h, 0E2h, 0C1h, 0C9h
        db      0C5h, 0D5h, 00Eh, 000h, 057h, 0CDh, 0C2h, 0E2h, 0DBh, 001h, 0E6h, 010h, 0BBh, 0CAh, 038h, 0E2h
        db      007h, 007h, 007h, 007h, 079h, 017h, 04Fh, 0CDh, 0BBh, 0E2h, 07Ah, 0B7h, 0F2h, 068h, 0E2h, 079h
        db      0FEh, 0E6h, 0CAh, 062h, 0E2h, 0FEh, 019h, 0C2h, 038h, 0E2h, 03Eh, 0FFh, 032h, 0F4h, 0DEh, 0C3h
        db      066h, 0E2h, 0AFh, 032h, 0F4h, 0DEh, 016h, 009h, 015h, 0C2h, 038h, 0E2h, 03Ah, 0F4h, 0DEh, 0A9h
        db      0D1h, 0C1h, 0C9h, 0E5h, 0D5h, 0CDh, 09Eh, 0E2h, 047h, 0B7h, 01Fh, 04Fh, 021h, 000h, 000h, 016h
        db      020h, 0CDh, 09Eh, 0E2h, 0D5h, 016h, 000h, 05Fh, 019h, 0D1h, 05Fh, 090h, 0D2h, 091h, 0E2h, 078h
        db      093h, 0B9h, 0D2h, 075h, 0E2h, 015h, 0C2h, 081h, 0E2h, 029h, 07Ch, 0D1h, 0E1h, 0C9h, 0D5h, 0CDh
        db      0BBh, 0E2h, 0DBh, 001h, 0E6h, 010h, 0BBh, 0CAh, 0A2h, 0E2h, 05Fh, 016h, 001h, 0DBh, 001h, 0E6h
        db      010h, 014h, 0BBh, 0CAh, 0ADh, 0E2h, 07Ah, 087h, 087h, 0D1h, 0C9h, 03Ah, 0F6h, 0DEh, 03Dh, 0C2h
        db      0BEh, 0E2h, 0DBh, 001h, 0E6h, 010h, 05Fh, 0C9h
LOADER_STAGE2_SIZE      equ     712           ; размер blob, байт
