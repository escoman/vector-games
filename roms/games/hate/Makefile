# Makefile — H.A.T.E. (Vortex Software, 1989) для Вектора-06Ц.
#
# Этап 1: заставка + мелодия. Звук — только TapeOut (PC0 ПИА1, порт 01h),
# как бипер ZX (TZ §3.8): ВИ53/AY в звуковом тракте не участвуют.
#
# make              — собрать hate.rom (+ hate.map);
# make title        — перегенерировать include/title.inc из assets/hate.png;
# make music        — перегенерировать include/title_music.asm из лога
#                     assets/title_music.txt;
# make font         — перегенерировать include/font.asm из assets/font_6300.bin;
# make terrain      — перегенерировать include/terrain.inc (рельеф меню)
#                     из assets/ring_8000.bin + assets/terrain_mask.bin;
# make leveldata    — снять assets/level_data.bin (байт-коды карт) из снапшота;
# make levels       — перегенерировать include/levels.inc (карты уровней)
#                     из assets/level_data.bin;
# make preview      — то же + превью PNG в assets/ (сверка глазами);
# make deploy       — положить ROM в эмулятор;
# make consist      — разбор состава образа (finally.mk);
# make clean        — убрать артефакты;
# make full         — clean + all + deploy.
#
# Ассеты — ИСХОДНИКИ, руками не правятся:
#   assets/hate.png       — картинка заставки 256x192, 8 цветов ZX;
#   assets/title_music.txt — лог всех переключений бипера ZX (t frame pc value);
#   assets/font_6300.bin  — шрифт 8x8 оригинала (96 слотов по 8 байт, $6300);
#   assets/ring_8000.bin  — кольцо $8000-$BFFF из снапшота (сцена без оверлеев);
#   assets/terrain_mask.bin — off(0) и окно $D5B2 (ktop,kbot) по 32 столбцам;
#   assets/level_data.bin — срез $C400-$CFFF: банк шаблонов клеток, записи
#                       столбцов, таблица частей, скрипты уровней;
#   assets/maps.png     — отрендеренные карты всех уровней, масштаб 1:1
#                       (сверка генерации уровней глазами).
# Ring/mask и level_data снимаются tools/extract_*.py — из внешнего zx-disasm,
# поэтому в сборке участвуют уже готовые .bin.

include ../../../config.mk

TARGET  = hate.rom
MAPFILE = hate.map

GEN_TITLE = tools/gen_title.py
GEN_MUSIC = tools/gen_title_music.py
GEN_FONT  = tools/gen_font.py
GEN_TERRAIN = tools/gen_terrain.py
GEN_LEVELS  = tools/gen_levels.py
EXTRACT_LEVELS = tools/extract_level_data.py

TITLE_INC = include/title.inc
MUSIC_ASM = include/title_music.asm
FONT_ASM  = include/font.asm
TERRAIN_INC = include/terrain.inc
LEVELS_INC = include/levels.inc

# include/render.asm (статичный рельеф меню, terrain.inc) в сборке не участвует:
# меню отложено, а его данные теперь рисует движок миссии. Файлы на месте —
# `make terrain` пересобирает terrain.inc, возврат меню начнётся с них.
SRCS = $(LIB)/sys/startup.asm \
       $(LIB)/sys/v06pal.asm \
       $(LIB)/gfx/mode.c $(LIB)/gfx/gfx.c $(LIB)/gfx/clr.asm \
       $(LIB)/gfx/pr.asm $(LIB)/gfx/dblbuf.asm $(LIB)/gfx/fade.c \
       $(LIB)/unpack/zx0.asm \
       $(LIB)/kbd/kbdscan.asm \
       $(LIB)/mem/heap.c \
       include/beep.asm $(MUSIC_ASM) \
       include/font.asm include/mission.asm include/sfx_hate.c main.c

# FONT_EXTERNAL: pr.asm берёт font_chars/font8x8 как EXTERN из include/font.asm
# (шрифт HATE) вместо латинского шрифта lib/gfx/fonts/default_8x8.inc.
ZFLAGS = +vector06c --no-crt -I$(LIB) -Iinclude -Ca-DFONT_EXTERNAL

.PHONY: all deploy clean full title music font terrain levels leveldata preview

all: $(TARGET)

full: clean all deploy

# Сгенерированные данные — неотъемлемая часть сборки, поэтому в prereq'ах.
$(TARGET): main.c include/sfx_hate.c include/sfx_hate.h include/beep.asm \
           include/mission.asm \
           $(TITLE_INC) $(MUSIC_ASM) $(FONT_ASM) $(LEVELS_INC) $(SRCS)
	ZCCCFG=$(ZCCCFG) PATH="$(Z88DK)/bin:$$PATH" \
	    $(ZCC) $(ZFLAGS) -m $(SRCS) -o $@
	@echo "=== Done: $@ ==="
	@ls -l $@

$(TITLE_INC): assets/hate.png $(GEN_TITLE)
	python3 $(GEN_TITLE)

$(MUSIC_ASM): assets/title_music.txt $(GEN_MUSIC)
	python3 $(GEN_MUSIC)

$(FONT_ASM): assets/font_6300.bin $(GEN_FONT)
	python3 $(GEN_FONT)

$(TERRAIN_INC): assets/ring_8000.bin assets/terrain_mask.bin $(GEN_TERRAIN)
	python3 $(GEN_TERRAIN)

assets/level_data.bin:
	python3 $(EXTRACT_LEVELS)

$(LEVELS_INC): assets/level_data.bin $(GEN_LEVELS)
	python3 $(GEN_LEVELS)

title: $(TITLE_INC)

music: $(MUSIC_ASM)

font: $(FONT_ASM)

terrain: $(TERRAIN_INC)

leveldata: assets/level_data.bin

levels: $(LEVELS_INC)

preview: $(TITLE_INC) $(FONT_ASM) $(TERRAIN_INC) $(LEVELS_INC)
	python3 $(GEN_TITLE) --preview
	python3 $(GEN_FONT) --preview
	python3 $(GEN_TERRAIN) --preview
	python3 $(GEN_LEVELS) --preview

include $(PROJECT_ROOT)finally.mk

clean:
	rm -f $(TARGET) $(MAPFILE) *.o *.lis zcc_opt.def *.c.asm
