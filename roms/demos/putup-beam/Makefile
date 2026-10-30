# Makefile — putup-beam: демо beam-подсистемы (lib/gfx/beam.c) на ассетах
# putup. Уровень 16x32 клетки (512px = 2 кольца VRAM), аппаратный скролл,
# герой с маской и субпикселем 4px, 2 врага, ключи -> мигающий выход ->
# рестарт. Данные: assets.inc (tools/gen_assets.py), level.inc
# (tools/gen_level.py) — перегенерируются вручную, в сборку не входят.
#
# Режим 8080 (таргет +vector06c сам зовёт z80asm -m8080).

include ../../../config.mk

TARGET  = putup-beam.rom
MAPFILE = putup-beam.map

SRCS = $(LIB)/sys/startup.asm \
       $(LIB)/sys/v06io.asm $(LIB)/sys/v06pal.asm \
       $(LIB)/gfx/clr.asm $(LIB)/gfx/nextframe.asm \
       $(LIB)/gfx/mode.c $(LIB)/gfx/gfx.c $(LIB)/gfx/fade.c \
       $(LIB)/gfx/spr.asm $(LIB)/gfx/beam.c \
       $(LIB)/timer/timer.asm \
       $(LIB)/kbd/kbdscan.asm $(LIB)/kbd/keyboard.c \
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

include $(PROJECT_ROOT)finally.mk

clean:
	rm -f $(TARGET) $(MAPFILE) *.o zcc_opt.def *.c.asm
