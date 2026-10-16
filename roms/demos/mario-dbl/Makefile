# Makefile — демка Mario double-buffering (2 пары плоскостей + своп палитрой)
# для Вектора-06Ц. v2 — вывод спрайта на 8080-ассемблере (src/render.asm).

include ../../../config.mk

TARGET = mario-dbl.rom
MAPFILE = mario-dbl.map

# Звук: прыжок/приземление — прямые делители КР580ВИ53 (src/sfx_mario.c -> vi53.c).
# sfx.c/notes.c не подключаются: frame-exact-таблица пишется в обход смесителя.
SRCS_COMMON = $(LIB)/sys/startup.asm \
       $(LIB)/sys/v06io.asm $(LIB)/sys/v06pal.asm $(LIB)/kbd/kbdscan.asm \
       $(LIB)/gfx/clr.asm $(LIB)/gfx/nextframe.asm $(LIB)/gfx/plane.asm \
       $(LIB)/gfx/mode.c $(LIB)/gfx/gfx.c $(LIB)/gfx/fade.c $(LIB)/gfx/pr.asm $(LIB)/kbd/keyboard.c \
       $(LIB)/mem/heap.c \
       src/render.asm src/sfx_mario.c main.c

# mario-dbl.rom — тон на КР580ВИ53 (шума нет: ветер не воспроизводится).
SRCS    = $(SRCS_COMMON) $(LIB)/snd/vi53.c

# Текст — латиница, дефолтный шрифт 8x8 (lib/gfx/fonts/default_8x8.inc),
# собирается внутрь pr.asm. Свой шрифт не подключается.
ZFLAGS = +vector06c --no-crt -I$(LIB)

.PHONY: all deploy clean full assets

all: $(TARGET)

full: clean assets all deploy

# Ассеты: raccoon_mario.png (8 поз) + тайлы земли -> src/*.inc
assets:
	python3 tools/gen_assets.py

src/sprites.inc src/tiles.inc: src/raccoon_mario.png tools/gen_assets.py
	python3 tools/gen_assets.py

GEN_SRC = src/sprites.inc src/tiles.inc main.c src/render.asm src/sfx_mario.c

$(TARGET): $(GEN_SRC) $(SRCS)
	ZCCCFG=$(ZCCCFG) PATH="$(Z88DK)/bin:$$PATH" \
	    $(ZCC) $(ZFLAGS) -m $(SRCS) -o $@
	@echo "=== Done: $@ ==="
	@ls -l $@

include $(PROJECT_ROOT)finally.mk

clean:
	rm -f $(TARGET) *.map *.o zcc_opt.def *.c.asm
