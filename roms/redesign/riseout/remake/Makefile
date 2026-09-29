# Makefile — TZ2 Stage R0: пересборка оригинала из его же asm-дерева.
#
# layout.asm — address-ordered экспорт из ../asm/ (v06c-asm-export, Stage 10),
# в котором чистые данные (глифы, карты уровней 1..20, музыкальные партитуры)
# вынесены в inc/*.inc генератором tools/split_data.py. На R0 сборка обязана
# остаться побайтово идентичной src/riseout.rom (цель verify) — это базовая
# точка перед заменой циклов заставки/игры на C (Stage R1+ по TZ2.md).
#
# Сборка: z80asm -b -m=8080_strict (те же флаги, что у Stage 10). Offset 0
# двоичного образа = адрес org 0x0100, срез не нужен.

# remake/ лежит на глубине 4 от корня, а формула PROJECT_ROOT в config.mk
# рассчитана на глубину 3 и использует ?= — задаём сами, до include.
PROJECT_ROOT := $(abspath $(dir $(realpath $(firstword $(MAKEFILE_LIST))))../../../..)/
include $(PROJECT_ROOT)config.mk

Z80ASM   = $(Z88DK)/bin/z80asm
ASMFLAGS = -b -m=8080_strict
TARGET   = RISEOUT_REMAKE.ROM
ORIG     = ../src/riseout.rom
IMGSIZE  = 20480
MASTER   = main.asm
INCS     = $(wildcard inc/*.inc)

.PHONY: all split verify full clean

all: $(TARGET)

# Перегенерировать layout.asm + inc/ из оригинального ../asm/layout.asm.
split:
	python3 tools/split_data.py --src ../asm/layout.asm --dst layout.asm --inc inc

$(TARGET): $(MASTER) layout.asm $(INCS)
	$(Z80ASM) $(ASMFLAGS) -o=$@ $(MASTER)
	@rm -f *.o *.sym *.err
	@python3 -c "import os,sys; s=os.path.getsize('$(TARGET)'); \
	  print('=== $(TARGET): %d байт ===' % s); \
	  sys.exit(0 if s==$(IMGSIZE) else 'размер %d != %d' % (s,$(IMGSIZE))!=0)"

# Побайтовая сверка с оригиналом: 0 расхождений = базовая точка R0.
verify: $(TARGET)
	@python3 -c "a=open('$(ORIG)','rb').read(); b=open('$(TARGET)','rb').read(); \
	  d=sum(x!=y for x,y in zip(a,b))+abs(len(a)-len(b)); \
	  print('size new=%d orig=%d ; byte diffs=%d'%(len(b),len(a),d)); \
	  exit(0 if d==0 else 1)"
	@echo "verify: $(TARGET) идентичен riseout.rom (0 расхождений)"

full: clean all verify deploy

clean:
	rm -f $(TARGET) *.o *.sym *.err

# Финализация по стандарту проекта: цели deploy/full/consist.
include $(PROJECT_ROOT)finally.mk
