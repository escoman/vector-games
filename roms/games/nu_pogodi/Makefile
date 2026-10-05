# Makefile — Ну, погоди! (Вектор-06Ц)
#
# make              — собрать ROM (читает src/screen.bmp и src/sprites/*.bmp);
# make assets       — создать src/screen.bmp и src/sprites/*.bmp из ground.png
#                     и атласа, ЕСЛИ их ещё нет (--force / FORCE=1 пересоздаст);
# make screen       — то же, только src/screen.bmp;
# make sprites      — то же, только src/sprites/*.bmp;
# make inc          — bg.inc + sprites.inc из screen.bmp+спрайтов (призраки тут);
# make preview      — src/preview.png для composed-фона (как в ROM);
# make clean        — убрать артефакты;
# make deploy       — положить ROM в эмулятор;
# make full         — clean + all + deploy.
#
# src/screen.bmp (поле+панель, без призраков) и src/sprites/*.bmp (спрайты 1x)
# — ИСХОДНИКИ, их правит человек в GIMP: палитра BMP настоящая векторная,
# индексы совпадают со слотами. Сборка ROM их НЕ перезаписывает — только
# читает. Призраки накладываются на поле при генерации bg.inc (make inc).
# Финальная палитра — в main.c (bg_palette[]), не в ассетах.
# Цели screen/sprites идемпотентны: существующие файлы не трогаются без FORCE=1.

include ../../../config.mk

GEN     = tools/gen_assets.py
GENFONT = tools/gen_font.py
TARGET  = nu_pogodi.rom

# FORCE=1 пересоздать screen.bmp/спрайты (осторожно: сотрёт ручную правку).
FORCE ?= 0
GFLAGS = $(if $(filter 1,$(FORCE)),--force,)

SRCS = $(LIB)/sys/startup.asm \
       $(LIB)/sys/v06io.asm $(LIB)/sys/v06pal.asm \
       $(LIB)/gfx/mode.c $(LIB)/gfx/gfx.c $(LIB)/gfx/clr.asm \
       $(LIB)/gfx/pr.asm \
       $(LIB)/gfx/plane.asm \
       $(LIB)/unpack/zx0.asm \
       $(LIB)/kbd/kbdscan.asm $(LIB)/kbd/keyboard.c \
       src/font.asm \
       main.c

# FONT_EXTERNAL: pr.asm берёт font_chars/font8x8 как EXTERN из src/font.asm
# (кириллический шрифт) вместо шрифта по умолчанию lib/gfx/fonts/default_8x8.inc.
ZFLAGS = +vector06c --no-crt -I$(LIB) -Ca-DFONT_EXTERNAL

.PHONY: all deploy clean full screen sprites assets preview inc font

all: $(TARGET)

full: clean all deploy

# main.c и библиотеки — prereq'и, иначе правка кода не вызывает пересборку.
$(TARGET): main.c $(GEN) src/font.asm src/bg.inc src/sprites.inc $(SRCS)
	ZCCCFG=$(ZCCCFG) PATH="$(Z88DK)/bin:$$PATH" \
	    $(ZCC) $(ZFLAGS) $(SRCS) -o $@
	@echo "=== Done: $@ ==="
	@ls -l $@

# Спрайты — исходники; wildcard на момент разбора (на свежем клоне они есть).
SPRITE_BMPS = $(wildcard src/sprites/*.bmp)

# Один запуск генератора делает оба файла — grouped target, чтобы make
# не вызвал его дважды. Зависит от screen.bmp и всех спрайтов: правка любого
# из них вызывает перегенерацию .inc (но сами исходники не трогаются).
src/bg.inc src/sprites.inc &: src/screen.bmp $(SPRITE_BMPS) $(GEN)
	@python3 $(GEN) inc

inc:
	@python3 $(GEN) inc

# Создать исходники, если их ещё нет (FORCE=1 пересоздаст, потеряв правку).
screen:
	@python3 $(GEN) screen $(GFLAGS)

sprites:
	@python3 $(GEN) sprites $(GFLAGS)

assets: screen sprites preview

preview:
	@python3 $(GEN) preview

# Перегенерировать кириллический шрифт src/font.asm из PUTUP + дефолтного.
font:
	@python3 $(GENFONT)

include $(PROJECT_ROOT)finally.mk

clean:
	rm -f $(TARGET) *.o zcc_opt.def *.c.asm
