#!/usr/bin/env python3
"""Редактор уровней riseout (пока только просмотр карт).

Данные — из inc-файлов самой игры:
  inc/level_01.inc .. level_20.inc  — упакованные RLE-карты;
  inc/glyph_block.inc               — растры глифов 8×8 (тайл t → глиф 0x60+t);
  inc/glyph_mode_table.inc          — режимы записи тайлов в плоскости
                                      (как есть / CMA-инверсия / заливка);
  inc/level_names.inc               — имена 20 уровней.
Формат карты (Stage 7): пары [длина|тайл] — мл. ниббл = длина повтора
(0 ⇒ 256), ст. ниббл = код тайла 0..15; развёртка = ровно 704 клетки
(22 ряда × 32, шаг ряда 0x20); тайл 0x0F → пусто, 0x00 — старт игрока,
0x04 — враг (точка появления; спрайты врагов живут в плоскости C000).

Запуск:  python3 tools/level_editor.py [номер 1..20]   — окно tkinter
         (нужен python3-tk: sudo apt install python3-tk);
         python3 tools/level_editor.py --ascii [номер] — карта в терминал
         (без номера — проверка всех 20 уровней: развёртка = 704 клетки);
         python3 tools/level_editor.py --png N файл.png — экспорт карты
         уровня N в PNG (без tkinter, x3).
"""
import base64
import re
import struct
import sys
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INC = ROOT / 'inc'
ROWS, COLS = 22, 32
CELLS = ROWS * COLS
BYTE_RE = re.compile(r'(?<![0-9A-Za-z_])([0-9A-Fa-f]{2,4})h(?![0-9A-Za-z_])')

# Цвета пикселей растра по коду тайла (фон всегда чёрный):
# старт — зелёный, враг — красный, ящики (9, A) — серо-голубые.
COLORS = {0x00: (80, 255, 80), 0x04: (255, 90, 90),
          0x09: (160, 195, 225), 0x0A: (160, 195, 225)}
COLOR_DEFAULT = (220, 220, 220)

# Композитный цвет пикселя по битам двух плоскостей записи карты
# (сверено с игрой): E000 (бит 0) — игрок, C000 (бит 1) — враги (спрайты,
# в картах не встречаются); A000 (бит 2) — стены, лестницы, ящики для сбора
# (голубой); 8000 (бит 3) — стены, дверь, мостки, ящики (жёлтый);
# пересечение A000+8000 — стены (светло-серые). Палитра в игре —
# анимированный ramp, оттенки здесь условные, но по плоскостям точные.
PLANE_COLORS = {(0, 0): (0, 0, 0), (1, 0): (255, 210, 60),
                (0, 1): (100, 200, 255), (1, 1): COLOR_DEFAULT}

# Вода (сверено с игрой): глубокая (тайл 6) — сплошная синяя, верхушка
# (тайл 8) — синяя со светло-серым гребнем. Оттенок темнее голубого A000:
# вода в игре по тону не совпадает с лестницами.
WATER_BLUE = (45, 115, 235)
TILE_PLANE_COLORS = {0x06: {(0, 1): WATER_BLUE},
                     0x08: {(0, 1): WATER_BLUE}}


def read_defb(path):
    """Байты всех defb-строк файла (комментарии после ';' отбрасываются)."""
    data = []
    for line in path.read_text(encoding='utf-8').splitlines():
        line = line.split(';', 1)[0]
        if not re.match(r'^\s*defb\s+', line):
            continue
        for v in BYTE_RE.findall(line):
            b = int(v, 16)
            if b > 0xFF:
                sys.exit('%s: значение %s не байт' % (path.name, v))
            data.append(b)
    return bytes(data)


def read_level_names():
    """Имена уровней из level_names.inc (NUL-терминированные строки)."""
    return [s.decode() for s in read_defb(INC / 'level_names.inc').split(b'\0') if s]


def expand_map(packed):
    """RLE-развёртка карты уровня: ровно CELLS байт (код тайла на клетку)."""
    cells = []
    for b in packed:
        run = b & 0x0F or 256
        cells.extend([b >> 4] * run)
        if len(cells) >= CELLS:
            break
    if len(cells) != CELLS:
        sys.exit('карта: %d клеток вместо %d' % (len(cells), CELLS))
    return cells


def glyph_rasters():
    """128 растров 8×8 из glyph_block.inc; байт0 = верх, MSB = левый пиксель."""
    block = read_defb(INC / 'glyph_block.inc')
    if len(block) != 1024:
        sys.exit('glyph_block.inc: %d байт вместо 1024' % len(block))
    return [block[i * 8:(i + 1) * 8] for i in range(128)]


def glyph_modes():
    """Режимы записи тайлов 0x60..0x6F по glyph_mode_table.inc.
    Повторяет func_render_glyph_vram: маска плоскости 0 = m & 0x88,
    плоскости 1 (0xA000) = RLC(m) & 0x88; 00 → заливка 0, 88 → заливка 1,
    80 → растр как есть, 08 → растр с инверсией (CMA). Байт режима:
    для кодов 0x65..0x6F — байт 0 группы, иначе байт 7."""
    tbl = read_defb(INC / 'glyph_mode_table.inc')
    if len(tbl) != 128:
        sys.exit('glyph_mode_table.inc: %d байт вместо 128' % len(tbl))

    def mask_mode(v):
        return {0x00: 'zero', 0x88: 'ones', 0x80: 'ras', 0x08: 'inv'}[v & 0x88]

    modes = {}
    for code in range(0x60, 0x70):
        grp = tbl[(code - 0x60) * 8:(code - 0x60) * 8 + 8]
        m = grp[0] if 0x65 <= code <= 0x6F else grp[7]
        rlc = ((m << 1) | (m >> 7)) & 0xFF
        modes[code] = (mask_mode(m), mask_mode(rlc))
    # Цикл рендера кодов 0x65..0x6F делает 8 проходов по четырём плоскостям,
    # каждый проход берёт свой байт группы режимов — двухплоскостная модель
    # выше это не передаёт. Сверено с игрой визуально: ящики (9, A) —
    # серо-голубые, видны в обеих плоскостях; тайл E — жёлтый неинвертированный
    # на 8000, как дверь. Вода (6, 8) и сундук (D) разбираются в cells_to_rgb.
    modes.update({0x69: ('ras', 'ras'),
                  0x6A: ('ras', 'ras'),
                  0x6E: ('ras', 'zero')})
    return modes


def plane_bit(mode, raster_byte, x):
    """Бит плоскости для пикселя x: заливка / растр / растр с инверсией."""
    if mode == 'zero':
        return 0
    if mode == 'ones':
        return 1
    on = 1 if raster_byte & (0x80 >> x) else 0
    return on if mode == 'ras' else 1 - on


def cells_to_rgb(cells, rasters, modes):
    """Карта 256×176 в байтах PPM (P6): две плоскости записи тайла
    (как func_render_glyph_vram) → композитный цвет пикселя."""
    out = bytearray()
    for row in range(ROWS):
        for y in range(8):                      # строка растра внутри ряда
            for col in range(COLS):
                tile = cells[row * COLS + col]
                if tile == 0x0F:                # пусто — растр не рисуется
                    out += b'\0\0\0' * 8
                    continue
                raster = rasters[0x60 + tile]
                ma, mb = modes[0x60 + tile]
                # Вода сверена с игрой: глубокая (6) — сплошная синяя;
                # верхушка (8) — гребень растра (ряды 0-5) светло-серый
                # над синей водой (ряды 6-7): цикл игры собирает это из
                # разных байтов группы режимов (C1 C1 C1 C4 C4 C4 44 41).
                if tile == 0x06:
                    ma, mb = 'zero', 'ones'
                elif tile == 0x08:
                    ma, mb = 'ras' if y < 6 else 'zero', 'ras'
                elif tile == 0x0D:
                    # Сундук сверен с игрой: три полоски на рядах 5-7 растра —
                    # голубая, светло-серая, голубая (средняя полоса пишется
                    # ещё и в 8000, отсюда серый).
                    ma, mb = 'ras' if y == 6 else 'zero', 'ras'
                for x in range(8):
                    pa, pb = plane_bit(ma, raster[y], x), plane_bit(mb, raster[y], x)
                    if tile in COLORS and (pa or pb):
                        out += bytes(COLORS[tile])
                    else:
                        pal = TILE_PLANE_COLORS.get(tile, PLANE_COLORS)
                        out += bytes(pal.get((pa, pb), PLANE_COLORS[(pa, pb)]))
    return out


def print_ascii(cells):
    """Карта в терминал: '#' — непустой тайл, 'S' — старт, 'E' — враг,
    'W' — глубокая вода, '~' — верхушка воды, 'C' — сундук, '.' — пусто."""
    for row in range(ROWS):
        line = ''
        for col in range(COLS):
            t = cells[row * COLS + col]
            line += '.' if t == 0x0F else ('S' if t == 0x00 else
                                           ('E' if t == 0x04 else
                                            ('W' if t == 0x06 else
                                             ('~' if t == 0x08 else
                                              ('C' if t == 0x0D else '#')))))
        print(line)


def encode_png(rgb, w, h, scale=3):
    """Минимальный PNG (RGB, без зависимостей): масштаб scale пикселей."""
    raw = bytearray()
    for y in range(h):
        line = bytearray()
        for x in range(w):
            line += rgb[(y * w + x) * 3:(y * w + x) * 3 + 3] * scale
        scan = b'\0' + bytes(line)               # фильтр 0 (None) на каждую строку
        raw += scan * scale                       # scale одинаковых строк

    def chunk(tag, data):
        return (struct.pack('>I', len(data)) + tag + data +
                struct.pack('>I', zlib.crc32(tag + data)))

    return (b'\x89PNG\r\n\x1a\n' +
            chunk(b'IHDR', struct.pack('>IIBBBBB', w * scale, h * scale, 8, 2, 0, 0, 0)) +
            chunk(b'IDAT', zlib.compress(bytes(raw), 9)) + chunk(b'IEND', b''))


def write_png(path, rgb, w, h, scale=3):
    """PNG-экспорт карты в файл."""
    Path(path).write_bytes(encode_png(rgb, w, h, scale))


def run_gui(level, names):
    try:
        import tkinter as tk
    except ImportError:
        sys.exit('нет tkinter: sudo apt install python3-tk '
                 '(или --ascii / --png режимы без GUI)')
    rasters = glyph_rasters()
    modes = glyph_modes()
    root = tk.Tk()
    root.title('riseout — просмотр карт уровней')
    box = tk.Listbox(root, width=22, exportselection=False)
    for n, name in enumerate(names, 1):
        box.insert('end', '%2d %s' % (n, name))
    box.pack(side='left', fill='y')
    right = tk.Frame(root)
    right.pack(side='left', fill='both', expand=True)
    canvas = tk.Canvas(right, width=COLS * 8 * 3, height=ROWS * 8 * 3, bg='black')
    canvas.pack()
    status = tk.Label(right, anchor='w', text='')
    status.pack(fill='x')

    packed = [None]                             # кэш упакованных карт
    image_ref = []

    def show(n):                                # n = 1..20
        path = INC / ('level_%02d.inc' % n)
        packed_bytes = read_defb(path)
        cells = expand_map(packed_bytes)
        # Tk 8.6 не читает PPM через data= — передаём base64 собственного PNG.
        # encode_png уже масштабирует ×3 (768×528) — повторный zoom не нужен.
        png = encode_png(cells_to_rgb(cells, rasters, modes), COLS * 8, ROWS * 8)
        img = tk.PhotoImage(data=base64.b64encode(png).decode())
        image_ref[:] = [img, cells]
        canvas.delete('all')
        canvas.create_image(0, 0, anchor='nw', image=img)
        root.title('riseout — уровень %d: %s' % (n, names[n - 1]))
        status.config(text='%d байт упаковки → %d клеток' % (len(packed_bytes),
                                                             len(cells)))

    def on_move(ev):
        cells = image_ref[1]
        col, row = ev.x // 24, ev.y // 24
        if 0 <= col < COLS and 0 <= row < ROWS:
            t = cells[row * COLS + col]
            status.config(text='ряд %2d  колонка %2d  тайл %X (глиф 0x%02X)%s'
                          % (row, col, t, 0x60 + t if t != 0x0F else 0x20,
                             '  — пусто' if t == 0x0F else
                             '  — старт игрока' if t == 0x00 else
                             '  — враг' if t == 0x04 else
                             '  — глубокая вода' if t == 0x06 else
                             '  — верхушка воды' if t == 0x08 else
                             '  — сундук' if t == 0x0D else ''))

    def on_select(_ev=None):
        show(box.curselection()[0] + 1)

    def on_key(ev):
        n = box.curselection()[0] + 1
        if ev.keysym == 'Left':
            n = max(1, n - 1)
        elif ev.keysym == 'Right':
            n = min(len(names), n + 1)
        else:
            return
        box.selection_clear(0, 'end')
        box.selection_set(n - 1)
        box.see(n - 1)
        show(n)

    box.bind('<<ListboxSelect>>', on_select)
    canvas.bind('<Motion>', on_move)
    root.bind('<Left>', on_key)
    root.bind('<Right>', on_key)
    box.selection_set(level - 1)
    box.see(level - 1)
    show(level)
    root.mainloop()


def main():
    args = [a for a in sys.argv[1:]]
    names = read_level_names()
    if len(names) != 20:
        sys.exit('level_names.inc: %d имён вместо 20' % len(names))
    if args and args[0] == '--ascii':
        if len(args) > 1:
            print_ascii(expand_map(read_defb(INC / ('level_%02d.inc' % int(args[1])))))
        else:
            for n in range(1, 21):
                expand_map(read_defb(INC / ('level_%02d.inc' % n)))
            print('все 20 карт: развёртка ровно %d клеток' % CELLS)
        return
    if args and args[0] == '--png':
        if len(args) != 3:
            sys.exit('--png: используйте --png <уровень 1..20> <файл.png>')
        n, out = int(args[1]), args[2]
        cells = expand_map(read_defb(INC / ('level_%02d.inc' % n)))
        rgb = cells_to_rgb(cells, glyph_rasters(), glyph_modes())
        write_png(out, rgb, COLS * 8, ROWS * 8)
        print('%s: уровень %d (%s), %d×%d ×3'
              % (out, n, names[n - 1], COLS * 8 * 3, ROWS * 8 * 3))
        return
    level = int(args[0]) if args else 1
    if not 1 <= level <= 20:
        sys.exit('номер уровня вне 1..20')
    run_gui(level, names)


if __name__ == '__main__':
    main()
