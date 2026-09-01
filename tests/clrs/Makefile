# Makefile — тест clrs (смена палитры по лучу) для Вектора-06Ц.

include ../../config.mk

Z80ASM   = $(Z88DK)/bin/z80asm

TARGET = clrs.rom

SRCS = clrs.asm

.PHONY: all deploy clean full

all: $(TARGET)

full: clean all deploy

$(TARGET):
	$(Z80ASM) -b -o=$@ $(SRCS)
	@echo "=== Done: $@ ==="
	@ls -l $@

deploy: $(TARGET)
	cp -f $(TARGET) $(PPSSPP_ROMS)/
	@echo "=== Deployed to $(PPSSPP_ROMS)/ ==="

clean:
	rm -f $(TARGET) *.o *.bin *.sym
