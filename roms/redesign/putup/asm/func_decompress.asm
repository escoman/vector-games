; func_decompress @ 0x0400
; Startup decompression. IN: none (hardcoded src=0x2761, dst=0x6000). OUT: none. 256 iterations x 4 bitplane unpackers x 8 bytes = 8192 bytes decompressed. Clobbers: all regs (saves H,D,B,PSW).

SECTION code

PUBLIC _func_decompress

_func_decompress:
    PUSH H                       ; 0x0401  [229]
    PUSH D                       ; 0x0402  [213]
    PUSH B                       ; 0x0403  [197]
    PUSH PSW                     ; 0x0404  [245]
    CALL func_decomp_transpose   ; 0x0405  [205, 205, 4]
    LXI H, 6000                 ; 0x0408  [33, 0, 96]
    LXI D, 3041                 ; 0x040B  [17, 65, 48]
    MVI B, 00                   ; 0x040E  [6, 0]
    PUSH B                       ; 0x0410  [197]
    PUSH D                       ; 0x0411  [213]
    CALL func_decomp_plane0      ; 0x0412  [205, 57, 4]
    POP D                       ; 0x0415  [209]
    PUSH D                       ; 0x0416  [213]
    CALL func_decomp_plane1      ; 0x0417  [205, 94, 4]
    POP D                       ; 0x041A  [209]
    PUSH D                       ; 0x041B  [213]
    CALL func_decomp_plane2      ; 0x041C  [205, 131, 4]
    POP D                       ; 0x041F  [209]
    PUSH D                       ; 0x0420  [213]
    CALL func_decomp_plane3      ; 0x0421  [205, 168, 4]
    POP D                       ; 0x0424  [209]
    POP B                       ; 0x0425  [193]
    DCR B                       ; 0x0426  [5]
    JNZ sub_042F                ; 0x0427  [194, 47, 4]
    POP PSW                     ; 0x042A  [241]
    POP B                       ; 0x042B  [193]
    POP D                       ; 0x042C  [209]
    POP H                       ; 0x042D  [225]
