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

; --- emit func_snd_set_period_ch0 @0x01ED (20 bytes) ---
    defs 0x01ED - $ ; align
    include "funcs/func_snd_set_period_ch0.asm"

; --- emit func_snd_out_ch0 @0x0201 (13 bytes) ---
    defs 0x0201 - $ ; align
    include "funcs/func_snd_out_ch0.asm"

; --- emit func_snd_calc_period @0x020E (11 bytes) ---
    defs 0x020E - $ ; align
    include "funcs/func_snd_calc_period.asm"

; --- emit func_snd_set_period_ch1 @0x0219 (20 bytes) ---
    defs 0x0219 - $ ; align
    include "funcs/func_snd_set_period_ch1.asm"

; --- emit func_snd_out_ch1 @0x022D (13 bytes) ---
    defs 0x022D - $ ; align
    include "funcs/func_snd_out_ch1.asm"

; --- emit func_snd_set_period_ch2 @0x023A (20 bytes) ---
    defs 0x023A - $ ; align
    include "funcs/func_snd_set_period_ch2.asm"

; --- emit func_snd_out_ch2 @0x024E (13 bytes) ---
    defs 0x024E - $ ; align
    include "funcs/func_snd_out_ch2.asm"

; --- emit func_snd_dispatch_nops @0x025B (15 bytes) ---
    defs 0x025B - $ ; align
    include "funcs/func_snd_dispatch_nops.asm"

; --- emit func_snd_op_epilogue @0x026A (4 bytes) ---
    defs 0x026A - $ ; align
    include "funcs/func_snd_op_epilogue.asm"

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

; --- emit data_snd_init @0x031A (7 bytes) ---
    defs 0x031A - $ ; align
    include "data/data_snd_init.asm"

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

; --- emit func_print_digit_tail @0x0364 (31 bytes) ---
    defs 0x0364 - $ ; align
    include "funcs/func_print_digit_tail.asm"

; --- emit func_hw_init @0x0383 (33 bytes) ---
    defs 0x0383 - $ ; align
    include "funcs/func_hw_init.asm"

; --- emit func_vblank_isr @0x03A4 (93 bytes) ---
    defs 0x03A4 - $ ; align
    include "funcs/func_vblank_isr.asm"

; --- emit func_load_glyph_block @0x0401 (56 bytes) ---
    defs 0x0401 - $ ; align
    include "funcs/func_load_glyph_block.asm"

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

; --- emit func_call_vector_053B @0x053B (7 bytes) ---
    defs 0x053B - $ ; align
    include "funcs/func_call_vector_053B.asm"

; --- emit func_blit_object_tile @0x0542 (190 bytes) ---
    defs 0x0542 - $ ; align
    include "funcs/func_blit_object_tile.asm"

; --- emit data_glyph_ptr_table @0x0600 (512 bytes) ---
    defs 0x0600 - $ ; align
    include "data/data_glyph_ptr_table.asm"

; --- emit func_put_char @0x0800 (3 bytes) ---
    defs 0x0800 - $ ; align
    include "funcs/func_put_char.asm"

; --- emit func_render_glyph @0x0803 (192 bytes) ---
    defs 0x0803 - $ ; align
    include "funcs/func_render_glyph.asm"

; --- emit data_ram_init_image_08C3 @0x08C3 (98 bytes) ---
    defs 0x08C3 - $ ; align
    include "data/data_ram_init_image_08C3.asm"

; --- emit str_credits_koi8 @0x0925 (126 bytes) ---
    defs 0x0925 - $ ; align
    include "data/str_credits_koi8.asm"

; --- emit data_title_attr_tail_09A3 @0x09A3 (99 bytes) ---
    defs 0x09A3 - $ ; align
    include "data/data_title_attr_tail_09A3.asm"

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

; --- emit data_game_object_init @0x0B3C (27 bytes) ---
    defs 0x0B3C - $ ; align
    include "data/data_game_object_init.asm"

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

; --- emit func_game_update_handlers @0x0F39 (490 bytes) ---
    defs 0x0F39 - $ ; align
    include "funcs/func_game_update_handlers.asm"

; --- emit func_prng @0x1123 (50 bytes) ---
    defs 0x1123 - $ ; align
    include "funcs/func_prng.asm"

; --- emit var_prng_seed_init @0x1155 (2 bytes) ---
    defs 0x1155 - $ ; align
    include "data/var_prng_seed_init.asm"

; --- emit func_spawn_egg @0x1157 (64 bytes) ---
    defs 0x1157 - $ ; align
    include "funcs/func_spawn_egg.asm"

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

; --- emit func_gamestate_handlers @0x1252 (184 bytes) ---
    defs 0x1252 - $ ; align
    include "funcs/func_gamestate_handlers.asm"

; --- emit func_draw_game_objects @0x130A (160 bytes) ---
    defs 0x130A - $ ; align
    include "funcs/func_draw_game_objects.asm"

; --- emit func_collision_death @0x13AA (205 bytes) ---
    defs 0x13AA - $ ; align
    include "funcs/func_collision_death.asm"

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

; --- emit data_egg_speed_table @0x1BFA (20 bytes) ---
    defs 0x1BFA - $ ; align
    include "data/data_egg_speed_table.asm"

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

; --- emit data_music_init @0x383A (30 bytes) @reloc 0x2841 ---
    defs 0x2841 - $ ; align
    include "data/data_music_init.asm"

; --- emit func_music_tick @0x3858 (52 bytes) @reloc 0x285F ---
    defs 0x285F - $ ; align
    include "funcs/func_music_tick.asm"

; --- emit data_music_tick_pad_388C @0x388C (4 bytes) @reloc 0x2893 ---
    defs 0x2893 - $ ; align
    include "data/data_music_tick_pad_388C.asm"

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

; --- emit var_music_voice2_flag_init @0x3BC8 (2 bytes) @reloc 0x2BCF ---
    defs 0x2BCF - $ ; align
    include "data/var_music_voice2_flag_init.asm"

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

; --- emit func_music_load_score @0x3DEB (47 bytes) @reloc 0x2DF2 ---
    defs 0x2DF2 - $ ; align
    include "funcs/func_music_load_score.asm"

; --- emit data_music_scores @0x3E1A (15 bytes) @reloc 0x2E21 ---
    defs 0x2E21 - $ ; align
    include "data/data_music_scores.asm"

; --- emit data_music_track_01 @0x3E29 (256 bytes) @reloc 0x2E30 ---
    defs 0x2E30 - $ ; align
    include "data/data_music_track_01.asm"

; --- emit data_music_track_02 @0x3F29 (256 bytes) @reloc 0x2F30 ---
    defs 0x2F30 - $ ; align
    include "data/data_music_track_02.asm"

; --- emit data_music_track_03 @0x4029 (256 bytes) @reloc 0x3030 ---
    defs 0x3030 - $ ; align
    include "data/data_music_track_03.asm"

; --- emit data_music_score_02 @0x4129 (241 bytes) @reloc 0x3130 ---
    defs 0x3130 - $ ; align
    include "data/data_music_score_02.asm"

; --- emit data_music_period_table @0x421A (192 bytes) @reloc 0x3221 ---
    defs 0x3221 - $ ; align
    include "data/data_music_period_table.asm"

; --- emit data_note_names_42DA @0x42DA (31 bytes) @reloc 0x32E1 ---
    defs 0x32E1 - $ ; align
    include "data/data_note_names_42DA.asm"

; --- emit data_note_table_ch1 @0x42F9 (256 bytes) @reloc 0x3300 ---
    defs 0x3300 - $ ; align
    include "data/data_note_table_ch1.asm"

; --- emit data_note_param_table_43F9 @0x43F9 (99 bytes) @reloc 0x3400 ---
    defs 0x3400 - $ ; align
    include "data/data_note_param_table_43F9.asm"

; --- emit data_music_vibrato_pre_445C @0x445C (1 bytes) @reloc 0x3463 ---
    defs 0x3463 - $ ; align
    include "data/data_music_vibrato_pre_445C.asm"

; --- emit data_note_freq_table_ch0 @0x445D (419 bytes) @reloc 0x3464 ---
    defs 0x3464 - $ ; align
    include "data/data_note_freq_table_ch0.asm"

; --- filler 0x3607..0x3607 (1 bytes) zeros (RAM в оригинале) ---
    defs 0x3608 - $ ; align

; --- unpacked glyph block @0x3608 (5048 bytes) ---
    include "data/data_glyph_block_unpacked.asm"

; image end @0x49C0
