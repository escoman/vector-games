# Makefile — тестовые ROM для Вектора-06Ц (z88dk / zcc).
#
# make              — собрать все ROM;
# make cls.rom      — только cls.rom;
# make dt2.rom      — только dt2.rom (256x256, 16 цветов);
# make dt2_512.rom  — только dt2_512.rom (512x256, 2 цвета);
# make clean        — убрать артефакты сборки;
# make deploy       — собрать и скопировать в папку ROMS эмулятора PPSSPP;
# make full         — clean + сборка всех + deploy.
#
# Путь до z88dk можно переопределить: make Z88DK=...

Z88DK   ?= /home/alexey/z88dk
ZCC      = $(Z88DK)/bin/zcc
ZCCCFG  := $(Z88DK)/lib/config
LIB      = ../lib
BMP2INC  = ../utils/bmp2inc.py
BMP2INC512 = ../utils/bmp2inc512.py
PPSSPP_ROMS = /home/alexey/snap/ppsspp-emu/common/.config/ppsspp/PSP/GAME/VECTOR06C/ROMS

TARGETS  = cls.rom dt2.rom dt2_512.rom 512x256.rom

# Общие источники
COMMON_SRCS = $(LIB)/startup.asm \
              $(LIB)/v06io.asm $(LIB)/v06pal.asm $(LIB)/kbdscan.asm \
              $(LIB)/graphpr.asm $(LIB)/graphclr.asm \
              $(LIB)/graph.c $(LIB)/keyboard.c

# Источники по ROM
SRCS_cls.rom       = $(COMMON_SRCS) cls.c
SRCS_dt2.rom       = $(COMMON_SRCS) dt2.c $(LIB)/graphrle.asm
SRCS_dt2_512.rom   = $(COMMON_SRCS) dt2_512.c $(LIB)/graphrle512.asm
SRCS_512x256.rom   = $(LIB)/startup.asm 512x256.c

ZFLAGS = +vector06c --no-crt -I$(LIB) -I.

.PHONY: all deploy clean full

all: $(TARGETS)

full: clean all deploy

# --- Сборка ROM ---
%.rom:
	ZCCCFG=$(ZCCCFG) PATH="$(Z88DK)/bin:$$PATH" \
	    $(ZCC) $(ZFLAGS) $(SRCS_$@) -o $@
	@echo "=== Done: $@ ==="
	@ls -l $@

# dt2.rom требует конвертированный BMP (256x256, 16 цветов)
dt2.rom: dt2_bmp.inc

dt2_bmp.inc: dt2.bmp $(BMP2INC)
	python3 $(BMP2INC) --bg-black $<

# dt2_512.rom требует конвертированный BMP (512x256, 2 цвета)
dt2_512.rom: dt2_512_bmp.inc

dt2_512_bmp.inc: dt2_512.bmp $(BMP2INC512)
	python3 $(BMP2INC512) $<

# --- Deploy / clean ---
deploy: $(TARGETS)
	cp -f $(TARGETS) $(PPSSPP_ROMS)/
	@echo "=== Deployed to $(PPSSPP_ROMS)/ ==="

clean:
	rm -f $(TARGETS) *.o zcc_opt.def *.c.asm dt2_bmp.inc dt2_512_bmp.inc
