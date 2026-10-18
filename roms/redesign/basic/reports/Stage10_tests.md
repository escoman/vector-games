# Stage 10.2 — поведенческая батарея BASIC (Tier 2)

Сверка: `эталон ↔ сборка` (VRAM `0x8000..0xFFFF`, мигающие байты исключены).
Эталон — `bas2997.rom` (org `0x0100`, самораспаковка на boot); сборка — `basic_new.r0m` (org `0x0000`).

| тест | строк | отпечаток эталон | отпечаток сборка | расхожд. | вердикт |
|---|---:|---|---|---:|---|
| 01_arith | 7 | `2edf49d70c4eb57a` | `39705c180c9587f2` | 0 | ✅ MATCH |
| 02_print_sep | 4 | `3db9d949e47da9cf` | `9ccc644b8f6e43f3` | 0 | ✅ MATCH |
| 03_for_next | 4 | `45d2a28cac50009b` | `45d2a28cac50009b` | 0 | ✅ MATCH |
| 04_gosub | 7 | `b0151e5b0ef65dcf` | `6bd7f7144c02908d` | 0 | ✅ MATCH |
| 05_if_then | 4 | `018a49e36c299bae` | `018a49e36c299bae` | 0 | ✅ MATCH |
| 06_var | 5 | `bd1dacadfed25c2c` | `18ce2395145ed04b` | 0 | ✅ MATCH |
| 07_hex | 3 | `39b24ec77f242626` | `ea40eec884227102` | 0 | ✅ MATCH |
| 08_octal_err | 2 | `8266727778d51ab6` | `8266727778d51ab6` | 0 | ✅ MATCH |
| 09_string | 3 | `7c6b44d1ced66f38` | `d0dc148eb32deaa1` | 0 | ✅ MATCH |

Скриншоты кадров — `reports/tests/*__new.png`.
