# Stage 5. Главный игровой цикл и экраны (exolon.rom)

> Источник фактов — MCP `vector-debugger`: статический дизасемблер (`debug_disassemble`),
> чтение памяти (`debug_read_memory_range`), **живой прогон** (`debug_load_rom` org 0x0100 →
> `debug_write_memory` `C3 00 01` по `0x0000` → `debug_run` + `debug_press_key`/`debug_type_key`
> + снимки экрана `debug_get_screen_snapshot`) и **дифф памяти** (`debug_create_memory_snapshot`
> ×2 → `debug_diff_memory`). `debug_reset` не вызывался. Единственный канал записи RDB —
> `debug_save_rdb`; `.rdb` руками не правился. Round-trip после правок пересобран
> `run_pipeline.sh exolon --from export_asm --apply` и сверен по SHA256 (см. §Round-trip).

## Goal

Закрыть Stage 5 из `TZ.md` (строки 170–196):

1. подтвердить через MCP прохождение ROM через 4 экрана (info → title → звёзды/меню → игра);
2. найти функцию перехода между экранами;
3. найти игровой цикл (движение спрайтов, столкновения, счёт);
4. найти бонус-режим;
5. выявить игровые переменные: `var_score`, `var_lives`, `var_player_x`, `var_player_y`,
   `var_bullets`, `var_enemies`, `var_level_progress`;
6. оформить экраны/переменные в RDB и не нарушить побайтовый round-trip.

## TL;DR (вердикт)

Экраны выстроены в **цепочку самомодифицируемого диспетчера**: единственный `func_entry_jmp`
(`0x0100` = `JMP <target>`) переключается между экранами, а адрес перехода пишется в operand
командой `SHLD 0101h`. В образе ровно **один** такой `SHLD` — в boot-коде `0x7883`, который
патчит переход `info → title`. Дальнейшие переходы (`title → gameplay`) идут не через `SHLD`,
а прямыми `JMP`/условными ветками в menu-loop. Фактически экранов **не 4, а 3 разных по виду**:
info-boot, title-меню (заставка и «мигание звёзд» — это один и тот же экран в `lbl_menu_loop`),
и геймплей. Бонус-режим существует в двух ипостасях: **stop-pointer мини-игра**
(`func_bonus_pointer_screen`, список `0x6E23` = «EXOLON BONUS SCREEN! / PRESS FIRE TO STOP POINTER»)
и **скрытые пикапы** в игре (`func_bonus_award @0x557A`). Найден и исправлен **misnomer**
предыдущего этапа: функция `0x6BE9` называлась `game_over`, но рендерит именно бонус-экран;
настоящий GAME OVER — список `0x7066` на `lbl_7048`.

## Цепочка экранов (live-verified)

```
0x0000  JMP 0x0100                        ; poke в рантайме (в образе нет)
0x0100  func_entry_jmp: JMP <target>      ; operand патчится SHLD 0101h
  │
0x786B  lbl_boot_entry  ── инициализация, CALL 1DFB (палитра/ВИ53)
  │       LXI H,7890 / CALL 3CC1          ; рендер INFO-экрана (список 0x7890)
  │       LXI H,762D / SHLD 0101          ; ← ЕДИНСТВЕННЫЙ self-patch: entry → TITLE
0x7886  lbl_boot_wait_rus: IN 01 / ANI 80 / JZ 0100  ; ждём РУС/ЛАТ (active-0) → JMP title
  │
0x762D  lbl_title_init  ── DI; SP=0100; сброс портов; CALL 1DFB; fill 0x9800/0x9B00
  │       LXI H,7782 / CALL 3CC1          ; рендер TITLE-экрана (список 0x7782)
  │       LXI H,70B4 / CALL 73BE          ; мелодия заставки (мигание-проигрыватель)
0x76B1  lbl_menu_loop   ── строб 0187=0FB; CALL 0147; опрос [0197]
  │       клавиши: 1(0FD)→игра, 2(0FB)→клавиатура, 3(0F7)→джойстик PU, 4(0EF)→джойстик P
  │       CALL 76FC (func_title_stars_menu) ; анимация звёзд/пунктов того же экрана
0x6F01  lbl_6f01        ── инициализация геймплея
0x6F6D  lbl_game_loop   ── главный цикл (~45 CALL/кадр): update_all_objects, HUD, beam-racing
```

### F1. Boot / info-экран — подтверждён вживую

Снимок экрана на `0x7886` (CPU стоит в цикле ожидания, `HL=0x762D` — self-patch уже выполнен)
показывает список подсказок управления. Транслит-тексты списка `0x7890`:

- `KLAWI[I UPRAWLENIQ:`
- `KLAWI[I KURSORA-PEREM]NIE`
- `RUS/LAT-VYSTREL`
- `DLITELXNOE UDERSHANIE-R...`
- `RUS/LAT+CC+YC-PEREZAPUSK IGRY`
- `DLYA NACHALA IGRY NAVMITE RUS/LAT`

Ожидание — `IN 01h; ANI 80h; JZ 0100` (переход по active-0, то есть по нажатию РУС/ЛАТ).

### F2. Title-экран = он же «мигание звёзд» (слияние экранов 2 и 3 из TZ)

После нажатия РУС CPU попадает в `0x762D`, затем в `lbl_menu_loop @0x76B1`. Снимок экрана:
логотип **EXOLON**, строка `RIVECCO AND NB INC`, меню `1 START GAME / 2 KEYBOARD /
3 JOYSTICK PU / 4 JOYSTICK P`, снизу `EXOLON L COPYRIGHT 1994`, вокруг — анимированные звёзды
(`func_title_stars_menu @0x76FC`, мигание через `func_blink_toggle`). То есть TZ-экраны
«заставка» и «мигание звёзд» — **один экран**: меню с логотипом и звёздами рисуются вместе,
мелодия играет в том же цикле.

Тексты title-списка `0x7782` (в т.ч. `EXOLON L COPYRIGHT 1994` @0x77EA, адрес автора
`310106, HARXKOW, UL.MOHNA^ANSKAQ / DOM 8-A KIT^ENKO MAKSIM / TEL. 99-26-23, KOD - (0572)`).

### F3. Переход в игру — по клавише «1»

В `lbl_menu_loop` опрос клавиатуры: строб `OUT 03 / MVI A,0FBh / STA 0187h`, чтение `IN 02h → [0197]`.
Клавиша `1` (код `0FDh`) даёт переход на `lbl_6f01` (инициализация геймплея) → `lbl_game_loop`.
Клавиши `2/3/4` выбирают способ управления (`[1E46]` = 0/1/2) и остаются в меню.

> Живое подтверждение: первый тап `1` (`debug_type_key`) не сработал (меню стробирует матрицу
> короткими окнами); удержание `1` через `debug_press_key` на ~1.5 c корректно перевело CPU
> из `0x76B1` в геймплей (`PC` ушёл в область `0x0147/0x0B3C`, экран сменился на игровой).

### F4. Геймплей и HUD — подтверждён вживую

Снимок сразу после входа: сайд-скроллинг-шутер (базовая постройка слева, скелет-игрок на
платформах, танк/пришельцы справа, планеты на фоне). HUD-подпись слева-направо:

`AMMO 55   GRENADES 10   POINTS 000000   LIVES 5   ZONES 000`

После ~2.5 c игры (удержание `RIGHT`+`RUS`/огонь): `AMMO 58  GRENADES 34  POINTS 000450→000900
LIVES 5  ZONES 001`. Дифф двух снапшотов памяти (см. §Переменные) подтвердил, какие ячейки
меняются при этих событиях.

### F5. Главный цикл

`lbl_game_loop @0x6F6D` — каркас кадра: `func_frame_sync` (поллинг ВИ53, без прерываний — Stage 4),
`func_update_all_objects @0x48FF` (агрегатор подсистем `49C4/49E7/4A05/4A85` + движение игрока
`func_20F4`), `func_refresh_hud` (счёт/таймер/HUD), `func_beam_delay` (гонки с лучом). Выходы
цикла: пауза (`func_paused_check`, флаг `[1F10]`), конец волны (`func_round_end_sequence @0x6B10`),
переход уровня (`func_level_advance @0x5941`).

## Игровые переменные (var_*)

Ключевой вывод: **переменные геймплея живут в RAM-рабочей области (~0x1E00–0x2600, 0x0B00–0x0C30)
и в RAM-копии кодового окна 0x3E00–0x3F00** (игра исполняется из скопированного в RAM образа,
поэтому `debug_read_memory` по статическим адресам показывает ROM-дефолты, а снапшоты рантайма —
живые значения). В **статическом ROM-образе** эти адреса — код/константы, поэтому в RDB они
оформлены комментариями и связями, а не объектами `var_*` (объект `var_*` поверх покрытия кода
нарушил бы побайтовый round-trip и исказил бы образ).

| Переменная | Адрес (рантайм) | Как доказано | Достоверность |
|---|---|---|---|
| `var_player_x` | `0x2090` (пара `0x2090/0x2091`, `SHLD 2090`) | diff: `16→22` при движении вправо; Stage2 | высокая |
| `var_player_y` | `0x2091` | Stage2 (`func_init_player_state` сбрасывает `0x2091`) | высокая |
| `var_score` | BCD-цифры `0x3E33–0x3E38` → ASCII-буфер `0x3E2C–0x3E31` | `func_refresh_hud`: `LXI D,3E38 / CALL func_render_bcd_value` каждый кадр; буфер показал `000900` при POINTS=900; diff `0x3E2F: '0'→'9'` | высокая |
| `var_level_progress` | `0x1FFB` | `func_init_player_state`: `INR [1FFB]`; HUD `LDA 1FFB → VRAM 0x171C`; diff `0→2`; ZONES 000→001 | высокая |
| `var_enemies` | таблица объектов `~0x25E6+` (записи x/y/type) | diff `0x25E6`: нули → записи-тройки при спавне врагов | высокая |
| `var_bullets` | физический набор `0x0BAE–0x0C27` (`func_spawn_player_bullet @0x47EB`) | diff: плотные изменения записей скорости/координат снарядов/эффектов | средняя–высокая |
| `var_lives` | иконки кораблей, таблица `0x3FE5` (`func_draw_ship_icons`); счётчик `0x3ED1` (divmod-рендер) | код + HUD «LIVES»; за выборку жизней не терялись (5→5), точный аккумулятор не изолирован | средняя |

Прочие найденные ячейки HUD: `0x3ED1` (обратный отсчёт, diff `99→98`), `0x3EDD` (счётчик
арсенала/бомб, diff `10→4`, полка `func_bomb_shelf`), `0x3EF1` (6-разрядный divmod-счётчик),
`0x3E8F` (кадровый таймер, `func_add_timer/func_dec_timer`), `0x1E48/0x1E4B` (флаги; `0x1E4B`
использует `func_poll_rus_continue` для раннего выхода из мигания по РУС/огонь).

## Бонус-режим (подтверждён текстами в ROM)

Поиск печатных строк в образе подтвердил наличие **всех** TZ-обещанных бонус-текстов:

| Адрес | Текст | Контекст |
|---|---|---|
| `0x6CD0` | `BRAVERY BONUS` | список `0x6C78`, рендер `func_round_end_sequence @0x6B10` |
| `0x6CE8` | `LIVES BONUS` | там же |
| `0x6CFF/0x6D0E` | `PRESS FIRE TO` / `RESUME PLAY` | пауза/продолжение после раунда |
| `0x6D52/0x6D67/0x6D7E` | `CONGRATULATIONS!` / `YOU HAVE PROVEN YOUR` / `COMBAT ABILITIES` | награда за бонус |
| `0x6E5C` | `EXOLON BONUS SCREEN!` | список `0x6E23`, рендер `func_bonus_pointer_screen @0x6BE9` |
| `0x6E74` | `PRESS FIRE TO STOP POINTER` | stop-pointer мини-игра |
| `0x706E` | `GAME  OVER` | список `0x7066`, рендер `lbl_7048` |

Две ипостаси бонуса:
1. **Stop-pointer мини-игра** по концу волны: `func_round_end_sequence` рисует подсчёт
   `BRAVERY/LIVES BONUS` и счёт из `0x3E6E`, затем `func_bonus_pointer_screen` показывает
   «EXOLON BONUS SCREEN! / PRESS FIRE TO STOP POINTER» (указатель останавливается огнём).
2. **Скрытые пикапы** в игре: `func_bonus_award @0x557A` сверяет позицию игрока (`0x2090/0x2091`)
   со скрытыми слотами (`0x5627` верхний, `0x562A` нижний); при совпадении рендерит список
   `0x5003/0x5014` и **восстанавливает жизни (`[3ED1]←0x63=99`) или боезапас (`[3EDD]←0x0A`)**,
   5× вспышка видео (`CALL 4C8E`).

## Расхождения с TZ (важно)

| Утверждение TZ (стр. 170–196) | Факт по образу/MCP |
|---|---|
| Info-экран показывает `EXOLON L COPYRIGHT 1994` и адрес автора | Это на **title**-списке `0x7782` (текст `0x77EA`). Info-список `0x7890` — только подсказки управления |
| Title показывает `DLYA NACHALA IGRY NAVMITE RUS/LAT` | Эта строка на **info**-списке `0x7890` |
| Экраны 2 (заставка) и 3 (мигание звёзд) — разные | Это **один экран** (`lbl_menu_loop` + `func_title_stars_menu`): логотип+меню+звёзды+мелодия вместе |
| HUD `00000 POINTS` | Фактически `POINTS 000000` (метка слева, 6 цифр); полный HUD: `AMMO / GRENADES / POINTS / LIVES / ZONES` |
| — | **Исправлен misnomer:** `func_game_over_screen @0x6BE9` переименован в `func_bonus_pointer_screen` (рендерит бонус-экран `0x6E23`, а не game-over); настоящий GAME OVER — `0x7066` на `lbl_7048` |
| Ожидание «1»: «порт 03h→0FDh, порт 02h→бит 1» | Клавиша читается как **значение** `0FDh` в `[0197]` (не «бит 1»); строка матрицы выбирается стробом `0187h=0FBh` |

## RDB-изменения (Stage 5)

Только безопасные к побайтовому совпадению операции (метки, комментарии, связи, переименование
функции) — новые `function`/`data` объекты поверх покрытия кода не создавались:

- Метки экранов: `lbl_boot_entry @0x786B`, `lbl_boot_wait_rus @0x7886`, `lbl_title_init @0x762D`,
  `lbl_menu_loop @0x76B1`, `lbl_game_loop @0x6F6D`.
- Метки данных (списки отображения): `data_info_display_list @0x7890`,
  `data_title_display_list @0x7782`, `data_bonus_pointer_display_list @0x6E23`,
  `data_game_over_display_list @0x7066`.
- Переименование: `func_game_over_screen @0x6BE9` → **`func_bonus_pointer_screen`**.
- Комментарии с картой var_* и live-диффом: `func_render_bcd_value @0x3DF1`,
  `func_update_all_objects @0x48FF`, `func_round_end_sequence @0x6B10`,
  `func_bonus_pointer_screen @0x6BE9`, `lbl_7048`.
- Связи цепочки экранов: `0x786B→0x762D→0x76B1→0x6F01→0x6F6D`, `0x786B→0x7890`,
  `0x762D→0x7782`, `0x76B1→0x76FC`, `0x6B10→0x6BE9→0x6E23`, `0x7048→0x7066`.

## Round-trip

`./utils/analyze/run_pipeline.sh exolon --from export_asm --apply` → **6/6 stages, 0 failures**,
`roundtrip_verify = SUCCESS`. Побайтовая сверка пересобранного образа:

```
ORIG 92be64d153b4286d01d1ed4ac9c673987542b4629dfb0e0f3208ab73347c4962  exolon.rom
RT   92be64d153b4286d01d1ed4ac9c673987542b4629dfb0e0f3208ab73347c4962  roundtrip.bin
```

Предупреждения `syntax_check`/`symbolic_operand_lint`/`measure_sizes` в отчёте — **наследные**
(условные дизасм-предупреждения и отсутствующие размеры объектов), существовали до Stage 5;
совпадение SHA256 подтверждает, что правки RDB не изменили ни одного байта образа.

## Limitations / открытые вопросы

- Точный аккумулятор **жизней** не изолирован: за выборку игрок не погиб (`LIVES 5→5`), а
  счётчик-иконки (`0x3FE5`, `0x3ED1`) меняются только на смерти. Нужно снять loss-of-life
  отдельным прогоном (Stage 6/7).
- Точный адрес **накопления очков** (кто пишет `0x3E33–0x3E38` при убийстве) определён косвенно
  (через рендер + live-дифф буфера), прямой `STA` по immediate не найден — запись идёт по
  указателю; уточнить трассировкой `func_update_all_objects`.
- Точное соответствие HUD-подписей (`AMMO/GRENADES/...`) слотам `0x1701/0x1708/0x1717/0x171C`
  не разобрано (это область Stage 6 — вывод текста).
- Stop-pointer мини-игра (`func_bonus_pointer_screen`) подтверждена по текстам и вхождению в
  round-end, но её цикл движения/остановки указателя детально не разобран (Stage 6/7).
- Слияние «заставка + звёзды» в один экран означает, что нумерация «4 экранов» в TZ условна;
  физически разных display-списка три (`0x7890`, `0x7782`, + HUD/бонусные).
