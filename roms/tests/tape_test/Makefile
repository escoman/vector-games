# Makefile — сборка tape_test.rom для Вектора-06Ц (z88dk / zcc).
#
# Тестовый ROM гибкой генерации шума Tape Out (ТЗ §15/§16). Проверяет
# разделение drum engine / output route / scheduler: frame-mode генерацию
# из interrupt, MANUAL + drum_tape_step()/drum_tape_generate(n) из main loop,
# фиксированный порог шагов/кадр, а также маршрут AY-Noise (Test F).
#
# make          — собрать tape_test.rom;
# make clean    — убрать артефакты сборки;
# make deploy   — собрать и положить ROM в папку ROMS эмулятора PPSSPP;
# make full     — clean + сборка + deploy последовательно.
#
# Путь до z88dk можно переопределить: make Z88DK=...

include ../../../config.mk


TARGET   = tape_test.rom

# Только ударные/Tape Out (drums.asm) + AY-маршрут (ay.c для Test F).
# Шаговый плеер sound.c и ВИ53 здесь не нужны.
SRCS     = $(LIB)/sys/startup.asm main.c \
           $(LIB)/sys/v06io.asm $(LIB)/sys/v06pal.asm $(LIB)/kbd/kbdscan.asm \
           $(LIB)/gfx/pr.asm $(LIB)/unpack/rle.asm $(LIB)/gfx/clr.asm \
           $(LIB)/snd/drums.asm $(LIB)/snd/ay.c \
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
