;
; loader_stage2.inc — сгенерировано из .scratch/loader_stage2.bin (utils/bin2inc.py), НЕ ПРАВИТЬ.
;
; Собран под ORG 0e000h: метки разрешены в абсолютные адреса этой
; области, поэтому массив копируется в память побайтово без
; релопации. docs/LOADER_TZ.MD.
;
loader_stage2:
        db      0F3h, 03Eh, 008h, 032h, 024h, 0E2h, 001h, 000h, 000h, 03Eh, 000h, 002h, 003h, 002h, 003h, 0B9h
        db      0C2h, 00Bh, 0E0h, 078h, 0FEh, 0E0h, 0C2h, 009h, 0E0h, 03Eh, 088h, 0D3h, 000h, 03Eh, 081h, 0D3h
        db      004h, 03Eh, 0FFh, 0D3h, 003h, 0D3h, 005h, 0D3h, 006h, 0D3h, 007h, 0AFh, 0D3h, 002h, 031h, 0F0h
        db      0DCh, 01Eh, 060h, 00Eh, 00Fh, 079h, 0D3h, 002h, 0E6h, 002h, 03Eh, 080h, 0CAh, 041h, 0E0h, 03Eh
        db      02Dh, 0D3h, 00Ch, 00Dh, 0F2h, 035h, 0E0h, 01Dh, 0C2h, 033h, 0E0h, 016h, 004h, 01Eh, 050h, 0AFh
        db      0D3h, 002h, 03Eh, 080h, 0D3h, 00Ch, 01Dh, 0C2h, 04Fh, 0E0h, 015h, 0C2h, 04Dh, 0E0h, 01Eh, 008h
        db      016h, 0C9h, 07Ah, 06Fh, 026h, 0C0h, 03Eh, 080h, 0CDh, 08Fh, 0E0h, 07Ah, 03Dh, 06Fh, 026h, 0C0h
        db      03Eh, 0FFh, 0CDh, 08Fh, 0E0h, 07Ah, 0D6h, 00Ah, 06Fh, 026h, 0C0h, 03Eh, 0FFh, 0CDh, 08Fh, 0E0h
        db      07Ah, 0D6h, 018h, 057h, 01Dh, 0C2h, 062h, 0E0h, 03Eh, 002h, 0D3h, 001h, 0C3h, 098h, 0E0h, 006h
        db      020h, 077h, 024h, 005h, 0C2h, 091h, 0E0h, 0C9h, 0CDh, 099h, 0E1h, 057h, 0B7h, 01Fh, 05Fh, 082h
        db      067h, 0CDh, 099h, 0E1h, 0BCh, 0DAh, 09Bh, 0E0h, 082h, 032h, 024h, 0E2h, 01Eh, 00Ch, 03Eh, 008h
        db      0CDh, 056h, 0E1h, 0FEh, 055h, 0CAh, 0BDh, 0E0h, 0FEh, 0AAh, 0C2h, 098h, 0E0h, 01Dh, 0C2h, 0AEh
        db      0E0h, 0CDh, 034h, 0E1h, 05Fh, 07Eh, 0FEh, 000h, 0C2h, 0C1h, 0E0h, 021h, 021h, 0E2h, 07Eh, 02Bh
        db      0BEh, 0C2h, 098h, 0E0h, 057h, 02Bh, 046h, 03Eh, 008h, 032h, 027h, 0E2h, 0CDh, 034h, 0E1h, 0F5h
        db      07Eh, 0FEh, 000h, 0CAh, 01Ah, 0E1h, 087h, 087h, 087h, 087h, 087h, 04Fh, 0F1h, 023h, 07Eh, 0BBh
        db      0C2h, 0DCh, 0E0h, 0D5h, 0C5h, 023h, 011h, 07Eh, 020h, 07Eh, 002h, 00Ah, 0AEh, 077h, 023h, 00Ch
        db      015h, 0C2h, 0F9h, 0E0h, 0C1h, 0D1h, 03Ah, 027h, 0E2h, 03Dh, 032h, 027h, 0E2h, 0B7h, 0C2h, 0DCh
        db      0E0h, 07Ah, 0FEh, 001h, 0C2h, 0DCh, 0E0h, 0C3h, 02Eh, 0E1h, 0F1h, 093h, 0CAh, 0DCh, 0E0h, 03Ch
        db      0C2h, 098h, 0E0h, 01Dh, 004h, 015h, 03Eh, 008h, 032h, 027h, 0E2h, 0C3h, 0DCh, 0E0h, 0AFh, 0D3h
        db      001h, 0C3h, 000h, 000h, 0C5h, 021h, 000h, 0E2h, 0E5h, 001h, 023h, 000h, 03Eh, 0FFh, 0CDh, 056h
        db      0E1h, 077h, 023h, 080h, 047h, 03Eh, 008h, 00Dh, 0C2h, 03Eh, 0E1h, 02Bh, 078h, 096h, 096h, 07Eh
        db      0E1h, 0C2h, 038h, 0E1h, 0C1h, 0C9h, 0C5h, 0D5h, 00Eh, 000h, 057h, 0CDh, 0E1h, 0E1h, 0DBh, 001h
        db      0E6h, 010h, 0BBh, 0CAh, 05Eh, 0E1h, 007h, 007h, 007h, 007h, 079h, 017h, 04Fh, 0CDh, 0E1h, 0E1h
        db      07Ah, 0B7h, 0F2h, 08Eh, 0E1h, 079h, 0FEh, 0E6h, 0CAh, 088h, 0E1h, 0FEh, 019h, 0C2h, 05Eh, 0E1h
        db      03Eh, 0FFh, 032h, 023h, 0E2h, 0C3h, 08Ch, 0E1h, 0AFh, 032h, 023h, 0E2h, 016h, 009h, 015h, 0C2h
        db      05Eh, 0E1h, 03Ah, 023h, 0E2h, 0A9h, 0D1h, 0C1h, 0C9h, 0E5h, 0D5h, 0CDh, 0C4h, 0E1h, 047h, 0B7h
        db      01Fh, 04Fh, 021h, 000h, 000h, 016h, 020h, 0CDh, 0C4h, 0E1h, 0D5h, 016h, 000h, 05Fh, 019h, 0D1h
        db      05Fh, 090h, 0D2h, 0B7h, 0E1h, 078h, 093h, 0B9h, 0D2h, 09Bh, 0E1h, 015h, 0C2h, 0A7h, 0E1h, 029h
        db      07Ch, 0D1h, 0E1h, 0C9h, 0D5h, 0CDh, 0E1h, 0E1h, 0DBh, 001h, 0E6h, 010h, 0BBh, 0CAh, 0C8h, 0E1h
        db      05Fh, 016h, 001h, 0DBh, 001h, 0E6h, 010h, 014h, 0BBh, 0CAh, 0D3h, 0E1h, 07Ah, 087h, 087h, 0D1h
        db      0C9h, 03Ah, 024h, 0E2h, 03Dh, 0C2h, 0E4h, 0E1h, 0DBh, 001h, 0E6h, 010h, 05Fh, 0C9h
LOADER_STAGE2_SIZE      equ     494           ; размер blob, байт
