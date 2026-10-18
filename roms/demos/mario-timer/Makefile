# Makefile — демка Mario racing-the-beam (одинарный буфер + таймер КР580ВИ53 ch2)
# для Вектора-06Ц. Вывод спрайта на 8080-ассемблере (include/render.asm),
# строб луча — стандартный модуль lib/timer/timer.asm (порт 09h).
#
# Раскладка по принципу «что участвует в сборке»:
#   include/ — всё, что заходит в конечный ROM: код (render.asm, sfx_mario.c)
#              и подключаемые данные (генерируемые .inc, закоммичены);
#   assets/  — сырьё (xcf/png/txt/mp3), из которого .inc добываются скриптами
#              tools/gen_*.py; может быть удалено без поломки сборки.
# main.c — точка входа, лежит в корне как во всех демках проекта.

include ../../../config.mk

TARGET = mario-timer.rom
MAPFILE = mario-timer.map

# Звук: прыжок/приземление — прямые делители КР580ВИ53 (include/sfx_mario.c -> vi53.c).
# sfx.c/notes.c не подключаются: frame-exact-таблица пишется в обход смесителя.
SRCS_COMMON = $(LIB)/sys/startup.asm \
       $(LIB)/sys/v06io.asm $(LIB)/sys/v06pal.asm $(LIB)/kbd/kbdscan.asm \
       $(LIB)/gfx/clr.asm $(LIB)/gfx/nextframe.asm $(LIB)/gfx/plane.asm \
       $(LIB)/gfx/mode.c $(LIB)/gfx/gfx.c $(LIB)/gfx/fade.c $(LIB)/gfx/pr.asm $(LIB)/kbd/keyboard.c \
       $(LIB)/mem/heap.c $(LIB)/timer/timer.asm \
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

# Конверсия сырья в данные сборки: raccoon_mario.png (8 поз) + тайл земли
# -> include/sprites.inc, include/tiles.inc; фон (кусты/облака/земля из
# mario-8cols) -> include/background.inc. Правила ниже дают то же самое по
# demand; эта цель — принудительная перегенерация всего: make assets.
assets:
	python3 tools/gen_assets.py
	python3 tools/gen_bg.py

include/sprites.inc include/tiles.inc: assets/raccoon_mario.png tools/gen_assets.py
	python3 tools/gen_assets.py

include/background.inc: tools/gen_bg.py ../mario-8cols/src/level.inc ../mario-8cols/src/prefabs.json
	python3 tools/gen_bg.py

GEN_SRC = include/sprites.inc include/tiles.inc include/background.inc \
          main.c include/render.asm include/sfx_mario.c

$(TARGET): $(GEN_SRC) $(SRCS)
	ZCCCFG=$(ZCCCFG) PATH="$(Z88DK)/bin:$$PATH" \
	    $(ZCC) $(ZFLAGS) -m $(SRCS) -o $@
	@echo "=== Done: $@ ==="
	@ls -l $@

include $(PROJECT_ROOT)finally.mk

# include/*.inc при clean НЕ удаляем: они закоммичены и обеспечивают сборку без
# сырья (assets/*); принудительная перегенерация — make assets.
clean:
	rm -f $(TARGET) *.map *.o zcc_opt.def *.c.asm
