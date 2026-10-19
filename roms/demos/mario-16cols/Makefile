# Makefile — демка Mario 16-цвет для Вектора-06Ц.
#
# Раскладка по принципу «что участвует в сборке» (как в mario-timer):
#   include/ — код (mario.asm) и генерируемые данные (.inc);
#   assets/  — сырьё/дизайн (xcf/png/txt/json), из которого .inc добывают
#              tools/gen_*.py и редактор уровня.
# main.c — точка входа, лежит в корне как во всех демках проекта.

include ../../../config.mk

TARGET = mario-16c.rom
MAPFILE = mario-16c.map

SRCS = $(LIB)/sys/startup.asm \
       $(LIB)/sys/v06io.asm $(LIB)/sys/v06pal.asm $(LIB)/kbd/kbdscan.asm \
       $(LIB)/gfx/clr.asm $(LIB)/gfx/nextframe.asm \
       $(LIB)/gfx/mode.c $(LIB)/gfx/gfx.c $(LIB)/gfx/fade.c \
       $(LIB)/kbd/keyboard.c \
       include/mario.asm main.c

# -Iinclude — чтобы main.c подключал генерируемые .inc без пути.
ZFLAGS = +vector06c --no-crt -I$(LIB) -Iinclude

.PHONY: all deploy clean full assets

all: $(TARGET)

full: clean all deploy

# Ассеты: tiles.png/tiles.json/mario.png -> include/level.inc, include/mario.inc
assets:
	python3 tools/gen_assets.py

include/level.inc include/mario.inc: assets/tiles.png assets/tiles.json assets/mario.png tools/gen_assets.py
	python3 tools/gen_assets.py

$(TARGET): include/level.inc include/mario.inc include/mario.asm main.c
	ZCCCFG=$(ZCCCFG) PATH="$(Z88DK)/bin:$$PATH" \
	    $(ZCC) $(ZFLAGS) -m $(SRCS) -o $@
	@echo "=== Done: $@ ==="
	@ls -l $@

include $(PROJECT_ROOT)finally.mk

clean:
	rm -f $(TARGET) $(MAPFILE) *.o zcc_opt.def *.c.asm
