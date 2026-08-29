# Makefile — тест LZ-сжатия для Вектора-06Ц.
#
# make              — собрать ROM;
# make clean        — убрать артефакты;
# make deploy       — скопировать в ROMS эмулятора;
# make full         — clean + сборка + deploy.

Z88DK   ?= /home/alexey/z88dk
ZCC      = $(Z88DK)/bin/zcc
ZCCCFG  := $(Z88DK)/lib/config
LIB      = ../../lib
BMP2INC_LZ = ../../utils/bmp2inc_lz.py
PPSSPP_ROMS = /home/alexey/snap/ppsspp-emu/common/.config/ppsspp/PSP/GAME/VECTOR06C/ROMS

TARGET = dt2_lz.rom

# Источники
SRCS = $(LIB)/startup.asm \
       $(LIB)/v06io.asm $(LIB)/v06pal.asm $(LIB)/kbdscan.asm \
       $(LIB)/graphpr.asm $(LIB)/graphclr.asm \
       $(LIB)/graph.c $(LIB)/keyboard.c \
       $(LIB)/graphlz.asm \
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
	rm -f $(TARGET) *.o zcc_opt.def *.c.asm ../assets/dt2_bmp.inc
