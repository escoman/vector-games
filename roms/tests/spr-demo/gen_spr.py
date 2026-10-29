#!/usr/bin/env python3
"""
gen_spr.py — генератор spr.inc для spr-demo: спрайт-«инопланетянин»
24×24 (3 столбца, плоскости П1/П0), три фазы анимации, в двух форматах
SPR_FORMAT (спека docs/SPR_FORMAT.MD, ядра lib/gfx/spr.asm):

  inv_flat_0..2  — плоский дескриптор для spr_blit
                   ([FLAGS, COLS, DEPTH] + DATA: по плоскостям П1, П0,
                    на столбец [SHIFT, LEN] + LEN байт — головные и
                    хвостовые нули не хранятся);
  inv_mask_0..2  — дескриптор с маской для spr_blit_mask
                   ([FLAGS, COLS, DEPTH] + TABLE (COLS пар [SHIFT, LEN],
                    общая для всех блоков) + DATA: блок МАСКИ первым
                    (mask = ~(П1|П0) построчно), затем прогоны П1, П0);
  inv_erase      — «ящик» зачистки 24×24 (нули в П1/П0, столбцы [0, 24])
                   — используется spr_blit для стирания прошлой позиции.

Арт рисуется программно (круги/прямоугольники): тело — круг П0,
брюшко и глаза — П1, рот — прорезь (прозрачность: в маск-варианте
сквозь него видно фон), ножки меняются по фазам. Плоскости:
П0 = бит 0 палитры, П1 = бит 1; П0+П1 = чёрный контур.

FLAGS: bit2=П1, bit3=П0; у маск-варианта +bit4 (маска), bit5 (sparse —
документационный, библиотекой не читается), bit6 (OR-композит).

Запуск: python3 gen_spr.py  →  spr.inc
"""

from pathlib import Path

W, H = 24, 24          # пикселей
PLANES = (1, 0)        # порядок прогонов: П1, П0 (как в библиотеке)


def disk(cx, cy, r):
    """Пиксели диска (круга) с центром (cx, cy) и радиусом r."""
    return {(x, y) for x in range(W) for y in range(H)
            if (x - cx) ** 2 + (y - cy) ** 2 <= r * r}


def rect(x0, y0, x1, y1):
    """Пиксели прямоугольника x0..x1 (вкл.), y0..y1 (вкл.)."""
    return {(x, y) for x in range(x0, x1 + 1) for y in range(y0, y1 + 1)}


def make_frames():
    """Три фазы: (П0, П1) — множества пикселей."""
    frames = []
    for f in range(3):
        p0 = set()
        p1 = set()

        # Антенны: два усика сверху.
        for x in (10, 13):
            p0 |= rect(x, 0, x, 3)

        # Тело: круг.
        p0 |= disk(12, 11, 8)

        # Брюшко: круг поверх тела.
        p1 |= disk(12, 12, 4)

        # Глаза.
        for cx in (8, 16):
            p1 |= disk(cx, 9, 2)

        # Рот — прорезь насквозь (прозрачность в обоих плоскостях).
        mouth = rect(8, 14, 15, 16)
        p0 -= mouth
        p1 -= mouth

        # Ножки по фазам.
        if f == 0:      # вместе
            p0 |= rect(6, 18, 9, 23) | rect(14, 18, 17, 23)
        elif f == 1:    # вразлёт
            p0 |= rect(4, 16, 8, 23) | rect(15, 16, 19, 23)
        else:           # вместе + ступни
            p0 |= rect(6, 17, 9, 22) | rect(14, 17, 17, 22)
            p0 |= rect(5, 23, 10, 23) | rect(13, 23, 18, 23)

        frames.append((p0, p1))
    return frames


def column_bytes(pix, c):
    """24 байта столбца c (по строке на байт), MSB = левый пиксель."""
    rows = []
    for y in range(H):
        b = 0
        for k in range(8):
            if (8 * c + (7 - k), y) in pix:
                b |= 1 << k
        rows.append(b)
    return rows


def compact(rows):
    """[SHIFT, LEN] + байты с первой по последнюю ненулевую строку."""
    first = next((i for i, b in enumerate(rows) if b), None)
    if first is None:
        return [0, 0]
    last = max(i for i, b in enumerate(rows) if b)
    return [first, last - first + 1] + rows[first:last + 1]


def flat_descriptor(p0, p1):
    """Плоский дескриптор: FLAGS=0x0C, прогоны П1, затем П0."""
    data = []
    for pix in (p1, p0):
        for c in range(3):
            data += compact(column_bytes(pix, c))
    return [0x0C, 3, H] + data


def mask_descriptor(p0, p1):
    """Дескриптор с маской: TABLE + [маска][П1][П0]."""
    table = []
    spans = []
    for c in range(3):
        s, l = compact(column_bytes(p0 | p1, c))[:2]
        spans.append((s, l))
        table += [s, l]

    data = []
    for c, (s, l) in enumerate(spans):
        mp = column_bytes(p0 | p1, c)
        for i in range(s, s + l):
            data.append((~mp[i]) & 0xFF)
    for pix in (p1, p0):
        for c, (s, l) in enumerate(spans):
            rows = column_bytes(pix, c)
            data += rows[s:s + l]

    return [0x7C, 3, H] + table + data


def erase_descriptor():
    """Ящик зачистки: нули в П1/П0, столбцы [0, 24] — полный рост."""
    data = []
    for _ in PLANES:
        for _c in range(3):
            data += [0, H] + [0] * H
    return [0x0C, 3, H] + data


def fmt(data, per_line=12):
    lines = []
    for i in range(0, len(data), per_line):
        lines.append('    ' + ', '.join(f'0x{b:02X}' for b in data[i:i + per_line]))
    return ',\n'.join(lines)


def main():
    frames = make_frames()
    out = []
    a = out.append
    a('/*')
    a(' * spr.inc — спрайт-«инопланетянин» 24×24 для spr-demo. СГЕНЕРИРОВАН')
    a(' * gen_spr.py — руками не править, перегенерировать: python3 gen_spr.py.')
    a(' *')
    a(' * Формат SPR_FORMAT (docs/SPR_FORMAT.MD), ядра lib/gfx/spr.asm:')
    a(' *   inv_flat_N — плоский дескриптор для spr_blit: [FLAGS, COLS, DEPTH]')
    a(' *     + DATA (прогоны П1, П0; столбец = [SHIFT, LEN] + LEN байт);')
    a(' *   inv_mask_N — дескриптор с маской для spr_blit_mask:')
    a(' *     [FLAGS, COLS, DEPTH] + TABLE (пары [SHIFT, LEN]) + DATA')
    a(' *     (блок маски первым, затем прогоны П1, П0);')
    a(' *   inv_erase  — ящик зачистки 24×24 (нули в П1/П0) для spr_blit.')
    a(' *')
    a(' * FLAGS: bit2=П1, bit3=П0; маск-вариант: +bit4 (маска), bit6 (OR).')
    a(' * Плоскости: П0=бит 0 палитры, П1=бит 1; П0+П1=чёрный. Рот спрайта —')
    a(' * прорезь: в маск-варианте сквозь неё видно фон, erase не нужен.')
    a(' */')
    a('')
    for i, (p0, p1) in enumerate(frames):
        a(f'static const unsigned char inv_flat_{i}[] = {{')
        a(fmt(flat_descriptor(p0, p1)))
        a('};')
        a('')
    for i, (p0, p1) in enumerate(frames):
        a(f'static const unsigned char inv_mask_{i}[] = {{')
        a(fmt(mask_descriptor(p0, p1)))
        a('};')
        a('')
    a('static const unsigned char * const inv_frames_flat[3] = {')
    a('    inv_flat_0, inv_flat_1, inv_flat_2')
    a('};')
    a('')
    a('static const unsigned char * const inv_frames_mask[3] = {')
    a('    inv_mask_0, inv_mask_1, inv_mask_2')
    a('};')
    a('')
    a('static const unsigned char inv_erase[] = {')
    a(fmt(erase_descriptor()))
    a('};')
    a('')
    Path(__file__).with_name('spr.inc').write_text('\n'.join(out))
    print(f'spr.inc: {len("\n".join(out))} байт текста')


if __name__ == '__main__':
    main()
