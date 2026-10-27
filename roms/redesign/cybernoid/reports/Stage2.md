# Stage 2. Подробное исследование функций (cyberno.rom)

> Ручной семантический Stage. Знание фиксируется в **RDB** (`src/cyberno.rdb`,
> только `debug_save_rdb`); отчёт — обзор со ссылками на объекты, не свалка.
> Приоритет по ТЗ — цепочка **генератора голоса из текста**.

## Цель

Дать функциям осмысленные имена/комментарии/связи; глубоко разобрать цепочку,
ведущую к речи; остальное — до уровня «назначение угадано, комментарий стоит».

## Метод (новые возможности MCP — задействованы)

Один живой сеанс: `debug_load_rom` → `debug_run` (~3 с, заставка+голос) →
`debug_pause`. Далее `debug_get_io_trace` (поток порта), `debug_find_bytecode_sequence`
(поиск опкода `OUT 00h` = `D3 00`), `debug_disassemble_range`, и code-intelligence:
`debug_get_function_context`, `debug_get_xrefs`, `debug_get_function`. Правки RDB:
`debug_create_function` / `debug_update_rdb_object` / `debug_set_rdb_comment` /
`debug_add_rdb_link` → `debug_save_rdb`.

## Ключевые выводы (голос — ядро интереса)

1. **Механизм речи количественно подтверждён.** `io_trace`: непрерывный поток
   `OUT 00h` со значениями строго `00h/01h`, интервал **ровно 40 T-состояний**
   (~37 кГц). Это 1-бит **PDM/PWM** на TapeOut, не AY/VI53.
2. **Цепочка текст→речь восстановлена** (call-graph; после ревизии — истинные abs):
   `func_speak_start`(0x06BC: DI→CALL→RET) → `func_speak_walker`(0x06C2) →
   `func_speak_phoneme`(0x071C) → `func_speak_emit_plane`(0x073F, `OUT 00h` на 0x075D),
   паузы — `func_voice_delay`(0x0715). (В первом проходе адреса каскада были
   смещены на 0x15…0x59 из-за рассинхрона линейного дампа — см. «Ревизия» ниже.)
3. **`func_speak_start` делает `DI`** — прерывания выключаются на всё время
   произношения (бит-бэнг с фиксированным периодом нельзя рвать). Это ответ на
   вопрос «тикер речи» (ТЗ Stage 4): речь — **busy-loop с выключенными IRQ**, не VBlank.
4. **Текст-зависимость доказана:** `func_speak_walker` идёт по строке посимвольно
   (`ORA A/RZ` — конец), фильтрует диапазон `'A'..'Z'`, спец-буквы `'C'/'H'/'''`,
   ремап `ADI 1Ah`, вставляет паузы по `'.',' ,',' '` (`DE=0x8000/0x4000` + delay).
   То есть вход движка — **translit-строка**; в ROM она лежит буквально:
   `str_speak_demo@0x065A` = «GRU DIL SOFT PREDLAGAET NOWEJSIE PROGRAMMY K WEKTOR NOL…».
5. **Декодирование фонемы:** двойная индексация таблиц (константы-адреса
   `0x06F7`, `0x076C`), из 2-байтной единицы: мл. ниббл — длительность, bit7 — флаг,
   bits4–6 — номер бита бит-плоскости. Внутренний цикл читает плоскости (база `DE=0x082E`).

### Ревизия проход-2 (важно, прочесть перед Stage 3)

Первый проход Stage 2 посеял часть функций из линейного дампа, который расходится с
границами кода на данных. Истинные abs-адреса (`debug_disassemble_range`/
`debug_read_memory_range`/`debug_find_bytecode_sequence` — три канала сверены между
собой и с файлом ROM, расхождения «между инструментами» нет) показали:

- адреса `0x0663 / 0x0669 / 0x06C3` из прошлой схемы попали **внутрь ASCII-фразы**
  `str_speak_demo` (0x065A..0x06B8) — это не код; `0x06BC` — не delay, а **вход речи**
  (`DI; CALL 0x0669; NOP; RET`). Функции переадресованы: walker `0x06C2..0x071B`,
  декодер `0x071C..0x073B`, эмиттер `0x073F..0x0786`, delay `0x0715`;
- `func_frame_out_128@0x0E00` и `func_frame_out_512@0x1011` — фантомы: 0x0E00 —
  данные/строки, 0x1011 — середина вычислителя адресов экрана. Настоящий
  видеовывод — **`func_video_frame_out@0x0F45`** (он и писал `OUT 0C/0D/0E/0F`);
  ВИ53 — **`func_vi53_timer_poll@0x0F9A`** (`OUT 08/09`);
- **аномалия ветвлений речи**: цели `CALL 0x0669`, `JMP 0x066B`, `JM/JP 0x069B`,
  `JZ 0x06B3`, `JMP JNC 0x06FD`, `CALL 0x06BC` из delay-цикла прилетают в область
  строки/входа (слайд 1-байтовыми NOP/MOV). Явного смысла не установлено —
  **Stage 7 решает трейсингом** (не спекулировать);
- `func_263d` (range 0x263D..0x77FF) → **`data_blob_263d`** (packer-архив);
  кластер `0x78xx` — за концом ROM (пустая RAM, дампы = NOP) → `label_phantom_78xx`;
  `func_0dd0` — MOV-шум данных → `label_blob_0dd0`.

## Что в RDB (ссылки)

- Цепочка голоса (переписана, abs): `str_speak_demo@0x065A` (String),
  `func_speak_start@0x06BC`, `func_speak_walker@0x06C2`, `func_speak_phoneme@0x071C`,
  `func_speak_emit_plane@0x073F`, `func_voice_delay@0x0715`; `0x0660/0x0663/0x0669/0x06C3`
  — деградированы в `label_*` с пояснением.
- Видео/таймер: `func_video_frame_out@0x0F45`, `func_vi53_timer_poll@0x0F9A`,
  `label_scr512_addr_calc@0x1011` (вычислитель адреса 512-буфера, не вход функции),
  `label_blob_0e00`.
- Загрузчик: `func_0100` (bootstrap: SP=DCEE, патч low-RAM векторов, relocation
  224B-стаба `0x0159→0xEE00`, `JMP EE00`), `func_01be`/`func_01c4` — хвосты
  релокационного блока (`JMP EE1A`, курсоры EDE2/EDE3/EDE6/EDE9).
- Игровые узлы: `func_0255` (frame-цикл), `func_114d` (клавиатурный диспетчер,
  CPI 93h…A9h, 14 call-in), `func_0f45`-семейство, `func_0b1e` (big-видео-модуль).
- Данные голоса: `var_voice_period@0x0733` (каденс бита), `var_voice_bufptr@0x0734`
  (курсор сэмпла), `data_pdm_planes@0x082E` (бит-плоскости; **кандидат**, размер не зафиксирован).
- Low-page RST-векторы `label_0008…0038` (добавлены на Stage 1) — сохранены.
- Массовая сигнатурная ценз-таблица функций (размер/call-in/OUT/IN-порты/IMM/RAM):
  `.scratch/asmtest/census.py` → `census.csv` — инструмент последующих проходов.

## Runtime-протокол, порты и вотчпоинты → в RDB (проход-3, новые MCP-инструменты)

Проверил живые возможности `v06c-mcp 0.6.7` (apiVersion 5) и сохранил результат
в RDB через `debug_add_rdb_link` / `debug_set_rdb_property` (не редактируя файл вручную):

- **Заморозка на входе речи.** `debug_load_rom` → `debug_set_breakpoint(0x06BC)` → CPU
  остановлен на `func_speak_start`; `debug_get_stack`/`debug_get_state` подтвердили,
  что речь запускается из распакованной RAM (blk `0xEE00`, fetch≈1.26M).
- **PDM-протокол (порт 0x00).** `debug_get_io_trace`: OUT в порт `0x00` с ровно
  **40 T-состояний** период (~37 кГц), значения строго `0x00/0x01`. Записано в
  `func_speak_emit_plane@0x073F`: `io_port_out`, `io_protocol=PDM`,
  `pdm_period_tstates=40`, `bitplane_tables`.
- **Видео-битбэнг (0x02/0x0C–0x0F).** `debug_get_raster_events` + io_trace:
  палитрные writes в середине кадра. Записано в `func_video_frame_out@0x0F45`:
  `io_ports`, `video_rows`, `watchpoint_vram` (blk `0xDC00`: W≈202k / R≈178k).
- **Вотчпоинты памяти** (`debug_get_memory_access_map`) → свойства у владельцев:
  `func_01be`: `watchpoint_archive_cursor` (blk `0xED00` R≈102k/W≈49k),
  `watchpoint_exec_ram` (blk `0xEE00`).
- **Граф вызовов речи как RDB-ссылки** (статические xrefs по каскаду пусты —
  цели CALL «стекают» в строку): навел явные `debug_add_rdb_link`:
  `str_speak_demo→walker`, `start→walker`, `walker→{phoneme,delay}`,
  `phoneme→{emit,tbl 0x06F7,tbl 0x076C}`, `emit→{0x075D,0x082E,0x0935}`,
  `delay→start` (re-entry), `video→0x10C1`.
- **Ревизия 0x0DD0.** `debug_get_raster_events` показал PC `0x0DDC/0x0DDE/0x0DE0` →
  OUT в палитру на строках 59–65, а mem-map — blk `0x0D00` fetch≈228k. Значит
  `label_blob_0DD0` — **не blob, а racing-the-beam код**. Зафиксировано свойствами
  `runtime_role`/`io_ports`/`watchpoint_block` + комментарием; переименование —
  после CFG-ревизии в Stage 3.

Итог по RDB: 41 объект со ссылками, 9 объектов с содержательными (не seed)
свойствами; `debug_save_rdb` → round-trip проверен на диске.

## Open questions / ограничения

- **Точная раскладка таблиц голоса** (`0x06F7/0x076C/0x082E`) частично перекрывается с
  кодом emit-цикла — классическая неоднозначность data/code. Вынесено в **Stage 7**
  (обязательный, «генератор голоса»).
- **Кто вызывает вход речи** — внешних CALL на 0x06BC в ROM-области нет (только
  внутренние 0x070C/0x0718/0x0779); значит вызов идёт из распакованной RAM-области →
  **Stage 3/5** (coverage после выполнения).
- Из ~125 посеянных функций подписано 16 (все ключевые + ревизия каскада); остальные
  ~100 не размечены намеренно: их census-сигнатуры получены из рассинхроненного
  линейного дампа и без CFG-выравнивания недостоверны. Массовая разметка — после
  Stage 3 (границ) либо точечно по call_in>=3 из `census.csv`.
- Методическая ловушка: `debug_disassemble_image`/`debug_analyze_code` по линейному
  диапазону сеют ложные функции на данных — всегда сверять старт функции через
   `debug_disassemble_range` с выравниванием, а IO-сигнатуры — с картой портов `lib/v06.h`
  (0=КС ПИА, 2=PB, 3=PA, 8/9=ВИ53, 14/15=AY DAT/SEL).
- Готча инструмента: `debug_get_function` показывает параллельный **символ отладчика**
  (может отставать), а источник истины для экспорта — **объект RDB**
  (`debug_get_rdb_object` подтвердил `func_speak_phoneme`).
