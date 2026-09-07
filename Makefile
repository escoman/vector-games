# Makefile — сборка всех ROM для Вектора-06Ц.
#
# make          — собрать все ROM, скопировать в release/;
# make clean    — убрать артефакты сборки всех проектов + папку release/;
# make full     — clean + сборка всех проектов.

MUSIC_ROMS = roms/musics/castlevania \
             roms/musics/drums \
             roms/musics/ducktales2 \
             roms/musics/jackal \
             roms/musics/nes_drums \
             roms/musics/supermario \
             roms/musics/synth

TESTS = roms/tests/512x256 \
        roms/tests/cls \
        roms/tests/clrs \
        roms/tests/dt2 \
        roms/tests/dt2_512 \
        roms/tests/dt2_lz \
        roms/tests/scr_modes

ALL = $(MUSIC_ROMS) $(TESTS)

RELEASE = release

MUSIC_ROM_NAMES = $(foreach p,$(MUSIC_ROMS),$(p)/$(notdir $(p)).rom)
TEST_NAMES      = $(foreach p,$(TESTS),$(p)/$(notdir $(p)).rom)

.PHONY: all clean full

all:
	@for p in $(ALL); do $(MAKE) -C $$p || exit 1; done
	@mkdir -p $(RELEASE)/musics $(RELEASE)/tests
	@for rom in $(MUSIC_ROM_NAMES); do \
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
