# Makefile — сборка всех ROM для Вектора-06Ц.
#
# make          — собрать все ROM, скопировать в release/;
# make clean    — убрать артефакты сборки всех проектов + папку release/;
# make full     — clean + сборка всех проектов.

# Под Windows этот Makefile тоже требует POSIX-шелла (for/do, mkdir -p, cp)
# — настройки SHELL/PATH тянутся из config.mk (он тянет windows.mk).
# Под Linux recipe'ы и так выполняются через sh, include не нужен.
ifeq ($(OS),Windows_NT)
include config.mk
endif

MUSIC_ROMS = roms/musics/castlevania \
             roms/musics/drums \
             roms/musics/ducktales2 \
             roms/musics/jackal \
             roms/musics/nes_drums \
             roms/musics/supermario \
             roms/musics/synth

# Саундтреки — ROM с двумя вариантами сборки (обычный + _ay.rom).
SOUNDTRACKS = roms/musics/castlevania \
              roms/musics/ducktales2 \
              roms/musics/jackal \
              roms/musics/supermario

TESTS = roms/tests/512x256 \
        roms/tests/boot-demo \
        roms/tests/cls \
        roms/tests/clrs \
        roms/tests/colors \
        roms/tests/dt2 \
        roms/tests/dt2_512 \
        roms/tests/dt2_lz \
        roms/tests/fonts \
        roms/tests/scr_modes \
        roms/tests/snd_backends \
        roms/tests/tape_test

ALL = $(MUSIC_ROMS) $(TESTS)

RELEASE = release

MUSIC_ROM_NAMES = $(foreach p,$(MUSIC_ROMS),$(p)/$(notdir $(p)).rom)
MUSIC_ROM_AY    = $(foreach p,$(SOUNDTRACKS),$(p)/$(notdir $(p))_ay.rom)
TEST_NAMES      = $(foreach p,$(TESTS),$(p)/$(notdir $(p)).rom)

.PHONY: all clean full loader2

all:
	@for p in $(ALL); do $(MAKE) -C $$p || exit 1; done
	@mkdir -p $(RELEASE)/musics $(RELEASE)/tests
	@for rom in $(MUSIC_ROM_NAMES) $(MUSIC_ROM_AY); do \
		if [ -f "$$rom" ]; then cp -f "$$rom" $(RELEASE)/musics/; fi; \
	done
	@for rom in $(TEST_NAMES); do \
		if [ -f "$$rom" ]; then cp -f "$$rom" $(RELEASE)/tests/; fi; \
	done
	@echo "=== Release ready ==="
	@echo "musics/:" && ls -1 $(RELEASE)/musics/*.rom 2>/dev/null
	@echo "tests/:" && ls -1 $(RELEASE)/tests/*.rom 2>/dev/null

clean:
	@for p in $(ALL); do $(MAKE) -C $$p clean; done
	@rm -rf $(RELEASE)/musics $(RELEASE)/tests
	@echo "=== All cleaned ==="

full: clean all

# ---------------------------------------------------------------------------
# loader2 — пересборка второго загрузчика (stage-2) и перегенерация .inc.
# blob собирается отдельным прогоном ассемблера с ORG 0E000h и -m=8080_strict
# (метки сразу
# абсолютные — копир в lib/boot/loader.asm не требует релопации);
# utils/bin2inc.py проверяет бюджет кода 768 Б (область 0E000h..0E2FFh; сразу
# за ней — слоты панелей 0E300h/0EF00h) и пишет
# lib/boot/loader_stage2.inc;
# utils/disasm8080.py — контроль ТЗ §9.4 и §9.3: бинарь целиком должен
# декодироваться как i8080 (z80asm собирает Z80-расширения молча, сборка о них
# не скажет), а все 16-битные адресные операнды — попадать в 0E000..0E2FF
# (плюс заглушка reset 0000h..0002h, выходной PCHL на 0000h, плоскость C000
# и high RAM переменных/конфига); LXI исключён сознательно — это не обращение.
# Спека: docs/LOADER_TZ.MD.
# ---------------------------------------------------------------------------
Z80ASM ?= z88dk/bin/z80asm
PYTHON ?= python3

loader2:
	@mkdir -p .scratch
	$(Z80ASM) -b -m=8080_strict -s lib/boot/loader_stage2.asm -o.scratch/loader_stage2.bin
	@mv lib/boot/loader_stage2.sym .scratch/loader_stage2.sym   # метки нужны тесту раунд-трипа (§9.2)
	@rm -f lib/boot/loader_stage2.o                             # z80asm пишет их рядом с исходником
	$(PYTHON) utils/bin2inc.py .scratch/loader_stage2.bin \
	    lib/boot/loader_stage2.inc --label loader_stage2 --max 768 --origin 0e000h
	$(PYTHON) utils/disasm8080.py .scratch/loader_stage2.bin --org 0e000h --no-interrupts --refs 0e000-0e2ff --ref-allow 0000-0002,0c000-0dfff,0fb00-0fb0f,0fb10-0fb1f
