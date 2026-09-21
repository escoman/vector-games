# Makefile — Stage 12: сборка PUTUP_NEW.ROM из asm/ (address-exact реконструкция
# оригинального src/putup.rom, org 0x0100, 17664 байта).
#
# Мастер asm/putup_new.asm и gap-файлы asm/bin/gap_*.bin генерируются
# tools/gen_layout.py (берёт адреса/размеры из src/putup.rdb + замеренные
# длины z80asm и берёт gap-байты ВЛОБ из src/putup.rom — это данные).
#
# Режим 8080: -m=8080_strict. Итог побайтово совпадает с оригиналом.

include ../../../config.mk

Z80ASM    = $(Z88DK)/bin/z80asm
ASMFLAGS  = -b -m=8080_strict -s
TARGET    = src/PUTUP_NEW.ROM
FULLBIN   = build_full.bin
MASTER    = putup_new.asm
GEN       = tools/gen_layout.py
ORIG      = src/putup.rom
IMGADDR   = 0x100
IMGSIZE   = 17664

.PHONY: all layout clean full deploy verify

all: $(TARGET)

# Перегенерировать компоновку (мастер + gap-бинари) из asm/ и оригинала.
layout:
	@python3 $(GEN)

$(TARGET): $(GEN) $(ORIG)
	@python3 $(GEN)
	@cd asm && $(Z80ASM) $(ASMFLAGS) -o=../$(FULLBIN) $(MASTER)
	@python3 -c "d=open('$(FULLBIN)','rb').read(); open('$(TARGET)','wb').write(d[256:256+$(IMGSIZE)])"
	@rm -f $(FULLBIN) asm/*.o asm/*.sym
	@echo "=== Done: $@ ($$(stat -c%s $@) bytes) ==="

# Побайтовая сверка с оригиналом (0 расхождений = идентичное поведение).
verify: $(TARGET)
	@python3 -c "a=open('$(ORIG)','rb').read(); b=open('$(TARGET)','rb').read(); \
	 d=sum(x!=y for x,y in zip(a,b)) + abs(len(a)-len(b)); \
	 print('size new=%d orig=%d ; byte diffs=%d'%(len(b),len(a),d)); \
	 exit(0 if d==0 else 1)"
	@echo "verify: PUTUP_NEW.ROM identical to putup.rom"

full: clean all deploy

clean:
	rm -f $(TARGET) $(FULLBIN) asm/*.o asm/*.sym asm/*.err asm/measure.asm asm/measure.bin asm/measure.sym

# Финализация по стандарту проекта: цели deploy/full.
include $(PROJECT_ROOT)finally.mk
