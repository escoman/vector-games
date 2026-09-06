# Makefile — тест check_bugs для Вектора-06Ц.
#
# Проверка багов стека: вызовы ASM-процедур (очистка экрана, палитра,
# рисование на плоскости) с намеренным PUSH-багом в plane_fill.

include ../../config.mk

LIB      = ../../lib

TARGET   = check_bugs.rom

SRCS = $(LIB)/sys/startup.asm \
       $(LIB)/sys/v06io.asm $(LIB)/sys/v06pal.asm \
       $(LIB)/gfx/clr.asm \
       $(LIB)/gfx/mode.c $(LIB)/gfx/gfx.c \
       main.c

ZFLAGS = +vector06c --no-crt -I$(LIB) -m

.PHONY: all deploy clean full

all: $(TARGET)

full: clean all deploy

$(TARGET):
	ZCCCFG=$(ZCCCFG) PATH="$(Z88DK)/bin:$$PATH" \
	    $(ZCC) $(ZFLAGS) $(SRCS) -o $@
	@echo "=== Done: $@ ==="
	@ls -l $@

deploy: $(TARGET)
	cp -f $(TARGET) $(PPSSPP_ROMS)/
	@echo "=== Deployed to $(PPSSPP_ROMS)/ ==="

clean:
	rm -f $(TARGET) *.o *.map zcc_opt.def *.c.asm
