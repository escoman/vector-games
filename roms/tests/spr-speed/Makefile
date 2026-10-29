# Makefile — spr-speed: бенчмарк реал-растр стоимости вывода спрайтов/фона
# подсистемы beam-sprites (lib/gfx/spr.asm + spr.c). Само-достаточный ROM:
# строит scratch-глифы в RAM, гоняет пачки вызовов blit-примитивов и служебных
# функций (spr_update) между VBlank'ами, складывает тики КР580ВИ53 в volatile
# RAM-символы bm_*. Читаем из отладчика (debug_read_memory_range), делим на
# (репы × 96 тиков/строку) => строки растра на операцию. Это baseline перед
# переписыванием spr на asm и сменой формата данных спрайтов.
#
# Режим 8080 (таргет +vector06c сам зовёт z80asm -m8080).

include ../../../config.mk

TARGET  = spr-speed.rom
MAPFILE = spr-speed.map

SRCS = $(LIB)/sys/startup.asm \
       $(LIB)/sys/v06io.asm $(LIB)/sys/v06pal.asm $(LIB)/kbd/kbdscan.asm \
       $(LIB)/gfx/clr.asm $(LIB)/gfx/nextframe.asm $(LIB)/gfx/pr.asm \
       $(LIB)/gfx/mode.c $(LIB)/gfx/gfx.c $(LIB)/kbd/keyboard.c \
       $(LIB)/timer/timer.asm \
       spr_old.asm spr_new.asm main.c

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
