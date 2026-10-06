# Makefile — mk (демо fire2: огонь 64×64 → 256×256 + тема Mortal Kombat).
#
# Музыка: music/theme.mus (исходник, правится вручную) → utils/mus2inc.py
# (--use-shared nes_drums) → rom_data/theme.inc. Конвертация из MIDI при сборке
# ОТКЛЮЧЕНА; .mus перегенерируют вручную: make regen-mus THEME=<midi>, где
# <midi> — имя файла в assets/ без расширения (theme | themeA | themeB).
# Два варианта вывода звука (взаимоисключающие библиотеки):
#   mk.rom     — ВИ53 (ударные Tape Out);
#   mk_ay.rom  — AY-3-8910 (ударные Noise C).
#
# make          — собрать оба ROM;
# make clean    — убрать артефакты (сгенерированные .inc; .mus НЕ трогает);
# make deploy   — собрать и положить ROM в папку ROMS эмулятора PPSSPP;
# make full     — clean + сборка + deploy;
# make regen-mus [THEME=<midi>] — перегенерировать music/theme.mus из выбранного
#   assets/<midi>.mid (по умолчанию THEME=theme).

include ../../../config.mk

TARGET    = mk.rom
TARGET_AY = mk_ay.rom

BMP2INC     = ../../../utils/bmp2inc.py
MUS2INC     = ../../../utils/mus2inc.py
MIDI2MUS    = ../../../utils/midi2mus.py
SOUNDTRACKS = ../soundtracks

# Какой MIDI из assets/ перегенерирует music/theme.mus (make regen-mus):
# theme | themeA | themeB. Имя без расширения .mid.
THEME ?= theme

# Общая часть источников (без библиотеки вывода — её добавляет вариант).
SRCS_COMMON = $(LIB)/sys/startup.asm \
       $(LIB)/sys/v06io.asm $(LIB)/sys/v06pal.asm $(LIB)/kbd/kbdscan.asm \
       $(LIB)/gfx/clr.asm $(LIB)/gfx/nextframe.asm $(LIB)/unpack/rle.asm \
       $(LIB)/gfx/pr.asm $(LIB)/snd/drums.asm \
       $(LIB)/gfx/mode.c $(LIB)/gfx/gfx.c $(LIB)/kbd/keyboard.c \
       $(LIB)/snd/notes.c $(LIB)/snd/music.c \
       $(SOUNDTRACKS)/nes_drums.c \
       fire.asm main.c

SRCS    = $(SRCS_COMMON) $(LIB)/snd/vi53.c   # TARGET    — вывод на ВИ53
SRCS_AY = $(SRCS_COMMON) $(LIB)/snd/ay.c     # TARGET_AY — вывод на AY

# Один флаг кодирует обе оси (тон + маршрут ударных): -D — в C-препроцессор
# (music.c), -Ca-D — в z80asm (drums.asm); обычный -D до ассемблера не доходит.
ZFLAGS_BASE = +vector06c --no-crt -I. -I$(LIB) -I$(SOUNDTRACKS) -DMUSIC_ONLY
ZFLAGS      = $(ZFLAGS_BASE) -DMUSIC_VI53_DRUMS_TAPE -Ca-DMUSIC_VI53_DRUMS_TAPE
ZFLAGS_AY   = $(ZFLAGS_BASE) -DMUSIC_AY_DRUMS_AY -Ca-DMUSIC_AY_DRUMS_AY

# Сгенерированные заголовки, нужные обоим вариантам.
GEN = assets/title_bmp.inc rom_data/theme.inc

.PHONY: all deploy clean full regen-mus

all: $(TARGET) $(TARGET_AY)

full: clean all deploy

# --- Генерация данных -------------------------------------------------

# Тема: .mus НЕ генерируется из MIDI при сборке — music/theme.mus является
# исходником и правится вручную. Перегенерация из выбранного assets/$(THEME).mid
# (нормализованный темп T118) — только по явному запросу `make regen-mus`:
#   make regen-mus              # из assets/theme.mid (по умолчанию)
#   make regen-mus THEME=themeA # из assets/themeA.mid
#   make regen-mus THEME=themeB # из assets/themeB.mid
# В выход всегда music/theme.mus, поэтому дальше сборка идёт как обычно.
regen-mus:
	@mkdir -p music
	python3 $(MIDI2MUS) assets/$(THEME).mid -o music/theme.mus --tempo 118

# .mus → .inc (семплы ударных берутся из общей библиотеки nes_drums).
rom_data/theme.inc: music/theme.mus
	@mkdir -p rom_data
	python3 $(MUS2INC) $< -o $@ --name theme --use-shared nes_drums \
	    --allow-len-mismatch

# Заставка: --no-opt сохраняет палитру BMP как есть (identity) — она
# байт-в-байт равна fire_palette из main.c, а заставка и огонь делят одну
# аппаратную палитру, поэтому перестановка индексов недопустима.
assets/title_bmp.inc: assets/title.bmp
	python3 $(BMP2INC) --no-opt $<

# --- Сборка ROM -------------------------------------------------------

# Вариант по умолчанию — вывод на КР580ВИ53 (ударные Tape Out).
$(TARGET): $(SRCS) $(GEN)
	ZCCCFG=$(ZCCCFG) PATH="$(Z88DK)/bin:$$PATH" \
	    $(ZCC) $(ZFLAGS) $(SRCS) -o $@
	@echo "=== Done: $@ ==="
	@ls -l $@

# AY-вариант: вывод на AY-3-8910 (ударные Noise C), без vi53.c.
$(TARGET_AY): $(SRCS_AY) $(GEN)
	ZCCCFG=$(ZCCCFG) PATH="$(Z88DK)/bin:$$PATH" \
	    $(ZCC) $(ZFLAGS_AY) $(SRCS_AY) -o $@
	@echo "=== Done: $@ ==="
	@ls -l $@

include $(PROJECT_ROOT)finally.mk

clean:
	rm -f $(TARGET) $(TARGET_AY) *.map *.o zcc_opt.def *.c.asm \
	    assets/title_bmp.inc rom_data/theme.inc
