# Makefile — mk (копия демо fire2: огонь 64×64 → 256×256 для Вектора-06Ц).

include ../../../config.mk


TARGET = mk.rom

BMP2INC = ../../../utils/bmp2inc.py

SRCS = $(LIB)/sys/startup.asm \
       $(LIB)/sys/v06io.asm $(LIB)/sys/v06pal.asm $(LIB)/kbd/kbdscan.asm \
       $(LIB)/gfx/clr.asm $(LIB)/gfx/nextframe.asm $(LIB)/unpack/rle.asm \
       $(LIB)/gfx/pr.asm \
       $(LIB)/gfx/mode.c $(LIB)/gfx/gfx.c $(LIB)/kbd/keyboard.c \
       fire.asm main.c

ZFLAGS = +vector06c --no-crt -I$(LIB)

.PHONY: all deploy clean full

all: $(TARGET)

full: clean all deploy

$(TARGET): assets/title_bmp.inc
	ZCCCFG=$(ZCCCFG) PATH="$(Z88DK)/bin:$$PATH" \
	    $(ZCC) $(ZFLAGS) $(SRCS) -o $@
	@echo "=== Done: $@ ==="
	@ls -l $@

# Заставка: --no-opt сохраняет палитру BMP как есть (identity) — она
# байт-в-байт равна fire_palette из main.c, а заставка и огонь делят одну
# аппаратную палитру, поэтому перестановка индексов недопустима.
assets/title_bmp.inc: assets/title.bmp
	python3 $(BMP2INC) --no-opt $<

include $(PROJECT_ROOT)finally.mk

clean:
	rm -f $(TARGET) *.map *.o zcc_opt.def *.c.asm assets/title_bmp.inc
