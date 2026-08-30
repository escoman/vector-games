# Makefile — тест 512x256 для Вектора-06Ц.

Z88DK   ?= /home/alexey/z88dk
ZCC      = $(Z88DK)/bin/zcc
ZCCCFG  := $(Z88DK)/lib/config
LIB      = ../../lib
PPSSPP_ROMS = /home/alexey/snap/ppsspp-emu/common/.config/ppsspp/PSP/GAME/VECTOR06C/ROMS

TARGET = 512x256.rom

SRCS = $(LIB)/startup.asm $(LIB)/graphpr512.asm $(LIB)/graphpr512t.asm $(LIB)/v06pal.asm main.c

ZFLAGS = +vector06c --no-crt -I$(LIB)

.PHONY: all deploy clean full

all: $(TARGET)

full: clean all deploy

$(TARGET):
	ZCCCFG=$(ZCCCFG) PATH="$(Z88DK)/bin:$$PATH" \
	    $(ZCC) $(ZFLAGS) $(SRCS) -o $@
	@echo "=== Done: $@ ==="
	@ls -l $@

deploy: $(TARGET)
	cp -f $(TARGET) $(PPSSPP_ROMS)/
	@echo "=== Deployed to $(PPSSPP_ROMS)/ ==="

clean:
	rm -f $(TARGET) *.o zcc_opt.def *.c.asm
