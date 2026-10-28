# Makefile — Stage 10: сборка CYBERNOID_NEW.r0m из asm/.
#
# tools/gen_layout.py порождает layout.asm из v06c-asm-export + repair-цикл
# (заменяет mis-decoded runs на defb verbatim из ROM). Мастер asm/main.asm
# (org 0h + include "layout.asm") даёт побайтовый двойник
# src/cybernoid_unpacked.r0m (RAM-образ после самораспаковки, 32768 байт).
#
# Ветвь A (byte-identical). Дефект экспортёра (метки на true+1, memory 1e37587b)
# компенсируется repair-циклом; после C++-фикса в vector-debugger repair
# превращается в no-op (0 runs → 0 diffs).

include ../../../config.mk

ASMFLAGS  = -b -m=8080_strict
TARGET    = src/CYBERNOID_NEW.r0m
ORIG      = src/cybernoid_unpacked.r0m
RDB       = src/cybernoid_unpacked.rdb
MASTER    = main.asm
IMGADDR   = 0x0000
IMGSIZE   = 32768
ROM_MAX   = 32768

.PHONY: all layout verify full clean

all: $(TARGET)

# Перегенерировать asm/ (layout.asm + main.asm + B-views) из RDB+ROM.
layout:
	@python3 tools/gen_layout.py

# Сборка RAM-образа: z80asm, org 0x0000 → 32768 байт.
$(TARGET): asm/$(MASTER) asm/layout.asm
	cd asm && $(Z80ASM) $(ASMFLAGS) -o=../$(TARGET) $(MASTER)
	@rm -f asm/*.o asm/*.sym asm/*.err
	@python3 -c "import os,sys; s=os.path.getsize('$(TARGET)'); \
	  print('=== $(TARGET): %d байт ===' % s); \
	  sys.exit(0 if s==$(IMGSIZE) else 1)"

# Побайтовая сверка с эталоном (RAM-образ после unpack).
verify: $(TARGET)
	@python3 -c "a=open('$(ORIG)','rb').read(); b=open('$(TARGET)','rb').read(); \
	  d=sum(x!=y for x,y in zip(a,b))+abs(len(a)-len(b)); \
	  print('size new=%d orig=%d ; byte diffs=%d'%(len(b),len(a),d)); \
	  exit(0 if d==0 else 1)"
	@echo "verify: CYBERNOID_NEW.r0m идентичен cybernoid_unpacked.r0m (0 расхождений)"

full: clean layout all verify deploy

clean:
	rm -f $(TARGET) asm/*.o asm/*.sym asm/*.err

# Финализация по стандарту проекта: цели deploy/full/consist.
include $(PROJECT_ROOT)finally.mk
