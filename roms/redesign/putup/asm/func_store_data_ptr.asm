; func_store_data_ptr @ 0x014F
; Store HL to data stream pointer at 0x0B53. SHLD 0B53; RET.

SECTION code

PUBLIC _func_store_data_ptr

_func_store_data_ptr:
    SHLD 0B53                    ; 0x014F  [34, 83, 11]
    RET                         ; 0x0152  [201]
