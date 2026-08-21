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
# Все мелодии вернулись в сборку после перехода на однобайтовые
# команды длительности E0..E7 (партитуры похудели на треть).
SONGS    = intro
MUS2INC  = ../../utils/mus2inc.py
TXT2MUS  = ../../utils/music2mus.py
TXT2SMP  = ../../utils/txt2smp.py
SAMPLES  = $(wildcard music/samples/*.smp)
INCS     = $(addprefix rom_data/,$(addsuffix _music.inc,$(SONGS)))
# Маппинг track_N.txt -> song.mus (final_boss в NSF отсутствует,
# его .mus остаётся старым NES-бинарным; правится вручную).
TRACK_MAP = intro:0 level1:1 level2:2 level3:3 boss:4 \
            stage_clear:5 game_over:6 ending:7

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
	@for pair in $(TRACK_MAP); do \
	  s=$${pair%:*}; n=$${pair#*:}; \
	  python3 $(TXT2MUS) music_txt/track_$$n.txt -o music/$$s.mus; \
	done
samples:
	python3 $(TXT2SMP) music_txt -o music/samples

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
