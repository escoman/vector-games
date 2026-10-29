# Makefile — демка Mario double-buffering (2 пары плоскостей + своп палитрой)
# для Вектора-06Ц. v2 — вывод спрайта на 8080-ассемблере (include/render.asm).
#
# Раскладка по принципу «что участвует в сборке» (как в mario-timer):
#   include/ — всё, что заходит в конечный ROM: код (render.asm, sfx_mario.c)
#              и подключаемые данные (генерируемые .inc);
#   assets/  — сырьё (xcf/png/txt/mp3), из которого .inc добываются скриптами
#              tools/gen_*.py.
# main.c — точка входа, лежит в корне как во всех демках проекта.

include ../../../config.mk

TARGET = mario-dbl.rom
MAPFILE = mario-dbl.map

# Звук: прыжок/приземление — прямые делители КР580ВИ53 (include/sfx_mario.c -> vi53.c).
# sfx.c/notes.c не подключаются: frame-exact-таблица пишется в обход смесителя.
SRCS_COMMON = $(LIB)/sys/startup.asm \
       $(LIB)/sys/v06io.asm $(LIB)/sys/v06pal.asm $(LIB)/kbd/kbdscan.asm \
       $(LIB)/gfx/clr.asm $(LIB)/gfx/nextframe.asm $(LIB)/gfx/plane.asm \
       $(LIB)/gfx/dblbuf.asm \
       $(LIB)/gfx/mode.c $(LIB)/gfx/gfx.c $(LIB)/gfx/fade.c $(LIB)/gfx/pr.asm $(LIB)/kbd/keyboard.c \
       $(LIB)/mem/heap.c \
       include/render.asm include/sfx_mario.c main.c

# mario-dbl.rom — тон на КР580ВИ53 (шума нет: ветер не воспроизводится).
SRCS    = $(SRCS_COMMON) $(LIB)/snd/vi53.c

# Текст — латиница, дефолтный шрифт 8x8 (lib/gfx/fonts/default_8x8.inc),
# собирается внутрь pr.asm. Свой шрифт не подключается.
# -Iinclude — чтобы main.c подключал генерируемые .inc без пути.
ZFLAGS = +vector06c --no-crt -I$(LIB) -Iinclude

.PHONY: all deploy clean full assets

all: $(TARGET)

full: clean assets all deploy

# Ассеты: raccoon_mario.png (8 поз) + тайлы земли -> include/*.inc
assets:
	python3 tools/gen_assets.py

include/sprites.inc include/tiles.inc: assets/raccoon_mario.png tools/gen_assets.py
	python3 tools/gen_assets.py

GEN_SRC = include/sprites.inc include/tiles.inc main.c include/render.asm include/sfx_mario.c

$(TARGET): $(GEN_SRC) $(SRCS)
	ZCCCFG=$(ZCCCFG) PATH="$(Z88DK)/bin:$$PATH" \
	    $(ZCC) $(ZFLAGS) -m $(SRCS) -o $@
	@echo "=== Done: $@ ==="
	@ls -l $@

include $(PROJECT_ROOT)finally.mk

clean:
	rm -f $(TARGET) *.map *.o zcc_opt.def *.c.asm
