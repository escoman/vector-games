#!/usr/bin/env python3
"""gen_main.py — генератор main.c для music-ROM саундтреков.

Читает rom.json, генерирует main.c с меню, обработчиком клавиш
и подключением треков.

Использование:
    python3 ../soundtracks/gen_main.py rom.json -o main.c
"""

import argparse
import json
import os
import struct
import sys


def read_bmp_width(json_path):
    """Читает ширину из BMP-файла заголовка (rom_data/title.bmp)."""
    bmp = os.path.join(os.path.dirname(json_path), 'rom_data', 'title.bmp')
    if not os.path.isfile(bmp):
        return 256
    with open(bmp, 'rb') as f:
        f.seek(18)
        return struct.unpack('<i', f.read(4))[0]


def generate(cfg, out):
    title = cfg['title']
    tracks = cfg['tracks']
    layout = cfg['layout']
    colors = cfg['colors']
    credits = cfg['credits']
    title_dx = cfg.get('title_dx', 0)
    menu_y0 = layout.get('menu_y0', 8)
    rle_y = layout.get('rle_y', 0)
    stop_dy = layout.get('stop_dy')

    # Авто-центрирование по X, если rle_x не задан явно
    title_width = cfg.get('title_bmp_width', 256)
    if 'rle_x' in layout:
        rle_x = layout['rle_x']
    elif title_width < 256:
        rle_x = ((256 - title_width) // 16) * 8
    else:
        rle_x = 0

    n = len(tracks)
    y_start = layout['y_start']
    y_step = layout['y_step']
    x_left = layout['x_left']
    x_right = layout['x_right']
    cols = layout['cols']

    # Автоматическая позиция STOP после последней сетки треков
    if stop_dy is None:
        last_row = (n - 1) // cols
        stop_dy = y_start + (last_row + 1) * y_step

    # --- Комментарий ---
    w = out.write
    w('/*\n')
    w(f' * main.c — music-ROM для Вектора-06Ц: {title}\n')
    w(' *\n')
    w(' * АВТОМАТИЧЕСКИ СГЕНЕРИРОВАН gen_main.py из rom.json.\n')
    w(' * НЕ РЕДАКТИРОВАТЬ ВРУЧНУЮ.\n')
    w(' */\n\n')

    # --- Includes ---
    w('#include <intrinsic.h>\n\n')
    w('#include "v06.h"\n')
    w('#include "nes_drums.h"\n\n')
    w('#include "rom_data/title_bmp.inc"\n')
    for t in tracks:
        w(f'#include "rom_data/{t["file"]}_music.inc"\n')
    w('\n')

    # --- Вспомогательные функции ---
    w('''static void wait_one_frame(void)
{
    unsigned int start;
    start = frame_count;
    while (frame_count == start)
        intrinsic_halt();
}

static void on_frame(void)
{
    music_tick();
    drum_tick();
}

static void play_song(const music_song_t *song, unsigned char loop)
{
    music_set_data(song);
    music_set_loop(loop);
    music_start();
}

''')

    # --- menu_lines[] ---
    w('static const struct {\n')
    w('    unsigned char dx;\n')
    w('    unsigned char dy;\n')
    w('    const char *text;\n')
    w('} menu_lines[] = {\n')
    w(f'    {{ {title_dx}u,  0u, "{title}" }},\n')
    w('\n')

    for i, t in enumerate(tracks):
        row = i // cols
        col = i % cols
        dx = (256 // cols) * col if col else x_left
        dy = y_start + row * y_step
        w(f'    {{ {dx}u, {dy}u, "{t["key"]}-{t["name"]}" }},\n')

    w(f'    {{ 0u,  {stop_dy}u, "0 - STOP MUSIC" }},\n')
    w('\n')

    # Credits
    cred_y = credits['y']
    w(f'    {{ 0u,     {cred_y}u, "{credits["left"]}" }},\n')
    for j, line in enumerate(credits['right']):
        dx = 112 if j == 0 else 112
        dy = cred_y + j * 10
        w(f'    {{ {dx}u, {dy}u, "{line}" }},\n')

    w('};\n\n')

    # --- show_menu() ---
    hl = colors['highlight']
    norm = colors['normal']
    w(f'''static void show_menu(unsigned char selected)
{{
    unsigned char x0 = 0u;
    unsigned char y0 = (unsigned char)(title_bmp_height + {menu_y0}u);
    unsigned char i;

    for (i = 0u; i < sizeof(menu_lines) / sizeof(menu_lines[0]); ++i) {{
        graph_print((unsigned char)(x0 + menu_lines[i].dx),
                    (unsigned char)(y0 + menu_lines[i].dy),
                    menu_lines[i].text, selected == i ? {hl}u : {norm}u);
    }}
}}

''')

    # --- main() ---
    bg = colors.get('background', 0)
    # Определяем диапазон клавиш
    if n <= 9:
        # Только цифровые клавиши 1-9
        max_key = str(n)
        key_check = f"key >= '1' && key <= '{max_key}'"
        track_calc = "track = key - '1';"
    else:
        # Цифровые 1-9 + буквенные A-F
        num_alpha = n - 9  # сколько буквенных клавиш нужно
        max_alpha = chr(ord('a') + num_alpha - 1)
        key_check = f"((key >= '1' && key <= '9') || (key >= 'a' && key <= '{max_alpha}'))"
        track_calc = f"track = (key <= '9') ? (key - '1') : (key - 'a' + 9);"

    w(f'''/* ------------------------------- main -------------------------------- */

int main(void)
{{
    unsigned char key;
    unsigned char prev_key = 0;

    frame_handler = on_frame;
    drum_init();

    graph_set_black_palette();
    graph_clear({bg});
    graph_rle_expand(title_bmp_screen_rle, {rle_x}u, {rle_y}u);
    show_menu(100);
    graph_set_palette(title_bmp_palette);

    play_song(&nes_drums_song, 0);

    unsigned char track;

    for (;;) {{
        wait_one_frame();

        key = kbd_scan();
        if (key != prev_key) {{
            if (key == '0') {{
                music_stop();
                show_menu(100);
            }} else if ({key_check}) {{
                {track_calc}
                const music_song_t *songs[] = {{
''')

    # Songs array (4 per line)
    for i in range(0, n, 4):
        chunk = [f'&{t["file"]}_music_song' for t in tracks[i:i+4]]
        line = ', '.join(chunk)
        comma = ',' if i + 4 < n else ''
        w(f'                    {line}{comma}\n')

    w(f'''                }};
                play_song(songs[track], 0);
                show_menu(track+1);
            }} else if (key == 27) {{
                break;
            }}
        }}
        prev_key = key;
    }}

    music_stop();
    return 0;
}}
''')


def main():
    p = argparse.ArgumentParser(description='Generate main.c from rom.json')
    p.add_argument('rom_json', help='path to rom.json')
    p.add_argument('-o', '--output', default='main.c', help='output file')
    args = p.parse_args()

    with open(args.rom_json, 'r', encoding='utf-8') as f:
        cfg = json.load(f)

    # Читает ширину BMP для авто-центрирования
    if 'title_bmp_width' not in cfg:
        cfg['title_bmp_width'] = read_bmp_width(args.rom_json)

    with open(args.output, 'w', encoding='utf-8') as f:
        generate(cfg, f)

    print(f'Generated {args.output} from {args.rom_json}')


if __name__ == '__main__':
    main()
