# Makefile — сборка snd_backends.rom для Вектора-06Ц (z88dk / zcc).
#
# Тестовый ROM разделения аудиомодулей (ТЗ §24, Test 1 и Test 4):
# в ОДНОМ образе линкуются оба аппаратных модуля — vi53/ (КР580ВИ53)
# и ay/ (AY-3-8910), плюс шаговый плеер sound.c и ударные drums.asm.
# Проверяет, что vi53_* и ay_* работают независимо и одновременно,
# а sound_* выводит мелодию на ВИ53 (с ударными на Tape Out).
#
# make          — собрать snd_backends.rom;
# make clean    — убрать артефакты сборки;
# make deploy   — собрать и положить ROM в папку ROMS эмулятора PPSSPP;
# make full     — clean + сборка + deploy последовательно.
#
# Путь до z88dk можно переопределить: make Z88DK=...

include ../../../config.mk


TARGET   = snd_backends.rom

# Без -DMUSIC_ONLY: доступен шаговый плеер sound.c (sound_*), а также
# безусловные vi53_*/ay_*/drum_* (см. v06.h).
SRCS     = $(LIB)/sys/startup.asm main.c \
           $(LIB)/sys/v06io.asm $(LIB)/sys/v06pal.asm $(LIB)/kbd/kbdscan.asm \
           $(LIB)/gfx/pr.asm $(LIB)/unpack/rle.asm $(LIB)/gfx/clr.asm \
           $(LIB)/snd/sound.c $(LIB)/snd/drums.asm \
           $(LIB)/snd/vi53.c $(LIB)/snd/ay.c $(LIB)/snd/notes.c \
           $(LIB)/gfx/mode.c $(LIB)/gfx/gfx.c $(LIB)/kbd/keyboard.c

ZFLAGS   = +vector06c --no-crt -I$(LIB)

.PHONY: all deploy clean full

all: $(TARGET)

full: clean all deploy

$(TARGET): $(SRCS)
	ZCCCFG=$(ZCCCFG) PATH="$(Z88DK)/bin:$$PATH" \
	    $(ZCC) $(ZFLAGS) $(SRCS) -o $@
	@echo "=== Done: $@ ==="
	@ls -l $@

include $(PROJECT_ROOT)finally.mk

clean:
	rm -f $(TARGET) *.o zcc_opt.def *.c.asm
