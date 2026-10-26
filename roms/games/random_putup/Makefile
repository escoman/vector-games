# Makefile — roms/games/random_putup: RANDOM PUTUP — OVERLAY-вариант игры putup.
#
# random_putup.rom = сборка НА ИСХОДНИКАХ putup (roms/games/putup/asm — база
# включается по относительным путям, копий исходников и symlink'ов нет) плюс
# «патч» overlay/:
#   overlay/funcs/<имя>.asm — замена файла базы с тем же именем;
#   overlay/splice.json     — вставка новых файлов (anchor "after"/"HEAD");
#   DEAD-список в tools/gen_layout.py — исключение файлов из образа.
# Порядок эмиссии = include-список собранного мастера базы. Закреплён только
# вход (0x0100), гэпов нет, ссылки символьны.
#
# Stage-0 gate: без замен/вставок в код — random_putup.rom побайтово == putup_new.rom.
# Поведенческие гейты оригинала (compare_color/compare_behavior) здесь не
# применимы; валидность random-сборки — tools/validate_random.py (Stage 4).
# Режим 8080: -m=8080_strict.

include ../../../config.mk

TARGET    = random_putup.rom
MAPFILE   = random_putup.map
FULLBIN   = build_full.bin
MASTER    = random_putup.asm
GEN       = tools/gen_layout.py
MANIFEST  = tools/mk_manifest.py
IMGADDR   = 0x100
BASE      = ../putup
BASE_ASM  = $(BASE)/asm
BASE_MASTER_DEP = $(BASE_ASM)/putup_new.asm

# -I../../putup/asm (путь ОТ CWD=asm/!): вложенные include базы (`data/...` внутри
# data_level_maps и т.п.) ищутся от CWD=asm/, находятся по пути к базе;
# сборка симметрична своей.
ASMFLAGS  = -b -m=8080_strict -s -I../../putup/asm

# Карта символов: vector-debugger берёт адреса функций/RAM из `NAME = $ADDR`.
# .map нужен по умолчанию; clean убирает его вместе с артефактами.

.PHONY: all clean full deploy

all: $(TARGET)

# ВНИМАНИЕ: предки покрывают БАЗУ putup/asm/* и overlay/, иначе правка базового
# файла не триггерит пересборку (тихий false-pass на устаревшем ROM). Порядок
# эмиссии читается из asm/putup_new.asm базы — сначала пересобираем базу.
$(TARGET): $(GEN) $(MANIFEST) $(BASE_MASTER_DEP) $(wildcard $(BASE_ASM)/*.asm) $(wildcard $(BASE_ASM)/funcs/*.asm) $(wildcard $(BASE_ASM)/data/*.asm) $(wildcard overlay/funcs/*.asm) $(wildcard overlay/data/*.asm) overlay/splice.json
	@$(MAKE) --no-print-directory -C $(BASE) all
	@python3 $(GEN)
	@cd asm && $(Z80ASM) $(ASMFLAGS) -o=../$(FULLBIN) $(MASTER)
	@cp asm/$(MASTER:.asm=.sym) $(MAPFILE)
	@python3 $(MANIFEST)
	@python3 -c "d=open('$(FULLBIN)','rb').read();open('$(TARGET)','wb').write(d[256:])"
	@rm -f $(FULLBIN) asm/*.o asm/*.sym asm/*.err
	@echo "=== Done: $@ ($$(stat -c%s $@) bytes, overlay-конкатенация), map: $$(stat -c%s $(MAPFILE)) B ==="

full: clean all deploy

clean:
	rm -f $(TARGET) $(MAPFILE) $(FULLBIN) asm/*.o asm/*.sym asm/*.err asm/$(MASTER)
	@# пережиток symlink-схемы: каталоги-дерево больше не генерируется
	rm -rf asm/funcs asm/data asm/var_ram_symbols.asm asm/rand_ram_symbols.asm

# Финализация по стандарту проекта: цели deploy/full.
include $(PROJECT_ROOT)finally.mk
