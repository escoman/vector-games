# Makefile — Ну, погоди! (Вектор-06Ц)
#
# make              — собрать ROM;
# make back         — перегенерировать src/back.bmp из src/ground.png;
# make preview      — src/preview.png для просмотра фона;
# make inc          — перегенерировать src/bg.inc и src/sprites.inc из back.bmp;
# make clean        — убрать артефакты;
# make deploy       — положить ROM в эмулятор;
# make full         — clean + all + deploy.
#
# src/back.bmp — 4-битный BMP, его можно править в GIMP: палитра у него
# настоящая векторная, индексы совпадают со слотами палитры. После правки
# достаточно `make inc` — генератор читает картинку, а не пересоздаёт её.
# Поэтому правило для back.bmp ручное (цель back), а не зависимость от времени.

include ../../../config.mk

GEN     = tools/gen_assets.py
TARGET  = nu_pogodi.rom

SRCS = $(LIB)/sys/startup.asm \
       $(LIB)/sys/v06io.asm $(LIB)/sys/v06pal.asm \
       $(LIB)/gfx/mode.c $(LIB)/gfx/gfx.c $(LIB)/gfx/clr.asm \
       $(LIB)/gfx/pr.asm \
       $(LIB)/gfx/plane.asm \
       $(LIB)/unpack/zx0.asm \
       $(LIB)/kbd/kbdscan.asm $(LIB)/kbd/keyboard.c \
       main.c

ZFLAGS = +vector06c --no-crt -I$(LIB)

.PHONY: all deploy clean full back preview inc

all: $(TARGET)

full: clean all deploy

# main.c и библиотеки — prereq'и, иначе правка кода не вызывает пересборку.
$(TARGET): main.c $(GEN) src/bg.inc src/sprites.inc $(SRCS)
	ZCCCFG=$(ZCCCFG) PATH="$(Z88DK)/bin:$$PATH" \
	    $(ZCC) $(ZFLAGS) $(SRCS) -o $@
	@echo "=== Done: $@ ==="
	@ls -l $@

# Один запуск генератора делает оба файла — grouped target, чтобы make
# не вызвал его дважды.
src/bg.inc src/sprites.inc &: src/back.bmp $(GEN)
	@python3 $(GEN) inc

inc:
	@python3 $(GEN) inc

# Пересоздать фон из фотографии. Теряет ручную правку back.bmp.
back:
	@python3 $(GEN) back
	@python3 $(GEN) preview

preview:
	@python3 $(GEN) preview

include $(PROJECT_ROOT)finally.mk

clean:
	rm -f $(TARGET) *.o zcc_opt.def *.c.asm
