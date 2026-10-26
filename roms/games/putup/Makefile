# Makefile — roms/games/putup: Putup со свободной компоновкой ROM (Stage-4).
#
# putup_new.rom (в корне проекта) = реконструкция Putup (asm-ветка redesign/putup)
# с запечённым блоком глифов data_glyph_block_unpacked и СВОБОДНОЙ КОНКАТАЕНАЦИЕЙ:
# emit-файлы идут подряд в порядке tools/order.json, закреплён только вход (0x0100).
# Мёртвый шлак (распаковщики/пакеты/legacy-blit) физически удалён; гэпов нет.
# Корректность — поведенческими гейтами (tools/compare_color.py, compare_behavior.py);
# адреса меток они берут из tools/layout.json (пишется из .sym после сборки).
#
# Компоновка: tools/gen_layout.py -> asm/putup_new.asm (порядок -> tools/order.json).
# Все данные — побайтовыми DEFB в asm-файлах, bin-артефактов нет.
# Режим 8080: -m=8080_strict.

include ../../../config.mk

ASMFLAGS  = -b -m=8080_strict -s
TARGET    = putup_new.rom
MAPFILE   = putup_new.map
FULLBIN   = build_full.bin
MASTER    = putup_new.asm
GEN       = tools/gen_layout.py
MANIFEST  = tools/mk_manifest.py
IMGADDR   = 0x100

# Карта символов (тот же формат, что у fire2/mario-8c) полезна дебаггеру:
# vector-debugger по `NAME = $ADDR` берёт адреса функций/RAM. KEEP_MAP=0 не
# влияет — .map нужен по умолчанию; clean убирает его вместе с артефактами.

.PHONY: all layout clean full deploy

all: $(TARGET)

# Перегенерировать компоновку (мастер-конкатенацию + tools/order.json) из asm/.
layout:
	@python3 $(GEN)

# ВНИМАНИЕ: мастер include-ит asm/funcs/*.asm и asm/data/*.asm — предок должен
# покрывать и подкаталоги, иначе добавление emit-файла в подкаталог не триггерит
# пересборку (тихий false-pass на устаревшем ROM).
$(TARGET): $(GEN) $(MANIFEST) $(wildcard asm/*.asm) $(wildcard asm/funcs/*.asm) $(wildcard asm/data/*.asm)
	@python3 $(GEN)
	@cd asm && $(Z80ASM) $(ASMFLAGS) -o=../$(FULLBIN) $(MASTER)
	@cp asm/$(MASTER:.asm=.sym) $(MAPFILE)
	@python3 $(MANIFEST)
	@python3 -c "d=open('$(FULLBIN)','rb').read();open('$(TARGET)','wb').write(d[256:])"
	@rm -f $(FULLBIN) asm/*.o asm/*.sym asm/*.err
	@echo "=== Done: $@ ($$(stat -c%s $@) bytes, конкатенация), map: $$(stat -c%s $(MAPFILE)) B ==="

full: clean all deploy

clean:
	rm -f $(TARGET) $(MAPFILE) $(FULLBIN) asm/*.o asm/*.sym asm/*.err

# Финализация по стандарту проекта: цели deploy/full.
include $(PROJECT_ROOT)finally.mk
