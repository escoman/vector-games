# Makefile — сборка composer.rom для Вектора-06Ц (z88dk / zcc).
#
# Приложение "Композитор": текстовый редактор партитур .mus с
# проигрыванием на AY-3-8910 + ВИ53 (3 тона + ударные).
#
# make          — собрать composer.rom;
# make clean    — убрать артефакты сборки;
# make deploy   — собрать и положить ROM в папку PPSSPP;
# make full     — clean + сборка + deploy.

include ../../../config.mk

SOUNDTRACK  = ../soundtracks

TARGET      = composer.rom

# Экран 256x256x2: активна одна плоскость 0xE000, значит 0x8000..0xBFFF
# можно отдавать образу, а 0xC000..0xDFFF — куче (lib/mem/heap.c).
# Потолок кучи (heap_top = 0xE000) поднимает сам main.c: без этого куча
# осталась бы под 0x8000 и при образе выше 0x8000 выдача вернула бы 0.
ROM_MAX     = 48896

SRCS        = $(LIB)/sys/startup.asm main.c parser.c \
              about.c help.c drums.c solo.c \
              $(SOUNDTRACK)/nes_drums.c \
              $(LIB)/sys/v06io.asm $(LIB)/sys/v06pal.asm $(LIB)/kbd/kbdscan.asm \
              $(LIB)/gfx/pr.asm \
              $(LIB)/unpack/rle.asm $(LIB)/gfx/clr.asm \
              $(LIB)/snd/drums.asm \
              $(LIB)/snd/vi53.c $(LIB)/snd/ay.c \
              $(LIB)/snd/notes.c \
              $(LIB)/snd/music.c \
              $(LIB)/gfx/mode.c $(LIB)/gfx/gfx.c $(LIB)/kbd/keyboard.c \
              $(LIB)/gfx/fstride.asm \
              $(LIB)/comps/comps.c $(LIB)/comps/textarea.c \
              $(LIB)/mem/heap.c

ZFLAGS      = +vector06c --no-crt -I$(LIB) -I$(LIB)/comps -I$(SOUNDTRACK) -DMUSIC_ONLY

.PHONY: all deploy clean full

all: $(TARGET)

full: clean all deploy

$(TARGET): $(SRCS) parser.h screens.h $(LIB)/comps/comps.h
	ZCCCFG=$(ZCCCFG) PATH="$(Z88DK)/bin:$$PATH" \
            $(ZCC) $(ZFLAGS) $(SRCS) -o $@
	@echo "=== Done: $@ ==="
	@ls -l $@

include $(PROJECT_ROOT)finally.mk

clean:
	rm -f $(TARGET) *.o zcc_opt.def *.c.asm
