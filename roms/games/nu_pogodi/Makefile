# Makefile — Ну, погоди! (Вектор-06Ц)
#
# make              — собрать ROM (читает src/screen.bmp и src/sprites/*.bmp);
# make assets       — создать src/screen.bmp и src/sprites/*.bmp из ground.png
#                     и атласа, ЕСЛИ их ещё нет (--force / FORCE=1 пересоздаст);
# make screen       — то же, только src/screen.bmp;
# make sprites      — то же, только src/sprites/*.bmp;
# make inc          — bg.inc + sprites.inc из screen.bmp+спрайтов (призраки тут);
# make music        — src/title_music.inc из src/sounds/title.mus (партитура);
# make smp          — переснять src/sounds/*.smp с оригиналов src/sounds/*.wav
#                     (ПЕРЕЗАПИСЫВАЕТ ручную правку пар R6/R10); в ROM сейчас
#                     не идут — Tape Out не используется
# make mus          — переимпортировать title.mus из title.mid (точит правку!);
# make preview      — src/preview.png для composed-фона (как в ROM);
# make clean        — убрать артефакты;
# make deploy       — положить ROM в эмулятор;
# make full         — clean + all + deploy.
#
# src/screen.bmp (поле+панель, без призраков) и src/sprites/*.bmp (спрайты 1x)
# — ИСХОДНИКИ, их правит человек в GIMP: палитра BMP настоящая векторная,
# индексы совпадают со слотами. Сборка ROM их НЕ перезаписывает — только
# читает. Призраки накладываются на поле при генерации bg.inc (make inc).
# Финальная палитра — в main.c (bg_palette[]), не в ассетах.
# Цели screen/sprites идемпотентны: существующие файлы не трогаются без FORCE=1.
#
# src/sounds/title.mus — ИСХОДНИК мелодии заставки (текстовая партитура, правится
# руками: Tempo + нотные строки score0/1/2). Сборка всегда перегоняет его в
# src/title_music.inc (mus2inc.py). title.mid — только исходник для импорта
# (`make mus`), ROM его не читает.

include ../../../config.mk

GEN     = tools/gen_assets.py
GENFONT = tools/gen_font.py
MIDI2MUS = ../../../utils/midi2mus.py
MUS2INC  = ../../../utils/mus2inc.py
DMC2SMP  = ../../../utils/dmc2smp.py
TARGET  = nu_pogodi.rom

# Шумовые эффекты в ROM НЕ идут: Tape Out в игре не используется вовсе,
# «разбилось» и «конец игры» — тональные гудки на КР580ВИ53 (main.c, шаг
# sfx_step_t). src/sounds/*.smp остаются как запись эксперимента (их снимает
# `make smp` с .wav), но в образ не попадают: список SFX_SMP пуст.
SFX_SMP =
SFX_INC = $(addprefix src/,$(addsuffix _smp.inc,$(SFX_SMP)))

# FORCE=1 пересоздать screen.bmp/спрайты (осторожно: сотрёт ручную правку).
FORCE ?= 0
GFLAGS = $(if $(filter 1,$(FORCE)),--force,)

SRCS = $(LIB)/sys/startup.asm \
       $(LIB)/sys/v06io.asm $(LIB)/sys/v06pal.asm \
       $(LIB)/gfx/mode.c $(LIB)/gfx/gfx.c $(LIB)/gfx/clr.asm \
       $(LIB)/gfx/pr.asm \
       $(LIB)/gfx/plane.asm \
       $(LIB)/unpack/zx0.asm \
       $(LIB)/kbd/kbdscan.asm $(LIB)/kbd/keyboard.c \
       $(LIB)/snd/notes.c $(LIB)/snd/music.c $(LIB)/snd/vi53.c \
       $(LIB)/snd/sfx.c \
       $(LIB)/snd/drums.asm \
       src/font.asm \
       main.c

# FONT_EXTERNAL: pr.asm берёт font_chars/font8x8 как EXTERN из src/font.asm
# (кириллический шрифт) вместо шрифта по умолчанию lib/gfx/fonts/default_8x8.inc.
# MUSIC_ONLY + MUSIC_VI53_DRUMS_TAPE: партитурный синтезатор music.c, тон на
# КР580ВИ53. Маршрут ударных задан Tape Out только чтобы не линковать AY-драйвер:
# партия ударных в заставке пустая, семплов в ROM нет, так что в PC0 игра не
# пишет ни разу. -D — в C-препроцессор (music.c), -Ca-D — в z80asm (drums.asm).
ZFLAGS = +vector06c --no-crt -I$(LIB) -Ca-DFONT_EXTERNAL \
         -DMUSIC_ONLY -DMUSIC_VI53_DRUMS_TAPE -Ca-DMUSIC_VI53_DRUMS_TAPE

.PHONY: all deploy clean full screen sprites assets preview inc font mus music smp sfx

all: $(TARGET)

full: clean all deploy

# main.c и библиотеки — prereq'и, иначе правка кода не вызывает пересборку.
$(TARGET): main.c $(GEN) src/font.asm src/bg.inc src/sprites.inc src/title_music.inc $(SFX_INC) $(SRCS)
	ZCCCFG=$(ZCCCFG) PATH="$(Z88DK)/bin:$$PATH" \
	    $(ZCC) $(ZFLAGS) $(SRCS) -o $@
	@echo "=== Done: $@ ==="
	@ls -l $@

# Спрайты — исходники; wildcard на момент разбора (на свежем клоне они есть).
SPRITE_BMPS = $(wildcard src/sprites/*.bmp)

# Один запуск генератора делает оба файла — grouped target, чтобы make
# не вызвал его дважды. Зависит от screen.bmp и всех спрайтов: правка любого
# из них вызывает перегенерацию .inc (но сами исходники не трогаются).
src/bg.inc src/sprites.inc &: src/screen.bmp $(SPRITE_BMPS) $(GEN)
	@python3 $(GEN) inc

inc:
	@python3 $(GEN) inc

# Создать исходники, если их ещё нет (FORCE=1 пересоздаст, потеряв правку).
screen:
	@python3 $(GEN) screen $(GFLAGS)

sprites:
	@python3 $(GEN) sprites $(GFLAGS)

assets: screen sprites preview

preview:
	@python3 $(GEN) preview

# Мелодия заставки: src/sounds/title.mus — ИСХОДНИК (правится руками в текстовом
# виде), из него на каждой сборке перегенерируется src/title_music.inc. Импорт из
# title.mid — отдельной целью `make mus` (ПЕРЕЗАПИСЫВАЕТ title.mus, теряя правку).
src/title_music.inc: src/sounds/title.mus $(MUS2INC)
	@python3 $(MUS2INC) $< -o $@ --name title_music --allow-len-mismatch

music: src/title_music.inc

mus:
	@python3 $(MIDI2MUS) src/sounds/title.mid -o src/sounds/title.mus --no-drums

# Шумовые эффекты: src/sounds/<имя>.smp — ИСХОДНИК (байты пар R6/R10, правятся
# руками), src/<имя>_smp.inc компилируется из него на сборке. Снять заново с
# оригинальных .wav — цель `make smp` (ПЕРЕЗАПИСЫВАЕТ все .smp, теряя правку).
src/%_smp.inc: src/sounds/%.smp $(MUS2INC)
	@python3 $(MUS2INC) $< -o $@ --name $(*)_sample

sfx: $(SFX_INC)

smp:
	@python3 $(DMC2SMP) src/sounds -o src/sounds -g 0.1

# Перегенерировать кириллический шрифт src/font.asm из PUTUP + дефолтного.
font:
	@python3 $(GENFONT)

include $(PROJECT_ROOT)finally.mk

clean:
	rm -f $(TARGET) *.o zcc_opt.def *.c.asm
