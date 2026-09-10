# Stage 7: Text Rendering & Glyph Analysis

## Context
Investigating text output functions in `putup.rom` (Vector-06C). Need to find all text strings, the text rendering function, glyph data block, and export glyphs to BMP.

## Key Findings So Far
- **English strings** at ROM 0x0AC7: "PUSH SPACE KEY", "MSX MAGAZINE, 1987", "HI ", "SCORE ", "ROUND ", "TIME ", " HURRY UP ! ", "GAME OVER", "CONGRATULATION !", "BONUS 5000 POINTS"
- **Russian strings** at ROM 0x0918 (KOI-8): "ВЕРСИЯ ДЛЯ ПР-06Ц 1991", "ЦЕНТР КОМПЬЮТЕР г.КИШИНЕВ"
- **draw_to_vram** (0x0800): Core VRAM write function, uses lookup table at 0x051B
- **data_process_loop** (0x0C65): Scans RAM 0x5180 for markers, calls draw_to_vram
- **copy_to_vram_3DCD** (0x3DCD): Called from data_process_loop area — not yet analyzed

## Next Steps
1. Analyze `copy_to_vram_3DCD` at 0x3DCD — likely the text rendering function
2. Examine lookup table at 0x051B (glyph pointer table?)
3. Check graphics RAM area 0x6000-0x7FFF for glyph data
4. Find code that reads from text string RAM area (0x51A0+)
5. Create RDB objects for all strings and glyph block
6. Export glyphs to BMP in ./dest/
7. Write Stage7.md report

## Files
- ROM: `/home/alexey/Projects/vector-games/roms/redesign/putup/src/putup.rom`
- RDB: `/home/alexey/Projects/vector-games/roms/redesign/putup/src/putup.rdb`
- Report: `/home/alexey/Projects/vector-games/roms/redesign/putup/reports/Stage7.md`
- Glyphs BMP: `/home/alexey/Projects/vector-games/roms/redesign/putup/dest/glyphs.bmp`
