# Makefile — сборка castlevania.rom для Вектора-06Ц (z88dk / zcc).
#
# make          — собрать castlevania.rom (пересобирается при изменении
#                 любого исходника из $(SRCS)); заставка
#                 rom_data/title_bmp.inc генерируется bmp2inc.py
#                 из rom_data/title.bmp;
# make clean    — убрать все артефакты сборки;
# make deploy   — собрать и положить ROM в папку ROMS эмулятора PPSSPP;
# make full     — clean + сборка + deploy последовательно.
#
# Путь до z88dk можно переопределить: make Z88DK=...

Z88DK   ?= /home/alexey/z88dk
ZCC      = $(Z88DK)/bin/zcc
ZCCCFG  := $(Z88DK)/lib/config
LIB      = ../../lib
BMP2INC  = ../../utils/bmp2inc.py
PPSSPP_ROMS = /home/alexey/snap/ppsspp-emu/common/.config/ppsspp/PSP/GAME/VECTOR06C/ROMS

TARGET   = castlevania.rom

# Пока только заставка; когда появятся партитуры music/*.mus, сюда
# вернутся правила mus2inc.py и music.c/drums.asm (см. jackal/Makefile).
SRCS     = $(LIB)/startup.asm main.c \
           $(LIB)/v06io.asm $(LIB)/v06pal.asm $(LIB)/kbdscan.asm \
           $(LIB)/graphpr.asm $(LIB)/graphrle.asm $(LIB)/graphclr.asm \
           $(LIB)/graph.c $(LIB)/keyboard.c

ZFLAGS   = +vector06c --no-crt -I$(LIB)

.PHONY: all deploy clean full

all: $(TARGET)

full: clean
	$(MAKE) deploy

rom_data/title_bmp.inc: rom_data/title.bmp $(BMP2INC)
	python3 $(BMP2INC) $<

$(TARGET): $(SRCS) rom_data/title_bmp.inc
	ZCCCFG=$(ZCCCFG) PATH="$(Z88DK)/bin:$$PATH" \
	    $(ZCC) $(ZFLAGS) $(SRCS) -o $@
	@echo "=== Done: $@ ==="
	@ls -l $@

deploy: $(TARGET)
	cp -f $(TARGET) $(PPSSPP_ROMS)/$(TARGET)
	@echo "=== Deployed to $(PPSSPP_ROMS)/$(TARGET) ==="

clean:
	rm -f $(TARGET) *.o zcc_opt.def *.c.asm
