# Makefile — Stage 10: сборка RISEOUT_NEW.ROM из asm/ (address-exact
# реконструкция оригинала src/riseout.rom: org 0x0100, 20480 байт).
#
# Мастер asm/main.asm (org 0100h + include layout.asm) и address-упорядоченный
# asm/layout.asm порождает v06c-asm-export из src/riseout.rdb + src/riseout.rom
# (цель `layout`). Каждый байт окна emitted ровно один раз: инструкция, RDB-
# данные или явный гэп gap_XXXX — поэтому отдельные gen_layout.py / bin/gap_*.bin
# (как у putup) здесь не нужны: гэпы уже вшиты в layout.asm.
#
# Сборка: z80asm -b -m=8080_strict (те же флаги, что utils/analyze/export_asm).
# Двоичный образ z80asm начинается с offset 0 = адрес org 0x0100, поэтому
# срез по смещению НЕ нужен. Итог побайтово совпадает с оригиналом (0 расхождений).

include ../../../config.mk

ASMFLAGS = -b -m=8080_strict
TARGET   = src/RISEOUT_NEW.ROM
ORIG     = src/riseout.rom
RDB      = src/riseout.rdb
MASTER   = main.asm
IMGADDR  = 0x0100
IMGSIZE  = 20480
ANALYZE  = $(PROJECT_ROOT)utils
EXPORTER ?=

.PHONY: all layout verify full clean

all: $(TARGET)

# Перегенерировать дерево asm/ (main.asm + layout.asm + views) из RDB+ROM.
layout:
	@PYTHONPATH=$(ANALYZE) python3 -m analyze.export_asm \
	    --rom $(ORIG) --rdb $(RDB) --org $(IMGADDR) --out asm \
	    $(if $(EXPORTER),--exporter $(EXPORTER),)

# Сборка ROM из мастера. Зависит от уже экспортированного asm/.
$(TARGET): asm/$(MASTER) asm/layout.asm
	cd asm && $(Z80ASM) $(ASMFLAGS) -o=../$(TARGET) $(MASTER)
	@rm -f asm/*.o asm/*.sym asm/*.err
	@python3 -c "import os,sys; s=os.path.getsize('$(TARGET)'); \
	  print('=== $(TARGET): %d байт ===' % s); \
	  sys.exit(0 if s==$(IMGSIZE) else 'размер %d != %d' % (s,$(IMGSIZE))!=0)"

# Побайтовая сверка с оригиналом: 0 расхождений = идентичное поведение.
verify: $(TARGET)
	@python3 -c "a=open('$(ORIG)','rb').read(); b=open('$(TARGET)','rb').read(); \
	  d=sum(x!=y for x,y in zip(a,b))+abs(len(a)-len(b)); \
	  print('size new=%d orig=%d ; byte diffs=%d'%(len(b),len(a),d)); \
	  exit(0 if d==0 else 1)"
	@echo "verify: RISEOUT_NEW.ROM идентичен riseout.rom (0 расхождений)"

full: clean layout all verify deploy

clean:
	rm -f $(TARGET) asm/*.o asm/*.sym asm/*.err

# Финализация по стандарту проекта: цели deploy/full/consist.
include $(PROJECT_ROOT)finally.mk
