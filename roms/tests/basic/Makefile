# Makefile — тест basic (вывод текста шрифтом BASIC) для Вектора-06Ц.
#
# Шрифт BASIC 5x8 хранится столбцами (вертикальными битами), а кадр Вектора —
# горизонтальными байтами, поэтому рендерер в main.c делает поворот на 90° и
# ставит глиф на любой X (точность до пикселя). Байтов шрифта в Makefile нет —
# basic_font.asm генерирует tools/gen_font.py из roms/redesign/basic.

include ../../../config.mk


TARGET = basic.rom

SRCS = $(LIB)/sys/startup.asm \
       $(LIB)/sys/v06io.asm $(LIB)/sys/v06pal.asm $(LIB)/kbd/kbdscan.asm \
       $(LIB)/gfx/pr.asm $(LIB)/gfx/clr.asm \
       $(LIB)/gfx/mode.c $(LIB)/gfx/gfx.c $(LIB)/kbd/keyboard.c \
       basic_font.asm \
       main.c

ZFLAGS = +vector06c --no-crt -I$(LIB)

.PHONY: all deploy clean full

all: $(TARGET)

full: clean all deploy

$(TARGET): basic_font.asm main.c
	ZCCCFG=$(ZCCCFG) PATH="$(Z88DK)/bin:$$PATH" \
	    $(ZCC) $(ZFLAGS) $(SRCS) -o $@
	@echo "=== Done: $@ ==="
	@ls -l $@

include $(PROJECT_ROOT)finally.mk

clean:
	rm -f $(TARGET) *.o zcc_opt.def *.c.asm
