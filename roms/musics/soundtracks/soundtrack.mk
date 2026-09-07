# soundtrack.mk — общие правила сборки для music-ROM саундтреков.
#
# Подключается из Makefile проекта:
#   include ../soundtracks/soundtrack.mk
#
# Переменные, которые нужно задать ДО include:
#   TARGET   — имя ROM (например, jackal.rom)
#   SONGS    — список треков без расширения (track_0 track_1 ...)
#   ROM_JSON — путь к rom.json (по умолчанию rom.json)

SOUNDTRACKS = ../soundtracks
# config.mk подключается из Makefile подпроекта до include soundtrack.mk
BMP2INC     = ../../../utils/bmp2inc.py
TXT2INC     = ../../../utils/txt2inc.py
GEN_MAIN    = $(SOUNDTRACKS)/gen_main.py

ROM_JSON  ?= rom.json
INCS       = $(addprefix rom_data/,$(addsuffix _music.inc,$(SONGS)))

SRCS       = $(LIB)/sys/startup.asm main.c $(SOUNDTRACKS)/nes_drums.c \
             $(LIB)/sys/v06io.asm $(LIB)/sys/v06pal.asm $(LIB)/kbd/kbdscan.asm $(LIB)/snd/vi53out.asm \
             $(LIB)/gfx/pr.asm $(LIB)/unpack/rle.asm $(LIB)/gfx/clr.asm \
             $(LIB)/snd/drums.asm \
             $(LIB)/gfx/mode.c $(LIB)/gfx/gfx.c $(LIB)/snd/music.c $(LIB)/kbd/keyboard.c

ZFLAGS     = +vector06c --no-crt -I. -I$(LIB) -I$(SOUNDTRACKS) -DMUSIC_ONLY

.PHONY: all clean

all: $(TARGET)

# Генерация main.c из rom.json
main.c: $(ROM_JSON) $(GEN_MAIN)
	python3 $(GEN_MAIN) $(ROM_JSON) -o $@

# Конвертация музыки: txt → inc
rom_data/%_music.inc: music_txt/%.txt $(SOUNDTRACKS)/nes_drums.h $(TXT2INC)
	@mkdir -p rom_data
	python3 $(TXT2INC) $< -o $@ --name $*_music --use-shared nes_drums --allow-len-mismatch

# Заставка: bmp → inc
rom_data/title_bmp.inc: rom_data/title.bmp $(BMP2INC)
	python3 $(BMP2INC) --bg-black $<

# Сборка ROM
$(TARGET): $(SRCS) $(INCS) rom_data/title_bmp.inc
	ZCCCFG=$(ZCCCFG) PATH="$(Z88DK)/bin:$$PATH" \
	    $(ZCC) $(ZFLAGS) $(SRCS) -o $@
	@echo "=== Done: $@ ==="
	@ls -l $@

clean:
	rm -f $(TARGET) main.c *.o zcc_opt.def *.c.asm $(INCS)
