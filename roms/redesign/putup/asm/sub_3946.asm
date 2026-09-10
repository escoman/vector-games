; sub_3946 @ 0x3946

SECTION code

PUBLIC _sub_3946

_sub_3946:
    LHLD 3854                    ; 0x3946  [42, 84, 56]
    PUSH H                       ; 0x3949  [229]
    LXI H, 3845                 ; 0x394A  [33, 69, 56]
    SHLD 0B41                    ; 0x394D  [34, 65, 11]
    POP H                       ; 0x3950  [225]
    MOV A, M                    ; 0x3951  [126]
    PUSH H                       ; 0x3952  [229]
    LHLD 0B41                    ; 0x3953  [42, 65, 11]
    PUSH D                       ; 0x3956  [213]
    PUSH PSW                     ; 0x3957  [245]
    LXI D, 000E                 ; 0x3958  [17, 14, 0]
    DAD D                       ; 0x395B  [25]
    POP PSW                     ; 0x395C  [241]
    POP D                       ; 0x395D  [209]
    MOV M, A                    ; 0x395E  [119]
    POP H                       ; 0x395F  [225]
    INX H                       ; 0x3960  [35]
    INX H                       ; 0x3961  [35]
    INX H                       ; 0x3962  [35]
    MOV A, M                    ; 0x3963  [126]
    PUSH H                       ; 0x3964  [229]
    LHLD 0B41                    ; 0x3965  [42, 65, 11]
    INX H                       ; 0x3968  [35]
    INX H                       ; 0x3969  [35]
    INX H                       ; 0x396A  [35]
    INX H                       ; 0x396B  [35]
    INX H                       ; 0x396C  [35]
    INX H                       ; 0x396D  [35]
