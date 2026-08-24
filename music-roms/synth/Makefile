# Makefile — сборка synth.rom для Вектора-06Ц (z88dk / zcc).
#
# Тестовый ROM партитурного синтезатора (lib/music.c, -DMUSIC_ONLY):
# .mus/.smp из каталога music/ компилируются utils/mus2inc.py в .inc
# (rom_data/), включаются в main.c и попадают в ROM.
#
# make          — собрать synth.rom (.inc пересобираются при изменении
#                 .mus/.smp; ROM — при изменении любого исходника);
# make clean    — убрать все артефакты сборки (включая rom_data/*.inc);
# make deploy   — собрать и положить ROM в папку ROMS эмулятора PPSSPP;
# make full     — clean + сборка + deploy последовательно.
#
# Путь до z88dk можно переопределить: make Z88DK=...

Z88DK   ?= /home/alexey/z88dk
ZCC      = $(Z88DK)/bin/zcc
ZCCCFG  := $(Z88DK)/lib/config
LIB      = ../../lib
MUS2INC  = python3 ../../utils/mus2inc.py
PPSSPP_ROMS = /home/alexey/snap/ppsspp-emu/common/.config/ppsspp/PSP/GAME/VECTOR06C/ROMS

TARGET   = synth.rom

SONGS    = scale voices drums01 rhythm sync flight
INCS     = $(addprefix rom_data/,$(addsuffix .inc,$(SONGS)))
SAMPLES  = $(wildcard music/samples/*.smp)

# music.c вместо sound.c (символы music_*/sound_*, см. v06.h)
SRCS     = $(LIB)/startup.asm main.c \
           $(LIB)/v06io.asm $(LIB)/v06pal.asm $(LIB)/kbdscan.asm \
           $(LIB)/graphpr.asm $(LIB)/graphrle.asm $(LIB)/graphclr.asm \
           $(LIB)/drums.asm \
           $(LIB)/vi53out.asm $(LIB)/music.c \
           $(LIB)/graph.c $(LIB)/keyboard.c

ZFLAGS   = +vector06c --no-crt -I$(LIB) -DMUSIC_ONLY

.PHONY: all deploy clean full

all: $(TARGET)

full: clean
	$(MAKE) deploy

rom_data/%.inc: music/%.mus $(SAMPLES)
	@mkdir -p rom_data
	$(MUS2INC) $< -o $@ --name $*

$(TARGET): $(INCS) $(SRCS)
	ZCCCFG=$(ZCCCFG) PATH="$(Z88DK)/bin:$$PATH" \
            $(ZCC) $(ZFLAGS) $(SRCS) -o $@
	@echo "=== Done: $@ ==="
	@ls -l $@

deploy: $(TARGET)
	cp -f $(TARGET) $(PPSSPP_ROMS)/$(TARGET)
	@echo "=== Deployed to $(PPSSPP_ROMS)/$(TARGET) ==="

clean:
	rm -f $(TARGET) *.o zcc_opt.def *.c.asm $(INCS)
