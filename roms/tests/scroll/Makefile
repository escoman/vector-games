# Makefile — тест скролла (исследование синхронизации луча и регистра скролла).
#
# Цель: понять, как меняется содержимое экрана при записи в порт скролла 03h
# в разные моменты кадра относительно позиции луча.
#
# Управление:
#   UP/DOWN — сдвиг скролла на ±1 строку
#   LEFT/RIGHT — сдвиг на ±16 строк
#   SPACE — сохранить снимок экрана (через vector-debugger)
#   ESC — выход

include ../../../config.mk

TARGET = scroll.rom

SRCS = $(LIB)/sys/startup.asm \
       $(LIB)/sys/v06io.asm $(LIB)/sys/v06pal.asm $(LIB)/kbd/kbdscan.asm \
       $(LIB)/gfx/pr.asm $(LIB)/gfx/clr.asm $(LIB)/gfx/nextframe.asm \
       $(LIB)/gfx/mode.c $(LIB)/gfx/gfx.c $(LIB)/kbd/keyboard.c \
       $(LIB)/timer/timer.asm \
       main.c

ZFLAGS = +vector06c --no-crt -I$(LIB)

.PHONY: all deploy clean full

all: $(TARGET)

full: clean all deploy

$(TARGET): main.c
	ZCCCFG=$(ZCCCFG) PATH="$(Z88DK)/bin:$$PATH" \
	    $(ZCC) $(ZFLAGS) $(SRCS) -o $@
	@echo "=== Done: $@ ==="
	@ls -l $@

include $(PROJECT_ROOT)finally.mk

clean:
	rm -f $(TARGET) *.o zcc_opt.def *.c.asm
