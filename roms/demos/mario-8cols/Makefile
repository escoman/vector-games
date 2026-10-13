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

# Ассеты: tiles.png/tiles.json/mario.png + объекты уровня -> src/*.inc
assets:
	python3 tools/gen_assets.py

# src/objects.json и src/prefabs.json ОБЯЗАТЕЛЬНЫ в списке зависимостей:
# level.inc печёт словарь вариантов и список экземпляров, а редактор уровня
# правит оба файла (и дописывает одиночные тайлы в prefabs.json). Без них make
# молча линкует ROM из устаревшего level.inc — карта в железе расходится с
# тем, что нарисовано в редакторе. src/palette.json там же: единственный
# источник цветов, который правится руками (level_palette и квантование).
# $(wildcard src/tiles/*.png): gen_assets читает НЕ мастер src/tiles.png, а
# нарезку src/tiles/tile_NNN.png. Правим отдельный тайл (например, дизеринг
# оранжевой площадки) — без этой строки make считает level.inc свежим, и ROM
# печётся из старых тайлов: штриховка «пропадает».
src/level.inc src/mario.inc: src/tiles.png src/tiles.json src/mario.png \
                             src/objects.json src/prefabs.json src/palette.json \
                             $(wildcard src/tiles/*.png) \
                             tools/gen_assets.py tools/prefablib.py
	python3 tools/gen_assets.py

$(TARGET): src/level.inc src/mario.inc mario.asm main.c
	ZCCCFG=$(ZCCCFG) PATH="$(Z88DK)/bin:$$PATH" \
	    $(ZCC) $(ZFLAGS) -m $(SRCS) -o $@
	@echo "=== Done: $@ ==="
	@ls -l $@

include $(PROJECT_ROOT)finally.mk

clean:
	rm -f $(TARGET) $(MAPFILE) *.o zcc_opt.def *.c.asm
