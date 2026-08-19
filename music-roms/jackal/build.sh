#!/bin/bash
set -e

Z88DK=/home/alexey/z88dk
export ZCCCFG="$Z88DK/lib/config"
export PATH="$Z88DK/bin:$PATH"

cd "$(dirname "$0")"

LIB=../../lib

echo "=== Building jackal.rom for Vector-06C ==="
if ! zcc +vector06c --no-crt -I"$LIB" \
    "$LIB/startup.asm" main.c \
    "$LIB/v06io.asm" "$LIB/v06pal.asm" "$LIB/kbdscan.asm" "$LIB/vi53out.asm" \
    "$LIB/graphpr.asm" \
    "$LIB/graph.c" "$LIB/sound.c" "$LIB/keyboard.c" \
    -o jackal.rom; then
    echo "*** BUILD FAILED ***"
    exit 1
fi

# Remove intermediate files
rm -f *.o zcc_opt.def

echo "=== Done: jackal.rom ==="
ls -l jackal.rom



ROMS_DIR=/home/alexey/snap/ppsspp-emu/common/.config/ppsspp/PSP/GAME/VECTOR06C/ROMS

if [ ! -f jackal.rom ]; then
    echo "jackal.rom not found, run ./build.sh first"
    exit 1
fi

echo "=== Copying jackal.rom to PPSSPP ROMS folder ==="
cp -f jackal.rom "$ROMS_DIR/jackal.rom"
ls -l "$ROMS_DIR/jackal.rom"
echo "Now launch PPSSPP and open jackal.rom from the VECTOR06C/ROMS folder."