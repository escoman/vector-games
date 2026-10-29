# Makefile — spr-demo: проверка стандартных ядер спрайтов lib/gfx/spr.asm
# (spr_init / spr_blit / spr_blit_mask) в 256x256x16. Само-достаточный ROM:
# две полосы фона, по ним патрулируют спрайты двумя способами вывода —
# композит с маской (без erase) и плоский битблит с ящиком зачистки.
# Данные спрайтов генерируются gen_spr.py -> spr.inc.
#
# Режим 8080 (таргет +vector06c сам зовёт z80asm -m8080).

include ../../../config.mk

TARGET  = spr-demo.rom
MAPFILE = spr-demo.map

SRCS = $(LIB)/sys/startup.asm \
       $(LIB)/sys/v06io.asm $(LIB)/sys/v06pal.asm \
       $(LIB)/gfx/clr.asm $(LIB)/gfx/nextframe.asm $(LIB)/gfx/pr.asm \
       $(LIB)/gfx/mode.c $(LIB)/gfx/gfx.c \
       $(LIB)/gfx/spr.asm main.c

ZFLAGS = +vector06c --no-crt -I$(LIB)

.PHONY: all deploy clean full

all: $(TARGET)

full: clean all deploy

$(TARGET):
	ZCCCFG=$(ZCCCFG) PATH="$(Z88DK)/bin:$$PATH" \
	    $(ZCC) $(ZFLAGS) -m $(SRCS) -o $@
	@echo "=== Done: $@ ==="
	@ls -l $@

include $(PROJECT_ROOT)finally.mk

clean:
	rm -f $(TARGET) $(MAPFILE) *.o zcc_opt.def *.c.asm
