# Makefile — демка Mario 8-цвет (сплит по плоскостям) для Вектора-06Ц.

include ../../../config.mk

TARGET = mario-8c.rom
MAPFILE = mario-8c.map

SRCS = $(LIB)/sys/startup.asm \
       $(LIB)/sys/v06io.asm $(LIB)/sys/v06pal.asm $(LIB)/kbd/kbdscan.asm \
       $(LIB)/gfx/clr.asm $(LIB)/gfx/nextframe.asm \
       $(LIB)/gfx/mode.c $(LIB)/gfx/gfx.c $(LIB)/gfx/fade.c \
       $(LIB)/kbd/keyboard.c \
       mario.asm main.c

ZFLAGS = +vector06c --no-crt -I$(LIB)

.PHONY: all deploy clean full assets

all: $(TARGET)

full: clean all deploy

# Ассеты: tiles.png/tiles.json/mario.png -> src/level.inc, src/mario.inc
assets:
	python3 tools/gen_assets.py

src/level.inc src/mario.inc: src/tiles.png src/tiles.json src/mario.png tools/gen_assets.py
	python3 tools/gen_assets.py

$(TARGET): src/level.inc src/mario.inc mario.asm main.c
	ZCCCFG=$(ZCCCFG) PATH="$(Z88DK)/bin:$$PATH" \
	    $(ZCC) $(ZFLAGS) -m $(SRCS) -o $@
	@echo "=== Done: $@ ==="
	@ls -l $@

include $(PROJECT_ROOT)finally.mk

clean:
	rm -f $(TARGET) $(MAPFILE) *.o zcc_opt.def *.c.asm
