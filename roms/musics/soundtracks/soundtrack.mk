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
# Индекс цвета в исходном .bmp, который bmp2inc фиксирует на нулевой индекс
# палитры — это цвет, которым gfx_clear(0) заливает фон заставки. Берётся из
# rom.json ("bg_index"); по умолчанию 0 (чёрный, как делал прежний --bg-black).
BG_INDEX  ?= $(shell python3 -c "import json;print(json.load(open('$(ROM_JSON)')).get('bg_index',0))" 2>/dev/null || echo 0)
INCS       = $(addprefix rom_data/,$(addsuffix _music.inc,$(SONGS)))

# Общая часть источников (без библиотеки вывода — её добавляет вариант).
SRCS_COMMON = $(LIB)/sys/startup.asm main.c $(SOUNDTRACKS)/nes_drums.c \
              $(LIB)/sys/v06io.asm $(LIB)/sys/v06pal.asm $(LIB)/kbd/kbdscan.asm \
              $(LIB)/gfx/pr.asm $(LIB)/unpack/rle.asm $(LIB)/gfx/clr.asm \
              $(LIB)/snd/drums.asm \
              $(LIB)/gfx/mode.c $(LIB)/gfx/gfx.c $(LIB)/snd/notes.c $(LIB)/snd/music.c $(LIB)/kbd/keyboard.c
# Библиотека вывода линкуется ОДНА на вариант: чужой вывод в ROM не попадает.
SRCS       = $(SRCS_COMMON) $(LIB)/snd/vi53.c     # TARGET    — вывод на ВИ53
SRCS_AY    = $(SRCS_COMMON) $(LIB)/snd/ay.c       # TARGET_AY — вывод на AY

# Вариант по умолчанию — VI53. Один флаг кодирует обе оси (тон + маршрут
# барабанов): -D уходит в C-препроцессор (music.c), -Ca-D — в z80asm
# (drums.asm); обычный -D до ассемблера не доходит.
ZFLAGS_BASE = +vector06c --no-crt -I. -I$(LIB) -I$(SOUNDTRACKS) -DMUSIC_ONLY
ZFLAGS      = $(ZFLAGS_BASE) -DMUSIC_VI53_DRUMS_TAPE -Ca-DMUSIC_VI53_DRUMS_TAPE
ZFLAGS_AY   = $(ZFLAGS_BASE) -DMUSIC_AY_DRUMS_AY -Ca-DMUSIC_AY_DRUMS_AY
# AY-вариант — тот же проект, суффикс _ay в имени ROM.
TARGET_AY   = $(TARGET:.rom=_ay.rom)

.PHONY: all clean

all: $(TARGET) $(TARGET_AY)

# Генерация main.c из rom.json
main.c: $(ROM_JSON) $(GEN_MAIN)
	python3 $(GEN_MAIN) $(ROM_JSON) -o $@

# Конвертация музыки: txt → inc
rom_data/%_music.inc: music_txt/%.txt $(SOUNDTRACKS)/nes_drums.h $(TXT2INC)
	@mkdir -p rom_data
	python3 $(TXT2INC) $< -o $@ --name $*_music --use-shared nes_drums --allow-len-mismatch

# Заставка: bmp → inc. --bg-index фиксирует фон (из rom.json) на нулевом индексе.
rom_data/title_bmp.inc: rom_data/title.bmp $(BMP2INC)
	python3 $(BMP2INC) --bg-index $(BG_INDEX) $<

# Сборка ROM: вариант по умолчанию — вывод на КР580ВИ53 (ударные Tape Out).
$(TARGET): $(SRCS) $(INCS) rom_data/title_bmp.inc
	ZCCCFG=$(ZCCCFG) PATH="$(Z88DK)/bin:$$PATH" \
	    $(ZCC) $(ZFLAGS) $(SRCS) -o $@
	@echo "=== Done: $@ ==="
	@ls -l $@

# AY-вариант: вывод на AY-3-8910 (ударные Noise C), без vi53.c.
$(TARGET_AY): $(SRCS_AY) $(INCS) rom_data/title_bmp.inc
	ZCCCFG=$(ZCCCFG) PATH="$(Z88DK)/bin:$$PATH" \
	    $(ZCC) $(ZFLAGS_AY) $(SRCS_AY) -o $@
	@echo "=== Done: $@ ==="
	@ls -l $@

clean:
	rm -f $(TARGET) $(TARGET_AY) main.c *.o zcc_opt.def *.c.asm $(INCS)
