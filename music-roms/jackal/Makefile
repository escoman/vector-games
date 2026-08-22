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
# Имена совпадают с исходниками: track_N.mus -> track_N_music.inc.
SONGS    = track_0 track_1 track_2 track_3 track_4 \
           track_5 track_6 track_7
MUS2INC  = ../../utils/mus2inc.py
TXT2MUS  = ../../utils/txt2mus.py
TXT2SMP  = ../../utils/txt2smp.py
SAMPLES  = $(wildcard music/samples/*.smp)
INCS     = $(addprefix rom_data/,$(addsuffix _music.inc,$(SONGS)))

SRCS     = $(LIB)/startup.asm main.c debug_sound.c \
           $(LIB)/v06io.asm $(LIB)/v06pal.asm $(LIB)/kbdscan.asm $(LIB)/vi53out.asm \
           $(LIB)/graphpr.asm $(LIB)/graphrle.asm $(LIB)/graphclr.asm \
           $(LIB)/drums.asm \
           $(LIB)/graph.c $(LIB)/music.c $(LIB)/keyboard.c

# music.c вместо sound.c (символы music_*/sound_* не конфликтуют,
# но в одном ROM — один плеер)
ZFLAGS   = +vector06c --no-crt -I$(LIB) -DMUSIC_ONLY

.PHONY: all deploy clean full mus samples

all: $(TARGET)

# Регенерация партитур из TXT и семплов из параметров шума NES.
# Не входит в `all`: .mus и .smp правятся вручную, эти таргеты —
# только для первичной генерации из исходного NSF-экспорта.
mus:
	@for f in music_txt/*.txt; do \
	  base=$$(basename "$$f" .txt); \
	  python3 $(TXT2MUS) "$$f" -o music/$$base.mus; \
	done
samples:
	python3 $(TXT2SMP) music_txt -o music/samples

full: clean
	$(MAKE) deploy

rom_data/%_music.inc: music/%.mus $(SAMPLES) $(MUS2INC)
	python3 $(MUS2INC) $< -o $@ --name $*_music --allow-len-mismatch

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
