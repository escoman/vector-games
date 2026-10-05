# Makefile — Ну, погоди! (Вектор-06Ц)
#
# Два варианта вывода звука (как в roms/musics/mk), взаимно исключающие
# библиотеки вывода:
#   nu_pogodi.rom      — КР580ВИ53;
#   nu_pogodi_ay.rom   — AY-3-8910.
#
# make              — собрать оба ROM (читает src/screen.bmp и src/sprites/*.bmp);
# make assets       — создать src/screen.bmp и src/sprites/*.bmp из ground.png
#                     и атласа, ЕСЛИ их ещё нет (--force / FORCE=1 пересоздаст);
# make screen       — то же, только src/screen.bmp;
# make sprites      — то же, только src/sprites/*.bmp;
# make inc          — bg.inc + sprites.inc из screen.bmp+спрайтов; призраки
#                     спрайтов на фон по умолчанию НЕ накладываются (так bg.inc
#                     компактнее), GHOSTS=1 возвращает их (make inc GHOSTS=1);
# make music        — src/title_music.inc из src/sounds/title.mus (партитура);
# make smp          — переснять src/sounds/*.smp с оригиналов src/sounds/*.wav
#                     (ПЕРЕЗАПИСЫВАЕТ ручную правку пар R6/R10); в ROM не идут —
#                     отдельные шумовые эффекты не используются (Tape Out занят
#                     партией ударных заставки)
# make mus          — переимпортировать title.mus из title.mid (точит правку!);
#                     какой трек из src/music/ кладётся в title.mid — переменной
#                     TITLE (по умолчанию title): make mus TITLE=titleA_loop;
#                     скорость воспроизведения — переменной TEMPO (правит
#                     строку Tempo: в готовом .mus): make mus TITLE=titleA;
# make preview      — src/preview.png для composed-фона (как в ROM; призраки —
#                     только с GHOSTS=1);
# make clean        — убрать артефакты;
# make deploy       — положить ROM в эмулятор;
# make full         — clean + all + deploy.
#
# src/screen.bmp (поле+панель, без призраков) и src/sprites/*.bmp (спрайты 1x)
# — ИСХОДНИКИ, их правит человек в GIMP: палитра BMP настоящая векторная,
# индексы совпадают со слотами. Сборка ROM их НЕ перезаписывает — только
# читает. Призраки спрайтов на поле по умолчанию НЕ накладываются (bg.inc без
# них компактнее); GHOSTS=1 (make inc/preview GHOSTS=1) возвращает наложение.
# Финальная палитра — в main.c (bg_palette[]), не в ассетах.
# Цели screen/sprites идемпотентны: существующие файлы не трогаются без FORCE=1.
#
# src/sounds/title.mus — ИСХОДНИК мелодии заставки (текстовая партитура, правится
# руками: Tempo + нотные строки score0/1/2). Сборка всегда перегоняет его в
# src/title_music.inc (mus2inc.py). title.mid — только исходник для импорта
# (`make mus`), ROM его не читает.
#
# Варианты мелодии заставки лежат в src/music/ (titleA/titleA_loop/titleB/
# titleB_loop + текущая title). `make mus TITLE=<имя>` копирует src/music/<имя>.mid
# в src/sounds/title.mid и импортирует из него партитуру — дальше обычная сборка.
# Без TITLE берётся title, то есть текущая.

include ../../../config.mk

GEN     = tools/gen_assets.py
GENFONT = tools/gen_font.py
MIDI2MUS = ../../../utils/midi2mus.py
MUS2INC  = ../../../utils/mus2inc.py
DMC2SMP  = ../../../utils/dmc2smp.py
# Общий набор ударных (16 семплов nes_drums) — тот же, что подключают
# music-ROM'ы через ../soundtracks/soundtrack.mk.
SOUNDTRACKS = ../../musics/soundtracks
NESDRUMS    = $(SOUNDTRACKS)/nes_drums.c
TARGET     = nu_pogodi.rom
TARGET_AY  = nu_pogodi_ay.rom

# Отдельные шумовые эффекты в ROM НЕ идут: «разбилось» и «конец игры» —
# тональные гудки на КР580ВИ53 (main.c, шаг sfx_step_t). Tape Out теперь занят
# партией ударных заставки (drums.asm), поэтому src/sounds/*.smp остаются лишь
# как запись эксперимента (их снимает `make smp` с .wav), но в образ не
# попадают: список SFX_SMP пуст.
SFX_SMP =
SFX_INC = $(addprefix src/,$(addsuffix _smp.inc,$(SFX_SMP)))

# Какая мелодия из src/music/ идёт на заставку (без .mid).
TITLE ?= title

# Темп. Движок music.c считает тики на кадр из расчёта 50 кадров/с, а игровой
# цикл на Векторе вытягивает ~24 (замер: 488 итераций за 20 с в заставке по
# _idle_frames, ~41 мс на итерацию). Значит мелодия звучит в 2,05 раза медленнее
# записанной. Важно: `midi2mus --tempo` скорости НЕ меняет — при импорте длины в
# тиках и тиков/кадр масштабируются вместе, время то же. Кнобка скорости —
# строка `Tempo:` уже в готовом .mus (движок берёт из неё num/den, а длительности
# нот остаются), поэтому импортируем на сетке T118, а правку T ставим здесь.
# 118 * 50/24,4 = 242. Если кадр станет легче и цикл поедет к 50 Гц, TEMPO надо
# понижать пропорционально.
TEMPO ?= 242

# FORCE=1 пересоздать screen.bmp/спрайты (осторожно: сотрёт ручную правку).
FORCE ?= 0
GFLAGS = $(if $(filter 1,$(FORCE)),--force,)

# GHOSTS=1 наложить призраки спрайтов на фон в bg.inc/preview (по умолчанию
# выключено — так ZX0-пакованный фон компактнее).
GHOSTS ?= 0
GHFLAGS = $(if $(filter 1,$(GHOSTS)),--ghosts,)

# Общая часть источников (без библиотеки вывода — её добавляет вариант).
SRCS_COMMON = $(LIB)/sys/startup.asm \
       $(LIB)/sys/v06io.asm $(LIB)/sys/v06pal.asm \
       $(LIB)/gfx/mode.c $(LIB)/gfx/gfx.c $(LIB)/gfx/clr.asm \
       $(LIB)/gfx/pr.asm \
       $(LIB)/gfx/plane.asm \
       $(LIB)/unpack/zx0.asm \
       $(LIB)/kbd/kbdscan.asm $(LIB)/kbd/keyboard.c \
       $(LIB)/snd/notes.c $(LIB)/snd/music.c \
       $(LIB)/snd/sfx.c \
       $(LIB)/snd/drums.asm \
       $(NESDRUMS) \
       src/font.asm \
       main.c

SRCS    = $(SRCS_COMMON) $(LIB)/snd/vi53.c   # TARGET    — тон на КР580ВИ53
SRCS_AY = $(SRCS_COMMON) $(LIB)/snd/ay.c     # TARGET_AY — тон на AY-3-8910

# FONT_EXTERNAL: pr.asm берёт font_chars/font8x8 как EXTERN из src/font.asm
# (кириллический шрифт) вместо шрифта по умолчанию lib/gfx/fonts/default_8x8.inc.
# MUSIC_ONLY + один флаг маршрута: он кодирует и чип тона, и путь ударных
# (music.c, drums.asm, sfx.c выбирают вывод по нему же на сборке). Партия
# ударных берётся из percussion-канала title.mid (midi2mus, GM-карта) и идёт
# на общих семплах nes_drums (--use-shared). Маршрут: ВИ53-вариант — Tape Out
# (PC0), AY-вариант — Noise C. -D — в C-препроцессор, -Ca-D — в z80asm.
ZFLAGS_BASE = +vector06c --no-crt -I. -I$(LIB) -I$(SOUNDTRACKS) -Ca-DFONT_EXTERNAL -DMUSIC_ONLY
ZFLAGS      = $(ZFLAGS_BASE) -DMUSIC_VI53_DRUMS_TAPE -Ca-DMUSIC_VI53_DRUMS_TAPE
ZFLAGS_AY   = $(ZFLAGS_BASE) -DMUSIC_AY_DRUMS_AY   -Ca-DMUSIC_AY_DRUMS_AY

.PHONY: all deploy clean full screen sprites assets preview inc font mus music smp sfx

all: $(TARGET) $(TARGET_AY)

full: clean all deploy

# main.c и библиотеки — prereq'и, иначе правка кода не вызывает пересборку.
GEN_HEADERS = src/font.asm src/bg.inc src/sprites.inc src/title_music.inc $(SFX_INC)

$(TARGET): main.c $(GEN) $(GEN_HEADERS) $(SRCS)
	ZCCCFG=$(ZCCCFG) PATH="$(Z88DK)/bin:$$PATH" \
	    $(ZCC) $(ZFLAGS) $(SRCS) -o $@
	@echo "=== Done: $@ ==="
	@ls -l $@

# AY-вариант: тон на AY-3-8910 (ударные — Noise C), без vi53.c.
$(TARGET_AY): main.c $(GEN) $(GEN_HEADERS) $(SRCS_AY)
	ZCCCFG=$(ZCCCFG) PATH="$(Z88DK)/bin:$$PATH" \
	    $(ZCC) $(ZFLAGS_AY) $(SRCS_AY) -o $@
	@echo "=== Done: $@ ==="
	@ls -l $@

# Спрайты — исходники; wildcard на момент разбора (на свежем клоне они есть).
SPRITE_BMPS = $(wildcard src/sprites/*.bmp)

# Один запуск генератора делает оба файла — grouped target, чтобы make
# не вызвал его дважды. Зависит от screen.bmp и всех спрайтов: правка любого
# из них вызывает перегенерацию .inc (но сами исходники не трогаются).
src/bg.inc src/sprites.inc &: src/screen.bmp $(SPRITE_BMPS) $(GEN)
	@python3 $(GEN) inc $(GHFLAGS)

inc:
	@python3 $(GEN) inc $(GHFLAGS)

# Создать исходники, если их ещё нет (FORCE=1 пересоздаст, потеряв правку).
screen:
	@python3 $(GEN) screen $(GFLAGS)

sprites:
	@python3 $(GEN) sprites $(GFLAGS)

assets: screen sprites preview

preview:
	@python3 $(GEN) preview $(GHFLAGS)

# Мелодия заставки: src/sounds/title.mus — ИСХОДНИК (правится руками в текстовом
# виде), из него на каждой сборке перегенерируется src/title_music.inc. Импорт из
# title.mid — отдельной целью `make mus` (ПЕРЕЗАПИСЫВАЕТ title.mus, теряя правку).
# Цель берёт src/music/$(TITLE).mid: TITLE — имя варианта, по умолчанию title.
# Копия делается в самом рецепте, а не отдельным файловым правилом: иначе выбор
# второго варианта подряд не срабатывал бы (title.mid свежее исходника).
src/title_music.inc: src/sounds/title.mus $(MUS2INC)
	@python3 $(MUS2INC) $< -o $@ --name title_music --use-shared nes_drums --allow-len-mismatch

music: src/title_music.inc

mus:
	@cp src/music/$(TITLE).mid src/sounds/title.mid
	@python3 $(MIDI2MUS) src/sounds/title.mid -o src/sounds/title.mus
	@sed -i "s/^Tempo: T.*/Tempo: T$(TEMPO)/" src/sounds/title.mus
	@echo "  Tempo: -> T$(TEMPO) (компенсация ~24 кадров/с вместо 50)"

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
	rm -f $(TARGET) $(TARGET_AY) *.o *.map zcc_opt.def *.c.asm
