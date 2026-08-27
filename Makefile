# Makefile — сборка всех music-ROM для Вектора-06Ц.
#
# make          — собрать все ROM, скопировать в release/ вместе с README;
# make clean    — убрать артефакты сборки всех проектов + папку release/;
# make full     — clean + сборка всех проектов.

PROJECTS = music-roms/castlevania \
           music-roms/drums \
           music-roms/ducktales2 \
           music-roms/jackal \
           music-roms/nes_drums \
           music-roms/synth

RELEASE  = release

ROMS     = $(foreach p,$(PROJECTS),$(p)/$(notdir $(p)).rom)

.PHONY: all clean full

all:
	@for p in $(PROJECTS); do $(MAKE) -C $$p || exit 1; done
	@mkdir -p $(RELEASE)
	@for rom in $(ROMS); do \
		if [ -f "$$rom" ]; then cp -f "$$rom" $(RELEASE)/; fi; \
	done
	@echo "=== Release ready in $(RELEASE)/ ==="
	@ls -l $(RELEASE)/*.rom

clean:
	@for p in $(PROJECTS); do $(MAKE) -C $$p clean; done
	rm -rf $(RELEASE)
	@echo "=== All cleaned ==="

full: clean all
