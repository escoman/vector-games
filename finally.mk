# finally.mk — универсальная финализация сборки для Вектора-06Ц.
# Подключается в конце каждого Makefile:
#   include $(PROJECT_ROOT)finally.mk
#
# Если цель не clean — копирует TARGET (.rom) и MAPFILE (.map)
# в PPSSPP_ROMS. Если директории нет — предупреждение.
#
# make consist — показать состав ROM (ресурсы/код/библиотеки) и размеры.
# make deploy  — собрать и положить в ROMS эмулятора.
# make full    — clean + all + deploy.

PPSSPP_ROMS ?= /home/alexey/snap/ppsspp-emu/common/.config/ppsspp/PSP/GAME/VECTOR06C/ROMS

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
		if [ "$$SIZE" -gt 32768 ]; then \
			echo "\033[33mWARNING: $$r is $${SIZE} bytes (> 32KB)\033[0m"; \
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
		rm -f "$(CONSIST_MAP)"; \
	else \
		echo "consist: карта $(CONSIST_MAP) не создана (zcc -m не сработал?)"; \
	fi
endif
