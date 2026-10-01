# Makefile — Ну, погоди! (Вектор-06Ц)

include ../../../config.mk

BMP2INC  = ../../../utils/bmp2inc.py

TARGET = nu_pogodi.rom

SRCS = $(LIB)/sys/startup.asm \
       $(LIB)/sys/v06io.asm $(LIB)/sys/v06pal.asm \
       $(LIB)/gfx/mode.c $(LIB)/gfx/gfx.c $(LIB)/gfx/clr.asm \
       $(LIB)/unpack/rle.asm \
       main.c

ZFLAGS = +vector06c --no-crt -I$(LIB)

.PHONY: all deploy clean full

all: $(TARGET)

full: clean all deploy

$(TARGET): src/back_bmp.inc
	ZCCCFG=$(ZCCCFG) PATH="$(Z88DK)/bin:$$PATH" \
	    $(ZCC) $(ZFLAGS) $(SRCS) -o $@
	@echo "=== Done: $@ ==="
	@ls -l $@

src/back_bmp.inc: src/back.bmp $(BMP2INC)
	python3 $(BMP2INC) --no-opt $<

include $(PROJECT_ROOT)finally.mk

clean:
	rm -f $(TARGET) *.o zcc_opt.def *.c.asm
