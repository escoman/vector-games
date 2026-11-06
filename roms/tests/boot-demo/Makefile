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

# Правило генерации панелей идёт в файле выше цели `all` — без этого
# make по умолчанию собирал бы include/panel_top.h вместо ROM.
.DEFAULT_GOAL := all


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

# Данные панелей: include/panel_*.h генерируются из assets/panel_*.png
# (utils/png2panel.py — 2-цветный PNG в плоскость C000). Сырые PNG —
# источники, headers — артефакты сборки (в .gitignore).
PNG2PANEL = $(PROJECT_ROOT)utils/png2panel.py
PANELS = include/panel_top.h include/panel_bottom.h

include/panel_top.h: assets/panel_top.png
	@mkdir -p include
	python3 $(PNG2PANEL) $< --name panel_top --emit h --corner top-left -o $@

include/panel_bottom.h: assets/panel_bottom.png
	@mkdir -p include
	python3 $(PNG2PANEL) $< --name panel_bottom --emit h --corner bottom-right -o $@

ZFLAGS = +vector06c --no-crt -I$(LIB)

.PHONY: all deploy clean full

all: $(TARGET)

full: clean all deploy

$(TARGET): $(SRCS) $(GEN_INC) $(PANELS)
	ZCCCFG=$(ZCCCFG) PATH="$(Z88DK)/bin:$$PATH" \
	    $(ZCC) $(ZFLAGS) $(SRCS) -o $@
	@echo "=== Done: $@ ==="
	@ls -l $@

include $(PROJECT_ROOT)finally.mk

clean:
	rm -f $(TARGET) *.o zcc_opt.def *.c.asm $(PANELS)
