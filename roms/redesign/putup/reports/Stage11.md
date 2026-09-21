# Stage 11 — Мелодия заставки: драйвер, партитуры, формат, вывод через порты

## Цель
По экспортированным из ROM данным дать полное описание мелодии заставки,
достаточное для однозначного преобразования в MIDI без эмулятора; зафиксировать
драйвер, партитуры, формат нот, алгоритм портового вывода в RDB и в
`reports/Stage11_music_spec.md`.

## ROM
- Файл: `src/putup.rom`, 17664 байта (0x4500), загрузка `0x0100` (`0x0100..0x45FF`).
- SHA256: `8486442efc390b15860ec7f69c32db93b0884908565fa11fec57d5c551b4e9a6`
- RDB: `src/putup.rdb` — 178 объектов после Stage 11 (было 167, +11).
- Точка входа ROM mapping: 0x0000; program entry `func_entry` = 0x0100.

## Метод (MCP-first, TZ Stage 0/11)
1. ROM загружен `debug_load_rom(org=0x100)`; запущен (`debug_run`), заставка играет
   музыку; остановлен (`debug_pause`) для снапшотов.
2. Сбор `debug_get_io_trace` (порты) и `debug_get_memory_access_map/log`.
3. `debug_analyze_code` + `debug_disassemble_range` — драйвер, обработчики портов,
   lookup периода. `debug_read_memory_range` — заголовок, потоки, таблица периодов.
4. Сверка с `docs/VECTOR_VERIFIED.md` / `docs/VECTOR_CPU_COMMANDS.md`; `asm/*` — только
   справочник. Скриптов пост-обработки MCP-данных нет.
5. Объекты/связи/комментарии — только через RDB API; `debug_save_rdb`.

---

## Findings

### F1 — Драйвер мелодии = func_music_tick @0x3858 (func_music_driver)
**Fact (evidence: disasm + ISR-трассировка Stage 5):** вызывается каждый кадр VBlank
из `func_vblank_isr` (RST 7 `0x0038`) через trampoline `CALL func_music_tick` в RAM
`0x03F8`. Ведёт счётчик `var_music_tick`(0x383A); на огибании тика (tick=DURATION=6)
инкрементирует индексы голосов `var_music_ptr_01/02/03`(0x383B/C/D) с оборотом по
LOOP=96, вызывает `func_music_process_voice`(0x3946) и `func_music_play_note_ch0`
(0x3BCA)/`_ch1`(0x3C7D). Выход — на KR580VI53 ch0/ch1/ch2.
**RDB:** объект `func_music_tick` @0x3858 (rename в `func_music_driver` невозможен —
занят адрес, псевдоним зафиксирован в комментарии), links: 0x3854,0x3BCA,0x3C7D,0x3E1A,0x421A.

### F2 — Партитуры и «таблица указателей»
**Fact (evidence: read + xref + init-disasm):** 15-байтовый заголовок
`data_music_scores` @ **0x3E1A** (`var_music_track_ptr` 0x3854 → сюда). Три потока
нот по 96 байт: `data_music_track_01` @ **0x3E29**, `_02` @ **0x3F29**, `_03` @ **0x4029**.
**Correction к модели плана:** отдельной DEFW-таблицы указателей на дорожки НЕТ.
Адреса дорожек = `var_music_track_base(0x3856=0x3E29) + N*0x100` (N=0,1,2); базы
потоков `0x383F/0x3841/0x3843` засевает `func_music_init` @0x3D4E шагом `DAD B`
(B=0x0100). RAM-указатели чтения: индексы `0x383B/C/D` + базы `0x383F/41/43`.
**RDB:** созданы `data_music_scores`, `data_music_track_01/02/03`,
`var_music_ptr_01/02/03`, `var_music_stream_base_01/02/03`.

### F3 — Формат события дорожки
**Fact (evidence: disasm func_music_process_voice 0x39D3/0x3A32/0x3A95 + read):**
Байт потока = КОД НОТЫ. `0x00` = REST; `0x01..0x7F` = NOTE с высотой
`data_music_period_table[BASE(6)+code]`; длительность фиксирована `DURATION=6` тиков.
Бит7 (`>=0x80`, только голос 2) = расширенная нота через `func_music_set_note_params`
→ 8-байтовый блок `data_note_param_table_43F9[((code&0x7F)-1)*8]`. Явного терминатора
нет — петля по 96 шагов.
**Fact:** во всех трёх потоках заставки бит7 НЕ установлен (макс коды 0x39/0x30/0x24),
расширенная ветка мелодией не задействуется.
**Примеры:** `track_01[0]=48`→idx54→period169→MIDI78(F#5); `track_01[1]=0`→REST;
`track_03[0]=12`→idx18→period1352→MIDI42(F#2).

### F4 — Закон высоты и таблица периодов
**Fact (evidence: read 0x421A 192 байт + disasm 0x3A11-0x3A1C):** 96 слов LE,
`period[idx]=round(3822/2^(idx/12))` (равномерная темперация, /2 каждые 12 idx).
Lookup: `A=code; ADD base(6); ADD A (×2); HL=421Ah+BC; [HL]=period` (func_music_process_voice).
**Fact (evidence: повторная трассировка 0x020E):** `func_snd_calc_period` возвращает
**12×** значение (DAD H→2v, DAD H→4v, DAD D→6v, DAD H→12v). → `count=12*period`;
`freq = f_VI53/(12*period)`. **MIDI = idx+24 = code+30.**
**Validation:** idx36 period478 → 1.5e6/(12·478)=261.5 Гц=C4=MIDI60; idx45 period284
→440.1 Гц=A4 ⇒ f_VI53=1.5 МГц и сдвиг +24 подтверждены.
**Correction:** прежняя рабочая гипотеза «6× / MIDI=idx+36» опровергнута; верно 12×/+24
(комментарий RDB `func_snd_calc_period` уже содержал 12× — согласовано).

### F5 — Алгоритм вывода через порты (чип = KR580VI53)
**Fact (evidence: disasm start_track 0x3DCD + out-handlers + io_trace):** AY-3-8910 НЕ
используется. Инициализация: `OUT 08h` слова `36h/76h/B6h` (mode-3 square, LSB/MSB,
binary) для ch0/ch1/ch2. Нота: HL=период канала (0x31A/0x31C/0x31E), `CALL 0x020E`
(→12×), `OUT lo; OUT hi` в порт **0Bh(ch0)/0Ah(ch1)/09h(ch2)**. REST глушит канал
(gate op8/9/10 заголовка).
**Evidence io_trace:** `OUT 0Bh←64,←05`, `OUT 0Ah←64,←08`. Порт 09h в короткий трейс
не попал (бас часто в паузе) — доказан дизассемблированием `op4`@0x24E (два `OUT 09h`).

### F6 — Темп / тайминг
**Fact:** DURATION=6 тиков/шаг, LOOP=96 шагов/голос (заголовок). **Emulator Behavior:**
кадр VBlank ≈50.08 Гц (312 строк) ⇒ тик 19.97 мс, шаг ≈119.8 мс, цикл ≈11.50 с.
Для MIDI: шаг=1/16 ⇒ ♩≈125 BPM. Точный музыкальный темп железом не гарантирован —
помечено Emulator Behavior.

### F7 — Вибрато
**Inference (evidence: disasm play_note_ch0 0x3BCA + read 0x445D):** по-тиковая
поправка периода из `data_music_vibrato_table` @0x445D (stride 20, row=scores[+0x0D]=5),
значения 0..3 (≈десятки центов). Это НЕ частотная таблица. Для базового MIDI опускаемо.
**RDB:** переименован 0x445D `data_note_freq_table_ch0` → `data_music_vibrato_table`.

---

## Обновление RDB
- Добавлено объектов: **11** (data_music_scores, data_music_track_01/02/03,
  data_music_period_table, var_music_ptr_01/02/03, var_music_stream_base_01/02/03);
  переименован 1 (0x445D → data_music_vibrato_table). Всего **178** (было 167).
- Добавлено связей: **~27** — driver↔scores↔period_table↔tracks↔ptrs;
  process_voice→(bases/ptrs/period_table/buf); init→stream_bases; start_track/op→ports.
- Комментарии с форматом событий — на всех новых объектах + func_music_tick/
  process_voice/play_note_ch0/data_voice_param_buf/data_note_param_table_43F9.
- `debug_save_rdb` → **success**, `debug_get_rdb_info`: dirty=false, object_count=178,
  exists_on_disk=true.

## Критерий приёмки (п.7)
**Выполнен.** `reports/Stage11_music_spec.md` + `asm/` дают детерминированное
восстановление: `MIDI=code+30`, длительность=6 тиков, 3 дорожки по 96 шагов, темп
119.8 мс/шаг, петля 96. Эмулятор не требуется.

**Подтверждено практикой (2026-09-21):** конвертер `tools/putup2midi.py` читает
потоки из `src/putup.rom` по адресам §2, сверяет их с дампами §10 и генерирует
`putup_title.mid` (SMF format 1, 4 трека, PPQ=192, шаг=48 тиков, ♩≈125.2 BPM):
ch0=84 ноты (66..87), ch1=87 (61..78), ch2=47 (42..66) — диапазоны точно
соответствуют §5.3, длительность цикла 4608 тиков ≈ 11.5 с (§6).

## Unknowns / ограничения
- Точная семантика gate/op6..op13 (маршрутизация оп-кодов) на высоту не влияет и
  до конца не расшифрована — помечено как внутренняя маршрутизация.
- Точный `f_VI53` (1497600 vs 1500000) — из документации; абсолютные Гц могут
  отличаться на доли %. A4=440 при 1.5 МГц (Inference-совпадение).
- Темп/кадр = Emulator Behavior (см. F6).
- Порт 09h не пойман живым io_trace (бас в паузе); подтверждён только дизассемблированием.
- Полный размер `data_music_vibrato_table` не определён (size=-1); для заставки
  используется только row=5.
- Огибащаяная/громкостная экспрессия в заставке отсутствует (фикс. длина, фикс. gate).
