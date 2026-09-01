# Makefile — тест dt2_512 (512x256, 2 цвета) для Вектора-06Ц.

include ../../config.mk

LIB      = ../../lib
BMP2INC512 = ../../utils/bmp2inc512.py

TARGET = dt2_512.rom

SRCS = $(LIB)/sys/startup.asm \
       $(LIB)/sys/v06io.asm $(LIB)/sys/v06pal.asm \
       $(LIB)/gfx/mode.c $(LIB)/gfx/clr.asm \
       $(LIB)/unpack/rle512.asm \
       main.c

ZFLAGS = +vector06c --no-crt -I$(LIB)

.PHONY: all deploy clean full

all: $(TARGET)

full: clean all deploy

$(TARGET): dt2_512_bmp.inc
	ZCCCFG=$(ZCCCFG) PATH="$(Z88DK)/bin:$$PATH" \
	    $(ZCC) $(ZFLAGS) $(SRCS) -o $@
	@echo "=== Done: $@ ==="
	@ls -l $@

dt2_512_bmp.inc: dt2_512.bmp $(BMP2INC512)
	python3 $(BMP2INC512) $<

dt2_512.bmp: ../assets/dt2_512.bmp
	cp $< $@

deploy: $(TARGET)
	cp -f $(TARGET) $(PPSSPP_ROMS)/
	@echo "=== Deployed to $(PPSSPP_ROMS)/ ==="

clean:
	rm -f $(TARGET) *.o zcc_opt.def *.c.asm dt2_512_bmp.inc dt2_512.bmp
