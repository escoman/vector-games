# Stage 5. Главный игровой цикл (riseout.rom)

> Источник фактов — MCP `vector-debugger`: канонический `debug_load_rom` (org 0x0100), `debug_disassemble_range`, `debug_analyze_code`, `debug_find_immediate_in_range`, `debug_read_memory_range`, живая трасса `debug_run`/`debug_pause`/`debug_press_key`/`debug_type_key`. `debug_reset` не вызывался (вешает ЦП на busy-wait `OUT 1C`/`IN 1B`). Механика Stage 0–4 (прогон `utils/analyze`, именование, ABI, вектора прерываний) здесь не пересказывается; цитируются только адреса и числа, на которых держатся вердикты этого этапа.

## Goal

1. Найти, где ROM печатает `HIT BUTTON OR SPACE KEY` и где **фактически** опрашивает клавишу старта (порты `KEYSTROB`/`KEYDATA`), и дать этому циклу имя `lbl_title_key_poll` (ТЗ, строка 155).
2. Определить, какая сущность является главным игровым циклом, и зафиксировать имя `func_main_game_loop`.
3. Пройти код после нажатия и построить полное дерево: boot → инициализация → заставка/меню → инициализация уровня → игровой цикл → смерть / завершение уровня → game over → возврат на заставку.
4. Выявить игровые переменные и завести их в RDB объектами `type=variable` (`var_score`, `var_lives`, `var_level`, `var_speed`, `var_player_x` и др.) с однострочными комментариями «кто пишет / кто читает» и связями func → var.
5. Подтвердить ключевые значения трассой (жизни, скорость, координаты, таймеры), а не догадкой; сохранить round-trip byte-for-byte.

## Method

1. **Предусловие.** `debug_get_rdb_info`: `loaded=true`, `object_count=366` (состояние после Stage 4), sha256 ROM `c265014b…a6991`; `debug_reload_rdb` не потребовался. Правки велись пачками ≤10 объектов, после каждой — `debug_save_rdb` + проверка `dirty=false`.
2. **Крестовые ссылки на RAM-адреса.** `debug_get_xrefs` для адресов выше 0x50FF возвращает пусто (это не адреса кода), поэтому вместо него ~25 раз использован `debug_find_immediate_in_range(value=десятичный, 256..20735)` — именно так найдены все write-сайты `var_*` и подтверждены/опровергнуты трактовки Stage 2.
3. **Статика.** `debug_disassemble_range` по 0x0100, 0x01A8..0x01F0, 0x04F7, 0x0863..0x09EC, 0x09BA..0x09EC (тело главного цикла), 0x1140..0x11D2, 0x1FAD..0x1FF4, 0x223C..0x22D8, 0x25FF..0x2660, 0x26C6..0x270B, 0x2A9A..0x2AE2, 0x2B61..0x2B8B; `debug_analyze_code` — для границ достижимого кода.
4. **Динамика (четыре прогона).** (а) `debug_type_key SPACE` ×3 с чтением меню-состояний после каждого нажатия; (б) `debug_run` + ~3 с + `debug_pause` и сравнение RAM-снимков; (в) точечный эксперимент с **удержанием** SPACE (`debug_press_key` → `debug_run` → 0.4 с → `debug_pause` → `debug_release_key`) для отображения «слот кольца ↔ клавиша»; (г) повторный прогон 1.5 с для проверки стабильности `[0x7C6E]`.
5. **Данные-якорь.** `debug_read_memory_range` 0x2B8B..0x2BF7 — таблица текстовых записей титульного экрана (формат `{строка, столбец, текст…00}`), 0x2B9D (`HIT BUTTON OR SPACE KEY`) и 0x2CDD (`SELECT SPEED LEVEL`) — сами строки; позиции верифицированы `debug_find_bytecode_sequence`.
6. **Пересборка.** `PATH=$PWD/z88dk/bin:$PATH utils/analyze/run_pipeline.sh riseout --from export_asm` — 3 раза после правок RDB (флаг `--resume` не использовался); `Stage1.md` перегенерирован `analyze.report_gen`.

## Заставка: где печатается `HIT BUTTON OR SPACE KEY`

`func_attract_draw_title` (`0x2B61`) рисует титул одной командой пакета:

```
0x2B61 MVI B,07            ; 7 записей
0x2B63 LXI H,2B8B          ; таблица записей
0x2B66 CALL 2D1B           ; пакетный вывод записей; далее 0x2B69/0x2B7B: LXI D,2C04, 2x15 глифов через CALL 0551
```

Формат записи подтверждён дампом `debug_read_memory_range` 0x2B8B..0x2BFF: `{строка, столбец, байты текста…, 00}`.

Все 7 записей (адреса — образ; заголовок = `{строка, столбец}`, дальше текст до `00`):

| № | Заголовок | строка, столбец | Текст | Адрес текста |
|---|---|---|---|---|
| 1 | `0x2B8B` | 10, 8 | `FROM DUNGEONS` | `0x2B8D` |
| 2 | `0x2B9B` | 5, 11 | **`HIT BUTTON OR SPACE KEY`** | **`0x2B9D`** |
| 3 | `0x2BB5` | 9, 14 | `UP TO 4 PLAYERS` | `0x2BB7` |
| 4 | `0x2BC7` | 15, 16 | `AND` | `0x2BC9` |
| 5 | `0x2BCD` | 10, 18 | `3 SPEED LEVEL` | `0x2BCF` |
| 6 | `0x2BDD` | 17, 21 | служебные коды `0B 0C 0D 0E 0F` (не ASCII) | `0x2BDF` |
| 7 | `0x2BE5` | 2, 22 | `COPYRIGHT 1983 ` + коды `2C 2D 2E 2F 3C 20 01..06` | `0x2BE7` |

ТЗ-якорь «`HIT BUTTON OR SPACE KEY` @0x2A9D» — **смещение в файле ROM**; адрес в образе = `0x2A9D + 0x100 = 0x2B9D` ✓ (позиция подтверждена `debug_find_bytecode_sequence` по `HIT BUTTON` — единственное совпадение во всём образе). Непосредственной ссылки-иммедиата на `0x2B9D` в образе нет (проверено `debug_find_immediate_in_range` в обоих порядках байт и `debug_find_bytecode_sequence`): до строки доходят адресом записи `0x2B9B` через обходчик `CALL 2D1B`. Объекты `str_*` по этому тексту **не создавались** — это предмет Stage 6.

## Клавиатура: от порта до решения «нажато»

Опрос портов делает **только** обработчик кадра VBlank (`func_irq_frame_service`, `0x04F7`), поз. `0x051C..0x0530`:

```
0x051C MVI A,8A : OUT 00        ; CW PIA1
0x0520 LXI H,081F               ; кольцо результатов
0x0523 MVI A,FE                 ; маска строки (активный 0)
0x0525 PUSH PSW : OUT 03        ; KEYSTROB = порт A PIA1 (номер опрашиваемой строки)
0x0528 IN  02                   ; KEYDATA  = порт B PIA1 (состояние столбцов)
0x052A MOV  M,A : POP PSW : INX H : RLC : JC 0x0525   ; 8 слотов, маски 0xFE→0x7F
0x0531 MVI A,88 : OUT 00 : MVI A,02 : OUT 01 : LDA 081B : OUT 03 : LDA 0720 : OUT 02
```

Поиск байт-последовательностей по всему образу (`debug_find_bytecode_sequence`, 0x0100..0x50FF) — подсчёт реальных обращений к портам клавиатуры:

`DB 02` (`IN 0x02`, чтение столбцов) — **1 совпадение: `0x0528`** (внутри `func_irq_frame_service`).
`D3 03` (`OUT 0x03`, маска строки) — **2 совпадения: `0x0526`** (тот же цикл скана) и **`0x053C`** (хвост ISR: `LDA [0x081B] / OUT 03` — обратно в порт A кладётся значение вертикальной прокрутки, порт A общий).
`DB 01` (`IN 0x01`, порт C — сдвиги) — **1 совпадение: `0x121F`** (`func_probe_control_keys`), т.е. это единственное место в ROM, где читаются сдвиги.

Дальше игра и аттракт **порты не читают вовсе** — они работают по кольцу `[0x081F+A]` (`var_key_ring`):

| Адрес | Функция | Что делает (проверено дизассемблированием) |
|---|---|---|
| `0x01E6` | `func_key_ring_peek` | `LXI H,081F; CALL 03D2; MOV A,M` → возвращает `[0x081F+A]` |
| `0x01A8` | `func_key_strobe_state` | `DCR A; JM 01AE` — содержательна **только при A=0**; читает слот 7 = `[0x0826]`, `ANI 80`; бит снят (клавиша нажата) → `CMA` → A=0xFF, иначе `XRA A` → 0. **При A=1 и A=2 всегда возвращает 0** |
| `0x01BC` | `func_key_code_decode` | тоже только при A=0, но слот 0 = `[0x081F]`; старший ниббл (`RRC×4; ANI 0F`) → 16-байтная таблица `0x01D5` = `00 03 05 04 07 00 06 05 01 02 00 03 08 01 07 00` |
| `0x2AB0` | `func_attract_key_row_scan` | тройной вызов `0x01A8` с A=0,1,2; latch `[0x7DF2]` (`STA @0x2AD6`), «активная линия» `[0x7C07]` (`STA @0x2ADA`): нажато → `(0xFF, 0)`, не нажато → `(00, 02)` |
| `0x2AE2` | `func_attract_key_code_scan` | тройной вызов `0x01BC` с A=0,1,2 + OR результатов |
| `0x121F` | `func_probe_control_keys` | единственный в игре прямой `IN 0x01` (Port C: сдвиги/статус) плюс `ANI 60; CPI 20`; иначе чтение кольца `[0x081F+2]` (`CPI 0F7`) |

**Эксперимент с удержанием SPACE** (0.4 с игры, затем пауза) — снимок кольца целиком: `[0x081F..0x0825] = FF FF FF FF FF FF FF`, `[0x0826] = **7F**`, `[0x7DF2] = FF`, `[0x7C07] = 00`. Т.е. SPACE попадает в **слот 7, бит 7**, и ветка `func_key_strobe_state` даёт ненулевой ответ. Отсюда следует (и это подтверждено трассой выхода из аттракта): «BUTTON OR SPACE» — это **любая клавиша линии, опрашиваемой слотом 7**, а не конкретный код; кодовая таблица `0x01D5` на старт не влияет.

## `lbl_title_key_poll` (`0x2633`) — сам цикл ожидания

Тело (в RDB — метка `lbl_title_key_poll`, тип `label`, как требует ТЗ):

```
0x2633 CALL 2651        ; func_attract_frame_step: CALL 277E (ввод+меню), CALL 2A9A (сдвиг плоскости), LDA 7DE2
0x2636 CPI 03
0x2638 JNZ 2633         ; ждать 4-й доли такта мелодии
0x263B XRA A : STA 7DE2 ; сброс счётчика долей
0x263F LDA 7C85 : ORA A
0x2643 JNZ 2633         ; пока меню ≠ 0 (титул) — остаться в цикле
0x2646 SHLD 082A : LHLD 7DF0 : SPHL : LHLD 082A : RET   ; lbl_attract_exit_restore
```

Три факта, каждый с отдельным доказательством:

1. **Вход — fall-through.** Единственная «внешняя» ссылка на `0x2633` — два её собственных `JNZ`. Цикл продолжает `func_attract_overlay_driver` (`0x25FF`), чья последняя инструкция — `CALL 265B` при `0x2630`. Выход из аттракта — `RET` на `0x2650`, причём `0x25FF` сохраняет стек в `[0x7DF0]` (`SHLD @0x260E`), а `0x2646..0x264C` его восстанавливает (`SPHL`) — аттракт живёт на «своём» стеке.
2. **Синхронизация — по музыке, а не по кадрам.** Порог `CPI 03` сравнивается с `[0x7DE2]`, который инкрементируется **внутри шага фоновой мелодии**: `INR M @0x2DB1` в воркере `0x2D94`, куда `func_irq_music_step` (`0x2EFB`) вызывает `CALL 2D94 @0x2F17`; сброс — `STA 7DE2 @0x2D90` в `func_music_start` и `STA 7DE2 @0x263C` в самом цикле. Объект, заведённый в начале Stage 5 как `var_menu_frame_steps`, после этой находки переименован в **`var_music_step_counter`** (переименование — через `debug_update_rdb_object`, дубля не создавалось).
3. **«Ждать нажатия» — это не петля по клавише, а условие выхода.** Нажатие фиксирует `func_attract_input_update` (`0x277E`): если `[0x7DF2]==0` → `CALL 2AB0`, и при ненулевом результате `CNZ 26C6` → обработчик меню. Обработчик, когда подтверждён последний слот, делает `JZ 0x2646`, то есть выходит из цикла прямо в середину своего вызывающего кадра (отсюда и манипуляция со стеком).

Трассировка трёх нажатий SPACE (аттракт, `debug_type_key`, чтение RAM между нажатиями): #1 → `[0x7C85]=1` (экран `HOW MANY PLAYERS`), #2 → `[0x7C85]=2`, `[0x7C87]=2` (экран `SELECT SPEED LEVEL`), #3 → коммит слотов → выход из аттракта → инициализация уровня.

## `func_attract_menu_key_handler` (`0x26C6`) — новый объект, шаг меню

Размер 70 (0x26C6..0x270B, тело заканчивается `RET` @0x270B):

```
0x26C6 CALL 2D4E          ; мигание-импульс
0x26C9 LDA 7C85 : CPI 02 : JZ 26DF     ; на экране скорости — коммит выбора
0x26D2 STA 7C85 (INR A)   ; 0→1→2, шаг меню
0x26D5 CPI 01 : JZ 2C22   ; нарисовать HOW MANY PLAYERS
0x26DA CPI 02 : JZ 2CA4   ; нарисовать SELECT SPEED LEVEL
0x26DF lbl_menu_commit_slot: LDA 7C84 (индекс слота); LDA 7C87 (курсор 1..3)
0x26E9 LXI H,7C88 : DAD B : MOV M,A    ; [0x7C88+slot] = скорость
0x26EE LXI H,7D91 : DAD B : LDA 7C07 : MOV M,A  ; [0x7D91+slot] = клавиатурная линия
0x26F8 ADI 32 : LXI H,55B3 : CALL 0124 ; цифра скорости в оверлей-страницу
0x2701 INR A : STA 7C84   ; следующий слот
0x2704 LDA 7C86 : CMP C : JZ 2646      ; все слоты подтверждены → выход из аттракта
```

## Скорость: куда ложится выбор `SELECT SPEED LEVEL`

Строка `SELECT SPEED LEVEL` — заголовок экрана меню: ТЗ-якорь `0x2BDD` = смещение в файле, в образе **`0x2CDD`** (подтверждено поиском байт-последовательности `SELECT SPEED`, единственное совпадение). Цепочка полностью пройдена статикой и частично трассой:

| Звено | Адрес | Доказательство |
|---|---|---|
| курсор (1=LOW, 2=MEDIUM, 3=HIGH) | `[0x7C87]` `var_speed_cursor` | по умолчанию 2 — `STA 0x7C87 @0x2CC8`; меняется клавишами |
| выбор по слотам | `[0x7C88+slot]` `var_speed` (4 байта, см. поправку в конце) | `MOV M,A @0x26ED` в обработчике меню |
| индекс слота | `[0x7DBC]` `var_player_turn_slot` | `STA 0x7DBC @0x08F3` в обходчике сессий |
| **производный период анимации** | `[0x7C6A]` `var_speed_period` | `func_start_new_level`: `LXI H,7C88 @0x1FDB; LDA 7DBC @0x1FDE; MOV A,M @0x1FE5; MVI A,04; SUB E; ADD A; ADD A; STA 7C6A @0x1FEC` → **`(4 − speed) × 4`** |
| потребление | `func_ramp_delay_cycle` (`0x183D`) | кадр выдержки главного цикла |

Трасса при старте уровня (скорость по умолчанию 2): `[0x7C87]=2`, `[0x7C88]=2`, `[0x7C6A]=8` = (4−2)×4 ✓.

## Полное дерево: boot → заставка → уровень → цикл → смерть / финал → game over → заставка

```
0x0100 func_boot_init          DI; LXI SP,0100; CALL 04B5 (вектора); LXI H,070D/SHLD 0827;
                               MVI A,03/STA 071E; очистка VRAM-области (LXI H,8000, цикл 0x0117)
  └─ 0x011E JMP 0863           ← единственный JMP в 0x0863 во всём образе (проверено поиском иммедиата)
      │
0x0863 func_session_state_driver   [внешний контур сессий]
  ├─ 0x08A9 CALL 2565  func_attract_mode_loop        заставка/аттракт (музыка CALL 2D7A)
  │    └─ 0x25FF func_attract_overlay_driver (SHLD 7DF0 @0x260E — сохранение SP)
  │         ├─ fall-through → 0x2633 lbl_title_key_poll   ← ТЗ-цикл
  │         │     0x2651 func_attract_frame_step: CALL 277E (ввод) + CALL 2A9A (сдвиг) + LDA 7DE2
  │         │     0x277E → CALL 2AB0 (опрос линии) → CNZ 26C6 func_attract_menu_key_handler
  │         │           0x26C6: шаг меню 0→1→2 (экраны титул / HOW MANY PLAYERS / SELECT SPEED LEVEL)
  │         │           0x26DF lbl_menu_commit_slot: [0x7C88+slot]=скорость, [0x7D91+slot]=линия
  │         │                 все слоты подтверждены → JZ 0x2646
  │         └─ 0x2646 lbl_attract_exit_restore: LHLD 7DF0; SPHL; RET  → выход в 0x08AC
  ├─ 0x08AC func_music_stop; инициализация слотов 0x08B6 / 0x08C8 / 0x08D7
  │         ([0x7DAB..]=уровень 1, [0x7DAF..]=жизни 5, [0x7DB3..]=счёт 0)
  ├─ 0x08E9 CALL 23B5          сброс экрана (MVI A,20/LXI H,5400/LXI B,0300/CALL 0142) + XRA A/SHLD 7C04
  └─ 0x08EF цикл по слотам C=0..3:
        0x08F3 STA 7DBC        var_player_turn_slot = C
        0x08FA/0x0900          [0x7DAF+C] → [0x7C06] (жизни), [0x7DAB+C] → [0x7C66] (уровень)
        0x0910 SHLD 7C04       [0x7DB3+2C] → счёт
        0x0918 ORA A / 0x0919 CNZ 095C   жизнь есть → сессия игрока
        0x091E/0x0926/0x0935   сохранение изменённых жизней/уровня/счёта обратно в таблицы слотов
        0x0938 LDA 7C86/CMP C/JNZ 0958   цикл до последнего игрока
        0x093F..0x0952         сумма жизней всех слотов; 0x0952 JZ 08A9 → GAME OVER → снова аттракт
        0x0955 LXI B,00FF / 0x0958 INR C / 0x0959 JMP 08EF   (перезапуск обхода с C=0, рандер-робин)

0x095C func_player_session     (сессия одного игрока: подготовка → цикл → исход)
  ├─ 0x095F CALL 1FAD  func_start_new_level   (скорость → [0x7C6A], линия → [0x7C07], позиция, поле)
  ├─ 0x0962 MVI A,02 / CALL 2D7A  func_music_start
  ├─ 0x0967 CALL 09BA  func_main_game_loop    ← ГЛАВНЫЙ ИГРОВОЙ ЦИКЛ (бесконечный, выходит только RET)
  ├─ 0x096A LDA 7C0C: 0 → 0x0989; FF → CALL 1A7B; FE → CALL 1A30
  ├─ 0x097B CALL 09A5  func_death_pause_loop (~100 кадров паузы со звуком)
  ├─ 0x097E CALL 17C6  func_dec_men_display   (−1 к «MEN», BCD)
  ├─ 0x0981 LDA 7C06 / 0x0985 CZ 223C  func_game_over_high_score  (жизни = 0)
  └─ ветка 0x0989 (уровень пройден): MVI A,03/CALL 2D7A; 0x098F MVI A,07/MVI E,28/CALL 0206;
        0x0996 MVI A,06/MVI E,07/CALL 0206; CALL 1AFA; CALL 17F9 (func_inc_level_number); 0x09A2 JMP 095F

0x223C func_game_over_high_score  звук 0x0206 (команды 01,03,07/E=B8,08/E=0E,09); MVI A,14/STA 7C5A;
        CALL 1ADF; цикл 0x2263: DCR [0x7C66] пока ≠0 (уровень «отматывается» вниз) с CALL 24CF/22D9;
        копии строк 0x2356→0x714A (13 байт) и 0x2363→0x71C8 (17 байт) через CALL 12E0;
        0x229A LHLD 7C04; 0x229E LHLD 7C8F; CALL 04F1 func_hl_eq_de; JNC 22AC; 0x22A8 SHLD 7C8F (новый рекорд);
        0x22AC LXI H,55D3 / SHLD 7C8D; LHLD 7C8F / SHLD 7C72; CALL 1DA6 (вывод цифр); выдержка 0..255 × CALL 183D; RET
```

## `func_main_game_loop` (`0x09BA`) — почему это именно он

Тело (0x09BA..0x09EC, 51 байт; `JMP 0x09BA` на `0x09EC` — вечная петля):

```
0x09BA LXI H,7C53 : DCR M : JNZ 09C7 : MVI A,03 : MOV M,A : CALL 09EF   ; ряды/генерация поля (раз в 3 прохода)
0x09C7 LXI H,7C54 : DCR M : JNZ 09D4 : MVI A,05 : MOV M,A : CALL 121F   ; опрос управляющих клавиш (раз в 5 проходов)
0x09D4 LDA 7C10 : ORA A : CNZ 0E9C @0x09D8  ; отложенная отрисовка поля, если запрос nonzero
0x09DB LDA 7C0C : ORA A @0x09DE : RNZ @0x09DF ; событие уровня → выход в func_player_session
0x09E0 LDA 7C01 : CPI 01 : RZ @0x09E5      ; игрок на верхней строке → «уровень пройден»
0x09E6 CALL 18B1 : 0x09E9 CALL 183D        ; звуковой эффект + кадровая выдержка (период из [0x7C6A])
0x09EC JMP 09BA
```

Доводы в пользу того, что ТЗ-имя `func_main_game_loop` принадлежит `0x09BA`, а не `0x0863`/`0x095C`:

1. Только `0x09BA` содержит «тело одного кадра игры» с собственными таймерами и собственной безусловной петлёй (`JMP 0x09BA`), т.е. является циклом в прямом смысле; `0x0863` — линейный дискретор (аттракт ↔ обход слотов), `0x095C` — конечная процедура с `RET` (вызывается как `CNZ 095C`).
2. Единственный вызов `0x09BA` — из `func_player_session` (`CALL 09BA @0x0967`), сразу после `func_start_new_level` и `func_music_start`, т.е. это цикл **после инициализации уровня**, ровно как формулирует ТЗ («пройти код после нажатия: инициализация уровня → игровой цикл»).
3. Выход из `0x09BA` и есть диспетчер исходов: `[0x7C0C]≠0` → `RNZ @0x09DF`, `[0x7C01]==1` → `RZ @0x09E5`; оба возврата попадают в `0x096A` — разбор смерти/прохождения уровня.
4. `0x0863`/`0x095C` были заведены как отдельные объекты `func_session_state_driver` и `func_player_session` (ранее не имели имён вообще), чтобы не смешивать три контура.

Решение по именованию: `func_game_main_loop` (Stage 2) → **`func_main_game_loop`**, старое имя сохранено в `properties.aliases` и упомянуто в комментарии как «было». В 5 объектах Stage 2–4, где старое имя встречалось в комментариях, комментарии переписаны однострочно (`func_death_pause_loop`, `func_sound_effect_dispatch`, `func_spawn_scroll_cells`, `func_init_palette_ramp`, `func_start_new_level`); повторный grep по `.rdb` даёт упоминание старого имени ровно в одном месте — в самом `func_main_game_loop` (алиас).

## Игровые переменные: 33 объекта `variable` в RDB

Ниже — краткая выжимка; в RDB у каждой переменной однострочный комментарий с точными адресами инструкций и связями func → var. «Трасса» = значение, снятое `debug_read_memory_range` с живого образа: `старт` — сразу после входа в уровень, `+3 с` — после ~3 с игры.

### Рабочая область ОЗУ (0x0100..0x50FF, доступна ROM'у напрямую)

| Адрес | Имя | Разм. | Кто пишет | Кто читает | Трасса |
|---|---|---|---|---|---|
| `0x071E` | `var_ramp_frames` | 1 | boot `STA @0x010F`=3; аттракт `STA @0x27CD` / `MVI M,04 @0x25ED`=4 | `func_irq_frame_service` (`LXI H,071E @0x04F7`, `DCR M @0x04FF`) — страж растера палитры | игра: 0 |
| `0x071F` | `var_field_dirty_flag` | 1 | `func_reset_cell_table` (`STA @0x0202`), `STA @0x1AF6`, `STA @0x119D` и др. | `func_irq_frame_service` (`LXI H,071F @0x0544`, `ORA M`, `MVI M,00 @0x0548`, `CNZ 03D7`) | игра: 0 (съедается ISR) |
| `0x081F` | `var_key_ring` | 8 | только ISR: `LXI H,081F @0x0520`, 8 × `MOV M,A @0x052A` | `func_key_ring_peek` → `func_key_strobe_state` / `func_key_code_decode` | с удерживаемым SPACE: `FF×7, 7F` |
| `0x0827` | `var_palette_ramp_ptr` | 2 | boot `LXI H,070D + SHLD @0x010A`; `SHLD @0x010A/0x27C8/0x25E4` | `func_irq_frame_service` (`LHLD 0827 @0x0503`) | 0x070D |
| `0x082A` | `var_scratch_word` | 2 | кэш `A`/HL по всей прогамме (`STA 082A`, `SHLD @0x2646`) | `func_irq_vblank_dispatcher`, глифовые примитивы | 0x20 |
| `0x7DF0` | — (входит в `lbl_attract_exit_restore`) | 2 | `SHLD 7DF0 @0x260E` (сохранение SP аттракта) | `LHLD 7DF0 @0x2649` | — |

### Состояние игры (выше 0x50FF)

| Адрес | Имя | Разм. | Кто пишет | Кто читает | Трасса |
|---|---|---|---|---|---|
| `0x7C00` | `var_player_x` | 1 | спавн `STA @0x204B`; движение `STA @0x0DF6` | `func_scroll_step_player`, отрисовка поля | старт: 2 |
| `0x7C01` | `var_player_y` | 1 | спавн `STA @0x2088`; шаг по строкам; `STA @0x123F` (из `func_probe_control_keys`) | `func_main_game_loop` (`CPI 01 → RZ` = уровень пройден) | старт: 8 → +3 с: **22** |
| `0x7C04` | `var_score` | 2 BCD | загрузка из слота `SHLD @0x0910`; обнуление `XRA A/SHLD @0x23C3` и `CALL 1751 @0x2022`; `func_add_score_display` | HUD, save-back `LHLD @0x0931`, сравнение с рекордом `LHLD @0x229A` | старт: 0; +3 с: 0 |
| `0x7C06` | `var_lives` | 1 | загрузка из `var_slot_lives_table` `STA @0x0915`, save-back `MOV M,A @0x091E`; `func_inc/dec_men_display` | HUD «MEN»; `ORA A @0x0983` → `CZ 223C` (game over) | **5** («MEN: 5») |
| `0x7C07` | `var_control_line` | 1 | аттракт `STA @0x2ADA` (0 или 2); коммит меню `[0x7D91+slot]`; `func_start_new_level` `STA @0x1FF4` | обработчик движения (`[0x7D91+slot]` → линия клавиатуры) | старт: 0 (старт нажатой клавишей) |
| `0x7C0C` | `var_game_event` | 1 | обработчик коллизий, `func_probe_control_keys` (`STA @0x1253`) | `func_main_game_loop` (`LDA @0x09DB/RNZ`), `func_player_session` (`0x096A`) | старт: 0 |
| `0x7C1E` | `var_cell_gen_counter` | 1 | `INR M` + `ANI 1F` в `func_spawn_scroll_cells` | индекс окна генерации рядов (`[0x7C91]/[0x7CB1]/[0x7CD1]/[0x7CF1]`) | старт: 19 → +3 с: **25** |
| `0x7C53` | `var_scroll_timer` | 1 | перезагрузка `MVI M,3 @0x09C1` | `DCR M @0x09BD` (главный цикл) | +3 с: 1 |
| `0x7C54` | `var_keyprobe_timer` | 1 | перезагрузка `MVI M,5 @0x09CE` | `DCR M @0x09CA` | +3 с: 2 |
| `0x7C65` | `var_level_drawn` | 1 | `func_start_new_level` (пара `[0x7C65..0x7C66]`) | `func_draw_level_digit` | 1 |
| `0x7C66` | `var_level` | 1 | загрузка из `var_slot_level_table` `STA @0x0900`, save-back `@0x0926`; `func_inc_level_number @0x17F9`; `DCR M @0x2263` (откат при game over) | HUD «LEVEL»; сравнения | **1** |
| `0x7C6A` | `var_speed_period` | 1 | `func_start_new_level` `STA @0x1FEC` = (4−скорость)×4 | `func_ramp_delay_cycle` (`LDA 7C6A` → длина выдержки) | **8** при скорости 2 |
| `0x7C6E` | `var_field_marker_count` | 1 | **единственный писатель** `func_count_player_cells` `STA @0x23AE` (дубль `@0x23B1` в `[0x7C71]`) | `func_dec_row_counter` (`LXI H,7C6E @0x11DC`) из 3 точек `func_spawn_scroll_cells`; `LDA @0x1C3B`, `LDA @0x1B10` | 8 при старте и те же 8 через +4.5 с |
| `0x7C72` | `var_bcd_display_word` | 2 BCD | `SHLD @0x1B00`, `SHLD @0x1DBA`, `SHLD @0x22B5` (сюда кладётся рекорд) | `LHLD @0x1DAF`, `LXI D,7C72 @0x1DC3` | 0 |
| `0x7C84` | `var_slot_write_idx` | 1 | сброс `STA @0x2C29`, `STA @0x2CD7`; `INR A/STA @0x2701` | индекс слота при коммите меню | 1 |
| `0x7C85` | `var_menu_state` | 1 | `STA @0x26D2` (шаг 0→1→2), сброс `STA @0x25C6` | `func_attract_menu_key_handler`, `lbl_title_key_poll` (`LDA @0x263F`) | 0→1→2 по нажатиям SPACE |
| `0x7C86` | `var_player_count` | 1 | `STA @0x25CA` = 0xFF на титуле; запись из экрана HOW MANY PLAYERS | сравнение с C в обходчике слотов (`CMP C @0x093A`), `JZ 2646` в меню | 0 (один игрок) |
| `0x7C87` | `var_speed_cursor` | 1 | по умолчанию 2 — `STA @0x2CC8`; клавиши меню | `LDA @0x26E3` при коммите | 2 |
| `0x7C88` | `var_speed` (4 байта, по слотам) | 4 | `MOV M,A @0x26ED` | `func_start_new_level` `LXI H,7C88 @0x1FDB` | `[0x7C88]=2` |
| `0x7C8D` | `var_bcd_display_ptr` | 2 | `SHLD @0x1DC0`; `LXI H,55D3 + SHLD @0x22AF` | `LHLD @0x1DE9` | 0 |
| `0x7C8F` | `var_high_score` | 2 BCD | только `SHLD @0x22A8` при новом рекорде | `LHLD @0x229E`, `LHLD @0x22B2` | 00 01 — явной инициализации в образе нет (open question) |
| `0x7D91` | `var_player_control_table` | 8 | коммит меню `LXI H,7D91 / DAD B / MOV M,A @0x26F5` | выборка линии управления игрока по `var_player_turn_slot` | `[0x7D91]=0` (линия 0) |
| `0x7DAB` | `var_slot_level_table` | 4 | инициализация `LXI H,7DAB @0x08B6` + `LXI B,0401` (4 слота по 1); save-back `@0x0926` | загрузка в `var_level` `STA @0x0900` | `1,1,1,1` |
| `0x7DAF` | `var_slot_lives_table` | 4 | инициализация `LXI B,0405 @0x08C8` (4 слота по 5); save-back `MOV M,A @0x091E` | загрузка в `var_lives` `STA @0x0915` | `5,5,5,5` — отсюда «MEN: 5» |
| `0x7DB3` | `var_slot_score_table` | 8 | инициализация нулём `LXI H,7DB3 @0x08D7`; save-back `LHLD 7C04 / SHLD` по слоту | загрузка в `var_score` `SHLD @0x0910` | все нули |
| `0x7DBC` | `var_player_turn_slot` | 1 | `STA @0x08F3` (`MOV A,C`) в обходчике слотов | `func_start_new_level` `0x1FDE`, `0x2009`, выбор индексов таблиц `0x2374` | 0 |
| `0x7DE2` | `var_music_step_counter` | 1 | сброс `STA @0x263C` (вход в опрос) и `STA @0x2D90` (`func_music_start`); `INR M @0x2DB1` в воркере `0x2D94` из `func_irq_music_step` | условие выхода из `lbl_title_key_poll` (`LDA @0x2657` → `CPI 03`) | 0 на паузе, растёт только при работающей мелодии |
| `0x7DF2` | `var_attract_strobe_latch` | 1 | `STA @0x2AD6` (результат `func_attract_key_row_scan`) | `func_attract_input_update` (`LDA 7DF2 / JNZ 278C`) | `FF` при удерживаемом SPACE |

## Числа из трассы (протоколы прогонов)

Все значения сняты `debug_read_memory_range` с живого образа; `debug_reset` ни разу не вызывался, вход в игру — только `debug_type_key` / `debug_press_key`.

| # | Протокол | Наблюдение |
|---|---|---|
| 1 | `debug_run` → `debug_type_key SPACE` → пауза, чтение `[0x7C85]` | 0 → **1** (титул → HOW MANY PLAYERS) |
| 2 | ещё одно SPACE | 1 → **2** (SELECT SPEED LEVEL), `[0x7C87]=2` (курсор по умолчанию) |
| 3 | ещё одно SPACE | коммит `[0x7C88]=2`, `[0x7D91]=0`, `[0x7C84]=1` → выход из аттракта → инициализация уровня |
| 4 | снимок сразу после старта уровня | `[0x7C00]=2`, `[0x7C01]=8`, `[0x7C04..05]=00 00`, `[0x7C06]=5`, `[0x7C66]=1`, `[0x7C6A]=8`, `[0x7C6E]=8`, `[0x7C70]=0x77`, `[0x7C85]=2`, `[0x7DAB..AE]=1,1,1,1`, `[0x7DAF..B2]=5,5,5,5`, `[0x7DB3..]=0`, `[0x7DBC]=0` |
| 5 | `debug_run` ~3 с → пауза | `[0x7C01]` 8 → **22** (игрок поднимается), `[0x7C1E]` 19 → **25**, `[0x7C53]=1`, `[0x7C54]=2`, PC в момент паузы `0x18AA`/`0x18A3` (петля выдержки), счёт `[0x7C04]` = 0, жизни = 5 |
| 6 | `debug_press_key SPACE` (удержание) → `debug_run` 0.4 с → пауза → `debug_release_key` | кольцо `[0x081F..0x0825]=FF×7`, `[0x0826]=**7F**`, `[0x7DF2]=FF`, `[0x7C07]=00` — привязка «SPACE ↔ слот 7, бит 7» |
| 7 | `debug_run` +1.5 с, чтение `[0x7C6E..0x7C71]` | `8, 0, 77, 8` — значения стабильны, т.е. `[0x7C6E]`/`[0x7C71]` пишутся пакетно `func_count_player_cells`, а не «нарастают» |
| 8 | чтение `[0x7C8D..0x7C92]`, `[0x7DE2]`, `[0x071F]` на паузе | `0,0,0,1,0,0` / `0` / `0`; `[0x7C90]=1` при `[0x7C8F]=0` — см. Open questions №3 |

Совпадение с ожиданиями ТЗ: «MEN: 5» ↔ `[0x7DAF..]=5` и `[0x7C06]=5` ✓; «3 SPEED LEVEL» ↔ курсор `1..3` в `[0x7C87]` и `[0x7C88]=2` ✓.

## Поправки к объектам Stage 2–4 (правило «противоречие — переписать и упомянуть»)

| Объект | Было | Стало | Доказательство |
|---|---|---|---|
| `0x09BA` `func_game_main_loop` | комментарий «Основной цикл уровня» | **`func_main_game_loop`** (ТЗ-имя), старое имя → `properties.aliases` | дерево вызовов `0x0863 → 0x095C → 0x09BA`, тело с `JMP 0x09BA` |
| `0x7C6E` `var_scroll_row_counter` | «счётчик рядов» | **`var_field_marker_count`**, алиас старого имени в `properties.aliases` | единственный писатель `func_count_player_cells` (`STA @0x23AE`), а не генератор рядов |
| `0x11DB` `func_dec_row_counter` | «[0x7C6E] — счётчик рядов/фазы в циклах прорисовки» | комментарий переписан: счётчик совпавших клеток + точка начисления очков `@0x11A8 → CALL 0x1751` | `debug_find_immediate_in_range(31854)` = 4 сайта всего |
| `0x7DE2` (создан на Stage 5) | `var_menu_frame_steps` | **`var_music_step_counter`** | `INR M @0x2DB1` внутри музыкального воркера `0x2D94`, куда идёт `CALL 2D94 @0x2F17` из `func_irq_music_step` |
| 5 объектов Stage 2–4 с упоминанием `func_game_main_loop` | — | комментарии переписаны однострочно | grep по `.rdb`: старое имя осталось ровно в 1 месте (алиас) |
| `0x2AAB` (probe-останов) из ТЗ-подсказки | «возможно, цикл ожидания клавиши» | подтверждено: **не** цикл ожидания, внутренняя петля копирования `func_attract_plane_shift` | реальный цикл — `0x2633` |
| `0x121F` `func_probe_control_keys` | «IN 0x01 (порт B КР580ВВ55 #1)», «[0x7C01] — флаг подтверждения/паузы» | комментарий переписан: `IN 0x01` = **порт C** (сдвиги, `io.md`/`keyboard.md`); `[0x081F+2]` = строка цифр → `0xF7` → `STA [0x7C01]=1` (форсаж конца уровня), `0xFB` → `CALL 0x17BB` (+1 жизнь); в Shift-ветке `[0x081F+6]` `0xFB` → `STA [0x7C0C]=FF`; выставлены `io`/`reads`/`writes` и связи → `0x17BB`, `0x7C06` | дизассемблирование `0x121F..0x1256`, `0x17BB..0x17C3` |
| `0x2651` `func_attract_frame_step` (имя Stage 2) | «Вызывающие: 0x2633 (func_attract_overlay_driver)» | комментарий исправлен: `0x2633` — это `lbl_title_key_poll`, а не `func_attract_overlay_driver` (`0x25FF`) | `debug_disassemble_range(9775)`: `0x2630` — последняя инструкция `0x25FF`, вызов `0x2651` лежит в `0x2633` |
| `0x1AFA` `func_level_intro_sequence`, `0x2312` `func_level_complete_sequence` (имена Stage 2) | «интро уровня» / «финаж» приписывались друг другу | комментарии дополнены пометкой «уточнение Stage 5»: `0x1AFA` вызывается из ветки **уровень пройден** (`@0x0993`), `0x2312` — из пролога (`@0x095F`) | трасса: `0x095F CALL 1FAD` перед циклом, `0x0993 CALL 1AFA` после `RZ` выхода цикла |

Ничего из имён Stage 2–4 не удалено и не перенесено на другой адрес; единственные переименования существующих объектов — `func_game_main_loop → func_main_game_loop` и три метки (`0x2633`, `0x2646`, `0x26DF`); остальное — переписанные однострочные комментарии и дополненные свойства. Имена Stage 2 `func_attract_frame_step`, `func_count_player_cells`, `func_level_intro_sequence`, `func_level_complete_sequence` сохранены (проверено по Stage2.md), правки коснулись только их комментариев.

## Новые объекты Stage 5

Функции (4):

| Адрес | Имя | Тип | Размер | Комментарий (сокращ.; в RDB — одна строка) | Связи |
|---|---|---|---|---|---|
| `0x0863` | `func_session_state_driver` | function | — (не размечен) | внешний контур: буфер 0x6000, аттракт, инициализация таблиц слотов, обход 4 слотов с загрузкой/сохранением жизни-уровня-счёта, возврат в аттракт при нуле жизней | → `0x2565`, `0x2D72`, `0x23B5`, `0x095C`, `0x7C04`, `0x7C06`, `0x7C66`, `0x7C86`, `0x7DAB`, `0x7DAF`, `0x7DB3`, `0x7DBC` |
| `0x095C` | `func_player_session` | function | 73 | сессия одного игрока: `func_start_new_level` → музыка → `func_main_game_loop` → разбор `[0x7C0C]` → пауза смерти / −1 жизнь / game over / переход на следующий уровень | → `0x1FAD`, `0x2D7A`, `0x09BA`, `0x09A5`, `0x17C6`, `0x17F9`, `0x1AFA`, `0x223C`, `0x2312`, `0x1A7B`, `0x1A30`, `0x7C06`, `0x7C0C` |
| `0x26C6` | `func_attract_menu_key_handler` | function | 70 | обработчик нажатия в меню заставки: шаг `[0x7C85]` 0→1→2, коммит скорости `[0x7C88+slot]` и линии `[0x7D91+slot]`, выход `JZ 0x2646` | → `0x2D4E`, `0x26DF`, `0x2C22`, `0x2CA4`, `0x2646`, `0x7C84`, `0x7C85`, `0x7C86`, `0x7C87`, `0x7C88`, `0x7C07`, `0x7D91` |
| `0x223C` | `func_game_over_high_score` | function | 157 | GAME OVER: звуки, откат `[0x7C66]` до 1, копии строк узоров `0x2356→0x714A` (13) и `0x2363→0x71C8` (17), сравнение `[0x7C04]` с рекордом `[0x7C8F]` через `func_hl_eq_de 0x04F1`, запись рекорда и его вывод | → `0x0206`, `0x04F1`, `0x12E0`, `0x1ADF`, `0x1DA6`, `0x183D`, `0x24CF`, `0x22D9`, `0x2374`, `0x2343`, `0x7C04`, `0x7C66`, `0x7C72`, `0x7C8D`, `0x7C8F` |

Метки (переименованы из `lbl_*` без смены адреса): `0x2633` `lbl_2633 → lbl_title_key_poll` (ТЗ-имя, тип `label`), `0x2646` `→ lbl_attract_exit_restore`, `0x26DF` `→ lbl_menu_commit_slot`.

Переменные: **33** объекта `type=variable` (в RDB до Stage 5 переменных не было вообще) — см. таблицы выше; у каждой указан размер (1/2/4/8 байт, всего 42 объекта в базе с известным размером) и однострочный комментарий «кто пишет / кто читает» с адресами инструкций.

## Сводка изменений в RDB за Stage 5

| Метрика | Значение |
|---|---|
| Объектов в RDB | **403** (было 366 после Stage 4) |
| Функции | **104** (было 100) — 4 новых: `0x0863`, `0x095C`, `0x223C`, `0x26C6` |
| Метки | **266** (без изменений по количеству; 3 переименованы: `lbl_2633`→`lbl_title_key_poll`, `lbl_2646`→`lbl_attract_exit_restore`, `lbl_26DF`→`lbl_menu_commit_slot`) |
| Переменные | **33** (было 0) — все в RAM выше 0x50FF, кроме 5 ячеек рабочей области (`0x071E`, `0x071F`, `0x081F`, `0x0827`, `0x082A`) |
| Связей (links) | **309** (было 193; +116) |
| Объектов со ссылками | 155 |
| Объектов с известным размером | **42** (было 6) — 33 переменные + 8 функций + метка `lbl_04ee` |
| Переименований | 4 метки/функции ТЗ-именами + 2 внутренних переименования переменной (`var_scroll_row_counter`→`var_field_marker_count`, `var_menu_frame_steps`→`var_music_step_counter`), старые имена — в `properties.aliases` |
| Комментариев переписано/дописано | 7 объектов несут явную пометку «Stage 5/уточнение Stage 5» в комментарии: `0x04F1`, `0x09BA`, `0x11DB`, `0x121F`, `0x1AFA`, `0x1FAD`, `0x2312` |
| Свойств выставлено | `params`/`returns`/`reads`/`writes`/`aliases` у ~15 объектов (в т.ч. впервые — портовый `io` у `0x121F`: `IN 0x01` Port C) |
| `debug_save_rdb` | 5 пакетов (по ≤10 объектов), каждый подтверждён `debug_get_rdb_info`: `loaded=true`, `dirty=false`, `object_count=403`, sha256 ROM `c265014b…a6991` без изменений |
| Проверка однострочности | проверены **все 403 объекта** (комментарий + все свойства): переносов строки — 0 |
| Покрытие переменных связями | **33/33** переменных имеют минимум один входящий link (проверено по `"links"` всех объектов) |

## Round-trip

Финальный прогон после всех правок RDB: `PATH=$PWD/z88dk/bin:$PATH utils/analyze/run_pipeline.sh riseout --from export_asm` (без `--resume`).

| Стадия | Результат |
|---|---|
| `export_asm` | экспортёр `v06c-asm-export` отработал, файлов 9, сборка `z80asm -b` → 20480 байт |
| `toolchain_lint` | чисто |
| `symbolic_operand_lint` | 375 находок, 0 блокирующих |
| `syntax_check` | собралось без единой претензии (ни одного «invalid character» — все комментарии Stage 5 однострочные) |
| **`roundtrip_verify`** | **`verdict="byte-for-byte identical"`**, `compared_bytes=20480`, `bytes_differing=0`, `offenders=[]`, `size_match=true`, `status="OK"` |
| `measure_sizes` | 366 расхождений размера из 403 объектов (штатно: размеры задавали только 42 объектам) |

Сводный итог прогона в `.scratch/pipeline/riseout/pipeline.md` — **PARTIAL**, и это не регресс: в режиме `--from export_asm` все мутирующие стадии возвращают PARTIAL (они ничего не меняют в RDB), а контрактная проверка `roundtrip_verify` = SUCCESS. Та же картина была на Stage 4.

Символы Stage 5 корректно попали в листинг (`.scratch/export/pipeline/layout.asm`): `func_main_game_loop:`, `func_attract_menu_key_handler:`, `func_game_over_high_score:`, `func_attract_frame_step:`, `call func_attract_frame_step`, `lbl_title_key_poll:`, `var_lives:`, `lda var_lives`, `shld var_score`, `sta var_field_marker_count`.

## Verified Facts

1. Строка «HIT BUTTON OR SPACE KEY» лежит в образе по адресу **`0x2B9D`** (= смещение в файле `0x2A9D` из ТЗ + org `0x0100`); она — вторая запись 7-элементной таблицы титула `0x2B8B`, которую рисует `func_attract_draw_title` (`0x2B61`) одним вызовом `func_draw_text_records` (`0x2D1B`).
2. Цикл ожидания старта — **`lbl_title_key_poll` @ `0x2633`** (`label` в RDB): `CALL 0x2651` → `CPI 03` → `JNZ 0x2633`, затем сброс `[0x7DE2]` и `LDA [0x7C85] / JNZ 0x2633`. Выход — `RET` из `lbl_attract_exit_restore` (`0x2646`) с восстановлением стека из `[0x7DF0]`.
3. Порты `KEYSTROB`/`KEYDATA` в этом ROM — **PIA1 port A (`OUT 0x03`, маска строки) и port B (`IN 0x02`, данные столбцов)**; опрос делает **только ISR кадра**: `func_irq_frame_service` (`0x04F7`), поз. `0x0523..0x0530`, 8 итераций с масками `0xFE…0x7F`, результат — в кольцо `var_key_ring` `[0x081F..0x0826]`. Игровой код и аттракт порты клавиатуры не читают вовсе.
4. Эксперимент с удержанием SPACE: `[0x0826] = 0x7F`, `[0x7DF2] = 0xFF`, `[0x7C07] = 0x00` — SPACE попала в слот 7, бит 7; т.е. старт детектируется по **линии (слоту), а не по коду клавиши** — кодовая таблица `0x01D5` (`func_key_code_decode` `0x01BC`) на вход в игру не влияет.
5. Главный игровой цикл — **`func_main_game_loop` @ `0x09BA`** (переименован из `func_game_main_loop`, старое имя в `properties.aliases`): тело `0x09BA..0x09EC`, таймеры `[0x7C53]` (reload 3 → `func_spawn_scroll_cells` `0x09EF`) и `[0x7C54]` (reload 5 → `func_probe_control_keys` `0x121F`), выход по событию `[0x7C0C] ≠ 0` (`RNZ @0x09DF`) и по достижению игроком верхней строки `[0x7C01] == 1` (`RZ @0x09E5`), иначе `CALL 0x18B1` + `CALL 0x183D` и `JMP 0x09BA`.
6. Три контура вложенности подтверждены статикой и трассой: `func_session_state_driver` (`0x0863`, аттракт ↔ обход слотов) → `func_player_session` (`0x095C`, один игрок) → `func_main_game_loop` (`0x09BA`, один кадр).
7. Инициализация состояния: таблицы слотов заполняются в `func_session_state_driver` — уровни `[0x7DAB..]=1,1,1,1` (`LXI B,0401 @0x08B6`), жизни `[0x7DAF..]=5,5,5,5` (`LXI B,0405 @0x08C8`), счёта `[0x7DB3..]=0` (`LXI H,0x08D7`); при передаче хода конкретному игроку значения загружаются в `[0x7C66]`/`[0x7C06]`/`[0x7C04]` (`@0x0900`, `@0x0915`, `SHLD @0x0910`) и обратно сохраняются (`@0x091E`, `@0x0926`, `LHLD @0x0931`). Трасса на старте уровня: жизни = **5**, уровень = **1**, счёт = **0**, `[0x7C00..01] = 2,8`.
8. Скорость: курсор меню `[0x7C87]` (1..3, по умолчанию **2** — `STA @0x2CC8`) → выбор по слотам `[0x7C88+slot]` (`MOV M,A @0x26ED`) → **`[0x7C6A] = (4 − speed) × 4`** (`func_start_new_level`: `MVI A,04; SUB E; ADD A; ADD A; STA 7C6A @0x1FEC`) → потребляется `func_ramp_delay_cycle` (`0x183D`), который вызывается каждой итерацией главного цикла. Трасса при скорости 2: `[0x7C6A] = 8` ✓.
9. `[0x7C6E]` — **не** счётчик рядов: единственный писатель `func_count_player_cells` (`0x238F`), `STA @0x23AE` (зеркало `STA [0x7C71] @0x23B1`), значение = число клеток `[0x7020..0x72FF]` с кодами `0x6D/0x69/0x6A`; `func_dec_row_counter` (`0x11DB`) уменьшает его из трёх точек `func_spawn_scroll_cells`, одна из которых (`0x11A8`) стоит непосредственно перед `MVI A,01 / CALL func_add_score_display 0x1751` — т.е. это путь начисления очков. Трасса: `[0x7C6E..71] = 8,0,77,8` и через +1.5 с те же значения.
10. GAME OVER (`func_game_over_high_score`, `0x223C`, размер 157) достигает `func_hl_eq_de` (`0x04F1`, `CALL @0x22A2`) — прямое закрытие open question Stage 2/3; при `[0x7C06] == 0` вызывается из `func_player_session` (`CZ 0x223C @0x0985`), внутри сравнивает `[0x7C04]` с рекордом `[0x7C8F]` и пишет новый (`SHLD @0x22A8`).
11. `func_probe_control_keys` (`0x121F`) содержит отладочные ветки: `IN 0x01` (порт C, сдвиги; порт B в комментарии Stage 2 — ошибка), `MVI A,02 / CALL 0x01E6 / CPI 0xF7 → STA [0x7C01],1` (мгновенное завершение уровня) и `CPI 0xFB → CALL 0x17BB` (**+1 жизнь**), в Shift-ветке `MVI A,06 / CALL 0x01E6 / CPI 0xFB → STA [0x7C0C],0xFF`.
12. Все 33 переменные имеют минимум одну входящую связь func/label → var; связей в RDB — **309**; переносов строки в комментариях и свойствах нет (проверено по всем 403 объектам); round-trip сохранён.

## Inferences (не доказано трассой)

1. «BUTTON OR SPACE» для детектора неразличимы: `func_key_strobe_state` (`0x01A8`) осмысленна только при `A=0` и смотрит слот 7 (`[0x0826]`, бит 7), то есть любой строб этой линии даёт «нажато». Различение возможно только выше — по номеру линии в `[0x7C07]` (0 или 2), который выбирает, какую строку матрицы считать управляющей
2. `[0x7C70] = 0x77` при старте уровня — тематически связан с узором/наградой (тот же регистр читается в `func_level_complete_sequence`), но прямой расшифровки нет.
3. Назначение `[0x7C8D]`/`[0x7C72]` как «адрес и значение BCD-поля вывода» принято по трём write-site/Read-site парам; механизм «счётчик очков на экране» подтверждён только для пути `func_inc_draw_counter_value`.
4. Ветки `0x1247`/`0x12BC` в `func_probe_control_keys` — предположительно пауза/служебный режим (Shift-сочетания), не проверялось.
5. «Аттракт живёт на отдельном стеке» (`SHLD [0x7DF0]` + `SPHL` на выходе) — факт кода, но мотив (защита от переполнения при демо-анимации) — догадка.

## Open questions (что ушло дальше)

1. **Почему порог выхода из `lbl_title_key_poll` именно 3 доли мелодии.** Код доказан (`CPI 03` против `[0x7DE2]`), эргономика (ждать ровно такт, чтобы смена экрана не «прыгала» в середине фразы) — предположение. Проверить можно только сравнением таймингов с другим порогом (патчем), что выходит за рамки аудита.
2. **`[0x7DE1]` — сосед мелодийного счётчика.** `func_music_start` пишет в него 0 (`STA 7DE1 @0x2D8D`) рядом с `STA 7DE2`, кто его читает и что он значит — не исследовано (это территория музыкального подэтапа); объекта `var_*` для него сознательно не заводилось, чтобы не плодить недоказанные сущности.
3. **Ветви `0x1247` (Shift-сочетания) и `0x12BC`.** Что именно делает `0x12BC` и какие Shift-клавиши там разбираются — не размечено; там же, вероятно, живёт пауза.
4. **Как игра различает «BUTTON» и «SPACE» для управления.** `[0x7C07]` (0 или 2) — зафиксировано как «номер линии», но логика выбора «какая линия какому игроку» в `[0x7D91+slot]` проверена только на одном игроке; 2–4 игрока в трассе не наблюдались (`[0x7C86]=0xFF` на титуле → один игрок).
5. **`var_cell_gen_counter [0x7C1E]` и окна `[0x7C91]/[0x7CB1]/[0x7CD1]/[0x7CF1]`.** Счётчик подтверждён трассой (19 → 25), сами четыре окна генерации рядов — только по адресам из `func_spawn_scroll_cells`, их содержимое (таблицы шаблонов рядов?) не расшифровано.
6. **Причина стабильности `[0x7C6E]=8`** в первые секунды: неясно, должен ли счётчик совпавших клеток меняться в динамике или 8 — константа стартового узора (код допускает и то, и другое).
7. **Остров `0x0217..0x03D1`** (из Stage 4) по-прежнему не пройден; в контексте Stage 5 это значит, что точный механизм «событие → звук» (`[0x7C12]`, `func_sound_effect_dispatch`) описан только со стороны циклов.
8. **Размеры объектов.** Из 403 объектов размер известен у 42; у `func_session_state_driver` (`0x0863`) размер не задан намеренно — функция «без RET» (внешний контур с `JMP`/`CALL`), формальная граница произвольна.

## Ограничения

- **Источник — эмулятор, не железо.** Все портовые трактовки (`OUT 0x03` = маска строки, `IN 0x02` = данные столбцов, `IN 0x01` = порт C) взяты из Knowledge Base (`io.md`, `keyboard.md`, статус verified) и сопоставлены с наблюдаемым кодом; на реальном Векторе не проверялись.
- **Именованные клавиши («2», «3», SHIFT) — вывод из матрицы `keyboard.md`**, а не из ROM: в ROM лежат только маски `0xF7`/`0xFB`. Подтверждение «нажми «2» → +1 жизнь» трассой **не** делалось (в трассе использовался только SPACE). Помечено в комментарии объекта как недоказанное.
- **Трасса — однократная и короткая** (порядка 3–4,5 с игрового времени на одном уровне, один игрок, скорость по умолчанию). Длительные сценарии (смерть, game over, 2–4 игрока, переход между уровнями) проверены **статически**; `func_game_over_high_score` и ветка «уровень пройден» в живой трассе не наблюдались.
- **Значения регистров BCD** (`[0x7C04]`, `[0x7C72]`, `[0x7C8F]`) трактованы как BCD по наличию `DAA` в `func_add_score_display`/`func_inc_draw_counter_value`; сам факт «младший байт — младшие 2 разряда» подтверждён порядком `LHLD/SHLD`, а не расшифровкой экрана.
- **Отсутствует автоматический oracle** для семантики RAM-переменных: `debug_find_immediate_in_range` находит только обращения с с непосредственным адресом, поэтому `STA M`/`STAX B`-записи (например, в `[0x7D91+slot]`) найдены вручную через разбор адресной арифметики, и их полный список не гарантирован.
- **Round-trip подтверждает только байтовое постоянство образа**, то есть корректность разметки как комментария/имени, но не правильность смысловых имён.

## Поправки (внесены после Stage 6, при разборе `rdb_lint`)

Две blocking-находки `rdb_lint` оказались наследием Stage 5, обе исправлены через MCP (`debug_update_rdb_object` / `debug_set_rdb_property` / `debug_set_rdb_comment` + `debug_save_rdb`), затем пересобрана экспортная цепочка (`run_pipeline.sh riseout --from export_asm`) — round-trip снова `byte-for-byte identical`.

| Адрес | Было | Стало | Доказательство |
|---|---|---|---|
| `0x7C88` `var_speed` | `size=8` (0x7C88..0x7C8F) — перекрывал начало `var_bcd_display_ptr` @0x7C8D | `size=4` (0x7C88..0x7C8B) | индекс слота 0-базирован и его максимум — 4: `LXI B,0000` / `STA 7DBC @0x08EC..0x08F3` (обходчик сессий), `XRA A` / `STA 7C86` / `STA 7C84 @0x2C25..0x2C29` (сброс счётчиков меню), `MVI B,04` рисует ровно 4 варианта @0x2C3A; база та же в чтении `LXI H,7C88 @0x1FDB` |
| `0x7C6E` `var_field_marker_count` | `properties.aliases` = «var_scroll_row_counter (временно Stage 5, до уточнения писателя)» — не проходил шаблон имён `[a-z][a-z0-9_]*` | `var_scroll_row_counter` | прежнее имя Stage 5 сохранено как корректный алиас; семантика «счётчик рядов» снята тем же доказательством писателя (`func_count_player_cells`, `STA @0x23AE`), что и в таблице выше |

После правок: `rdb_lint` — 0 errors; `symbolic_operand_lint` — 408 находок, 0 блокирующих; `syntax_check` — clean.
