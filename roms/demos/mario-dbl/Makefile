# Makefile — демка Mario double-buffering (2 пары плоскостей + своп палитрой)
# для Вектора-06Ц. v2 — вывод спрайта на 8080-ассемблере (src/render.asm).

include ../../../config.mk

TARGET = mario-dbl.rom
TARGET_AY = mario-dbl_ay.rom
MAPFILE = mario-dbl.map

# Общая часть источников (без библиотеки вывода звука — её добавляет вариант).
# Звук: notes.c (таблицы нот) + sfx.c (3-голосный смеситель тональных эффектов).
SRCS_COMMON = $(LIB)/sys/startup.asm \
       $(LIB)/sys/v06io.asm $(LIB)/sys/v06pal.asm $(LIB)/kbd/kbdscan.asm \
       $(LIB)/gfx/clr.asm $(LIB)/gfx/nextframe.asm $(LIB)/gfx/plane.asm \
       $(LIB)/gfx/mode.c $(LIB)/gfx/gfx.c $(LIB)/gfx/fade.c $(LIB)/gfx/pr.asm $(LIB)/kbd/keyboard.c \
       $(LIB)/mem/heap.c \
       $(LIB)/snd/notes.c $(LIB)/snd/sfx.c \
       src/render.asm src/sfx_mario.c main.c

# mario-dbl.rom     — тон на КР580ВИ53 (шума нет: ветер не воспроизводится).
# mario-dbl_ay.rom  — тон на AY-3-8910 + шум ветра на канале C (drums.asm).
SRCS    = $(SRCS_COMMON) $(LIB)/snd/vi53.c
SRCS_AY = $(SRCS_COMMON) $(LIB)/snd/ay.c $(LIB)/snd/drums.asm

# Текст — латиница, дефолтный шрифт 8x8 (lib/gfx/fonts/default_8x8.inc),
# собирается внутрь pr.asm. Свой шрифт не подключается.
# AY-вариант: один флаг кодирует и чип тона, и маршрут шума (sfx.c, drums.asm
# выбирают вывод по нему на сборке); -D — в C, -Ca-D — в z80asm.
ZFLAGS = +vector06c --no-crt -I$(LIB)
ZFLAGS_AY = $(ZFLAGS) -DMUSIC_AY_DRUMS_AY -Ca-DMUSIC_AY_DRUMS_AY

.PHONY: all deploy clean full assets

all: $(TARGET) $(TARGET_AY)

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

# AY-вариант: тон на AY-3-8910, шум ветра — Noise C через drums.asm.
$(TARGET_AY): $(GEN_SRC) $(SRCS_AY)
	ZCCCFG=$(ZCCCFG) PATH="$(Z88DK)/bin:$$PATH" \
	    $(ZCC) $(ZFLAGS_AY) -m $(SRCS_AY) -o $@
	@echo "=== Done: $@ ==="
	@ls -l $@

include $(PROJECT_ROOT)finally.mk

clean:
	rm -f $(TARGET) $(TARGET_AY) *.map *.o zcc_opt.def *.c.asm
