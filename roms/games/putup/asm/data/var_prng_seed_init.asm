; Данные: var_prng_seed_init
; Адрес: 0x1155
; Размер: 2 байта
; Описание: Инициализация слова-состояния ГПСЧ (func_prng LHLD/SHLD var_prng_state).
var_prng_seed_init:
    DEFB 01h, 00h
