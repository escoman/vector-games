# Makefile — roms/games/putup: Putup с распакованными данными.
#
# PUTUP_NEW.ROM (в корне проекта) = адресно-точная реконструкция оригинала
# (0x0100..0x45FF, asm-ветка Stage 12 redesign/putup) + распакованный блок глифов
# data_glyph_block_unpacked (8192 Б) по адресу GLYPH_BASE (итог этапа B:
# 0x5600 — минует текстовый back-буфер 0x5000..0x53FF; исторический A — 0x6000).
#
# Компоновка: tools/gen_layout.py -> asm/putup_unpacked.asm (гэпы — inline DEFB).
# Все данные — побайтовыми DEFB в asm-файлах, bin-артефактов нет.
# Режим 8080: -m=8080_strict. make verify — побайтовая сверка кодовой зоны
# с оригиналом (отличия — только заглушки удалённой распаковки).

include ../../../config.mk

ASMFLAGS  = -b -m=8080_strict -s
TARGET    = PUTUP_NEW.ROM
ORIG      = ../../redesign/putup/src/putup.rom
FULLBIN   = build_full.bin
MASTER    = putup_unpacked.asm
GEN       = tools/gen_layout.py
IMGADDR   = 0x100
GLYPH_BASE ?= 0x5600         # одна константа переноса: make GLYPH_BASE=0x6000 (A)
GLYPH_SIZE = 8192
KEEP_DEAD  ?= 0              # 1 = Stage A: мёртвые распаковщики остаются в сборке

.PHONY: all layout clean full deploy verify

all: $(TARGET)

# Перегенерировать компоновку (мастер + gap-бинари) из asm/ и оригинала.
layout:
	@GLYPH_BASE=$(GLYPH_BASE) KEEP_DEAD=$(KEEP_DEAD) python3 $(GEN)

$(TARGET): $(GEN) $(ORIG) $(wildcard asm/*.asm)
	@GLYPH_BASE=$(GLYPH_BASE) KEEP_DEAD=$(KEEP_DEAD) python3 $(GEN)
	@cd asm && $(Z80ASM) $(ASMFLAGS) -o=../$(FULLBIN) $(MASTER)
	@GLYPH_BASE=$(GLYPH_BASE) GLYPH_SIZE=$(GLYPH_SIZE) python3 -c "import os; gb=int(os.environ['GLYPH_BASE'],0); gs=int(os.environ['GLYPH_SIZE']); d=open('$(FULLBIN)','rb').read(); open('$(TARGET)','wb').write(d[256:gb+gs])"
	@rm -f $(FULLBIN) asm/*.o asm/*.sym
	@echo "=== Done: $@ ($$(stat -c%s $@) bytes) ==="

# Кодовая зона 0x0100..0x45FF = оригинал с точностью до: заглушек в
# func_main_init (3 NOP на месте CALL func_load_glyph_block, 0x0B83; 34 NOP
# выжженного копира спрайтов, 0x0B86) и выжженных нулями dead-диапазонов
# (этап B, tools/dead_ranges.json их генератор пишет).
verify: $(TARGET)
	@KEEP_DEAD=$(KEEP_DEAD) python3 tools/verify_image.py

full: clean all deploy

clean:
	rm -f $(TARGET) $(FULLBIN) asm/*.o asm/*.sym asm/*.err

# Финализация по стандарту проекта: цели deploy/full.
include $(PROJECT_ROOT)finally.mk
