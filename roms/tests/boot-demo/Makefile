# Makefile — сборка boot-demo.rom для Вектора-06Ц (z88dk / zcc).
#
# Тестовая ROM-заставка второго загрузчика (docs/LOADER_TZ.MD §8): ждёт любую
# клавишу и зовёт loader_boot(), которая копирует stage-2 в 0xE000 и уходит
# туда навсегда — возврата в main нет.
#
# Blob загрузчика в ROM тянется из lib/boot/loader_stage2.inc (он
# сгенерированный, НЕ ПРАВИТЬ): loader.asm подключает его INCLUDE'ом, сам
# .inc в SRCS не перечисляется — тот же порядок, что у шрифтов в gfx/pr.asm.
# Пересборка blob: `make loader2` в корне проекта.
#
# make          — собрать boot-demo.rom;
# make clean    — убрать артефакты сборки;
# make deploy   — собрать и положить ROM в папку ROMS эмулятора;
# make full     — clean + сборка + deploy.

include ../../../config.mk


TARGET = boot-demo.rom

SRCS = $(LIB)/sys/startup.asm \
       $(LIB)/sys/v06io.asm $(LIB)/sys/v06pal.asm $(LIB)/kbd/kbdscan.asm \
       $(LIB)/gfx/pr.asm $(LIB)/gfx/clr.asm \
       $(LIB)/gfx/mode.c $(LIB)/gfx/gfx.c $(LIB)/kbd/keyboard.c \
       $(LIB)/boot/loader.asm \
       main.c

# Сгенерированный blob: в SRCS его нет (INCLUDE внутри loader.asm), но он
# должен перетригаться, если stage-2 пересобрали.
GEN_INC = $(LIB)/boot/loader_stage2.inc

ZFLAGS = +vector06c --no-crt -I$(LIB)

.PHONY: all deploy clean full

all: $(TARGET)

full: clean all deploy

$(TARGET): $(SRCS) $(GEN_INC)
	ZCCCFG=$(ZCCCFG) PATH="$(Z88DK)/bin:$$PATH" \
	    $(ZCC) $(ZFLAGS) $(SRCS) -o $@
	@echo "=== Done: $@ ==="
	@ls -l $@

include $(PROJECT_ROOT)finally.mk

clean:
	rm -f $(TARGET) *.o zcc_opt.def *.c.asm
