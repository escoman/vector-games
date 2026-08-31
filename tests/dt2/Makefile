# Makefile — тест dt2 (RLE-картинка) для Вектора-06Ц.

Z88DK   ?= /home/alexey/z88dk
ZCC      = $(Z88DK)/bin/zcc
ZCCCFG  := $(Z88DK)/lib/config
LIB      = ../../lib
BMP2INC  = ../../utils/bmp2inc.py
PPSSPP_ROMS = /home/alexey/snap/ppsspp-emu/common/.config/ppsspp/PSP/GAME/VECTOR06C/ROMS

TARGET = dt2.rom

SRCS = $(LIB)/sys/startup.asm \
       $(LIB)/sys/v06io.asm $(LIB)/sys/v06pal.asm $(LIB)/kbd/kbdscan.asm \
       $(LIB)/gfx/pr.asm $(LIB)/gfx/clr.asm \
       $(LIB)/gfx/gfx.c $(LIB)/kbd/keyboard.c \
       $(LIB)/unpack/rle.asm \
       main.c

ZFLAGS = +vector06c --no-crt -I$(LIB)

.PHONY: all deploy clean full

all: $(TARGET)

full: clean all deploy

$(TARGET): dt2_bmp.inc
	ZCCCFG=$(ZCCCFG) PATH="$(Z88DK)/bin:$$PATH" \
	    $(ZCC) $(ZFLAGS) $(SRCS) -o $@
	@echo "=== Done: $@ ==="
	@ls -l $@

dt2_bmp.inc: dt2.bmp $(BMP2INC)
	python3 $(BMP2INC) --bg-black $<

dt2.bmp: ../assets/dt2.bmp
	cp $< $@

deploy: $(TARGET)
	cp -f $(TARGET) $(PPSSPP_ROMS)/
	@echo "=== Deployed to $(PPSSPP_ROMS)/ ==="

clean:
	rm -f $(TARGET) *.o zcc_opt.def *.c.asm dt2_bmp.inc dt2.bmp
