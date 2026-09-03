# Makefile — тест controls (UI-компоненты) для Вектора-06Ц.

include ../../config.mk

LIB      = ../../lib

TARGET = controls.rom

SRCS = $(LIB)/sys/startup.asm $(LIB)/sys/v06io.asm $(LIB)/sys/v06pal.asm \
       $(LIB)/gfx/mode.c $(LIB)/gfx/gfx.c $(LIB)/gfx/clr.asm \
       $(LIB)/gfx/pr.asm \
       $(LIB)/kbd/kbdscan.asm $(LIB)/kbd/keyboard.c \
       $(LIB)/comps/comps.c $(LIB)/comps/textarea.c \
       main.c

ZFLAGS = +vector06c --no-crt -I$(LIB) -I$(LIB)/comps

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
