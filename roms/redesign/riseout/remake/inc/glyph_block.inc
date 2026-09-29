; Шрифт 8x8: 128 глифов по 8 байт, адрес = 0x3114+8*код, байт0 = верхняя строка, MSB = левый пиксель; копируется в RAM 0x6000 и 0x6400 (LXI H,3114 / LXI D,6000 / LXI B,0400 / CALL 017C @0x2B32 и @0x23C6); func_render_glyph_vram читает 0x6007+8*код вниз (DCX H) при росте адреса VRAM
data_glyph_block:
        defb    00h,00h,00h,18h,18h,00h,00h,00h
        defb    0CCh,0CCh,0CCh,0FDh,0FCh,0CDh,0CDh,0CDh
        defb    00h,00h,00h,45h,41h,75h,55h,75h
        defb    00h,00h,00h,10h,00h,50h,90h,54h
        defb    0FCh,0FCh,0C0h,0C0h,0CDh,0CDh,0FDh,0FDh
        defb    00h,00h,00h,04h,0C5h,5Dh,55h,0DDh
        defb    00h,00h,00h,10h,0C0h,50h,0D0h,54h
        defb    0E0h,6Ch,0ECh,6Ch,0ECh,6Fh,0EFh,60h
        defb    75h,27h,25h,25h,00h,00h,00h,00h
        defb    00h,00h,3Ch,20h,2Ch,24h,3Ch,00h
        defb    00h,00h,22h,36h,2Ah,22h,22h,00h
        defb    00h,00h,00h,00h,07h,07h,0Fh,0Eh
        defb    00h,00h,00h,00h,0E7h,0EFh,0EEh,0EEh
        defb    00h,00h,00h,00h,0F8h,0FDh,1Dh,1Dh
        defb    00h,00h,00h,00h,0FEh,0FFh,0C7h,0C7h
        defb    00h,00h,00h,00h,77h,77h,77h,77h
        defb    30h,30h,5Eh,7Bh,1Ch,37h,20h,60h
        defb    30h,30h,1Ch,7Ah,1Ah,38h,28h,04h
        defb    30h,30h,18h,1Ch,18h,30h,3Ch,18h
        defb    30h,30h,1Ch,7Ah,1Ah,38h,28h,14h
        defb    0Ch,0Ch,7Ah,0DEh,38h,0ECh,04h,06h
        defb    0Ch,0Ch,38h,5Eh,58h,1Ch,14h,20h
        defb    0Ch,0Ch,18h,38h,18h,0Ch,3Ch,18h
        defb    0Ch,0Ch,38h,5Eh,58h,1Ch,14h,28h
        defb    1Ah,1Ah,4Ah,7Ch,18h,14h,14h,10h
        defb    58h,58h,4Ah,3Eh,18h,28h,28h,08h
        defb    00h,00h,00h,18h,00h,00h,00h,00h
        defb    5Ah,5Ah,4Ah,3Ch,18h,28h,28h,28h
        defb    0Eh,0Ah,1Eh,30h,60h,0F0h,0A0h,00h
        defb    00h,00h,22h,36h,2Ah,22h,22h,00h
        defb    0FFh,80h,80h,0FFh,8Eh,99h,0AEh,0C9h
        defb    0DBh,2Ah,2Ah,0CAh,0EAh,4Ah,4Ah,5Bh
        defb    00h,00h,00h,00h,00h,00h,00h,00h          ; space (20h)
        defb    38h,38h,38h,38h,10h,00h,10h,10h          ; '!' (21h)
        defb    6Ch,6Ch,48h,24h,00h,00h,00h,00h          ; '"' (22h)
        defb    6Ch,0FEh,0FEh,6Ch,0FEh,0FEh,6Ch,00h      ; '#' (23h)
        defb    36h,36h,12h,24h,00h,00h,00h,00h          ; '$' (24h)
        defb    00h,00h,00h,0FFh,0FFh,00h,00h,00h        ; '%' (25h)
        defb    18h,18h,18h,18h,18h,18h,18h,18h          ; '&' (26h)
        defb    00h,00h,00h,1Fh,1Fh,18h,18h,18h          ; ''' (27h)
        defb    18h,30h,60h,60h,60h,30h,18h,00h          ; '(' (28h)
        defb    60h,30h,18h,18h,18h,30h,60h,00h          ; ')' (29h)
        defb    10h,54h,38h,0FEh,38h,54h,10h,00h         ; '*' (2Ah)
        defb    1Ch,1Ch,38h,38h,7Fh,7Fh,0E0h,0E0h
        defb    0EFh,0E7h,0E1h,0E0h,0EEh,0EEh,0EFh,0E7h
        defb    81h,0E1h,0F9h,7Dh,1Dh,1Dh,0FDh,0F8h
        defb    0C0h,0C0h,0C0h,0C0h,0C7h,0C7h,0FFh,0FEh
        defb    77h,77h,77h,77h,77h,77h,77h,77h
        defb    7Ch,8Eh,8Eh,8Eh,8Eh,8Eh,7Ch,00h          ; '0' (30h)
        defb    1Ch,3Ch,7Ch,1Ch,1Ch,1Ch,7Eh,00h          ; '1' (31h)
        defb    7Ch,8Eh,0Eh,1Eh,78h,0F2h,0FEh,00h        ; '2' (32h)
        defb    7Ch,8Eh,0Eh,3Ch,0Eh,8Eh,7Ch,00h          ; '3' (33h)
        defb    3Ch,5Ch,9Ch,9Ch,0FEh,1Ch,1Ch,00h         ; '4' (34h)
        defb    0FEh,0C0h,0FCh,1Eh,1Eh,1Eh,0FCh,00h      ; '5' (35h)
        defb    7Ch,8Eh,80h,0FCh,9Eh,9Eh,7Ch,00h         ; '6' (36h)
        defb    0FEh,8Eh,1Ch,3Ch,3Ch,3Ch,3Ch,00h         ; '7' (37h)
        defb    7Ch,8Eh,8Eh,7Ch,8Eh,8Eh,7Ch,00h          ; '8' (38h)
        defb    7Ch,8Eh,8Eh,7Eh,0Eh,8Eh,7Ch,00h          ; '9' (39h)
        defb    00h,30h,30h,00h,00h,30h,30h,00h          ; ':' (3Ah)
        defb    00h,00h,00h,00h,00h,0C0h,0C0h,00h        ; ';' (3Bh)
        defb    00h,00h,00h,00h,00h,03h,01h,02h
        defb    08h,0Ch,0FEh,0FFh,0FEh,0Ch,08h,00h       ; '=' (3Dh)
        defb    0FCh,70h,70h,70h,70h,70h,0FCh,00h        ; '>' (3Eh)
        defb    7Ch,8Eh,0Eh,1Ch,38h,00h,38h,00h          ; '?' (3Fh)
        defb    3Ch,42h,0BDh,0A1h,0A1h,0BDh,42h,3Ch      ; '@' (40h)
        defb    3Ch,7Eh,8Eh,8Eh,0FEh,8Eh,8Eh,00h         ; 'A' (41h)
        defb    0FCh,4Eh,4Eh,7Ch,4Eh,4Eh,0FCh,00h        ; 'B' (42h)
        defb    7Ch,0E2h,0E0h,0E0h,0E0h,0E2h,7Ch,00h     ; 'C' (43h)
        defb    0FCh,5Eh,4Eh,4Eh,4Eh,5Eh,0FCh,00h        ; 'D' (44h)
        defb    0FEh,72h,70h,7Ch,70h,72h,0FEh,00h        ; 'E' (45h)
        defb    0FEh,0E2h,0E0h,0FCh,0E0h,0E0h,0E0h,00h   ; 'F' (46h)
        defb    7Ch,8Eh,80h,0BEh,8Eh,8Eh,7Ch,00h         ; 'G' (47h)
        defb    8Eh,8Eh,8Eh,0FEh,8Eh,8Eh,8Eh,00h         ; 'H' (48h)
        defb    7Ch,38h,38h,38h,38h,38h,7Ch,00h          ; 'I' (49h)
        defb    3Eh,1Ch,1Ch,1Ch,9Ch,9Ch,78h,00h          ; 'J' (4Ah)
        defb    0E6h,0E6h,0ECh,0F8h,0ECh,0E6h,0E6h,00h   ; 'K' (4Bh)
        defb    0E0h,0E0h,0E0h,0E0h,0E0h,0E2h,0FEh,00h   ; 'L' (4Ch)
        defb    8Eh,0DEh,0FEh,0AEh,8Eh,8Eh,8Eh,00h       ; 'M' (4Dh)
        defb    8Eh,0CEh,0EEh,0FEh,0BEh,9Eh,8Eh,00h      ; 'N' (4Eh)
        defb    7Ch,8Eh,8Eh,8Eh,8Eh,8Eh,7Ch,00h          ; 'O' (4Fh)
        defb    0FCh,0E6h,0E6h,0E6h,0FCh,0E0h,0E0h,00h   ; 'P' (50h)
        defb    7Ch,8Eh,8Eh,8Eh,0AEh,9Ch,7Ah,00h         ; 'Q' (51h)
        defb    0FCh,0E6h,0E6h,0FCh,0F8h,0ECh,0E6h,00h   ; 'R' (52h)
        defb    7Ch,8Eh,80h,7Ch,0Eh,8Eh,7Ch,00h          ; 'S' (53h)
        defb    0FEh,38h,38h,38h,38h,38h,38h,00h         ; 'T' (54h)
        defb    8Eh,8Eh,8Eh,8Eh,8Eh,8Eh,7Ch,00h          ; 'U' (55h)
        defb    8Eh,8Eh,8Eh,8Eh,5Ch,5Ch,38h,00h          ; 'V' (56h)
        defb    8Eh,8Eh,0AEh,0AEh,0AEh,0FEh,5Ch,00h      ; 'W' (57h)
        defb    8Eh,8Eh,5Ch,38h,5Ch,8Eh,8Eh,00h          ; 'X' (58h)
        defb    8Eh,8Eh,8Eh,7Ch,38h,38h,38h,00h          ; 'Y' (59h)
        defb    0FEh,8Eh,1Ch,38h,70h,0E2h,0FEh,00h       ; 'Z' (5Ah)
        defb    00h,00h,00h,0F8h,0F8h,18h,18h,18h        ; '[' (5Bh)
        defb    18h,18h,18h,0F8h,0F8h,00h,00h,00h        ; '\' (5Ch)
        defb    18h,18h,18h,1Fh,1Fh,00h,00h,00h          ; ']' (5Dh)
        defb    00h,00h,00h,7Eh,7Eh,00h,00h,00h          ; '^' (5Eh)
        defb    00h,00h,00h,18h,18h,00h,00h,00h          ; '_' (5Fh)
        defb    38h,38h,1Eh,7Bh,0DCh,37h,20h,60h         ; tile 00 — маркер старта игрока (Stage 7)
        defb    11h,88h,55h,22h,44h,0AAh,11h,0A8h        ; tile 01 (Stage 7)
        defb    45h,22h,55h,88h,11h,0AAh,44h,2Ah         ; tile 02 (Stage 7)
        defb    70h,30h,70h,30h,70h,30h,70h,30h          ; tile 03 (Stage 7)
        defb    38h,38h,1Eh,7Bh,0DCh,37h,20h,60h         ; tile 04 — целевая клетка (Stage 7)
        defb    0Ch,12h,21h,0A1h,40h,0A1h,12h,0Ch        ; tile 05 (Stage 7)
        defb    00h,0AAh,00h,49h,00h,44h,00h,00h         ; tile 06 (Stage 7)
        defb    70h,30h,70h,30h,70h,30h,70h,30h          ; tile 07 (Stage 7)
        defb    00h,00h,0EEh,0BBh,6Dh,00h,0AAh,0FFh      ; tile 08 (Stage 7)
        defb    00h,00h,00h,00h,00h,7Eh,7Eh,7Eh          ; tile 09 (Stage 7)
        defb    00h,00h,00h,00h,00h,7Eh,7Eh,7Eh          ; tile 0A (Stage 7)
        defb    99h,00h,99h,99h,99h,00h,99h,99h          ; tile 0B (Stage 7)
        defb    7Fh,7Fh,7Fh,7Fh,7Fh,7Fh,7Fh,7Fh          ; tile 0C (Stage 7)
        defb    00h,00h,00h,00h,00h,7Eh,7Eh,7Eh          ; tile 0D (Stage 7)
        defb    0FFh,0FFh,55h,00h,00h,00h,00h,00h        ; tile 0E (Stage 7)
        defb    0FFh,81h,0C3h,66h,00h,00h,00h,00h        ; tile 0F — пусто (Stage 7)
        defb    11h,8Bh,57h,27h,47h,0AFh,13h,0A9h
        defb    45h,23h,5Fh,8Fh,1Fh,0AFh,47h,2Bh
        defb    17h,9Fh,7Fh,7Fh,7Fh,0FFh,17h,0ABh
        defb    5Fh,3Fh,7Fh,0FFh,7Fh,0BFh,5Fh,2Fh
        defb    91h,0CBh,0F7h,0F7h,0F7h,0EFh,0D3h,0A9h
        defb    0C5h,0E3h,0F7h,0FBh,0F7h,0FBh,0E5h,0ABh
        defb    91h,0C8h,0F5h,0F2h,0F4h,0FAh,0D1h,0A8h
        defb    0C5h,0E2h,0F5h,0F8h,0F1h,0FAh,0E4h,0AAh
        defb    0F1h,0F8h,0FDh,0FEh,0FCh,0FEh,0F1h,0E8h
        defb    0F5h,0FAh,0FDh,0FEh,0FFh,0FEh,0FCh,0FAh
        defb    91h,0C9h,0FFh,0FFh,0FFh,0FFh,0D3h,0A9h
        defb    0C5h,0A3h,0FFh,0FFh,0FFh,0FFh,0C5h,0ABh
        defb    11h,88h,0D5h,0FFh,0FFh,0ABh,11h,0A8h
        defb    45h,22h,0D5h,0FFh,0FFh,0ABh,44h,2Ah
        defb    11h,88h,55h,0A3h,0FFh,0ABh,11h,0A8h
        defb    45h,22h,55h,8Bh,0FFh,0AAh,44h,2Ah
