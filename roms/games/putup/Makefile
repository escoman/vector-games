# Makefile — roms/games/putup: Putup с распакованными данными.
#
# PUTUP_NEW.ROM (в корне проекта) = реконструкция Putup (asm-ветка Stage 12
# redesign/putup) с распакованным блоком глифов data_glyph_block_unpacked.
# ПО УМОЛЧАНИЮ собирается КОМПАКТНЫЙ образ (Фаза 2, COMPACT=1, ~21768 Б):
# два мёртвых пакета в.code вырезаны, верхняя половина поднята new_addr(),
# GLYPH_BASE=0x3608. Побайтовая точность гарантирована только на [0x0100,
# 0x2761); выше — корректность доказывается поведенчески (compare_behavior.py:
# VRAM/глифы title/play1/play2). Дефолт осознанно смещён в compact: образ и
# дальше будет уходить от оригинала, поэтому главный гейт — сравнение экранов
# и поведения, а не побайтовый diff. Побайтовый A/B-режим — `make COMPACT=0`
# (25856 Б, byte-exact [0x0100,0x45FF), GLYPH_BASE=0x4600).
#
# Компоновка: tools/gen_layout.py -> asm/putup_unpacked.asm (гэпы — inline DEFB).
# Все данные — побайтовыми DEFB в asm-файлах, bin-артефактов нет.
# Режим 8080: -m=8080_strict. make verify — сверка с оригиналом: в COMPACT=0
# побайтовая по кодовой зоне; в COMPACT=1 инвариант перемещения (каждый diff
# выше 0x2761 = 16-битный операнд new_addr).

include ../../../config.mk

ASMFLAGS  = -b -m=8080_strict -s
TARGET    = PUTUP_NEW.ROM
ORIG      = ../../redesign/putup/src/putup.rom
FULLBIN   = build_full.bin
MASTER    = putup_unpacked.asm
GEN       = tools/gen_layout.py
IMGADDR   = 0x100
COMPACT  ?= 1               # по умолчанию Фаза 2 (вырез дыр + relocation); COMPACT=0 — побайтовый A/B
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

# ВНИМАНИЕ: мастер include-ит asm/funcs/*.asm и asm/data/*.asm — предок должен
# покрывать и подкаталоги, иначе добавление emit-файла в подкаталог не триггерит
# пересборку и verify молчит на устаревшем ROM (тихий false-pass).
$(TARGET): $(GEN) $(ORIG) $(wildcard asm/*.asm) $(wildcard asm/funcs/*.asm) $(wildcard asm/data/*.asm)
	@COMPACT=$(COMPACT) GLYPH_BASE=$(GLYPH_BASE) KEEP_DEAD=$(KEEP_DEAD) python3 $(GEN)
	@cd asm && $(Z80ASM) $(ASMFLAGS) -o=../$(FULLBIN) $(MASTER)
	@python3 -c "import json;J=json.load(open('tools/dead_ranges.json'));d=open('$(FULLBIN)','rb').read();gb=J['glyph_base'];gs=J['glyph_size'];open('$(TARGET)','wb').write(d[256:gb+gs])"
	@rm -f $(FULLBIN) asm/*.o asm/*.sym
	@echo "=== Done: $@ ($$(stat -c%s $@) bytes, COMPACT=$(strip $(COMPACT))) ==="

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
