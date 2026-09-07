# Makefile — огонь 64×64 → 256×256 для Вектора-06Ц.

include ../../config.mk

LIB      = ../../lib

TARGET = fire2.rom
MAPFILE = fire2.map

SRCS = $(LIB)/sys/startup.asm \
       $(LIB)/sys/v06io.asm $(LIB)/sys/v06pal.asm $(LIB)/kbd/kbdscan.asm \
       $(LIB)/gfx/clr.asm $(LIB)/gfx/nextframe.asm \
       $(LIB)/gfx/mode.c $(LIB)/gfx/gfx.c $(LIB)/kbd/keyboard.c \
       main.c

ZFLAGS = +vector06c --no-crt -I$(LIB)

.PHONY: all deploy clean full

all: $(TARGET)

full: clean all deploy

$(TARGET):
	ZCCCFG=$(ZCCCFG) PATH="$(Z88DK)/bin:$$PATH" \
	    $(ZCC) $(ZFLAGS) -m $(SRCS) -o $@
	@echo "=== Done: $@ ==="
	@ls -l $@

deploy: $(TARGET)
	cp -f $(TARGET) $(PPSSPP_ROMS)/
	cp -f $(MAPFILE) $(PPSSPP_ROMS)/
	@echo "=== Deployed to $(PPSSPP_ROMS)/ ==="

clean:
	rm -f $(TARGET) $(MAPFILE) *.o zcc_opt.def *.c.asm
