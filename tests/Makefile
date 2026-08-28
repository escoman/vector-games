# Makefile — тестовые ROM для Вектора-06Ц (z88dk / zcc).
#
# make              — собрать cls.rom;
# make clean        — убрать артефакты сборки;
# make deploy       — собрать и положить ROM в папку ROMS эмулятора PPSSPP;
# make full         — clean + сборка + deploy.
#
# Путь до z88dk можно переопределить: make Z88DK=...

Z88DK   ?= /home/alexey/z88dk
ZCC      = $(Z88DK)/bin/zcc
ZCCCFG  := $(Z88DK)/lib/config
LIB      = ../lib
PPSSPP_ROMS = /home/alexey/snap/ppsspp-emu/common/.config/ppsspp/PSP/GAME/VECTOR06C/ROMS

TARGET   = cls.rom

SRCS     = $(LIB)/startup.asm cls.c \
           $(LIB)/v06io.asm $(LIB)/v06pal.asm $(LIB)/kbdscan.asm \
           $(LIB)/graphpr.asm $(LIB)/graphclr.asm \
           $(LIB)/graph.c $(LIB)/keyboard.c

ZFLAGS   = +vector06c --no-crt -I$(LIB)

.PHONY: all deploy clean full

all: $(TARGET)

full: clean
	$(MAKE) deploy

$(TARGET): $(SRCS)
	ZCCCFG=$(ZCCCFG) PATH="$(Z88DK)/bin:$$PATH" \
	    $(ZCC) $(ZFLAGS) $(SRCS) -o $@
	@echo "=== Done: $@ ==="
	@ls -l $@

deploy: $(TARGET)
	cp -f $(TARGET) $(PPSSPP_ROMS)/$(TARGET)
	@echo "=== Deployed to $(PPSSPP_ROMS)/$(TARGET) ==="

clean:
	rm -f $(TARGET) *.o zcc_opt.def *.c.asm
