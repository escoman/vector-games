# Makefile — H.A.T.E. (Vortex Software, 1989) для Вектора-06Ц.
#
# Этап 1: заставка + мелодия. Звук — только TapeOut (PC0 ПИА1, порт 01h),
# как бипер ZX (TZ §3.8): ВИ53/AY в звуковом тракте не участвуют.
#
# make              — собрать hate.rom (+ hate.map);
# make title        — перегенерировать include/title.inc из assets/hate.png;
# make music        — перегенерировать include/title_music.asm из лога
#                     assets/title_music.txt;
# make preview      — то же + assets/title_preview.png для сверки картинки;
# make deploy       — положить ROM в эмулятор;
# make consist      — разбор состава образа (finally.mk);
# make clean        — убрать артефакты;
# make full         — clean + all + deploy.
#
# Ассеты — ИСХОДНИКИ, руками не правятся:
#   assets/hate.png       — картинка заставки 256x192, 8 цветов ZX;
#   assets/title_music.txt — лог всех переключений бипера ZX (t frame pc value).

include ../../../config.mk

TARGET  = hate.rom
MAPFILE = hate.map

GEN_TITLE = tools/gen_title.py
GEN_MUSIC = tools/gen_title_music.py

TITLE_INC = include/title.inc
MUSIC_ASM = include/title_music.asm

SRCS = $(LIB)/sys/startup.asm \
       $(LIB)/sys/v06pal.asm \
       $(LIB)/gfx/mode.c $(LIB)/gfx/gfx.c $(LIB)/gfx/clr.asm \
       $(LIB)/unpack/zx0.asm \
       $(LIB)/kbd/kbdscan.asm \
       include/beep.asm $(MUSIC_ASM) \
       include/sfx_hate.c main.c

ZFLAGS = +vector06c --no-crt -I$(LIB) -Iinclude

.PHONY: all deploy clean full title music preview

all: $(TARGET)

full: clean all deploy

# Сгенерированные данные — неотъемлемая часть сборки, поэтому в prereq'ах.
$(TARGET): main.c include/sfx_hate.c include/sfx_hate.h include/beep.asm \
           $(TITLE_INC) $(MUSIC_ASM) $(SRCS)
	ZCCCFG=$(ZCCCFG) PATH="$(Z88DK)/bin:$$PATH" \
	    $(ZCC) $(ZFLAGS) -m $(SRCS) -o $@
	@echo "=== Done: $@ ==="
	@ls -l $@

$(TITLE_INC): assets/hate.png $(GEN_TITLE)
	python3 $(GEN_TITLE)

$(MUSIC_ASM): assets/title_music.txt $(GEN_MUSIC)
	python3 $(GEN_MUSIC)

title: $(TITLE_INC)

music: $(MUSIC_ASM)

preview: $(TITLE_INC)
	python3 $(GEN_TITLE) --preview

include $(PROJECT_ROOT)finally.mk

clean:
	rm -f $(TARGET) $(MAPFILE) *.o *.lis zcc_opt.def *.c.asm
