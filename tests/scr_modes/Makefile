# Makefile — тест scr_modes (переключение видеорежимов) для Вектора-06Ц.

include ../../config.mk

LIB      = ../../lib
BMP2INC  = ../../utils/bmp2inc.py
ASSETS   = ../assets

TARGET = scr_modes.rom

SRCS = $(LIB)/sys/startup.asm $(LIB)/sys/v06io.asm $(LIB)/sys/v06pal.asm \
       $(LIB)/gfx/mode.c $(LIB)/gfx/gfx.c $(LIB)/gfx/clr.asm \
       $(LIB)/gfx/pr.asm $(LIB)/gfx/pr512.asm $(LIB)/gfx/pr512t.asm \
       $(LIB)/unpack/rle.asm \
       $(LIB)/kbd/kbdscan.asm $(LIB)/kbd/keyboard.c \
       main.c

ZFLAGS = +vector06c --no-crt -I$(LIB)

.PHONY: all deploy clean full

all: $(TARGET)

full: clean all deploy

$(TARGET): $(ASSETS)/logo16_bmp.inc
	ZCCCFG=$(ZCCCFG) PATH="$(Z88DK)/bin:$$PATH" \
	    $(ZCC) $(ZFLAGS) $(SRCS) -o $@
	@echo "=== Done: $@ ==="
	@ls -l $@

$(ASSETS)/logo16_bmp.inc: $(ASSETS)/logo16.bmp $(BMP2INC)
	python3 $(BMP2INC) $<

deploy: $(TARGET)
	cp -f $(TARGET) $(PPSSPP_ROMS)/
	@echo "=== Deployed to $(PPSSPP_ROMS)/ ==="

clean:
	rm -f $(TARGET) *.o zcc_opt.def *.c.asm
