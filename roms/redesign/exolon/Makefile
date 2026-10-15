# Makefile — Stage 10: сборка EXOLON_NEW.ROM из asm/.
#
# tools/gen_layout.py порождает из RDB+ROM ОДИН монолит asm/code.asm
# (весь код мнемониками + данные/строки/шрифты/спрайты/гэпы помеченными
# секциями defb/defm по меткам RDB) и мастер asm/exolon_new.asm (org 0100h +
# include "code.asm"). Каждый байт окна 0x0100..0x7FFF emitted ровно один раз.
# Сборка z80asm -b -m=8080_strict даёт побайтовую копию exolon.rom
# (0 расхождений, SHA 92be64d1…). Никаких per-object .bin-блобов.

include ../../../config.mk

ASMFLAGS  = -b -m=8080_strict
TARGET    = src/EXOLON_NEW.ROM
ORIG      = src/exolon.rom
RDB       = src/exolon.rdb
MASTER    = exolon_new.asm
IMGADDR   = 0x0100
IMGSIZE   = 32512

.PHONY: all layout verify full clean

all: $(TARGET)

# Перегенерировать монолит asm/code.asm + мастер asm/exolon_new.asm из RDB+ROM.
layout:
	@python3 tools/gen_layout.py

# Сборка ROM из мастера. Зависит от asm/exolon_new.asm и asm/code.asm.
$(TARGET): asm/$(MASTER) asm/code.asm
	cd asm && $(Z80ASM) $(ASMFLAGS) -o=../$(TARGET) $(MASTER)
	@rm -f asm/*.o asm/*.sym asm/*.err
	@python3 -c "import os,sys; s=os.path.getsize('$(TARGET)'); \
	  print('=== $(TARGET): %d байт ===' % s); \
	  sys.exit(0 if s==$(IMGSIZE) else 1)"

# Побайтовая сверка с оригиналом.
verify: $(TARGET)
	@python3 -c "a=open('$(ORIG)','rb').read(); b=open('$(TARGET)','rb').read(); \
	  d=sum(x!=y for x,y in zip(a,b))+abs(len(a)-len(b)); \
	  print('size new=%d orig=%d ; byte diffs=%d'%(len(b),len(a),d)); \
	  exit(0 if d==0 else 1)"
	@echo "verify: EXOLON_NEW.ROM идентичен exolon.rom (0 расхождений)"

full: clean layout all verify deploy

clean:
	rm -f $(TARGET) asm/*.o asm/*.sym asm/*.err

include $(PROJECT_ROOT)finally.mk
