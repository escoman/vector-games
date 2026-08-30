# Makefile — тест clrs (смена палитры по лучу) для Вектора-06Ц.

Z88DK   ?= /home/alexey/z88dk
Z80ASM   = $(Z88DK)/bin/z80asm
PPSSPP_ROMS = /home/alexey/snap/ppsspp-emu/common/.config/ppsspp/PSP/GAME/VECTOR06C/ROMS

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
