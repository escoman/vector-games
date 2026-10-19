# Makefile — демка Mario 8-цвет (сплит по плоскостям) для Вектора-06Ц.
#
# Раскладка по принципу «что участвует в сборке» (как в mario-timer):
#   include/ — код (mario.asm) и генерируемые данные (.inc);
#   assets/  — сырьё/дизайн (xcf/png/txt/json), из которого .inc добывают
#              tools/gen_*.py и редакторы уровня/префабов.
# main.c — точка входа, лежит в корне как во всех демках проекта.

include ../../../config.mk

TARGET = mario-8c.rom
MAPFILE = mario-8c.map

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

# Ассеты: tiles.png/tiles.json/mario.png + объекты уровня -> include/*.inc
assets:
	python3 tools/gen_assets.py

# assets/objects.json и assets/prefabs.json ОБЯЗАТЕЛЬНЫ в списке зависимостей:
# level.inc печёт словарь вариантов и список экземпляров, а редактор уровня
# правит оба файла (и дописывает одиночные тайлы в prefabs.json). Без них make
# молча линкует ROM из устаревшего level.inc — карта в железе расходится с
# тем, что нарисовано в редакторе. assets/palette.json там же: единственный
# источник цветов, который правится руками (level_palette и квантование).
# $(wildcard assets/tiles/*.png): gen_assets читает НЕ мастер assets/tiles.png, а
# нарезку assets/tiles/tile_NNN.png. Правим отдельный тайл (например, дизеринг
# оранжевой площадки) — без этой строки make считает level.inc свежим, и ROM
# печётся из старых тайлов: штриховка «пропадает».
include/level.inc include/mario.inc: assets/tiles.png assets/tiles.json assets/mario.png \
                             assets/objects.json assets/prefabs.json assets/palette.json \
                             $(wildcard assets/tiles/*.png) \
                             tools/gen_assets.py tools/prefablib.py
	python3 tools/gen_assets.py

$(TARGET): include/level.inc include/mario.inc include/mario.asm main.c
	ZCCCFG=$(ZCCCFG) PATH="$(Z88DK)/bin:$$PATH" \
	    $(ZCC) $(ZFLAGS) -m $(SRCS) -o $@
	@echo "=== Done: $@ ==="
	@ls -l $@

include $(PROJECT_ROOT)finally.mk

clean:
	rm -f $(TARGET) $(MAPFILE) *.o zcc_opt.def *.c.asm
