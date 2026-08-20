# Makefile — сборка jackal.rom для Вектора-06Ц (z88dk / zcc).
#
# make          — собрать jackal.rom (пересобирается при изменении
#                 любого исходника из $(SRCS)); партитуры .inc
#                 компилируются mus2inc.py из music/*.mus;
# make clean    — убрать все артефакты сборки;
# make deploy   — собрать и положить ROM в папку ROMS эмулятора PPSSPP;
# make full     — clean + сборка + deploy последовательно.
#
# Путь до z88dk можно переопределить: make Z88DK=...

Z88DK   ?= /home/alexey/z88dk
ZCC      = $(Z88DK)/bin/zcc
ZCCCFG  := $(Z88DK)/lib/config
LIB      = ../../lib
PPSSPP_ROMS = /home/alexey/snap/ppsspp-emu/common/.config/ppsspp/PSP/GAME/VECTOR06C/ROMS

TARGET   = jackal.rom

# Партитуры: music/*.mus (+ samples/*.smp) -> rom_data/*_music.inc
# ВРЕМЕННО: не все мелодии — каждый следующий добавляется по мере
# надобности, ROM не должен доходить до видеоОЗУ (ROM с 0100h,
# видеоОЗУ с 8000h)
SONGS    = intro level1 ending
MUS2INC  = ../../utils/mus2inc.py
SAMPLES  = $(wildcard music/samples/*.smp)
INCS     = $(addprefix rom_data/,$(addsuffix _music.inc,$(SONGS)))

SRCS     = $(LIB)/startup.asm main.c \
           $(LIB)/v06io.asm $(LIB)/v06pal.asm $(LIB)/kbdscan.asm $(LIB)/vi53out.asm \
           $(LIB)/graphpr.asm $(LIB)/graphrle.asm $(LIB)/graphclr.asm \
           $(LIB)/drums.asm \
           $(LIB)/graph.c $(LIB)/music.c $(LIB)/keyboard.c

# music.c вместо sound.c (символы music_*/sound_* не конфликтуют,
# но в одном ROM — один плеер)
ZFLAGS   = +vector06c --no-crt -I$(LIB) -DMUSIC_ONLY

.PHONY: all deploy clean full

all: $(TARGET)

full: clean
	$(MAKE) deploy

rom_data/%_music.inc: music/%.mus $(SAMPLES) $(MUS2INC)
	python3 $(MUS2INC) $< -o $@ --name $*_music

$(TARGET): $(SRCS) $(INCS)
	ZCCCFG=$(ZCCCFG) PATH="$(Z88DK)/bin:$$PATH" \
	    $(ZCC) $(ZFLAGS) $(SRCS) -o $@
	@echo "=== Done: $@ ==="
	@ls -l $@

deploy: $(TARGET)
	cp -f $(TARGET) $(PPSSPP_ROMS)/$(TARGET)
	@echo "=== Deployed to $(PPSSPP_ROMS)/$(TARGET) ==="

clean:
	rm -f $(TARGET) *.o zcc_opt.def *.c.asm $(INCS)
