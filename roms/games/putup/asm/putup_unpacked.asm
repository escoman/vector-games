; PUTUP_NEW.ROM (games/putup) — putup с РАСПАКОВАННЫМИ данными
; ГЕНЕРАТОР tools/gen_layout.py — не править руками.
; РЕЖИМ COMPACT (Фаза 2): мёртвые дыры [0x2761,0x2F61)+[0x3041,0x383A) вырезаны;
; объекты >=0x2761 сдвинуты вверх (new_addr, суммарный сдвиг -4089 Б);
; byte-exact сохранён только для [0x0100,0x2761); выше — поведенческая сверка.
; 0x3608..0x49BF: data_glyph_block_unpacked (5048 Б, снимок пост-иниц 0x6000..0x7FFF).

    org 0h
    include "var_ram_symbols.asm"
    include "var_reloc_anchors.asm"

; --- emit func_entry @0x0100 (4 bytes) ---
    defs 0x0100 - $ ; align
    include "funcs/func_entry.asm"

; --- emit func_draw_tile_at_ptr @0x0104 (29 bytes) ---
    defs 0x0104 - $ ; align
    include "funcs/func_draw_tile_at_ptr.asm"

; --- emit func_sound_init @0x0121 (36 bytes) ---
    defs 0x0121 - $ ; align
    include "funcs/func_sound_init.asm"

; --- emit func_draw_char_at_hl @0x0145 (10 bytes) ---
    defs 0x0145 - $ ; align
    include "funcs/func_draw_char_at_hl.asm"

; --- emit func_set_text_ptr @0x014F (4 bytes) ---
    defs 0x014F - $ ; align
    include "funcs/func_set_text_ptr.asm"

; --- emit func_decode_key @0x0153 (25 bytes) ---
    defs 0x0153 - $ ; align
    include "funcs/func_decode_key.asm"

; --- emit data_keycode_table @0x016C (16 bytes) ---
    defs 0x016C - $ ; align
    include "data/data_keycode_table.asm"

; --- emit func_check_start_key @0x017C (27 bytes) ---
    defs 0x017C - $ ; align
    include "funcs/func_check_start_key.asm"

; --- emit func_read_keybuf @0x0197 (10 bytes) ---
    defs 0x0197 - $ ; align
    include "funcs/func_read_keybuf.asm"

; --- emit func_print_char_at_ptr @0x01A1 (13 bytes) ---
    defs 0x01A1 - $ ; align
    include "funcs/func_print_char_at_ptr.asm"

; --- emit func_restore_cursor @0x01AE (14 bytes) ---
    defs 0x01AE - $ ; align
    include "funcs/func_restore_cursor.asm"

; --- emit func_sound_op @0x01BC (17 bytes) ---
    defs 0x01BC - $ ; align
    include "funcs/func_sound_op.asm"

; --- emit data_snd_dispatch_table @0x01CD (32 bytes) ---
    defs 0x01CD - $ ; align
    include "data/data_snd_dispatch_table.asm"

; --- gap 0x01ED..0x0201 (20 bytes) from original image @reloc 0x01ED ---
    defs 0x01ED - $ ; align
    DEFB 07Bh, 032h, 01Ah, 03h, 0CDh, 01h, 02h, 0C3h
    DEFB 06Ah, 02h, 07Bh, 032h, 01Bh, 03h, 0CDh, 01h
    DEFB 02h, 0C3h, 06Ah, 02h
; --- emit func_snd_out_ch0 @0x0201 (13 bytes) ---
    defs 0x0201 - $ ; align
    include "funcs/func_snd_out_ch0.asm"

; --- emit func_snd_calc_period @0x020E (11 bytes) ---
    defs 0x020E - $ ; align
    include "funcs/func_snd_calc_period.asm"

; --- gap 0x0219..0x022D (20 bytes) from original image @reloc 0x0219 ---
    defs 0x0219 - $ ; align
    DEFB 07Bh, 032h, 01Ch, 03h, 0CDh, 02Dh, 02h, 0C3h
    DEFB 06Ah, 02h, 07Bh, 032h, 01Dh, 03h, 0CDh, 02Dh
    DEFB 02h, 0C3h, 06Ah, 02h
; --- emit func_snd_out_ch1 @0x022D (13 bytes) ---
    defs 0x022D - $ ; align
    include "funcs/func_snd_out_ch1.asm"

; --- gap 0x023A..0x024E (20 bytes) from original image @reloc 0x023A ---
    defs 0x023A - $ ; align
    DEFB 07Bh, 032h, 01Eh, 03h, 0CDh, 04Eh, 02h, 0C3h
    DEFB 06Ah, 02h, 07Bh, 032h, 01Fh, 03h, 0CDh, 04Eh
    DEFB 02h, 0C3h, 06Ah, 02h
; --- emit func_snd_out_ch2 @0x024E (13 bytes) ---
    defs 0x024E - $ ; align
    include "funcs/func_snd_out_ch2.asm"

; --- gap 0x025B..0x026E (19 bytes) from original image @reloc 0x025B ---
    defs 0x025B - $ ; align
    DEFB 0C3h, 06Ah, 02h, 0C3h, 06Ah, 02h, 0C3h, 06Ah
    DEFB 02h, 0C3h, 06Ah, 02h, 0CDh, 06Eh, 02h, 0F1h
    DEFB 0D1h, 0E1h, 0C9h
; --- emit func_snd_toggle @0x026E (18 bytes) ---
    defs 0x026E - $ ; align
    include "funcs/func_snd_toggle.asm"

; --- emit data_snd_toggle_table @0x0280 (16 bytes) ---
    defs 0x0280 - $ ; align
    include "data/data_snd_toggle_table.asm"

; --- emit func_snd_enable_ch0 @0x0290 (14 bytes) ---
    defs 0x0290 - $ ; align
    include "funcs/func_snd_enable_ch0.asm"

; --- emit func_snd_enable_ch1 @0x029E (14 bytes) ---
    defs 0x029E - $ ; align
    include "funcs/func_snd_enable_ch1.asm"

; --- emit func_snd_enable_ch2 @0x02AC (14 bytes) ---
    defs 0x02AC - $ ; align
    include "funcs/func_snd_enable_ch2.asm"

; --- emit func_snd_enable_ch01 @0x02BA (6 bytes) ---
    defs 0x02BA - $ ; align
    include "funcs/func_snd_enable_ch01.asm"

; --- emit func_snd_enable_ch02 @0x02C0 (6 bytes) ---
    defs 0x02C0 - $ ; align
    include "funcs/func_snd_enable_ch02.asm"

; --- emit func_snd_enable_ch12 @0x02C6 (6 bytes) ---
    defs 0x02C6 - $ ; align
    include "funcs/func_snd_enable_ch12.asm"

; --- emit func_snd_enable_ch012 @0x02CC (6 bytes) ---
    defs 0x02CC - $ ; align
    include "funcs/func_snd_enable_ch012.asm"

; --- emit func_snd_gate_ch0 @0x02D2 (24 bytes) ---
    defs 0x02D2 - $ ; align
    include "funcs/func_snd_gate_ch0.asm"

; --- emit func_snd_gate_ch1 @0x02EA (24 bytes) ---
    defs 0x02EA - $ ; align
    include "funcs/func_snd_gate_ch1.asm"

; --- emit func_snd_gate_ch2 @0x0302 (24 bytes) ---
    defs 0x0302 - $ ; align
    include "funcs/func_snd_gate_ch2.asm"

; --- gap 0x031A..0x0321 (7 bytes) from original image @reloc 0x031A ---
    defs 0x031A - $ ; align
    DEFB 01h, 01h, 01h, 01h, 01h, 01h, 0FFh
; --- emit func_print_string @0x0321 (11 bytes) ---
    defs 0x0321 - $ ; align
    include "funcs/func_print_string.asm"

; --- emit func_hl_add_a @0x032C (5 bytes) ---
    defs 0x032C - $ ; align
    include "funcs/func_hl_add_a.asm"

; --- emit func_print_uint16 @0x0331 (36 bytes) ---
    defs 0x0331 - $ ; align
    include "funcs/func_print_uint16.asm"

; --- emit func_divmod_u16 @0x0355 (15 bytes) ---
    defs 0x0355 - $ ; align
    include "funcs/func_divmod_u16.asm"

; --- gap 0x0364..0x0383 (31 bytes) from original image @reloc 0x0364 ---
    defs 0x0364 - $ ; align
    DEFB 0F6h, 030h, 0F5h, 0FEh, 030h, 0CAh, 071h, 03h
    DEFB 03Eh, 01h, 032h, 0E2h, 08h, 03Ah, 0E2h, 08h
    DEFB 0B7h, 0C2h, 07Fh, 03h, 03Eh, 020h, 0CDh, 0A1h
    DEFB 01h, 0F1h, 0C9h, 0F1h, 0C3h, 0A1h, 01h
; --- emit func_hw_init @0x0383 (33 bytes) ---
    defs 0x0383 - $ ; align
    include "funcs/func_hw_init.asm"

; --- emit func_vblank_isr @0x03A4 (93 bytes) ---
    defs 0x03A4 - $ ; align
    include "funcs/func_vblank_isr.asm"

; --- gap 0x0401..0x0439 (56 bytes) from original image @reloc 0x0401 ---
    defs 0x0401 - $ ; align
    DEFB 00h, 00h, 00h, 00h, 00h, 00h, 00h, 00h
    DEFB 00h, 00h, 00h, 00h, 00h, 00h, 00h, 00h
    DEFB 00h, 00h, 00h, 00h, 00h, 00h, 00h, 00h
    DEFB 00h, 00h, 00h, 00h, 00h, 00h, 00h, 00h
    DEFB 00h, 00h, 00h, 00h, 00h, 00h, 00h, 00h
    DEFB 00h, 00h, 00h, 00h, 00h, 00h, 00h, 00h
    DEFB 00h, 00h, 00h, 00h, 00h, 00h, 00h, 00h
; --- emit func_blit_plane_mask80 @0x0439 (37 bytes) ---
    defs 0x0439 - $ ; align
    include "funcs/func_blit_plane_mask80.asm"

; --- emit func_blit_plane_mask40 @0x045E (37 bytes) ---
    defs 0x045E - $ ; align
    include "funcs/func_blit_plane_mask40.asm"

; --- emit func_blit_plane_mask20 @0x0483 (37 bytes) ---
    defs 0x0483 - $ ; align
    include "funcs/func_blit_plane_mask20.asm"

; --- emit func_blit_plane_mask10 @0x04A8 (37 bytes) ---
    defs 0x04A8 - $ ; align
    include "funcs/func_blit_plane_mask10.asm"

; --- gap 0x04CD..0x051B (78 bytes) from original image @reloc 0x04CD ---
    defs 0x04CD - $ ; align
    DEFB 00h, 00h, 00h, 00h, 00h, 00h, 00h, 00h
    DEFB 00h, 00h, 00h, 00h, 00h, 00h, 00h, 00h
    DEFB 00h, 00h, 00h, 00h, 00h, 00h, 00h, 00h
    DEFB 00h, 00h, 00h, 00h, 00h, 00h, 00h, 00h
    DEFB 00h, 00h, 00h, 00h, 00h, 00h, 00h, 00h
    DEFB 00h, 00h, 00h, 00h, 00h, 00h, 00h, 00h
    DEFB 00h, 00h, 00h, 00h, 00h, 00h, 00h, 00h
    DEFB 00h, 00h, 00h, 00h, 00h, 00h, 00h, 00h
    DEFB 00h, 00h, 00h, 00h, 00h, 00h, 00h, 00h
    DEFB 00h, 00h, 00h, 00h, 00h, 00h
; --- emit data_vram_col_table @0x051B (32 bytes) ---
    defs 0x051B - $ ; align
    include "data/data_vram_col_table.asm"

; --- gap 0x053B..0x0600 (197 bytes) from original image @reloc 0x053B ---
    defs 0x053B - $ ; align
    DEFB 0CDh, 015h, 00h, 0CDh, 015h, 00h, 0C9h, 021h
    DEFB 00h, 00h, 039h, 022h, 013h, 00h, 03Ah, 010h
    DEFB 00h, 0B7h, 0CAh, 064h, 03h, 021h, 0FFh, 0FFh
    DEFB 022h, 0Eh, 00h, 03Ch, 0C2h, 064h, 03h, 03Ch
    DEFB 032h, 010h, 00h, 02Ah, 0Ch, 00h, 0C3h, 08Ah
    DEFB 03h, 0CDh, 091h, 06h, 0C2h, 033h, 05h, 021h
    DEFB 010h, 00h, 07Eh, 0B7h, 0CAh, 076h, 03h, 035h
    DEFB 0CAh, 033h, 05h, 02Ah, 0Ch, 00h, 0CDh, 094h
    DEFB 06h, 0CDh, 02Eh, 00h, 0Eh, 020h, 0CDh, 015h
    DEFB 00h, 0CDh, 015h, 00h, 0CDh, 02Eh, 03h, 0CDh
    DEFB 096h, 02h, 057h, 021h, 038h, 05h, 01h, 011h
    DEFB 00h, 0BEh, 0CAh, 0F0h, 04h, 023h, 0Dh, 0C2h
    DEFB 094h, 03h, 0Eh, 0Ah, 0BEh, 0CAh, 0DCh, 04h
    DEFB 023h, 0Dh, 0C2h, 09Fh, 03h, 0Eh, 06h, 0BEh
    DEFB 0CAh, 0C1h, 04h, 023h, 0Dh, 0C2h, 0AAh, 03h
    DEFB 0E6h, 0C0h, 0FEh, 040h, 0CAh, 0A7h, 04h, 0FEh
    DEFB 080h, 0CAh, 098h, 04h, 07Ah, 0E6h, 0C7h, 0D6h
    DEFB 04h, 0CAh, 089h, 04h, 03Dh, 0CAh, 083h, 04h
    DEFB 03Dh, 0CAh, 06Fh, 04h, 07Ah, 0E6h, 0C0h, 0CAh
    DEFB 03Dh, 04h, 07Ah, 0E6h, 07h, 0CAh, 032h, 04h
    DEFB 0D6h, 02h, 0CAh, 027h, 04h, 0D6h, 02h, 0CAh
    DEFB 01Ch, 04h, 0D6h, 03h, 0CAh, 0Dh, 04h, 07Ah
    DEFB 0E6h, 08h, 0C2h, 0FEh, 04h, 07Ah, 0E6h, 07h
    DEFB 04Fh, 03Dh, 021h, 02Ch, 06h, 09h, 0CDh, 0E6h
    DEFB 02h, 0CDh, 0F6h, 02h, 0FEh
; --- emit data_glyph_ptr_table @0x0600 (512 bytes) ---
    defs 0x0600 - $ ; align
    include "data/data_glyph_ptr_table.asm"

; --- emit func_put_char @0x0800 (3 bytes) ---
    defs 0x0800 - $ ; align
    include "funcs/func_put_char.asm"

; --- emit func_render_glyph @0x0803 (192 bytes) ---
    defs 0x0803 - $ ; align
    include "funcs/func_render_glyph.asm"

; --- gap 0x08C3..0x0925 (98 bytes) from original image @reloc 0x08C3 ---
    defs 0x08C3 - $ ; align
    DEFB 03h, 00h, 0Ch, 00h, 022h, 05Eh, 019h, 022h
    DEFB 020h, 01Ah, 022h, 0EEh, 019h, 021h, 00h, 01h
    DEFB 031h, 01Eh, 01Ah, 0E5h, 021h, 02h, 00h, 0E5h
    DEFB 02Bh, 02Bh, 022h, 01Eh, 01h, 0E5h, 00h, 022h
    DEFB 00h, 00h, 00h, 00h, 00h, 00h, 00h, 021h
    DEFB 079h, 06h, 022h, 029h, 00h, 03Ah, 05Dh, 00h
    DEFB 0FEh, 020h, 00h, 00h, 06h, 021h, 00h, 00h
    DEFB 0C3h, 0E5h, 0Dh, 031h, 016h, 01Ah, 0CDh, 04Eh
    DEFB 012h, 0Eh, 01h, 0C4h, 097h, 06h, 0CDh, 044h
    DEFB 012h, 03Eh, 023h, 0CDh, 0EFh, 011h, 0CDh, 0DEh
    DEFB 011h, 0CDh, 06h, 012h, 0FEh, 0Dh, 0CAh, 0FEh
    DEFB 06h, 021h, 045h, 019h, 036h, 00h, 0FEh, 02Dh
    DEFB 0C2h, 02Ah
; --- emit str_credits_koi8 @0x0925 (126 bytes) ---
    defs 0x0925 - $ ; align
    include "data/str_credits_koi8.asm"

; --- gap 0x09A3..0x0A06 (99 bytes) from original image @reloc 0x09A3 ---
    defs 0x09A3 - $ ; align
    DEFB 01h, 01h, 02h, 01h, 01h, 01h, 01h, 01h
    DEFB 01h, 01h, 01h, 01h, 01h, 01h, 01h, 01h
    DEFB 01h, 01h, 01h, 01h, 01h, 01h, 01h, 01h
    DEFB 01h, 01h, 01h, 01h, 01h, 01h, 01h, 01h
    DEFB 01h, 01h, 01h, 01h, 01h, 01h, 01h, 01h
    DEFB 01h, 01h, 01h, 01h, 01h, 01h, 01h, 01h
    DEFB 01h, 01h, 01h, 01h, 01h, 01h, 01h, 01h
    DEFB 01h, 01h, 01h, 01h, 01h, 01h, 01h, 01h
    DEFB 01h, 01h, 01h, 02h, 02h, 06h, 06h, 06h
    DEFB 06h, 02h, 08h, 08h, 02h, 06h, 06h, 06h
    DEFB 06h, 02h, 02h, 02h, 02h, 02h, 02h, 02h
    DEFB 02h, 02h, 02h, 02h, 02h, 02h, 02h, 02h
    DEFB 02h, 02h, 02h
; --- emit str_title_logo @0x0A06 (193 bytes) ---
    defs 0x0A06 - $ ; align
    include "data/str_title_logo.asm"

; --- emit str_push_space @0x0AC7 (15 bytes) ---
    defs 0x0AC7 - $ ; align
    include "data/str_push_space.asm"

; --- emit str_msx_magazine @0x0AD6 (19 bytes) ---
    defs 0x0AD6 - $ ; align
    include "data/str_msx_magazine.asm"

; --- emit str_hi @0x0AE9 (4 bytes) ---
    defs 0x0AE9 - $ ; align
    include "data/str_hi.asm"

; --- emit str_score @0x0AED (7 bytes) ---
    defs 0x0AED - $ ; align
    include "data/str_score.asm"

; --- emit str_round @0x0AF4 (7 bytes) ---
    defs 0x0AF4 - $ ; align
    include "data/str_round.asm"

; --- emit str_time @0x0AFB (6 bytes) ---
    defs 0x0AFB - $ ; align
    include "data/str_time.asm"

; --- emit str_hurry_up @0x0B01 (13 bytes) ---
    defs 0x0B01 - $ ; align
    include "data/str_hurry_up.asm"

; --- emit str_game_over @0x0B0E (10 bytes) ---
    defs 0x0B0E - $ ; align
    include "data/str_game_over.asm"

; --- emit str_congratulation @0x0B18 (17 bytes) ---
    defs 0x0B18 - $ ; align
    include "data/str_congratulation.asm"

; --- emit str_bonus @0x0B29 (19 bytes) ---
    defs 0x0B29 - $ ; align
    include "data/str_bonus.asm"

; --- gap 0x0B3C..0x0B57 (27 bytes) from original image @reloc 0x0B3C ---
    defs 0x0B3C - $ ; align
    DEFB 08h, 0DAh, 0FEh, 06h, 07Dh, 02h, 03h, 0C3h
    DEFB 03Ah, 09h, 0AFh, 032h, 03Fh, 019h, 0CDh, 044h
    DEFB 012h, 0CDh, 04Ah, 014h, 032h, 040h, 019h, 0CDh
    DEFB 0E1h, 012h, 0E5h
; --- emit func_main_init @0x0B57 (270 bytes) ---
    defs 0x0B57 - $ ; align
    include "funcs/func_main_init.asm"

; --- emit lbl_title_key_poll @0x0C65 (62 bytes) ---
    defs 0x0C65 - $ ; align
    include "funcs/lbl_title_key_poll.asm"

; --- emit func_erase_char_08E9 @0x0CA3 (61 bytes) ---
    defs 0x0CA3 - $ ; align
    include "funcs/func_erase_char_08E9.asm"

; --- emit func_game_update @0x0CE0 (421 bytes) ---
    defs 0x0CE0 - $ ; align
    include "funcs/func_game_update.asm"

; --- emit lbl_main_game_loop @0x0E85 (114 bytes) ---
    defs 0x0E85 - $ ; align
    include "funcs/lbl_main_game_loop.asm"

; --- emit func_delay @0x0EF7 (18 bytes) ---
    defs 0x0EF7 - $ ; align
    include "funcs/func_delay.asm"

; --- emit func_score_and_redraw @0x0F09 (48 bytes) ---
    defs 0x0F09 - $ ; align
    include "funcs/func_score_and_redraw.asm"

; --- gap 0x0F39..0x1123 (490 bytes) from original image @reloc 0x0F39 ---
    defs 0x0F39 - $ ; align
    DEFB 02Ah, 0F3h, 08h, 01h, 064h, 00h, 09h, 022h
    DEFB 0F3h, 08h, 021h, 0Fh, 09h, 034h, 07Eh, 07h
    DEFB 0C6h, 017h, 032h, 0FEh, 08h, 03Eh, 018h, 032h
    DEFB 0FFh, 08h, 0CDh, 0AEh, 01h, 03Eh, 072h, 0CDh
    DEFB 0A1h, 01h, 03Eh, 06Dh, 0CDh, 0A1h, 01h, 0C3h
    DEFB 025h, 0Fh, 021h, 0FBh, 08h, 034h, 0CDh, 0E9h
    DEFB 011h, 0C3h, 028h, 0Fh, 03Eh, 06h, 032h, 0Ch
    DEFB 09h, 021h, 0E3h, 08h, 03Ah, 01h, 09h, 0BEh
    DEFB 0C2h, 085h, 0Fh, 023h, 03Ah, 02h, 09h, 0BEh
    DEFB 02Bh, 0CAh, 088h, 0Fh, 0CDh, 04h, 01h, 03Ah
    DEFB 01h, 09h, 06Fh, 03Ah, 02h, 09h, 067h, 022h
    DEFB 0E3h, 08h, 0EBh, 03Ah, 0Ch, 09h, 087h, 087h
    DEFB 021h, 0DEh, 026h, 0CDh, 02Ch, 03h, 0CDh, 0A8h
    DEFB 01Bh, 02Ah, 0E9h, 08h, 023h, 07Dh, 0E6h, 01Fh
    DEFB 022h, 0E9h, 08h, 0C2h, 0D1h, 0Fh, 06h, 02h
    DEFB 0CDh, 021h, 01h, 0CDh, 0A3h, 0Ch, 06h, 01h
    DEFB 0CDh, 0F7h, 0Eh, 02Ah, 0F3h, 08h, 01h, 0Ah
    DEFB 00h, 09h, 022h, 0F3h, 08h, 0CDh, 097h, 011h
    DEFB 03Ah, 0EAh, 08h, 0FEh, 02h, 0CAh, 07Ch, 019h
    DEFB 0C3h, 0A2h, 0Fh, 021h, 02h, 09h, 034h, 0AFh
    DEFB 032h, 0Dh, 09h, 056h, 03Ah, 01h, 09h, 05Fh
    DEFB 0CDh, 0D4h, 01Bh, 022h, 03h, 09h, 023h, 07Eh
    DEFB 0FEh, 077h, 0D2h, 0F8h, 0Fh, 01h, 020h, 00h
    DEFB 09h, 07Eh, 0FEh, 077h, 0DAh, 0FCh, 0Fh, 021h
    DEFB 02h, 09h, 035h, 03Ah, 0F8h, 08h, 047h, 03Ah
    DEFB 0F7h, 08h, 032h, 0F8h, 08h, 078h, 032h, 0F7h
    DEFB 08h, 0B7h, 0C2h, 068h, 0Dh, 03Ah, 0F9h, 08h
    DEFB 032h, 07h, 09h, 0C3h, 06Dh, 0Dh, 021h, 02h
    DEFB 09h, 035h, 03Eh, 01h, 032h, 0Dh, 09h, 056h
    DEFB 03Ah, 01h, 09h, 05Fh, 0CDh, 0D4h, 01Bh, 022h
    DEFB 03h, 09h, 07Eh, 0FEh, 077h, 0D2h, 03Bh, 010h
    DEFB 01h, 020h, 00h, 09h, 07Eh, 0FEh, 077h, 0DAh
    DEFB 03Fh, 010h, 021h, 02h, 09h, 034h, 0C3h, 0FCh
    DEFB 0Fh, 02Ah, 01h, 09h, 0EBh, 0CDh, 0D4h, 01Bh
    DEFB 022h, 03h, 09h, 01h, 040h, 00h, 09h, 07Eh
    DEFB 0FEh, 07Eh, 0CAh, 01Ah, 011h, 0FEh, 07Dh, 0CAh
    DEFB 088h, 011h, 03Ah, 0Fh, 09h, 0FEh, 01h, 0CAh
    DEFB 06Bh, 010h, 0FEh, 02h, 0CAh, 06Bh, 010h, 0C3h
    DEFB 068h, 0Dh, 02Ah, 03h, 09h, 01h, 040h, 00h
    DEFB 09h, 07Eh, 0FEh, 079h, 0C2h, 068h, 0Dh, 06h
    DEFB 05h, 0CDh, 021h, 01h, 03Ah, 02h, 09h, 032h
    DEFB 0FEh, 08h, 03Ah, 01h, 09h, 0C6h, 02h, 032h
    DEFB 0FFh, 08h, 0CDh, 0AEh, 01h, 03Eh, 07Bh, 0CDh
    DEFB 0A1h, 01h, 03Eh, 07Ch, 0CDh, 0A1h, 01h, 03Ah
    DEFB 0Fh, 09h, 03Dh, 032h, 0Fh, 09h, 07h, 0C6h
    DEFB 019h, 032h, 0FEh, 08h, 03Eh, 018h, 032h, 0FFh
    DEFB 08h, 0CDh, 0AEh, 01h, 03Eh, 020h, 0CDh, 0A1h
    DEFB 01h, 0CDh, 0A1h, 01h, 03Ah, 010h, 09h, 03Ch
    DEFB 032h, 010h, 09h, 03Ah, 0F5h, 08h, 0FEh, 0Ah
    DEFB 06h, 01h, 0DAh, 0C8h, 010h, 06h, 02h, 03Ah
    DEFB 010h, 09h, 0B8h, 0C2h, 068h, 0Dh, 03Ah, 011h
    DEFB 09h, 057h, 03Ah, 012h, 09h, 05Fh, 021h, 02Ah
    DEFB 027h, 0CDh, 087h, 01Bh, 06h, 05h, 0CDh, 021h
    DEFB 01h, 03Eh, 07h, 032h, 0Ch, 09h, 021h, 0E5h
    DEFB 08h, 03Ah, 012h, 09h, 0BEh, 0C2h, 0FAh, 010h
    DEFB 023h, 03Ah, 011h, 09h, 0BEh, 02Bh, 0CAh, 0FDh
    DEFB 010h, 0CDh, 04h, 01h, 03Ah, 012h, 09h, 06Fh
    DEFB 03Ah, 011h, 09h, 067h, 022h, 0E5h, 08h, 0EBh
    DEFB 03Ah, 0Ch, 09h, 087h, 087h, 021h, 0DEh, 026h
    DEFB 0CDh, 02Ch, 03h, 0CDh, 0A8h, 01Bh, 0C3h, 068h
    DEFB 0Dh, 02Ah, 01h, 09h, 0EBh, 01Ch, 01Ch, 0C3h
    DEFB 057h, 011h
; --- emit func_prng @0x1123 (50 bytes) ---
    defs 0x1123 - $ ; align
    include "funcs/func_prng.asm"

; --- gap 0x1155..0x1197 (66 bytes) from original image @reloc 0x1155 ---
    defs 0x1155 - $ ; align
    DEFB 01h, 00h, 0CDh, 023h, 011h, 0E6h, 07h, 0FEh
    DEFB 05h, 0D2h, 020h, 011h, 032h, 01Ch, 09h, 03Ah
    DEFB 01Ch, 09h, 0FEh, 04h, 0C2h, 074h, 011h, 0CDh
    DEFB 023h, 011h, 0E6h, 01h, 0C2h, 01Ah, 011h, 03Ah
    DEFB 01Ch, 09h, 0C6h, 0Ah, 06Fh, 026h, 00h, 029h
    DEFB 029h, 01h, 06h, 027h, 09h, 0CDh, 087h, 01Bh
    DEFB 0C3h, 068h, 0Dh, 02Ah, 01h, 09h, 0EBh, 01Ch
    DEFB 01Ch, 021h, 016h, 027h, 0CDh, 087h, 01Bh, 0C3h
    DEFB 068h, 0Dh
; --- emit func_draw_score_hud @0x1197 (82 bytes) ---
    defs 0x1197 - $ ; align
    include "funcs/func_draw_score_hud.asm"

; --- emit func_play_sfx @0x11E9 (5 bytes) ---
    defs 0x11E9 - $ ; align
    include "funcs/func_play_sfx.asm"

; --- emit func_draw_level_hud @0x11EE (44 bytes) ---
    defs 0x11EE - $ ; align
    include "funcs/func_draw_level_hud.asm"

; --- emit func_draw_status_hud @0x121A (56 bytes) ---
    defs 0x121A - $ ; align
    include "funcs/func_draw_status_hud.asm"

; --- gap 0x1252..0x130A (184 bytes) from original image @reloc 0x1252 ---
    defs 0x1252 - $ ; align
    DEFB 021h, 0E0h, 00h, 022h, 0E9h, 08h, 03Eh, 07h
    DEFB 032h, 01Eh, 09h, 0CDh, 01Ah, 012h, 0CDh, 023h
    DEFB 011h, 0E6h, 03h, 0C6h, 0Ah, 032h, 01Ch, 09h
    DEFB 06Fh, 026h, 00h, 029h, 029h, 03Ah, 020h, 09h
    DEFB 057h, 03Ah, 023h, 09h, 05Fh, 01h, 06h, 027h
    DEFB 09h, 0E5h, 0CDh, 087h, 01Bh, 0E1h, 03Ah, 021h
    DEFB 09h, 057h, 03Ah, 024h, 09h, 05Fh, 0CDh, 087h
    DEFB 01Bh, 03Ah, 02h, 09h, 032h, 020h, 09h, 03Eh
    DEFB 023h, 032h, 023h, 09h, 021h, 0Ah, 050h, 0CDh
    DEFB 04Fh, 01h, 021h, 01h, 0Bh, 0CDh, 021h, 03h
    DEFB 06h, 08h, 0CDh, 021h, 01h, 03Eh, 09h, 032h
    DEFB 01Ah, 09h, 03Ch, 032h, 01Bh, 09h, 0C3h, 04Ah
    DEFB 0Eh, 021h, 01h, 09h, 035h, 05Eh, 03Ah, 02h
    DEFB 09h, 057h, 0CDh, 0D4h, 01Bh, 022h, 03h, 09h
    DEFB 02Ah, 03h, 09h, 07Eh, 0FEh, 077h, 0D2h, 0D2h
    DEFB 012h, 023h, 07Eh, 0FEh, 077h, 0DAh, 0E0h, 012h
    DEFB 0AFh, 032h, 00h, 09h, 032h, 06h, 09h, 021h
    DEFB 01h, 09h, 034h, 0C3h, 041h, 0Dh, 021h, 06h
    DEFB 09h, 034h, 07Eh, 0FEh, 04h, 0DAh, 0F3h, 012h
    DEFB 0AFh, 032h, 06h, 09h, 03Eh, 02h, 032h, 00h
    DEFB 09h, 0C3h, 041h, 0Dh, 021h, 06h, 09h, 034h
    DEFB 07Eh, 0FEh, 03h, 0DAh, 07h, 013h, 0AFh, 032h
    DEFB 06h, 09h, 032h, 00h, 09h, 0C3h, 041h, 0Dh
; --- emit func_draw_game_objects @0x130A (160 bytes) ---
    defs 0x130A - $ ; align
    include "funcs/func_draw_game_objects.asm"

; --- gap 0x13AA..0x1477 (205 bytes) from original image @reloc 0x13AA ---
    defs 0x13AA - $ ; align
    DEFB 06h, 02h, 0CDh, 021h, 01h, 03Ah, 01h, 09h
    DEFB 0D6h, 02h, 032h, 0Eh, 09h, 03Ah, 02h, 09h
    DEFB 032h, 05h, 09h, 01h, 00h, 00h, 021h, 0FAh
    DEFB 01Bh, 09h, 07Eh, 0FEh, 0FFh, 0CAh, 024h, 014h
    DEFB 0Fh, 0Fh, 0Fh, 0E6h, 01Fh, 05Fh, 03Ah, 0Eh
    DEFB 09h, 083h, 0FEh, 018h, 0D2h, 024h, 014h, 032h
    DEFB 0Ah, 09h, 03Ah, 05h, 09h, 032h, 09h, 09h
    DEFB 03Eh, 06h, 032h, 0Ch, 09h, 0E5h, 0C5h, 021h
    DEFB 0E3h, 08h, 03Ah, 0Ah, 09h, 0BEh, 0C2h, 0FCh
    DEFB 013h, 023h, 03Ah, 09h, 09h, 0BEh, 02Bh, 0CAh
    DEFB 0FFh, 013h, 0CDh, 04h, 01h, 03Ah, 0Ah, 09h
    DEFB 06Fh, 03Ah, 09h, 09h, 067h, 022h, 0E3h, 08h
    DEFB 0EBh, 03Ah, 0Ch, 09h, 087h, 087h, 021h, 0DEh
    DEFB 026h, 0CDh, 02Ch, 03h, 0CDh, 0A8h, 01Bh, 06h
    DEFB 01h, 0CDh, 0F7h, 0Eh, 0C1h, 0E1h, 0Ch, 0C3h
    DEFB 0C0h, 013h, 0CDh, 0Ah, 013h, 0AFh, 032h, 0Fh
    DEFB 09h, 021h, 0FBh, 08h, 035h, 07Eh, 0FEh, 0FFh
    DEFB 0CAh, 038h, 014h, 0C3h, 0A0h, 019h, 0CDh, 0E5h
    DEFB 01Bh, 021h, 06Ah, 051h, 0CDh, 04Fh, 01h, 021h
    DEFB 0Eh, 0Bh, 0CDh, 021h, 03h, 02Ah, 0F3h, 08h
    DEFB 0EBh, 02Ah, 0EBh, 08h, 032h, 03Dh, 0Bh, 07Dh
    DEFB 09Bh, 06Fh, 07Ch, 09Ah, 067h, 0E5h, 0F5h, 0B5h
    DEFB 0CAh, 063h, 014h, 0E1h, 03Eh, 0BFh, 0A5h, 06Fh
    DEFB 0E5h, 0F1h, 0E1h, 03Ah, 03Dh, 0Bh, 0D2h, 06Fh
    DEFB 014h, 0EBh, 022h, 0EBh, 08h, 06h, 05h, 0CDh
    DEFB 077h, 014h, 0C3h, 0C2h, 0Bh
; --- emit func_delay_long @0x1477 (18 bytes) ---
    defs 0x1477 - $ ; align
    include "funcs/func_delay_long.asm"

; --- emit func_entity_state1 @0x1489 (112 bytes) ---
    defs 0x1489 - $ ; align
    include "funcs/func_entity_state1.asm"

; --- emit func_entity_state2 @0x14F9 (111 bytes) ---
    defs 0x14F9 - $ ; align
    include "funcs/func_entity_state2.asm"

; --- emit func_entity_state3 @0x1568 (119 bytes) ---
    defs 0x1568 - $ ; align
    include "funcs/func_entity_state3.asm"

; --- emit func_entity_state4 @0x15DF (112 bytes) ---
    defs 0x15DF - $ ; align
    include "funcs/func_entity_state4.asm"

; --- emit func_entity_state5 @0x164F (173 bytes) ---
    defs 0x164F - $ ; align
    include "funcs/func_entity_state5.asm"

; --- emit func_entity_state6 @0x16FC (172 bytes) ---
    defs 0x16FC - $ ; align
    include "funcs/func_entity_state6.asm"

; --- emit func_entity_state7 @0x17A8 (169 bytes) ---
    defs 0x17A8 - $ ; align
    include "funcs/func_entity_state7.asm"

; --- emit func_entity_state8 @0x1851 (173 bytes) ---
    defs 0x1851 - $ ; align
    include "funcs/func_entity_state8.asm"

; --- emit func_entity_state9 @0x18FE (29 bytes) ---
    defs 0x18FE - $ ; align
    include "funcs/func_entity_state9.asm"

; --- emit func_entity_state10 @0x191B (97 bytes) ---
    defs 0x191B - $ ; align
    include "funcs/func_entity_state10.asm"

; --- emit func_level_loader @0x197C (523 bytes) ---
    defs 0x197C - $ ; align
    include "funcs/func_level_loader.asm"

; --- emit func_draw_tile_to_buf @0x1B87 (33 bytes) ---
    defs 0x1B87 - $ ; align
    include "funcs/func_draw_tile_to_buf.asm"

; --- emit func_render_tile_vram @0x1BA8 (33 bytes) ---
    defs 0x1BA8 - $ ; align
    include "funcs/func_render_tile_vram.asm"

; --- emit func_memcpy @0x1BC9 (11 bytes) ---
    defs 0x1BC9 - $ ; align
    include "funcs/func_memcpy.asm"

; --- emit func_coords_to_textbuf @0x1BD4 (17 bytes) ---
    defs 0x1BD4 - $ ; align
    include "funcs/func_coords_to_textbuf.asm"

; --- emit func_clear_textbuf @0x1BE5 (21 bytes) ---
    defs 0x1BE5 - $ ; align
    include "funcs/func_clear_textbuf.asm"

; --- gap 0x1BFA..0x1C0E (20 bytes) from original image @reloc 0x1BFA ---
    defs 0x1BFA - $ ; align
    DEFB 010h, 09h, 04h, 01h, 00h, 01h, 04h, 09h
    DEFB 010h, 019h, 024h, 031h, 040h, 051h, 064h, 079h
    DEFB 090h, 0A9h, 0C4h, 0FFh
; --- emit data_level_params @0x1C0E (128 bytes) ---
    defs 0x1C0E - $ ; align
    include "data/data_level_params.asm"

; --- emit data_level_maps @0x1C8E (2640 bytes) ---
    defs 0x1C8E - $ ; align
    include "data/data_level_maps.asm"

; --- emit data_tile_table_26DE @0x26DE (40 bytes) ---
    defs 0x26DE - $ ; align
    include "data/data_tile_table_26DE.asm"

; --- emit data_tile_graphics @0x2706 (91 bytes) ---
    defs 0x2706 - $ ; align
    include "data/data_tile_graphics.asm"

; --- emit data_sprites_2F61 @0x2F61 (224 bytes) @reloc 0x2761 ---
    defs 0x2761 - $ ; align
    include "data/data_sprites_2F61.asm"

; --- gap 0x383A..0x3858 (30 bytes) from original image @reloc 0x2841 ---
    defs 0x2841 - $ ; align
    DEFB 04h, 028h, 028h, 028h, 020h
    DW 02E30h   ; reloc-указатель (orig 0x383F -> 0x3E29)
    DW 02ED0h   ; reloc-указатель (orig 0x3841 -> 0x3EC9)
    DW 02F70h   ; reloc-указатель (orig 0x3843 -> 0x3F69)
    DEFB 07Fh, 00h, 0FDh, 00h, 0C3h, 01h, 01Fh, 069h
    DEFB 0Fh, 00h, 00h, 00h, 03h, 02h, 038h
    DW 02E21h   ; reloc-указатель (orig 0x3854 -> 0x3E1A)
    DW 02E30h   ; reloc-указатель (orig 0x3856 -> 0x3E29)
; --- emit func_music_tick @0x3858 (52 bytes) @reloc 0x285F ---
    defs 0x285F - $ ; align
    include "funcs/func_music_tick.asm"

; --- gap 0x388C..0x3890 (4 bytes) from original image @reloc 0x2893 ---
    defs 0x2893 - $ ; align
    DEFB 0CDh, 0CDh, 03Dh, 0C9h
; --- emit func_music_sub_3890 @0x3890 (114 bytes) @reloc 0x2897 ---
    defs 0x2897 - $ ; align
    include "funcs/func_music_sub_3890.asm"

; --- emit func_music_load_voice_params @0x3902 (62 bytes) @reloc 0x2909 ---
    defs 0x2909 - $ ; align
    include "funcs/func_music_load_voice_params.asm"

; --- emit func_snd_op_keep_a @0x3940 (6 bytes) @reloc 0x2947 ---
    defs 0x2947 - $ ; align
    include "funcs/func_snd_op_keep_a.asm"

; --- emit func_music_process_voice @0x3946 (457 bytes) @reloc 0x294D ---
    defs 0x294D - $ ; align
    include "funcs/func_music_process_voice.asm"

; --- emit func_music_set_note_params @0x3B0F (185 bytes) @reloc 0x2B16 ---
    defs 0x2B16 - $ ; align
    include "funcs/func_music_set_note_params.asm"

; --- gap 0x3BC8..0x3BCA (2 bytes) from original image @reloc 0x2BCF ---
    defs 0x2BCF - $ ; align
    DEFB 035h, 029h
; --- emit func_music_play_note_ch0 @0x3BCA (173 bytes) @reloc 0x2BD1 ---
    defs 0x2BD1 - $ ; align
    include "funcs/func_music_play_note_ch0.asm"

; --- emit func_snd_op_keep_a2 @0x3C77 (6 bytes) @reloc 0x2C7E ---
    defs 0x2C7E - $ ; align
    include "funcs/func_snd_op_keep_a2.asm"

; --- emit func_music_play_note_ch1 @0x3C7D (203 bytes) @reloc 0x2C84 ---
    defs 0x2C84 - $ ; align
    include "funcs/func_music_play_note_ch1.asm"

; --- emit func_snd_op_keep_a3 @0x3D48 (6 bytes) @reloc 0x2D4F ---
    defs 0x2D4F - $ ; align
    include "funcs/func_snd_op_keep_a3.asm"

; --- emit func_music_init @0x3D4E (106 bytes) @reloc 0x2D55 ---
    defs 0x2D55 - $ ; align
    include "funcs/func_music_init.asm"

; --- emit func_memcpy_keep_psw @0x3DB8 (13 bytes) @reloc 0x2DBF ---
    defs 0x2DBF - $ ; align
    include "funcs/func_memcpy_keep_psw.asm"

; --- emit func_music_trampoline @0x3DC5 (8 bytes) @reloc 0x2DCC ---
    defs 0x2DCC - $ ; align
    include "funcs/func_music_trampoline.asm"

; --- emit func_music_start_track @0x3DCD (27 bytes) @reloc 0x2DD4 ---
    defs 0x2DD4 - $ ; align
    include "funcs/func_music_start_track.asm"

; --- emit data_music_track_setup @0x3DE8 (3 bytes) @reloc 0x2DEF ---
    defs 0x2DEF - $ ; align
    include "data/data_music_track_setup.asm"

; --- gap 0x3DEB..0x421A (1071 bytes) from original image @reloc 0x2DF2 ---
    defs 0x2DF2 - $ ; align
    DEFB 03Eh, 01h, 021h, 01Ah, 03Eh, 0A7h, 0FEh, 00h
    DEFB 0C8h, 0FEh, 06h, 0D0h, 03Dh, 0FEh, 00h, 0CAh
    DEFB 0Ch, 03Eh, 047h, 011h, 0Fh, 03h, 019h, 0F5h
    DEFB 05h, 0CAh, 0Bh, 03Eh, 0F1h, 0C3h, 01h, 03Eh
    DEFB 0F1h, 022h, 054h, 038h, 01h, 0Fh, 00h, 09h
    DEFB 022h, 056h, 038h, 0CDh, 088h, 038h, 0C9h, 038h
    DEFB 06h, 06h, 0Fh, 00h, 0Eh, 060h, 060h, 060h
    DEFB 01Fh, 00h, 03h, 02h, 05h, 00h, 030h, 00h
    DEFB 02Bh, 00h, 00h, 030h, 02Fh, 030h, 032h, 00h
    DEFB 02Bh, 00h, 00h, 032h, 030h, 032h, 034h, 032h
    DEFB 034h, 035h, 037h, 00h, 035h, 034h, 032h, 00h
    DEFB 02Bh, 00h, 00h, 032h, 034h, 037h, 039h, 039h
    DEFB 039h, 039h, 032h, 032h, 034h, 035h, 037h, 037h
    DEFB 037h, 037h, 030h, 030h, 032h, 034h, 035h, 035h
    DEFB 035h, 035h, 02Fh, 02Fh, 030h, 032h, 034h, 032h
    DEFB 034h, 035h, 037h, 037h, 037h, 037h, 039h, 039h
    DEFB 039h, 039h, 032h, 032h, 034h, 035h, 037h, 037h
    DEFB 037h, 037h, 030h, 030h, 032h, 034h, 035h, 034h
    DEFB 032h, 030h, 030h, 02Dh, 02Fh, 02Fh, 030h, 02Bh
    DEFB 028h, 02Bh, 024h, 024h, 00h, 00h, 00h, 00h
    DEFB 00h, 00h, 00h, 00h, 00h, 00h, 00h, 00h
    DEFB 00h, 00h, 00h, 00h, 00h, 00h, 00h, 00h
    DEFB 00h, 00h, 00h, 00h, 00h, 00h, 00h, 00h
    DEFB 00h, 00h, 00h, 00h, 00h, 00h, 00h, 00h
    DEFB 00h, 00h, 00h, 00h, 00h, 00h, 00h, 00h
    DEFB 00h, 00h, 00h, 00h, 00h, 00h, 00h, 00h
    DEFB 00h, 00h, 00h, 00h, 00h, 00h, 00h, 00h
    DEFB 00h, 00h, 00h, 00h, 00h, 00h, 00h, 00h
    DEFB 00h, 00h, 00h, 00h, 00h, 00h, 00h, 00h
    DEFB 00h, 00h, 00h, 00h, 00h, 00h, 00h, 00h
    DEFB 00h, 00h, 00h, 00h, 00h, 00h, 00h, 00h
    DEFB 00h, 00h, 00h, 00h, 00h, 00h, 00h, 00h
    DEFB 00h, 00h, 00h, 00h, 00h, 00h, 00h, 00h
    DEFB 00h, 00h, 00h, 00h, 00h, 00h, 00h, 00h
    DEFB 00h, 00h, 00h, 00h, 00h, 00h, 00h, 00h
    DEFB 00h, 00h, 00h, 00h, 00h, 00h, 00h, 00h
    DEFB 00h, 00h, 00h, 00h, 00h, 00h, 00h, 00h
    DEFB 00h, 00h, 00h, 00h, 00h, 00h, 00h, 00h
    DEFB 00h, 00h, 00h, 00h, 00h, 00h, 00h, 00h
    DEFB 00h, 00h, 00h, 00h, 00h, 00h, 024h, 028h
    DEFB 02Bh, 029h, 028h, 026h, 024h, 00h, 01Fh, 023h
    DEFB 026h, 024h, 023h, 021h, 01Fh, 00h, 024h, 023h
    DEFB 024h, 026h, 028h, 029h, 02Bh, 028h, 026h, 00h
    DEFB 01Fh, 00h, 02Bh, 02Ah, 02Bh, 00h, 029h, 02Bh
    DEFB 02Dh, 030h, 02Fh, 02Dh, 02Bh, 029h, 028h, 029h
    DEFB 02Bh, 02Fh, 02Dh, 02Bh, 029h, 028h, 026h, 028h
    DEFB 029h, 02Dh, 02Bh, 029h, 028h, 026h, 028h, 024h
    DEFB 028h, 02Bh, 030h, 02Fh, 030h, 00h, 029h, 02Bh
    DEFB 02Dh, 030h, 02Fh, 02Dh, 02Bh, 029h, 028h, 029h
    DEFB 02Bh, 02Fh, 02Dh, 02Bh, 029h, 028h, 026h, 028h
    DEFB 029h, 02Dh, 02Bh, 02Dh, 02Fh, 02Bh, 030h, 00h
    DEFB 02Bh, 00h, 024h, 00h, 030h, 02Fh, 00h, 00h
    DEFB 00h, 00h, 00h, 00h, 00h, 00h, 00h, 00h
    DEFB 00h, 00h, 00h, 00h, 00h, 00h, 00h, 00h
    DEFB 00h, 00h, 00h, 00h, 00h, 00h, 00h, 00h
    DEFB 00h, 00h, 00h, 00h, 00h, 00h, 00h, 00h
    DEFB 00h, 00h, 00h, 00h, 00h, 00h, 00h, 00h
    DEFB 00h, 00h, 00h, 00h, 00h, 00h, 00h, 00h
    DEFB 00h, 00h, 00h, 00h, 00h, 00h, 00h, 00h
    DEFB 00h, 00h, 00h, 00h, 00h, 00h, 00h, 00h
    DEFB 00h, 00h, 00h, 00h, 00h, 00h, 00h, 00h
    DEFB 00h, 00h, 00h, 00h, 00h, 00h, 00h, 00h
    DEFB 00h, 00h, 00h, 00h, 00h, 00h, 00h, 00h
    DEFB 00h, 00h, 00h, 00h, 00h, 00h, 00h, 00h
    DEFB 00h, 00h, 00h, 00h, 00h, 00h, 00h, 00h
    DEFB 00h, 00h, 00h, 00h, 00h, 00h, 00h, 00h
    DEFB 00h, 00h, 00h, 00h, 00h, 00h, 00h, 00h
    DEFB 00h, 00h, 00h, 00h, 00h, 00h, 00h, 00h
    DEFB 00h, 00h, 00h, 00h, 00h, 00h, 00h, 00h
    DEFB 00h, 00h, 00h, 00h, 00h, 00h, 00h, 00h
    DEFB 00h, 00h, 00h, 00h, 00h, 00h, 00h, 00h
    DEFB 00h, 00h, 00h, 00h, 00h, 00h, 0Ch, 00h
    DEFB 013h, 00h, 018h, 00h, 00h, 00h, 013h, 00h
    DEFB 01Ah, 00h, 01Fh, 00h, 00h, 00h, 018h, 00h
    DEFB 013h, 00h, 01Ch, 00h, 018h, 00h, 017h, 015h
    DEFB 013h, 00h, 00h, 00h, 01Fh, 00h, 011h, 00h
    DEFB 015h, 00h, 013h, 00h, 01Fh, 00h, 013h, 00h
    DEFB 010h, 00h, 015h, 00h, 021h, 00h, 011h, 00h
    DEFB 0Eh, 00h, 013h, 00h, 01Fh, 00h, 024h, 00h
    DEFB 018h, 00h, 01Ch, 01Fh, 018h, 00h, 011h, 00h
    DEFB 015h, 00h, 013h, 00h, 01Fh, 00h, 010h, 00h
    DEFB 013h, 00h, 011h, 00h, 021h, 00h, 011h, 00h
    DEFB 015h, 00h, 013h, 00h, 017h, 00h, 018h, 00h
    DEFB 013h, 00h, 0Ch, 00h, 0Ch, 00h, 00h, 00h
    DEFB 00h, 00h, 00h, 00h, 00h, 00h, 00h, 00h
    DEFB 00h, 00h, 00h, 00h, 00h, 00h, 00h, 00h
    DEFB 00h, 00h, 00h, 00h, 00h, 00h, 00h, 00h
    DEFB 00h, 00h, 00h, 00h, 00h, 00h, 00h, 00h
    DEFB 00h, 00h, 00h, 00h, 00h, 00h, 00h, 00h
    DEFB 00h, 00h, 00h, 00h, 00h, 00h, 00h, 00h
    DEFB 00h, 00h, 00h, 00h, 00h, 00h, 00h, 00h
    DEFB 00h, 00h, 00h, 00h, 00h, 00h, 00h, 00h
    DEFB 00h, 00h, 00h, 00h, 00h, 00h, 00h, 00h
    DEFB 00h, 00h, 00h, 00h, 00h, 00h, 00h, 00h
    DEFB 00h, 00h, 00h, 00h, 00h, 00h, 00h, 00h
    DEFB 00h, 00h, 00h, 00h, 00h, 00h, 00h, 00h
    DEFB 00h, 00h, 00h, 00h, 00h, 00h, 00h, 00h
    DEFB 00h, 00h, 00h, 00h, 00h, 00h, 00h, 00h
    DEFB 00h, 00h, 00h, 00h, 00h, 00h, 00h, 00h
    DEFB 00h, 00h, 00h, 00h, 00h, 00h, 00h, 00h
    DEFB 00h, 00h, 00h, 00h, 00h, 00h, 00h, 00h
    DEFB 00h, 00h, 00h, 00h, 00h, 00h, 00h, 00h
    DEFB 00h, 00h, 00h, 00h, 00h, 00h, 00h, 00h
    DEFB 00h, 00h, 00h, 00h, 00h, 00h, 038h, 06h
    DEFB 06h, 0Fh, 0Dh, 0Dh, 060h, 060h, 060h, 01h
    DEFB 00h, 00h, 019h, 05h, 03h, 024h, 00h, 027h
    DEFB 00h, 026h, 00h, 024h, 00h, 02Bh, 02Ah, 02Bh
    DEFB 00h, 00h, 026h, 029h, 027h, 024h, 00h, 027h
    DEFB 00h, 026h, 00h, 024h, 00h, 01Fh, 01Eh, 01Fh
    DEFB 00h, 00h, 01Fh, 021h, 023h, 024h, 00h, 027h
    DEFB 00h, 026h, 00h, 024h, 00h, 02Ch, 02Ch, 02Ch
    DEFB 02Ch, 02Ch, 027h, 026h, 024h, 026h, 00h, 029h
    DEFB 00h, 027h, 00h, 026h, 00h, 02Bh, 02Bh, 02Bh
    DEFB 02Bh, 02Bh, 027h, 026h, 024h, 024h, 00h, 027h
    DEFB 00h, 026h, 00h, 024h, 00h, 030h, 030h, 030h
    DEFB 030h, 030h, 02Bh, 027h, 024h, 026h, 00h, 029h
    DEFB 00h, 027h, 00h, 026h, 00h, 027h, 026h, 024h
    DEFB 024h, 024h, 024h, 00h, 00h, 00h, 00h, 00h
    DEFB 00h, 00h, 00h, 00h, 00h, 00h, 00h, 00h
    DEFB 00h, 00h, 00h, 00h, 00h, 00h, 00h, 00h
    DEFB 00h, 00h, 00h, 00h, 00h, 00h, 00h, 00h
    DEFB 00h, 00h, 00h, 00h, 00h, 00h, 00h, 00h
    DEFB 00h, 00h, 00h, 00h, 00h, 00h, 00h, 00h
    DEFB 00h, 00h, 00h, 00h, 00h, 00h, 00h, 00h
    DEFB 00h, 00h, 00h, 00h, 00h, 00h, 00h, 00h
    DEFB 00h, 00h, 00h, 00h, 00h, 00h, 00h, 00h
    DEFB 00h, 00h, 00h, 00h, 00h, 00h, 00h, 00h
    DEFB 00h, 00h, 00h, 00h, 00h, 00h, 00h, 00h
    DEFB 00h, 00h, 00h, 00h, 00h, 00h, 00h, 00h
    DEFB 00h, 00h, 00h, 00h, 00h, 00h, 00h, 00h
    DEFB 00h, 00h, 00h, 00h, 00h, 00h, 00h, 00h
    DEFB 00h, 00h, 00h, 00h, 00h, 00h, 00h, 00h
    DEFB 00h, 00h, 00h, 00h, 00h, 00h, 00h, 00h
    DEFB 00h, 00h, 00h, 00h, 00h, 00h, 00h
; --- emit data_music_period_table @0x421A (192 bytes) @reloc 0x3221 ---
    defs 0x3221 - $ ; align
    include "data/data_music_period_table.asm"

; --- gap 0x42DA..0x42F9 (31 bytes) from original image @reloc 0x32E1 ---
    defs 0x32E1 - $ ; align
    DEFB 064h, 069h, 073h, 06Bh, 020h, 077h, 069h, 074h
    DEFB 068h, 020h, 062h, 02Dh, 043h, 063h, 044h, 064h
    DEFB 045h, 046h, 066h, 047h, 067h, 041h, 061h, 042h
    DEFB 043h, 062h, 020h, 03Dh, 05Bh, 016h, 0C3h
; --- emit data_note_table_ch1 @0x42F9 (256 bytes) @reloc 0x3300 ---
    defs 0x3300 - $ ; align
    include "data/data_note_table_ch1.asm"

; --- emit data_note_param_table_43F9 @0x43F9 (99 bytes) @reloc 0x3400 ---
    defs 0x3400 - $ ; align
    include "data/data_note_param_table_43F9.asm"

; --- gap 0x445C..0x445D (1 bytes) from original image @reloc 0x3463 ---
    defs 0x3463 - $ ; align
    DEFB 0Ah
; --- emit data_note_freq_table_ch0 @0x445D (419 bytes) @reloc 0x3464 ---
    defs 0x3464 - $ ; align
    include "data/data_note_freq_table_ch0.asm"

; --- filler 0x3607..0x3607 (1 bytes) zeros (RAM в оригинале) ---
    defs 0x3608 - $ ; align

; --- unpacked glyph block @0x3608 (5048 bytes) ---
    include "data/data_glyph_block_unpacked.asm"

; image end @0x49C0
