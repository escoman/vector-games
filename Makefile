# Makefile — сборка всех ROM для Вектора-06Ц.
#
# make          — собрать все ROM, скопировать в release/;
# make clean    — убрать артефакты сборки всех проектов + папку release/;
# make full     — clean + сборка всех проектов.

MUSIC_ROMS = music-roms/castlevania \
             music-roms/drums \
             music-roms/ducktales2 \
             music-roms/jackal \
             music-roms/nes_drums \
             music-roms/supermario \
             music-roms/synth

TESTS = tests/512x256 \
        tests/cls \
        tests/clrs \
        tests/dt2 \
        tests/dt2_512 \
        tests/dt2_lz

ALL = $(MUSIC_ROMS) $(TESTS)

RELEASE = release

MUSIC_ROM_NAMES = $(foreach p,$(MUSIC_ROMS),$(p)/$(notdir $(p)).rom)
TEST_NAMES      = $(foreach p,$(TESTS),$(p)/$(notdir $(p)).rom)

.PHONY: all clean full

all:
	@for p in $(ALL); do $(MAKE) -C $$p || exit 1; done
	@mkdir -p $(RELEASE)/music-roms $(RELEASE)/tests
	@for rom in $(MUSIC_ROM_NAMES); do \
		if [ -f "$$rom" ]; then cp -f "$$rom" $(RELEASE)/music-roms/; fi; \
	done
	@for rom in $(TEST_NAMES); do \
		if [ -f "$$rom" ]; then cp -f "$$rom" $(RELEASE)/tests/; fi; \
	done
	@echo "=== Release ready ==="
	@echo "music-roms/:" && ls -1 $(RELEASE)/music-roms/*.rom 2>/dev/null
	@echo "tests/:" && ls -1 $(RELEASE)/tests/*.rom 2>/dev/null

clean:
	@for p in $(ALL); do $(MAKE) -C $$p clean; done
	@rm -rf $(RELEASE)/music-roms $(RELEASE)/tests
	@echo "=== All cleaned ==="

full: clean all
