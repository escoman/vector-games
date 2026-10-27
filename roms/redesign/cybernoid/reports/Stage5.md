# Stage 5. Главный цикл и экраны (cyberno.rom) — обзор

## Постановка (TZ §Stage 5)

Установить маршрут `boot → меню (1.START / 2.LOAD / 3.PASS) → игра` и
**момент(ы) произношения голосовых фраз** (заставка? инфо? смерть?). Найти
**функцию перехода между экранами**. Игровые переменные — только поверху
(`var_score`, `var_lives`, `var_stage`); парольную систему (2.LOAD / 3.PASS) —
как данные (Stage 8). Отчёт **обзорный**, без подробного матчера спрайтов.

## Метод

Только live через `vector-debugger` MCP. `debug_load_rom` (сброс состояния),
`debug_get_screen_snapshot` по состояниям (boot/заставка → меню → игра),
клавиши `debug_press_key`/`debug_type_key` (SPACE, «1»). Точки останова на
входе речи (exec 0x0663) с чтением `ret`/caller и HL (указатель фразы).
`debug_disassemble_range` по exec-адресам bootstrap/меню/пути START.
`debug_get_memory_access_map` для локализации горячего игрового блока.
`debug_get_call_graph` — снят, но непригоден (загрязнён data-as-code, см.
ограничения). Писали в RDB только MCP-инструментами.

## Факты

### Маршрут (живой)
`reset → 0x0100 bootstrap` (DI; `LXI SP`; патч low-RAM векторов
`0x0000=JMP 0100`, `0x0038=JMP 0E00`) `→ CALL 0x0573` (речь заставки,
**момент #1**) `→ ` тремплины `→ CALL 0x147C` (иниц. игровых таблиц) `→
CALL 0x11D8` (рендер экранного скрипта) `→` **заставка** «CYBERNOID / THE FATAL
RETURN / DIL SOFT MINSK / HI SCORE / BY NEWSON» `→` по клавише —
**меню** «1.START / 2.LOAD / 3.PASS» `→` **диспетчер**.

### Функция перехода между экранами — `func_menu_dispatcher` @ exec 0x018B
Цикл: `CALL 0x0F15` (читалка клавиш) `→ ORA A → JZ 0x018B` (ждать клавишу),
затем таблица кодов:
| код | CPI | цель JZ | экран |
|-----|-----|---------|-------|
| 0x11 | `CPI 11` | `JZ 0x02F6` | 1.START |
| 0x12 | `CPI 12` | `JZ 0x0FA5` | 2.LOAD |
| 0x13 | `CPI 13` | `JZ 0x020A` | 3.PASS |
иначе `JMP 0x018B`. Расположен в exec-области bootstrap сразу после рендера
заставки.

### Читалка клавиш — `func_get_key` @ exec 0x0F15
`LDA 0x0E47` (залatch. клавиша) `→ ORA A → RZ` (нет — A=0) `→` иначе
`XRA A; STA 0x0E47` (сброс latch) `→ RET` с кодом в A. Лatch — RAM-переменная
`var_key_latch` @ **0x0E47** (0 = нет клавиши).

### Вход в игру — путь START
`0x02F6` (`label_screen_start`) ведёт на exec **0x01A4**: `CALL 0xDD0`
(палитра/beam) `→ LXI H,0EAE; CALL 0x0F45` (`func_video_frame_out` — вывод
экрана/HUD) `→ EI; MVI A,80; HLT; DCR A; JNZ` (выдержка ~128 кадров на HLT)
`→ JMP 0x1000` — **главный цикл игры**.

### Главный цикл — `func_game_main` @ exec 0x1000
Горячий блок по `memory_access_map` во время игры: **0x1700** (fetch ≈6.77M —
внутренний цикл/растер), 0x1100 (≈2.55M), 0x1400/0x1500/0x1000. Игровой код в
RAM `0x1000..0x2500` после распаковки. Подробный разбор цикла и спрайтов —
вне scope Stage 5.

### Моменты речи (live-свидетели, BP на exec 0x0663)
1. **Заставка (момент #1).** bootstrap `CALL 0x0573`; тело: `CALL 0xDD0` →
   `LXI H,0600` → `CALL 0x0660` (NOP-sled → `DI`-триггер на 0x0663) →
   произносит буфер 0x0600 «**GRU DIL SOFT PREDLAGAET NOWEJSIE…**» (ГРУ Дил
   Софт предлагает…). Возврат 0x057C, caller — bootstrap (0x0118).
2. **Меню (момент #2).** `func_text_walk_speak` @0x0582 (обходчик строки:
   `MOV A,M; ORA A; RZ; INX H; CALL 0x058D; INR B; JMP 0x0582`) идёт по
   экранным скриптам 0x0E72/0x0E7B/0x0E84; посимвольный диспетчер **0x058D**
   на каждом символе вызывает речь (`CALL 0x0660 @ 0x05A6`, возврат 0x05A9) —
   озвучка цифр меню `ODIN/DWA/TRI` (таблица 0x09C3). HL при ловле = 0x05FE.

> Примечание: прежняя Stage-3 гипотеза о 0x058D («frame-тайминг, OUT-сигнатура
> ложна») **снята** — CALL внутрь области 0x0660 это обращение к движку речи.

### Игровые переменные (поверхностно)
HUD на экране игры: `LEVEL:START`, `FIRE:BOUNCE 5`, `SCORE:00`, `LIFE:6`,
`STAGE:0`. Вывод — через `func_video_frame_out`@0x0F45 (путь START:
`LXI H,0EAE`). **Точные адреса `var_score`/`var_lives`/`var_stage` не
пинились** (TZ: только поверху; разбор рендера текста/экрана → Stage 6).
Подтверждённая переменная цикла: `var_key_latch`@0x0E47.

### Экраны 2.LOAD / 3.PASS (как данные)
`label_screen_load`@0x0FA5, `label_screen_pass`@0x020A — цели диспетчера по
кодам 0x12/0x13. Парольная система (проходы) — **Stage 8**, здесь только
маршрутные ярлыки.

## Итог в RDB
- `func_0100`: `route_stage5` (полный маршрут) + link → 0x0573.
- `func_menu_dispatcher` @0x018B (бывш. `lbl_018b`): комментарий (CPI-таблица),
  links → 0x0F15, 0x02F6, 0x0FA5, 0x020A.
- `func_get_key` @0x0F15: комментарий + `key_latch_var`; link → 0x0E47.
- `var_key_latch` @0x0E47 (новая Variable): RAM-latch клавиши.
- `func_game_main` @0x1000 (новая Function): комментарий + `hud_vars_note`,
  `hot_block`.
- `lbl_01a4`: link → 0x1000 (START→игра).
- `func_title_speech_caller` @0x0573 (бывш. `func_0573`): `CALL 0xDD0`,
  `LXI H,0600`, `CALL 0x0660`; links → 0x0DD0, 0x0663.
- `func_text_walk_speak` @0x0582 (бывш. `func_0582`): link → 0x058D.
- `func_058d`: комментарий исправлен (посимвольный диспетчер речи меню);
  link → 0x0663.
- `label_screen_start`@0x02F6, `label_screen_load`@0x0FA5
  (`screen_role`), `label_screen_pass`@0x020A (`screen_role`).
Сохранено `debug_save_rdb`; контрольный grep `.rdb` — имена/комментарии/
свойства/links на диске подтверждены.

## Ограничения и открытые вопросы
- **Call graph непригоден:** `debug_get_call_graph` загрязнён data-as-code
  (0x0038 «вызывается» 793×, цели 0xDCDC/0xD0E8/0xC0FC — данные). Главный
  цикл локализован через `memory_access_map` + живой дамп, не через граф.
- **Распаковка игрового кода (0x1000..0x2500)** и стабов (0x0E00, −0x59 речи) —
  механизм архива, Stage 7.
- **`var_score`/`var_lives`/`var_stage`** — адреса не закреплены (обзор);
  рендер HUD/текста экрана → Stage 6.
- **Доп. моменты речи** (смерть/info/конец уровня) не исключены, но в этом
  прогоне не ловлены; подтверждены #1 заставка и #2 меню. Полное покрытие
  фраз — за Stage 6/7 (strings_scan-кандидаты: `THE%FEDERATION%WILL%REWARD`,
  `PLEASE%ENTER%YOUR%NAME`, `CONGRATULATIONS%%`).
- **2.LOAD/3.PASS** — только маршруты; пароли как данные → Stage 8.
