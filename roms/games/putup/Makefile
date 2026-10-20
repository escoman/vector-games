# Makefile — roms/games/putup: Putup со свободной компоновкой ROM (Stage-4).
#
# PUTUP_NEW.ROM (в корне проекта) = реконструкция Putup (asm-ветка redesign/putup)
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
TARGET    = PUTUP_NEW.ROM
FULLBIN   = build_full.bin
MASTER    = putup_new.asm
GEN       = tools/gen_layout.py
MANIFEST  = tools/mk_manifest.py
IMGADDR   = 0x100

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
	@python3 $(MANIFEST)
	@python3 -c "d=open('$(FULLBIN)','rb').read();open('$(TARGET)','wb').write(d[256:])"
	@rm -f $(FULLBIN) asm/*.o asm/*.sym asm/*.err
	@echo "=== Done: $@ ($$(stat -c%s $@) bytes, конкатенация) ==="

full: clean all deploy

clean:
	rm -f $(TARGET) $(FULLBIN) asm/*.o asm/*.sym asm/*.err

# Финализация по стандарту проекта: цели deploy/full.
include $(PROJECT_ROOT)finally.mk
