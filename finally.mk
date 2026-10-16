# finally.mk — универсальная финализация сборки для Вектора-06Ц.
# Подключается в конце каждого Makefile:
#   include $(PROJECT_ROOT)finally.mk
#
# Если цель не clean — копирует TARGET (.rom) и MAPFILE (.map)
# в PPSSPP_ROMS. Если директории нет — предупреждение.
#
# COMPRESS=1 — дополнительно собрать рядом $(TARGET:.rom=.r0m): самораспаковывающийся
# образ (см. utils/rompack.py). deploy при этом отдаёт обычный несжатый .rom.
#
# make consist — показать состав ROM (ресурсы/код/библиотеки) и размеры.
# make deploy  — собрать и положить в ROMS эмулятора.
# make full    — clean + all + deploy.

PPSSPP_ROMS ?= /home/alexey/snap/ppsspp-emu/common/.config/ppsspp/PSP/GAME/VECTOR06C/ROMS

# Предел образа ROM в байтах. По умолчанию 32 КБ: образ вместе с BSS
# лежит в 0x0100..0x7FFF, выше — видеопамять.
# Проект с одной активной плоскостью 0xE000 поднимает предел до
# 0xC000-0x100 = 48896: загрузчик во время загрузки рисует свою таблицу
# в 0xC000, поэтому образ выше 0xBFFF не влезает никогда.
# Это только про образ. Потолок кучи — отдельное решение проекта:
# heap_top по умолчанию 0x8000 (lib/mem/heap.c), и проект, отдавший
# образу память выше него, должен поднять и его.
ROM_MAX ?= 32768

ifneq ($(filter clean,$(MAKECMDGOALS)),clean)

deploy: $(TARGET)
ifneq ($(TARGET_AY),)
deploy: $(TARGET_AY)
endif
ifeq ($(wildcard $(PPSSPP_ROMS)),)
	@echo "Oops! This is not Alexey's PC"
	@echo "Directory not found: $(PPSSPP_ROMS)"
	@echo "Override with: make PPSSPP_ROMS=/path/to/roms"
else
ifdef TARGET
	cp -f $(TARGET) $(PPSSPP_ROMS)/
endif
ifdef TARGET_AY
	cp -f $(TARGET_AY) $(PPSSPP_ROMS)/
endif
ifdef MAPFILE
	cp -f $(MAPFILE) $(PPSSPP_ROMS)/
endif
	@echo "=== Deployed to $(PPSSPP_ROMS)/ ==="
	@for r in $(TARGET) $(TARGET_AY); do \
		[ -f "$$r" ] || continue; \
		SIZE=$$(stat -c%s "$$r"); \
		if [ "$$SIZE" -gt $(ROM_MAX) ]; then \
			echo "\033[33mWARNING: $$r is $${SIZE} bytes (> $(ROM_MAX))\033[0m"; \
		else \
			echo "$$r: $${SIZE} bytes"; \
		fi; \
	done
endif

endif # not clean

# --- make consist -------------------------------------------------------
# Разбор состава ROM: сколько занимают ресурсы (rodata — таблицы треков,
# картинки), код программы, библиотеки и runtime. Пересобирает линковкой с
# картой (-m), печатает отчёт utils/romconsist.py и удаляет карту. Позволяет
# понять, что ужимать, когда ROM переваливает за 32 КБ.
# KEEP_MAP=1 оставляет карту — по адресам символов из неё удобно снимать
# состояние игры эмулятором.
ROMCONSIST ?= $(PROJECT_ROOT)utils/romconsist.py
CONSIST_MAP = $(TARGET:.rom=.map)

.PHONY: consist

ifeq ($(origin SRCS),undefined)
consist:
	@echo "consist: SRCS не определён — нет данных для разбора состава"
else
consist: $(TARGET)
	@ZCCCFG=$(ZCCCFG) PATH="$(Z88DK)/bin:$$PATH" \
	    $(ZCC) $(ZFLAGS) -m $(SRCS) -o $(TARGET) >/dev/null 2>&1
	@if [ -f "$(CONSIST_MAP)" ]; then \
		python3 "$(ROMCONSIST)" "$(CONSIST_MAP)"; \
		if [ "$(KEEP_MAP)" != "1" ]; then rm -f "$(CONSIST_MAP)"; fi; \
	else \
		echo "consist: карта $(CONSIST_MAP) не создана (zcc -m не сработал?)"; \
	fi
endif

# --- COMPRESS=1 -----------------------------------------------------------
# Дополнительно к обычному $(TARGET) (.rom) собрать $(R0M) — самораспаковывающийся
# образ. utils/rompack.py сжимает $(TARGET) потоком ZX0 «backward» и оборачивает
# в крошечный 8080-stub (lib/unpack/unpack_r0m.asm). .r0m эмулятор грузит в 0x0000
# и запускает с него: stub обратнораспаковывает оригинал в 0x0100 и Jump-ит туда.
# Несжатый $(TARGET) остаётся на месте; deploy по-прежнему кладёт в ROMS его.
#   make COMPRESS=1                 # соберёт foo.rom и рядом foo.r0m
#   make COMPRESS=1 Z88DK=/path     # если тулчейн не в ./z88dk
COMPRESS ?= 0
ROMPACK  ?= $(PROJECT_ROOT)utils/rompack.py
R0M       = $(TARGET:.rom=.r0m)

# make clean убирает и упакованный артефакт (.r0m регенерируется).
ifneq ($(TARGET),)
.PHONY: clean-r0m
clean: clean-r0m
clean-r0m:
	@rm -f $(R0M)
endif

ifneq ($(filter clean,$(MAKECMDGOALS)),clean)
ifeq ($(COMPRESS),1)
all: $(R0M)

$(R0M): $(TARGET)
	@echo "=== Packing self-extracting $(R0M) (COMPRESS=1) ==="
	@Z88DK=$(Z88DK) python3 $(ROMPACK) $(TARGET) -o $(R0M) --verify
endif
endif
