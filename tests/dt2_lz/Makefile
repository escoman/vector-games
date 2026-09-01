# Makefile — тест LZ-сжатия для Вектора-06Ц.
#
# make              — собрать ROM;
# make clean        — убрать артефакты;
# make deploy       — скопировать в ROMS эмулятора;
# make full         — clean + сборка + deploy.

include ../../config.mk

LIB      = ../../lib
BMP2INC_LZ = ../../utils/bmp2inc_lz.py

TARGET = dt2_lz.rom

# Источники
SRCS = $(LIB)/sys/startup.asm \
       $(LIB)/sys/v06io.asm $(LIB)/sys/v06pal.asm $(LIB)/kbd/kbdscan.asm \
       $(LIB)/gfx/pr.asm $(LIB)/gfx/clr.asm $(LIB)/unpack/lz.asm \
       $(LIB)/gfx/gfx.c $(LIB)/kbd/keyboard.c \
       main.c

ZFLAGS = +vector06c --no-crt -I$(LIB) -I..

.PHONY: all deploy clean full

all: $(TARGET)

full: clean all deploy

# --- Сборка ROM ---
$(TARGET): ../assets/dt2_bmp.inc
	ZCCCFG=$(ZCCCFG) PATH="$(Z88DK)/bin:$$PATH" \
	    $(ZCC) $(ZFLAGS) $(SRCS) -o $@
	@echo "=== Done: $@ ==="
	@ls -l $@

# Конвертация BMP
../assets/dt2_bmp.inc: ../assets/dt2.bmp $(BMP2INC_LZ)
	python3 $(BMP2INC_LZ) $<

# --- Deploy / clean ---
deploy: $(TARGET)
	cp -f $(TARGET) $(PPSSPP_ROMS)/
	@echo "=== Deployed to $(PPSSPP_ROMS)/ ==="

clean:
	rm -f $(TARGET) *.o *.lis zcc_opt.def *.c.asm ../assets/dt2_bmp.inc
