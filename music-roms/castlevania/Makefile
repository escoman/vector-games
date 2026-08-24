# Makefile — сборка castlevania.rom для Вектора-06Ц (z88dk / zcc).
#
# make          — собрать castlevania.rom (пересобирается при изменении
#                 любого исходника из $(SRCS)); заставка
#                 rom_data/title_bmp.inc генерируется bmp2inc.py
#                 из rom_data/title.bmp;
# make clean    — убрать все артефакты сборки;
# make deploy   — собрать и положить ROM в папку ROMS эмулятора PPSSPP;
# make full     — clean + сборка + deploy последовательно.
#
# Путь до z88dk можно переопределить: make Z88DK=...

Z88DK   ?= /home/alexey/z88dk
ZCC      = $(Z88DK)/bin/zcc
ZCCCFG  := $(Z88DK)/lib/config
LIB      = ../../lib
BMP2INC  = ../../utils/bmp2inc.py
TXT2INC  = ../../utils/txt2inc.py
PPSSPP_ROMS = /home/alexey/snap/ppsspp-emu/common/.config/ppsspp/PSP/GAME/VECTOR06C/ROMS

TARGET   = castlevania.rom

# Партитуры: music_txt/*.txt -> rom_data/*_music.inc
# Цепочка: txt2inc.py (txt → mus → повторы → inc).
SONGS    = track_0 track_1 track_2 track_3 track_4 track_5 track_6 track_7 track_8
INCS     = $(addprefix rom_data/,$(addsuffix _music.inc,$(SONGS)))

SRCS     = $(LIB)/startup.asm main.c nes_drums.c \
           $(LIB)/v06io.asm $(LIB)/v06pal.asm $(LIB)/kbdscan.asm $(LIB)/vi53out.asm \
           $(LIB)/graphpr.asm $(LIB)/graphrle.asm $(LIB)/graphclr.asm \
           $(LIB)/drums.asm \
           $(LIB)/graph.c $(LIB)/music.c $(LIB)/keyboard.c

ZFLAGS   = +vector06c --no-crt -I. -I$(LIB) -DMUSIC_ONLY

.PHONY: all deploy clean full

all: $(TARGET)

full: clean
	$(MAKE) deploy

rom_data/title_bmp.inc: rom_data/title.bmp $(BMP2INC)
	python3 $(BMP2INC) $<

rom_data/%_music.inc: music_txt/%.txt nes_drums.h $(TXT2INC)
	python3 $(TXT2INC) $< -o $@ --name $*_music --use-shared nes_drums --allow-len-mismatch

$(TARGET): $(SRCS) rom_data/title_bmp.inc $(INCS)
	ZCCCFG=$(ZCCCFG) PATH="$(Z88DK)/bin:$$PATH" \
	    $(ZCC) $(ZFLAGS) $(SRCS) -o $@
	@echo "=== Done: $@ ==="
	@ls -l $@

deploy: $(TARGET)
	cp -f $(TARGET) $(PPSSPP_ROMS)/$(TARGET)
	@echo "=== Deployed to $(PPSSPP_ROMS)/$(TARGET) ==="

clean:
	rm -f $(TARGET) *.o zcc_opt.def *.c.asm $(INCS)
