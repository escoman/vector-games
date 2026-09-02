# Makefile — сборка composer.rom для Вектора-06Ц (z88dk / zcc).
#
# Приложение "Композитор": текстовый редактор партитур .mus с
# проигрыванием на AY-3-8910 + ВИ53 (3 тона + ударные).
#
# make          — собрать composer.rom;
# make clean    — убрать артефакты сборки;
# make deploy   — собрать и положить ROM в папку PPSSPP;
# make full     — clean + сборка + deploy.

include ../../config.mk

LIB         = ../../lib
SOUNDTRACK  = ../soundtracks

TARGET      = composer.rom

SRCS        = $(LIB)/sys/startup.asm main.c parser.c editor.c \
              about.c help.c drums.c \
              $(SOUNDTRACK)/nes_drums.c \
              $(LIB)/sys/v06io.asm $(LIB)/sys/v06pal.asm $(LIB)/kbd/kbdscan.asm \
              $(LIB)/gfx/pr.asm \
              $(LIB)/unpack/rle.asm $(LIB)/gfx/clr.asm \
              $(LIB)/snd/drums.asm \
              $(LIB)/snd/vi53out.asm $(LIB)/snd/music.c \
              $(LIB)/gfx/mode.c $(LIB)/gfx/gfx.c $(LIB)/kbd/keyboard.c

ZFLAGS      = +vector06c --no-crt -I$(LIB) -I$(SOUNDTRACK) -DMUSIC_ONLY

.PHONY: all deploy clean full

all: $(TARGET)

full: clean
	$(MAKE) deploy

$(TARGET): $(SRCS) parser.h editor.h screens.h
	ZCCCFG=$(ZCCCFG) PATH="$(Z88DK)/bin:$$PATH" \
            $(ZCC) $(ZFLAGS) $(SRCS) -o $@
	@echo "=== Done: $@ ==="
	@ls -l $@

deploy: $(TARGET)
	cp -f $(TARGET) $(PPSSPP_ROMS)/$(TARGET)
	@echo "=== Deployed to $(PPSSPP_ROMS)/$(TARGET) ==="

clean:
	rm -f $(TARGET) *.o zcc_opt.def *.c.asm
