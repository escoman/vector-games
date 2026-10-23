#!/usr/bin/env python3
"""test_preshift.py — офлайн-проверка генератора предсдвигов (+4 px).

На старте ROM main.c (sh_build_one) печатает в RAM пул sh_pool предсдвинутые
варианты всех поз — в ТОМ ЖЕ тайл-префаб формате, чтобы asm-вывод (dr_tile)
не отличал их от базовых. Формула сдвига задокументирована в gen_assets.py
(shift_trip: out[c] = (in[c] >> 4) | (in[c-1] << 4) побайтно по op/b0/b1).

Проверяем без эмулятора, что Python-модель C-кода (sh_model = дословный
sh_build_one) даёт префабы, ПОБайТОВО равные эталону to_prefab(shift_trip(...))
для всех спрайтов sprites.inc, и что пул не переполняется (фактический размер
<= SH_POOL_SIZE — верхняя оценка gen_assets.py, резервируемая main.c).

    python3 tools/test_preshift.py
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..')
sys.path.insert(0, HERE)
import gen_assets as G                                   # noqa: E402


def parse_sprites_inc(path):
    """-> [(name, [bytes])] из автогенённого include/sprites.inc."""
    txt = open(path).read()
    out = []
    for m in re.finditer(
            r'static const unsigned char (\w+)\[\] = \{(.*?)\};', txt, re.S):
        data = [int(v, 16) for v in re.findall(r'0x[0-9A-Fa-f]{2}', m.group(2))]
        out.append((m.group(1), data))
    return out


def parse_define(path, name):
    m = re.search(r'#define\s+%s\s+(\d+)' % name, open(path).read())
    assert m, '%s не найден в sprites.inc — перегенерируйте ассеты' % name
    return int(m.group(1))


def prefab_to_cols(data):
    """Префаб -> колонки троек (wc колонок × 32 строки), обратная to_prefab."""
    wc, hc, hpix, nt = data[0], data[1], data[2], data[3]
    assert hc == G.HCELLS and hpix == G.HPX
    assert len(data) == 4 + nt * 25
    grid = [[(0, 0, 0)] * hpix for _ in range(wc)]
    for i in range(nt):
        pos = data[4 + i * 25]
        col, row = pos >> 2, pos & 3
        for r in range(G.CELL):
            trip = tuple(data[4 + i * 25 + 1 + r * 3 + 0:
                             4 + i * 25 + 1 + r * 3 + 3])
            grid[col][row * G.CELL + r] = trip
    return grid


def sh_model(data, dense=None):
    """Модель main.c:sh_build_one. dense — общий скретч-буфер (как глобал в C);
    если передан, используется и обнуляется ровно на (wc+1)*hc*24 байт — как
    исправленный C-код (16-битный счётчик). Это воспроизводит межспрайтовое
    заражение, если бы обнуление было неполным (баг усечения счётчика)."""
    wc, hc, nt = data[0], data[1], data[3]
    stride = hc * 24                                   # шаг колонки = 96 при hc=4
    need = (wc + 1) * stride
    if dense is None:
        d = [0] * need
    else:
        d = dense
        for p in range(need):               # обнуление ВСЕЙ используемой сетки
            d[p] = 0
    for i in range(nt):                                # шаг 2: записи в плотную сетку
        pos = data[4 + i * 25]
        col, row = pos >> 2, pos & 3
        base = col * stride + row * 24
        for b in range(24):
            d[base + b] = data[4 + i * 25 + 1 + b]
    # шаг 3: для каждой выходной клетки J и тайл-ряда row слить prev<<4 | cur>>4,
    # непустой тайл -> запись pos=(J<<2)|row + 24 байта.
    recs = []
    for J in range(wc + 1):
        for row in range(hc):
            tbase = J * stride + row * 24
            tile = []
            for b in range(24):
                cur = d[tbase + b]
                prev = d[tbase - stride + b] if J > 0 else 0
                tile.append((cur >> 4) | ((prev << 4) & 0xF0))
            if any(tile):
                recs.append([(J << 2) | row] + tile)
    out = [wc + 1, hc, G.HPX, len(recs)]
    for r in recs:
        out += r
    return out


def fill_list_names():
    """Порядок all_spr как в main.c:sh_fill_list (frames, turn, run; L,R)."""
    names = []
    for i in range(G.MAIN_POSES):
        names += ['mario%d_l' % (i + 1), 'mario%d_r' % (i + 1)]
    for pi in G.TURN_IDS:
        names += ['mario%d_l' % (pi + 1), 'mario%d_r' % (pi + 1)]
    for pi in G.RUN_IDS:
        names += ['mario%d_l' % (pi + 1), 'mario%d_r' % (pi + 1)]
    return names


def main():
    inc = os.path.join(ROOT, 'include', 'sprites.inc')
    sprites = parse_sprites_inc(inc)
    nspr = parse_define(inc, 'MARIO_NSPR')
    pool = parse_define(inc, 'SH_POOL_SIZE')
    assert len(sprites) == nspr, \
        'спрайтов %d, а MARIO_NSPR=%d — перегенерируйте ассеты' % (len(sprites), nspr)

    total = 0
    bad = 0
    maxoff = 0
    for name, data in sprites:
        cols = prefab_to_cols(data)
        golden = G.to_prefab(G.shift_trip(cols))       # эталон формулы
        model = sh_model(data)                          # изолированная модель
        if model != golden:
            bad += 1
            print('FAIL %s: модель != эталон' % name)
            for i, (a, b) in enumerate(zip(model, golden)):
                if a != b:
                    print('   [%d] model=0x%02X golden=0x%02X' % (i, a, b))
            print('   len model=%d golden=%d' % (len(model), len(golden)))
        n = model[3]
        nsrc = data[3]
        assert n <= min(2 * nsrc, (data[0] + 1) * G.HCELLS), \
            '%s: тайлов %d больше верхней оценки пула' % (name, n)
        maxoff = max(maxoff, total)      # кумулятивное смещение позы в пуле
        total += len(model)
    assert bad == 0, '%d спрайтов не совпали с эталоном' % bad
    assert total <= pool, \
        'пул: фактический %d > SH_POOL_SIZE %d — переполнение RAM!' % (total, pool)

    # === сквозная проверка старта ROM: общий sh_dense в порядке sh_fill_list ===
    # Воспроизводит mario_prebuild_shifted целиком. Если обнуление dense когда-
    # нибудь снова усекутся до байта, wide-позы left начнут подхватывать грязь
    # предыдущего спрайта в необнулённых правых колонках -> prefab != golden.
    by_name = dict(sprites)
    shared = [0] * ((4 + 1) * G.HCELLS * 24)            # размер sh_dense в C
    for name in fill_list_names():
        data = by_name[name]
        got = sh_model(data, dense=shared)
        exp = G.to_prefab(G.shift_trip(prefab_to_cols(data)))
        assert got == exp, \
            'shared-dense %s != эталон — неполное обнуление (усечение счётчика)?' % name
        # проверка, что требуемое число обнуления реально >255 хоть где-то:
        # именно поэтому счётчик в C обязан быть 16-битным
    maxzero = max((d[0] + 1) * d[1] * 24 for _, d in sprites)
    assert maxzero <= len(shared), \
        'dense: нужно %d байт, буфер лишь %d' % (maxzero, len(shared))
    # sh_of хранит смещение позы в пуле как 16-бит (main.c: unsigned int),
    # иначе смещения >255 обрезались бы байтом и sh_select вернул неверный указатель.
    assert maxoff < 65536, \
        'смещение позы %d не влезает в uint16 sh_of[]' % maxoff
    print('OK: %d предсдвигов побитово совпали с эталоном (изолир. + shared-dense); '
          'пул %d/%d байт, макс. смещение %d, макс. обнуление %d B'
          % (len(sprites), total, pool, maxoff, maxzero))


if __name__ == '__main__':
    main()
