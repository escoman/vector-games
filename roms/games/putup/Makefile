# Makefile — roms/games/putup: Putup с распакованными данными.
#
# PUTUP_NEW.ROM (в корне проекта) = адресно-точная реконструкция оригинала
# (0x0100..0x45FF, asm-ветка Stage 12 redesign/putup) + распакованный блок глифов
# data_glyph_block_unpacked (8192 Б) по адресу GLYPH_BASE (итог Фазы 1:
# 0x4600 — вплотную к концу кода; текстовый back-буфер перенесён на 0x6600,
# дыра 0x4600..0x55FF схлопнута; копир спрайтов возвращён).
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
COMPACT  ?= 0               # 1 = Фаза 2: вырез мёртвых дыр + relocation (не byte-exact выше 0x2761)
ifeq ($(strip $(COMPACT)),0)
  DEFAULT_GLYPH_BASE = 0x4600   # Фаза 1: блок вплотную к концу оригинального кода
else
  DEFAULT_GLYPH_BASE = 0x3608   # Фаза 2: после reloc код кончается на 0x3607
endif
GLYPH_BASE ?= $(DEFAULT_GLYPH_BASE)   # константа переноса (make GLYPH_BASE=... для A-регрессии)
GLYPH_SIZE = 8192
KEEP_DEAD  ?= 0              # 1 = Stage A: мёртвые распаковщики остаются в сборке

.PHONY: all layout clean full deploy verify

all: $(TARGET)

# Перегенерировать компоновку (мастер + gap-бинари) из asm/ и оригинала.
layout:
	@COMPACT=$(COMPACT) GLYPH_BASE=$(GLYPH_BASE) KEEP_DEAD=$(KEEP_DEAD) python3 $(GEN)

$(TARGET): $(GEN) $(ORIG) $(wildcard asm/*.asm)
	@COMPACT=$(COMPACT) GLYPH_BASE=$(GLYPH_BASE) KEEP_DEAD=$(KEEP_DEAD) python3 $(GEN)
	@cd asm && $(Z80ASM) $(ASMFLAGS) -o=../$(FULLBIN) $(MASTER)
	@python3 -c "import json;d=open('$(FULLBIN)','rb').read();gb=json.load(open('tools/dead_ranges.json'))['glyph_base'];gs=$(GLYPH_SIZE);open('$(TARGET)','wb').write(d[256:gb+gs])"
	@rm -f $(FULLBIN) asm/*.o asm/*.sym
	@echo "=== Done: $@ ($$(stat -c%s $@) bytes, COMPACT=$(COMPACT)) ==="

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
