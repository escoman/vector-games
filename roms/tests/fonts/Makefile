# Makefile — тест fonts (подключаемые шрифты) для Вектора-06Ц.
#
# Фаза 1: экран 256x256 2 цвета, два шрифта 8x8 рядом — шрифт библиотеки
# по умолчанию и шрифт игры PUTUP (putup_font.asm), плюс цифры тем же
# PUTUP-шрифтом в режиме прямого индекса.
# Фаза 2 (клавиша 5): экран 512x256 4 цвета, шрифты 16x8 и тонкий 4x8 —
# таблица имён и прямой индекс (range_fonts.asm).

include ../../../config.mk


TARGET = fonts.rom

SRCS = $(LIB)/sys/startup.asm \
       $(LIB)/sys/v06io.asm $(LIB)/sys/v06pal.asm $(LIB)/kbd/kbdscan.asm \
       $(LIB)/gfx/pr.asm $(LIB)/gfx/pr512.asm $(LIB)/gfx/pr512t.asm \
       $(LIB)/gfx/clr.asm \
       $(LIB)/gfx/mode.c $(LIB)/gfx/gfx.c $(LIB)/kbd/keyboard.c \
       putup_font.asm range_fonts.asm \
       main.c

ZFLAGS = +vector06c --no-crt -I$(LIB)

.PHONY: all deploy clean full

all: $(TARGET)

full: clean all deploy

$(TARGET): putup_font.asm range_fonts.asm main.c
	ZCCCFG=$(ZCCCFG) PATH="$(Z88DK)/bin:$$PATH" \
	    $(ZCC) $(ZFLAGS) $(SRCS) -o $@
	@echo "=== Done: $@ ==="
	@ls -l $@

include $(PROJECT_ROOT)finally.mk

clean:
	rm -f $(TARGET) *.o zcc_opt.def *.c.asm
