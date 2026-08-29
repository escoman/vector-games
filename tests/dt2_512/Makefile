# Makefile — тест dt2_512 (512x256, 2 цвета) для Вектора-06Ц.

Z88DK   ?= /home/alexey/z88dk
ZCC      = $(Z88DK)/bin/zcc
ZCCCFG  := $(Z88DK)/lib/config
LIB      = ../../lib
BMP2INC512 = ../../utils/bmp2inc512.py
PPSSPP_ROMS = /home/alexey/snap/ppsspp-emu/common/.config/ppsspp/PSP/GAME/VECTOR06C/ROMS

TARGET = dt2_512.rom

SRCS = $(LIB)/startup.asm \
       $(LIB)/v06io.asm $(LIB)/v06pal.asm $(LIB)/kbdscan.asm \
       $(LIB)/graphpr.asm $(LIB)/graphclr.asm \
       $(LIB)/graph.c $(LIB)/keyboard.c \
       $(LIB)/graphrle512.asm \
       main.c

ZFLAGS = +vector06c --no-crt -I$(LIB)

.PHONY: all deploy clean full

all: $(TARGET)

full: clean all deploy

$(TARGET): dt2_512_bmp.inc
	ZCCCFG=$(ZCCCFG) PATH="$(Z88DK)/bin:$$PATH" \
	    $(ZCC) $(ZFLAGS) $(SRCS) -o $@
	@echo "=== Done: $@ ==="
	@ls -l $@

dt2_512_bmp.inc: ../assets/dt2_512.bmp $(BMP2INC512)
	python3 $(BMP2INC512) $<

deploy: $(TARGET)
	cp -f $(TARGET) $(PPSSPP_ROMS)/
	@echo "=== Deployed to $(PPSSPP_ROMS)/ ==="

clean:
	rm -f $(TARGET) *.o zcc_opt.def *.c.asm dt2_512_bmp.inc
