"""Спрайты юнита игрока (самолётик и танк) -> include/unit.inc.

  python3 tools/gen_unit.py [--preview assets/unit_preview.png]

Почему спрайт, а не патч в кольцо. В оригинале объект — это 3D-каркас из
банка форм $653A, который $D9D6 кладёт в кольцо патчем 4x21 байт (ENGINE.MD
§4.4). У нас кольцо — это 32 мировых столбца, а не полосы глубины, поэтому
юнит рисуется прямо в свободную плоскость буфера (C000 у A, 8000 у B) тем
же шагом адресации, что и рельеф: байт колонки — 8 пикселей по горизонтали.

Формат таблицы. Спрайт сдвинут на 2*phase пикселей вправо (4 фазы, как
фаз ракурса у оригинала), поэтому для каждой фазы в ROM лежит свой набор
из 5 байтовых столбцов по un_rows байт; столбец c, строка r — байт
c*un_rows + r, строка 0 — НИЖНЯЯ (байты кладутся вверх по экрану, как в
m_blit). Фаза занимает un_cols*un_rows байт, всего на спрайт 4 фазы.

Арт генерится кодом (не ASCII), чтобы форму можно было править числами;
превью — тот же растр, что уйдёт в ROM.
"""

import sys

W = 32                      # ширина рисунка в пикселях (без сдвигов фаз)
H = 20                      # высота спрайта, строк
COLS = (W + 2 * 3 + 7) // 8  # 5: рисунок + три сдвига по 2 пикселя
PHASES = 4


# ------------------------------------------------------------------ самолётик

def plane():
    """Вид сзади-сверху: каркас дельта-крыла, фюзеляж-игла, киль."""
    px = [[0] * W for _ in range(H)]
    cx = (W - 1) / 2.0

    def put(x, y):
        if 0 <= x < W and 0 <= y < H:
            px[y][x] = 1

    def near(v, target, eps):
        return abs(v - target) <= eps

    # задняя кромка крыла — сплошная, в две строки
    for y in range(0, 2):
        for x in range(W):
            if abs(x - cx) <= 15:
                put(x, y)
    # кромки крыла: линии, сходящиеся к носу (тонкий каркас)
    for y in range(1, 10):
        half = 15 - (y - 1) * 1.6
        if half < 0:
            break
        for x in range(W):
            if near(abs(x - cx), half, 0.6):
                put(x, y)
    # фюзеляж: спина от кромки до киля
    for y in range(1, H):
        for x in range(int(cx) - 1, int(cx) + 1):
            put(x, y)
    # киль
    for y in range(12, H):
        for x in (int(cx) - 2, int(cx) + 2):
            put(x, y)
    # фонарь кабины — просвет в спине
    for y in range(9, 12):
        for x in range(int(cx) - 1, int(cx) + 1):
            px[y][x] = 0
    return px


# --------------------------------------------------------------------- танк

def tank():
    """Корпус с гусеницами, башня, ствол вверх-вперёд."""
    px = [[0] * W for _ in range(H)]
    cx = (W - 1) / 2.0

    def put(x, y):
        if 0 <= x < W and 0 <= y < H:
            px[y][x] = 1

    # гусеницы: две широкие полосы по краям корпуса
    for y in range(0, 7):
        for x in range(W):
            d = abs(x - cx)
            if 11 <= d <= 15:
                put(x, y)
    # корпус
    for y in range(5, 10):
        for x in range(W):
            if abs(x - cx) <= 12:
                put(x, y)
    # башня
    for y in range(9, 15):
        half = 6 - (y - 9) * 0.7
        for x in range(W):
            if abs(x - cx) <= half:
                put(x, y)
    # ствол
    for y in range(15, H):
        for x in range(int(cx) - 1, int(cx) + 1):
            put(x, y)
    return px


# ------------------------------------------------------------------- растр

def shifted(art, phase):
    """Арт, сдвинутый на 2*phase пикселей вправо, разложенный по столбцам."""
    cols = []
    for c in range(COLS):
        run = []
        for r in range(H):
            v = 0
            for bit in range(8):
                x = c * 8 + bit - 2 * phase
                if 0 <= x < W and art[H - 1 - r][x]:
                    v |= 0x80 >> bit
            run.append(v)
        cols.append(run)
    return cols


def fmt(name, art):
    out = ['%s:' % name]
    for phase in range(PHASES):
        cols = shifted(art, phase)
        out.append('; фаза %d (+%d px)' % (phase, 2 * phase))
        for c, run in enumerate(cols):
            out.append('    defb %s' % ','.join('0%02Xh' % v for v in run))
    return out


def preview(art, path):
    from PIL import Image
    zoom = 6
    img = Image.new('RGB', (W * zoom + 8, H * zoom + 8), (0, 0, 0))
    for y in range(H):
        for x in range(W):
            if art[y][x]:
                px = 4 + x * zoom
                py = 4 + (H - 1 - y) * zoom
                for dy in range(zoom):
                    for dx in range(zoom):
                        img.putpixel((px + dx, py + dy), (255, 255, 255))
    img.save(path)
    print('превью:', path, img.size)


HEADER = """\
; unit.inc — спрайты юнита игрока (самолётик и танк).
;
; Сгенерировано tools/gen_unit.py — руками не правится; включается из
; include/unit.asm.
;
; Спрайт = un_cols байтовых столбцов по un_rows байт (столбец = 8 пикселей
; по горизонтали, строка 0 — нижняя). Фаз 4, сдвиг фазы — 2 пикселя вправо;
; фаза занимает un_cols*un_rows байт, как в банке форм оригинала (4 ракурса).

SECTION rodata_user

PUBLIC un_plane
PUBLIC un_tank

un_cols  EQU %d
un_rows  EQU %d
un_bytes EQU %d                 ; байт на одну фазу (un_cols*un_rows)

""" % (COLS, H, COLS * H)


def main():
    art = {'plane': plane(), 'tank': tank()}
    path = None
    if '--preview' in sys.argv:
        path = sys.argv[sys.argv.index('--preview') + 1]
    if path:
        from PIL import Image  # noqa: F401
        preview(art['plane'], path)
    lines = [HEADER]
    lines += fmt('un_plane', art['plane'])
    lines.append('')
    lines += fmt('un_tank', art['tank'])
    out = 'include/unit.inc'
    with open(out, 'w') as f:
        f.write('\n'.join(lines) + '\n')
    print('записан', out)


if __name__ == '__main__':
    main()
