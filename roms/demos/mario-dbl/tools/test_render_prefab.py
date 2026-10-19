#!/usr/bin/env python3
"""test_render_prefab.py — проверка тайл-префаба render.asm на эмуляторе v06_emu.

Гоняет НАСТОЯЩИЙ include/render.asm (после текстового раскрытия макроса SBYTE —
мини-ассемблер v06_emu не знает MACRO) для всех спрайтов из include/sprites.inc
в обоих путях: frac=0 (dr_tile, тайлы из записей) и frac=4 (rec_build +
drs_stage + tile-цикл пропуска пустых пар). Результат сравнивается с
независимым Python-эталоном:

  композиция:      res = v ^ ((v ^ bit) & op)     (v — байт VRAM)
  frac=0:          для КАЖДОЙ записи [pos][8 троек]:
                   addr(plane, i) = top + (pos>>2)*0x100 - (pos&3)*8 - i
  frac=4:          records -> плотные колонки (отсутствующий тайл = нули);
                   выходная колонка j=0..wc собирается побайтово
                   s = (prev & 0x0F) << 4 | (cur & 0xF0) >> 4, за пределами
                   спрайта сосед = 0 (zcol); строка r: addr = top + j*0x100 - r
  плоскость b1 = плоскость b0 - 0x2000 (зеркало main.c: rs_p1 = rs_p0 - 0x2000).

Эталон рисует ВСЕ строки; ASM вправе пропускать пары пустых тайлов — если
пропуск ошибочен (staged op != 0), байты разойдутся и тест это поймает.

Запуск:  python3 tools/test_render_prefab.py   (из roms/demos/mario-dbl)
"""
import os
import random
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'utils', 'emulator'))
from v06_emu import Emulator8080, Assembler8080  # noqa: E402

RENDER = os.path.join(HERE, '..', 'include', 'render.asm')
SPRITES = os.path.join(HERE, '..', 'include', 'sprites.inc')

GLOBALS = ['_rs_spr', '_rs_data', '_rs_p0', '_rs_p1', '_rs_s0', '_rs_s1']


def expand_sbyte(lines):
    """Раскрыть SBYTE MACRO ofs ... ENDM текстово (v06_emu не знает MACRO)."""
    out, body, in_def = [], None, False
    for ln in lines:
        s = ln.strip()
        if not in_def and re.match(r'^SBYTE\s+MACRO\b', s, re.I):
            in_def = True
            body = []
            continue
        if in_def:
            if re.match(r'^\s*ENDM\b', s, re.I):
                in_def = False
                continue
            body.append(s)
            continue
        m = re.match(r'^\s*SBYTE\s+(\d+)\s*$', ln, re.I)
        if m:
            ofs = m.group(1)
            for b in body:
                out.append('        ' + re.sub(r'\bofs\b', ofs, b))
        else:
            out.append(ln.rstrip('\n'))
    return out


def parse_sprites():
    txt = open(SPRITES, encoding='utf-8').read()
    sprites = []
    for m in re.finditer(
            r'static const unsigned char (mario\w+)\[\] = \{([^}]*)\}', txt):
        data = [int(x, 16) for x in re.findall(r'0x([0-9A-Fa-f]{2})', m.group(2))]
        sprites.append((m.group(1), data))
    return sprites


def build_asm_text(sprites):
    lines = expand_sbyte(open(RENDER, encoding='utf-8').read().splitlines())
    harness = ['', '; --- harness globals (в сборке определены в main.c) ---']
    for g in GLOBALS:
        harness.append('%s: defw 0' % g)
    harness.append('_rs_cols: defb 0')
    harness.append('_rs_frac: defb 0')
    harness.append('')
    for name, data in sprites:
        harness.append('%s:' % name)
        for i in range(0, len(data), 16):
            harness.append('    defb ' + ', '.join('0x%02X' % b for b in data[i:i + 16]))
    return ['ORG 0x0100'] + lines + harness


def to_dense(data):
    """records -> плотные колонки троек [col][row32] = (op,b0,b1)."""
    wc, hc, hp, nt = data[:4]
    dense = [[(0, 0, 0)] * (hc * 8) for _ in range(wc)]
    for k in range(nt):
        rec = data[4 + k * 25: 4 + k * 25 + 25]
        pos = rec[0]
        col, row = pos >> 2, pos & 3
        for i in range(8):
            dense[col][row * 8 + i] = (rec[1 + i * 3], rec[2 + i * 3], rec[3 + i * 3])
    return wc, hc, dense


def model_draw(mem, top, data, frac):
    """Эталон: композиция спрайта в mirror-память mem (полный проход без пропусков)."""
    wc, hc, dense = to_dense(data)
    def comp(addr, op, bit):
        v = mem[addr]
        mem[addr] = v ^ ((v ^ bit) & op)
    if frac == 0:
        nt = data[3]
        for k in range(nt):
            rec = data[4 + k * 25: 4 + k * 25 + 25]
            col, row = rec[0] >> 2, rec[0] & 3
            for i in range(8):
                op, b0, b1 = rec[1 + i * 3], rec[2 + i * 3], rec[3 + i * 3]
                off = col * 0x100 - row * 8 - i
                comp((top + off) & 0xFFFF, op, b0)
                comp((top - 0x2000 + off) & 0xFFFF, op, b1)
    else:
        for j in range(wc + 1):
            cur = dense[j] if j < wc else [(0, 0, 0)] * 32
            prev = dense[j - 1] if j > 0 else [(0, 0, 0)] * 32
            for r in range(32):
                po = prev[r]
                co = cur[r]
                s_op = ((po[0] & 0x0F) << 4) | ((co[0] & 0xF0) >> 4)
                s_b0 = ((po[1] & 0x0F) << 4) | ((co[1] & 0xF0) >> 4)
                s_b1 = ((po[2] & 0x0F) << 4) | ((co[2] & 0xF0) >> 4)
                a0 = (top + j * 0x100 - r) & 0xFFFF
                a1 = (a0 - 0x2000) & 0xFFFF
                comp(a0, s_op, s_b0)
                comp(a1, s_op, s_b1)


def run_case(emu, top, spr_addr, data, frac, seed):
    c = emu.reset()                       # чистая RAM + программа
    rnd = random.Random(seed)
    for a in range(0x8000, 0x10000):      # весь VRAM-оокно случайный шум
        c.mem[a] = rnd.randrange(256)
    mirror = bytearray(c.mem)
    model_draw(mirror, top, data, frac)
    c.ww(emu.asm.labels['_rs_spr'], spr_addr)
    c.ww(emu.asm.labels['_rs_p0'], top)
    c.ww(emu.asm.labels['_rs_p1'], (top - 0x2000) & 0xFFFF)
    c.wb(emu.asm.labels['_rs_frac'], frac)
    emu.call('_mario_draw_sprite', sp=0x6000, max_steps=2_000_000)
    diff = [(a, c.mem[a], mirror[a]) for a in range(0x8000, 0x10000)
            if c.mem[a] != mirror[a]]
    return diff


def main():
    sprites = parse_sprites()
    assert sprites, 'sprites.inc пуст — перегенерируй gen_assets.py'
    path = os.path.join(HERE, '.scratch_render_prefab.asm')
    with open(path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(build_asm_text(sprites)) + '\n')
    emu = Emulator8080()
    emu.load_asm(path)
    print('asm: %d строк, метка _mario_draw_sprite=0x%04X' %
          (len(sprites), emu.asm.labels['_mario_draw_sprite']))

    n_fail = 0
    for name, data in sprites:
        for frac in (0, 4):
            # L=top&0xFF: 0xF8 — без займа при delta<=24; 0x08 — с займом
            for lsb in (0xF8, 0x08):
                top = 0xE100 | lsb
                diff = run_case(emu, top, emu.asm.labels[name.lower()],
                                data, frac, seed=0xC0FFEE)
                if diff:
                    n_fail += 1
                    a, got, want = diff[0]
                    print('FAIL %-10s frac=%d top=0x%04X: %d байт, '
                          'напр. 0x%04X asm=%02X эталон=%02X' %
                          (name, frac, top, len(diff), a, got, want))
    total = len(sprites) * 2 * 2
    if n_fail:
        print('ИТОГ: %d/%d ПРОВАЛОВ' % (n_fail, total))
        sys.exit(1)
    print('ИТОГ: OK — %d кейсов (26 спрайтов x frac{0,4} x borrow{нет,е}) '
          'побитово совпали с эталоном' % total)
    os.remove(path)


if __name__ == '__main__':
    main()
