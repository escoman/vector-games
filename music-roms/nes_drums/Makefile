# Makefile — сборка nes_drums.rom для Вектора-06Ц (z88dk / zcc).
#
# make          — собрать nes_drums.rom;
# make clean    — убрать все артефакты сборки;
# make deploy   — собрать и положить ROM в папку ROMS эмулятора PPSSPP;
# make full     — clean + сборка + deploy последовательно;
# make samples  — перегенерировать 16 семплов (gen_samples.py).
#
# Путь до z88dk можно переопределить: make Z88DK=...

Z88DK   ?= /home/alexey/z88dk
ZCC      = $(Z88DK)/bin/zcc
ZCCCFG  := $(Z88DK)/lib/config
LIB      = ../../lib
MUS2INC  = python3 ../../utils/mus2inc.py
PPSSPP_ROMS = /home/alexey/snap/ppsspp-emu/common/.config/ppsspp/PSP/GAME/VECTOR06C/ROMS

TARGET   = nes_drums.rom

INCS     = nes_drums.h nes_drums.c \
           rom_data/examples.inc rom_data/track_0.inc rom_data/track_1.inc \
           rom_data/track_1_rep.inc
SAMPLES  = $(wildcard src/samples/*.smp)

SRCS     = $(LIB)/startup.asm main.c \
           nes_drums.c \
           $(LIB)/v06io.asm $(LIB)/v06pal.asm $(LIB)/kbdscan.asm \
           $(LIB)/graphpr.asm $(LIB)/graphrle.asm $(LIB)/graphclr.asm \
           $(LIB)/drums.asm \
           $(LIB)/vi53out.asm $(LIB)/music.c \
           $(LIB)/graph.c $(LIB)/keyboard.c

# music.c: партитурный синтезатор (-DMUSIC_ONLY)
ZFLAGS   = +vector06c --no-crt -I. -I$(LIB) -DMUSIC_ONLY

.PHONY: all deploy clean full samples

all: $(TARGET)

full: clean
	$(MAKE) deploy

samples:
	python3 gen_samples.py

nes_drums.h nes_drums.c: src/nes_drums.mus $(SAMPLES)
	$(MUS2INC) $< -o nes_drums.inc --name nes_drums --shared-lib

rom_data/examples.inc: src/examples.mus nes_drums.h
	$(MUS2INC) $< -o $@ --name examples_music --use-shared nes_drums --allow-len-mismatch

rom_data/track_0.inc: src/track_0.mus nes_drums.h
	$(MUS2INC) $< -o $@ --name track_0_music --use-shared nes_drums --allow-len-mismatch

rom_data/track_1.inc: src/track_1.mus nes_drums.h
	$(MUS2INC) $< -o $@ --name track_1_music --use-shared nes_drums --allow-len-mismatch

rom_data/track_1_rep.inc: src/track_1_rep.mus nes_drums.h
	$(MUS2INC) $< -o $@ --name track_1_rep_music --use-shared nes_drums --allow-len-mismatch

$(TARGET): $(INCS) $(SRCS)
	ZCCCFG=$(ZCCCFG) PATH="$(Z88DK)/bin:$$PATH" \
	    $(ZCC) $(ZFLAGS) $(SRCS) -o $@
	@echo "=== Done: $@ ==="
	@ls -l $@

deploy: $(TARGET)
	cp -f $(TARGET) $(PPSSPP_ROMS)/$(TARGET)
	@echo "=== Deployed to $(PPSSPP_ROMS)/$(TARGET) ==="

clean:
	rm -f $(TARGET) *.o zcc_opt.def *.c.asm \
		 nes_drums.h nes_drums.c nes_drums.inc \
		rom_data/examples.inc rom_data/track_0.inc rom_data/track_1.inc \
		rom_data/track_1_rep.inc
