# finally.mk — универсальная финализация сборки для Вектора-06Ц.
# Подключается в конце каждого Makefile:
#   include $(PROJECT_ROOT)finally.mk
#
# Если цель не clean — копирует TARGET (.rom) и MAPFILE (.map)
# в PPSSPP_ROMS. Если директории нет — предупреждение.

PPSSPP_ROMS ?= /home/alexey/snap/ppsspp-emu/common/.config/ppsspp/PSP/GAME/VECTOR06C/ROMS

ifneq ($(filter clean,$(MAKECMDGOALS)),clean)

deploy: $(TARGET)
ifeq ($(wildcard $(PPSSPP_ROMS)),)
	@echo "Oops! This is not Alexey's PC"
	@echo "Directory not found: $(PPSSPP_ROMS)"
	@echo "Override with: make PPSSPP_ROMS=/path/to/roms"
else
ifdef TARGET
	cp -f $(TARGET) $(PPSSPP_ROMS)/
endif
ifdef MAPFILE
	cp -f $(MAPFILE) $(PPSSPP_ROMS)/
endif
	@echo "=== Deployed to $(PPSSPP_ROMS)/ ==="
	@if [ -f "$(TARGET)" ]; then \
		SIZE=$$(stat -c%s "$(TARGET)"); \
		if [ "$$SIZE" -gt 32768 ]; then \
			echo "\033[33mWARNING: $(TARGET) is $${SIZE} bytes (> 32KB)\033[0m"; \
		else \
			echo "$(TARGET): $${SIZE} bytes"; \
		fi; \
	fi
endif

endif # not clean
