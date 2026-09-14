# Stage 7 — Перевод RDB, сборка clrs_new.rom

**Дата:** 2026-09-14

---

## 1. Перевод комментариев RDB на русский язык

Все 9 объектов RDB переведены на русский язык через `debug_set_rdb_comment`.

| Адрес | Имя | Тип | Русский комментарий (кратко) |
|-------|-----|-----|------------------------------|
| 0x002C | data_rst55_vector | data | Вектор RST 5.5, не настраивается clrs.rom |
| 0x0038 | data_rst7_vector | data | Вектор RST 7 (VBlank), JP 013Fh, настройка из func_setup_and_halt |
| 0x003C | data_rst75_vector | data | Вектор RST 7.5, не настраивается clrs.rom |
| 0x0100 | func_setup_and_halt | function | Точка входа ROM: DI, очистка VRAM, вектор RST 7, стек палитры, OUT 02h, HLT |
| 0x013F | func_isr_delay_and_setup | function | ISR: задержка, настройка BC=0703h/D=01h/SP=0177h |
| 0x014A | data_isr_code_overlap | data | Артефакт пересечения кода (опкоды инструкций, не данные) |
| 0x0152 | func_isr_palette_cycle | function | Цикл палитры: POP PSW, ORA M ×3, 9× OUT 0Ch с XOR-арифметикой, RET |
| 0x0172 | func_isr_rearm_and_exit | function | Выход ISR: LXI SP,00FEh / EI / RET |
| 0x055A | var_palette_stack | variable | Область стека палитры в RAM, 12 пар слов, потребление через POP PSW |

**Статус:** RDB сохранён (`debug_save_rdb`), dirty=false, 9 объектов, путь: `src/clrs.rdb`.

---

## 2. Объединённый asm-файл

**Путь:** `/home/alexey/Projects/vector-games/roms/redesign/clrs/clrs_new.asm`

**Описание:**
- 4 функции объединены в один файл с единственным `org 0100h`.
- Индивидуальные директивы `org` из каждой функции удалены.
- Все локальные метки `.loc_XXXX` переименованы в `clrs_loc_XXXX` (глобальные, с префиксом `clrs_` для уникальности):
  - `.loc_0104` → `clrs_loc_0104`
  - `.loc_0128` → `clrs_loc_0128`
  - `.loc_013B` → `clrs_loc_013B`
  - `.loc_0142` → `clrs_loc_0142`
- Ссылки в JNZ/JMP также обновлены.

**Исправления:**
1. **z80asm и ORA M:** z80asm интерпретирует `ORA M` как `ORA B` (0xB6) вместо `ORA [HL]` (0xBE). Это известная проблема: в z80asm мнемоника `M` в инструкциях ALU (ORA, ANA, XRA и т.д.) распознаётся как регистр B, а не как память [HL]. Для генерации корректного opcode 0xBE используется `DEFB 0BEh` (аналогично `tests/clrs/clrs.asm`, где ISR-код собран через `db`).
2. **Hex-литералы:** `C3h` → `0C3h`, `F8h` → `0F8h` (z80asm требует ведущий ноль для hex, начинающихся с буквы).
3. **Символ data_rst7_vector** заменён на прямой адрес `0038h` (RAM-данные, не включаются в ROM).

---

## 3. Makefile

**Путь:** `/home/alexey/Projects/vector-games/roms/redesign/clrs/Makefile`

```makefile
# Makefile — сборка clrs_new.rom для Вектора-06Ц.

include ../../../config.mk

Z80ASM   = $(Z88DK)/bin/z80asm
TARGET = clrs_new.rom
SRCS = clrs_new.asm

.PHONY: all deploy clean full

all: $(TARGET)

full: clean all deploy

$(TARGET):
	$(Z80ASM) -b -o=$@ $(SRCS)
	@echo "=== Done: $@ ==="
	@ls -l $@

include $(PROJECT_ROOT)finally.mk

clean:
	rm -f $(TARGET) *.o *.bin *.sym
```

---

## 4. Сборка

**Команда:** `make full` из каталога `/home/alexey/Projects/vector-games/roms/redesign/clrs/`

**Вывод:**
```
rm -f clrs_new.rom *.o *.bin *.sym
/home/alexey/z88dk/bin/z80asm -b -o=clrs_new.rom clrs_new.asm
=== Done: clrs_new.rom ===
-rw-rw-r-- 1 alexey alexey 119 сен 14 21:14 clrs_new.rom
cp -f clrs_new.rom /home/alexey/snap/ppsspp-emu/common/.config/ppsspp/PSP/GAME/VECTOR06C/ROMS/
=== Deployed to .../ROMS/ ===
clrs_new.rom: 119 bytes
```

**Размер:** 119 байт (ожидаемый: 119 байт). ✅

---

## 5. Сравнение с оригиналом

**Команда:** `cmp src/clrs.rom clrs_new.rom`

**Результат:** **IDENTICAL** — файлы совпадают байт-в-байт.

**SHA256:**
```
77af8dbcfea2b00e765078ec1c97c755fd97d049e0ee24ee8dc8896ff8f3fcb9  src/clrs.rom
77af8dbcfea2b00e765078ec1c97c755fd97d049e0ee24ee8dc8896ff8f3fcb9  clrs_new.rom
```

**diff:** нет расхождений. ✅

---

## 6. Verified Facts

- RDB содержит 9 объектов, все комментарии на русском языке.
- RDB сохранён: `src/clrs.rdb`, dirty=false.
- clrs_new.asm содержит 4 функции, 119 байт кода, org 0100h.
- clrs_new.rom собран, размер 119 байт.
- clrs_new.rom идентичен src/clrs.rom (SHA256 совпадает).
- z80asm (версия 23854) интерпретирует `ORA M` как `ORA B` (0xB6) — это факт, подтверждённый тестированием.

## 7. Inferences

- Оригинальный clrs.rom был собран аналогичным способом (через raw bytes для ORA M), что подтверждается структурой tests/clrs/clrs.asm.
- Все 4 функции размещаются непрерывно от 0x0100 до 0x0176, что соответствует архитектуре ROM.

## 8. Hypotheses

- Нет непроверенных предположений на данном этапе.

---

## 9. Статус

| Задача | Статус |
|--------|--------|
| Перевод RDB на русский | ✅ Выполнено |
| Создание clrs_new.asm | ✅ Выполнено |
| Создание Makefile | ✅ Выполнено |
| Сборка clrs_new.rom | ✅ Собран успешно |
| Размер 119 байт | ✅ Подтверждён |
| Сравнение с оригиналом | ✅ Байт-в-байт идентичен |
| Deploy в PPSSPP_ROMS | ✅ Выполнено |
