# Makefile — сборка clrs_new.rom для Вектора-06Ц.

include ../../../config.mk

Z80ASM   = $(Z88DK)/bin/z80asm
TARGET = clrs_new.rom
SRCS = clrs_new.asm

.PHONY: all deploy clean full

all: $(TARGET)

full: clean all deploy

$(TARGET):
	$(Z80ASM) -b -o=$@ $(SRCS)
	@echo "=== Done: $@ ==="
	@ls -l $@

include $(PROJECT_ROOT)finally.mk

clean:
	rm -f $(TARGET) *.o *.bin *.sym
