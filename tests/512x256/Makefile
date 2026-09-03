# Makefile — тест 512x256 для Вектора-06Ц.

include ../../config.mk

LIB      = ../../lib

TARGET = 512x256.rom

SRCS = $(LIB)/sys/startup.asm $(LIB)/sys/v06io.asm $(LIB)/sys/v06pal.asm \
       $(LIB)/gfx/mode.c $(LIB)/gfx/clr.asm $(LIB)/gfx/fstride.asm \
       $(LIB)/gfx/pr512.asm $(LIB)/gfx/pr512t.asm main.c

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
