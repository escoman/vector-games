# Makefile — Stage 10: воспроизводимая сборка реконструированного BASIC.
#
# Ветвь A (побайтовый монолит, выбрана на Stage 9). Ключевая особенность
# таргета: объект — RAM-образ интерпретатора `basic.r0m` (org 0x0000,
# 17152 байта), а НЕ самораспаковывающийся `bas2997.rom` (org 0x0100 + LZ-стаб
# + staging в VRAM). Эмулятор грузит `.r0m` ровно в 0x0000 и стартует с
# reset-вектора — поэтому собранный образ запускается НАПРЯМУЮ, упаковщик для
# запуска не нужен. `pack` ниже даёт лишь сжатый дистрибутив (ZX0) как
# доказательство, что payload целостен; побайтовое совпадение с `bas2997.rom`
# невозможно (у оригинала свой forward-стаб) — это относят к аппаратной фазе.
#
# Ярусы приёмки:
#   verify (Tier 1, детерминированный): src/basic_new.r0m == src/basic.r0m
#            байт-в-байт.   Tier 2 (поведенческий, functional-батарея) — Stage 10.2.
#
#   make layout    — перегенерировать asm/ из RDB + выхода экспортёра (Stage 9 tool)
#   make           — собрать src/basic_new.r0m из asm/basic_new.asm (org 0x0000)
#   make verify    — побайтовая сверка RAM-образа с эталоном basic.r0m
#   make pack      — ZX0-поток из basic_new.r0m + self-verify round-trip
#   make snapshot  — СНОВО снять basic.r0m с bas2997.rom в эмуляторе (нужен MCP)
#   make deploy    — положить basic_new.r0m в ROMS эмулятора (finally.mk)
#   make full      — clean + all + deploy

include ../../../config.mk

# TARGET — собранный RAM-образ (boot напрямую в 0x0000).
# ROMIMG   — эталон Stage 0 (17152, отслеживается git).
# MASTER   — единственный вход сборки (org 0x0000).
# PACKED   — сжатый дистрибутив (build-продукт).
# LAYOUT   — генератор asm-дерева (Stage 9).
ASMFLAGS = -b -m=8080_strict
TARGET   = src/basic_new.r0m
ROMIMG   = src/basic.r0m
MASTER   = basic_new.asm
PACKED   = src/basic_new.zx0
LAYOUT   = tools/stage9_asm_layout.py

.PHONY: all layout build verify pack snapshot clean full deploy

all: $(TARGET)

# Перегенерировать asm/{code,equates,basic_new}.asm из RDB + layout.asm.
# Пути внутри инструмента резолвятся от корня проекта (функция _abs), cd не нужен.
layout:
	@PYTHONPATH=$(PROJECT_ROOT)utils python3 $(LAYOUT) --apply

# Сборка RAM-образа: z80asm, org 0x0000 -> полный файл 17152 байт (без среза).
$(TARGET): asm/$(MASTER) asm/code.asm asm/equates.asm
	@cd asm && $(Z80ASM) $(ASMFLAGS) -o=../$(TARGET) $(MASTER)
	@rm -f asm/*.o asm/*.sym
	@echo "=== built $@ ($$(stat -c%s $@) bytes) ==="

build: $(TARGET)

# Tier 1: побайтовая сверка собранного образа с эталоном basic.r0m.
verify: $(TARGET)
	@python3 -c "a=open('$(ROMIMG)','rb').read(); b=open('$(TARGET)','rb').read(); \
	 d=sum(x!=y for x,y in zip(a,b)) + abs(len(a)-len(b)); \
	 print('RAM image: new=%d ref=%d ; byte diffs=%d' % (len(b),len(a),d)); \
	 exit(0 if d==0 else 1)"
	@echo "verify: basic_new.r0m идентичен basic.r0m (RAM-образ, байт-в-байт)"

# Сжатый дистрибутив: ZX0-поток + self-verify (zx0.decompress == исходник).
pack: $(TARGET)
	@python3 -c "import sys; sys.path.insert(0,'$(PROJECT_ROOT)utils'); import zx0; \
	 d=open('$(TARGET)','rb').read(); p=zx0.compress(d); open('$(PACKED)','wb').write(p); \
	 assert zx0.decompress(p)==d, 'ZX0 round-trip не сошёлся'; \
	 print('pack: ZX0 %d -> %d байт (%.1f%%), decompress round-trip OK' \
	       % (len(d), len(p), 100.0*len(p)/len(d)))"

# Съёмка эталона с живого образа (требует запущенный MCP-эмулятор; opt-in).
snapshot:
	@PYTHONPATH=$(PROJECT_ROOT)utils python3 tools/dump_interp.py

full: clean all deploy

clean:
	@rm -f $(TARGET) $(PACKED) asm/*.o asm/*.sym asm/*.err

# Финализация по стандарту проекта: цели deploy/full.
include $(PROJECT_ROOT)finally.mk
