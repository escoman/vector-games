# Makefile — демка Mario racing-the-beam (одинарный буфер + таймер КР580ВИ53 ch2)
# для Вектора-06Ц. Вывод спрайта на 8080-ассемблере (src/render.asm),
# строб луча — src/timer.asm (порт 09h).

include ../../../config.mk

TARGET = mario-timer.rom
MAPFILE = mario-timer.map

# Звук: прыжок/приземление — прямые делители КР580ВИ53 (src/sfx_mario.c -> vi53.c).
# sfx.c/notes.c не подключаются: frame-exact-таблица пишется в обход смесителя.
SRCS_COMMON = $(LIB)/sys/startup.asm \
       $(LIB)/sys/v06io.asm $(LIB)/sys/v06pal.asm $(LIB)/kbd/kbdscan.asm \
       $(LIB)/gfx/clr.asm $(LIB)/gfx/nextframe.asm $(LIB)/gfx/plane.asm \
       $(LIB)/gfx/mode.c $(LIB)/gfx/gfx.c $(LIB)/gfx/fade.c $(LIB)/gfx/pr.asm $(LIB)/kbd/keyboard.c \
       $(LIB)/mem/heap.c \
       src/render.asm src/timer.asm src/sfx_mario.c main.c

# mario-dbl.rom — тон на КР580ВИ53 (шума нет: ветер не воспроизводится).
SRCS    = $(SRCS_COMMON) $(LIB)/snd/vi53.c

# Текст — латиница, дефолтный шрифт 8x8 (lib/gfx/fonts/default_8x8.inc),
# собирается внутрь pr.asm. Свой шрифт не подключается.
ZFLAGS = +vector06c --no-crt -I$(LIB)

.PHONY: all deploy clean full assets

all: $(TARGET)

full: clean assets all deploy

# Ассеты: raccoon_mario.png (8 поз) + тайлы земли -> src/*.inc;
# src/background.inc (фон: кусты/облака/земля из mario-8cols, сплит по плоскостям).
assets:
	python3 tools/gen_assets.py
	python3 tools/gen_bg.py

src/sprites.inc src/tiles.inc: src/raccoon_mario.png tools/gen_assets.py
	python3 tools/gen_assets.py

src/background.inc: tools/gen_bg.py ../mario-8cols/src/level.inc ../mario-8cols/src/prefabs.json
	python3 tools/gen_bg.py

GEN_SRC = src/sprites.inc src/tiles.inc src/background.inc main.c src/render.asm src/sfx_mario.c

$(TARGET): $(GEN_SRC) $(SRCS)
	ZCCCFG=$(ZCCCFG) PATH="$(Z88DK)/bin:$$PATH" \
	    $(ZCC) $(ZFLAGS) -m $(SRCS) -o $@
	@echo "=== Done: $@ ==="
	@ls -l $@

include $(PROJECT_ROOT)finally.mk

clean:
	rm -f $(TARGET) *.map *.o zcc_opt.def *.c.asm
