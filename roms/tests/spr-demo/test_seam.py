#!/usr/bin/env python3
"""Регрессия шва кольца 256 строк в lib/gfx/spr.asm (col_copy / col_or).

Модель: y спрайта — мировая координата по mod 256; строка r кольца лежит в
VRAM по адресу base + (x/8+col)*0x100 + (255 - r). Прогон, уходящий за
нуль столбца, ядро обязано разбить на seg1 (до offset 0x00) и seg2 (с
offset 0xFF того же блока), не задев соседние столбцы.

Запуск: python3 test_seam.py  (собирает spr.asm встроенным ассемблером
utils/emulator/v06_emu.py и вызывает _spr_init/_spr_blit/_spr_blit_mask).
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "utils" / "emulator"))
from v06_emu import Emulator8080  # noqa: E402

SPR_ASM = str(ROOT / "lib" / "gfx" / "spr.asm")
DESC_AREA = 0x6000  # дескрипторы раскладываются здесь (вне кода и VRAM)
SP = 0x7FF0  # стек в ОЗУ выше лесенок (0x7000..0x7203), VRAM не трогает

PLANE_BASE = {3: 0x8000, 2: 0xA000, 1: 0xC000, 0: 0xE000}


def ring_addr(x, col_idx, world_row, plane):
    """VRAM-адрес строки world_row (ring) в столбце col_idx плоскости plane."""
    return PLANE_BASE[plane] + ((x >> 3) + col_idx) * 0x100 + (255 - (world_row & 0xFF))


# ---------- модель дескрипторов ----------

def flat_desc(plane_cols):
    """plane_cols: [(plane, [(shift, bytes), ...]), ...] — плоскости в порядке П3..П0."""
    flags = 0
    cols = len(plane_cols[0][1])
    depth = max(s + len(d) for _, cs in plane_cols for s, d in cs)
    out = bytearray()
    for plane, _ in plane_cols:
        flags |= 1 << (3 - plane)
    out += bytes([flags, cols, depth])
    for _, cs in plane_cols:
        for shift, data in cs:
            out += bytes([shift, len(data)])
            out += data
    return bytes(out)


def mask_desc(cols_table, mask_bytes, plane_data, planes):
    """cols_table: [(shift, len)]; mask_bytes: линейно по столбцам;
    plane_data: [bytes...] на плоскость (линейно по столбцам); planes: список
    присутствующих плоскостей в порядке П3..П0."""
    flags = 0x10
    for p in planes:
        flags |= 1 << (3 - p)
    depth = max(s + l for s, l in cols_table)
    out = bytearray([flags, len(cols_table), depth])
    for s, l in cols_table:
        out += bytes([s, l])
    out += mask_bytes
    for d in plane_data:
        out += d
    return bytes(out)


def model_flat(x, y, plane_cols, bg=None):
    """Эталон: VRAM-словарь addr -> byte после плоского blit."""
    exp = dict(bg or {})
    for plane, cs in plane_cols:
        for ci, (shift, data) in enumerate(cs):
            for k, byte in enumerate(data):
                exp[ring_addr(x, ci, y + shift + k, plane)] = byte
    return exp


def model_mask(x, y, cols_table, mask_bytes, plane_data, planes, bg):
    """Эталон: dst = (dst AND mask) OR color на ring-строках."""
    exp = dict(bg)
    off = 0
    for ci, (shift, ln) in enumerate(cols_table):
        for k in range(ln):
            addr = ring_addr(x, ci, y + shift + k, planes[0])
            m = mask_bytes[off + k]
            for pi, p in enumerate(planes):
                col_byte = plane_data[pi][off + k]
                a = PLANE_BASE[p] + (addr & 0x1FFF)
                exp[a] = (exp.get(a, 0) & m) | col_byte
        off += ln
    return exp


# ---------- прогон кейса ----------

def run_case(name, build, expected):
    emu = Emulator8080()
    asm = emu.load_asm(SPR_ASM)
    labels = asm.labels if hasattr(asm, "labels") else asm.symbols
    cpu = emu.cpu
    desc = build(cpu)
    for i, b in enumerate(desc):
        cpu.wb(DESC_AREA + i, b)
    emu.call(labels["_spr_init"], args=(), sp=SP)
    entry = build.entry
    emu.call(labels[entry], args=(DESC_AREA, build.y, build.x), sp=SP)
    bad = []
    seen = set()
    for addr, val in sorted(expected.items()):
        seen.add(addr & 0xFFFF)
        got = cpu.rb(addr)
        if got != val:
            bad.append(f"  addr {addr:04X}: ожидалось {val:02X}, получено {got:02X}")
    # вне эталона VRAM должна остаться нулевой (bg-кейсы задают фон явно)
    if build.check_clean:
        for a in range(0x8000, 0x10000):
            if a in seen:
                continue
            got = cpu.rb(a)
            want = expected.get(a, 0) if a in expected else 0
            if got != want:
                bad.append(f"  чистота: addr {a:04X} = {got:02X} (ожидалось {want:02X})")
                if len(bad) > 12:
                    break
    status = "OK" if not bad else "FAIL"
    print(f"[{status}] {name}")
    for line in bad[:12]:
        print(line)
    return not bad


class Case:
    def __init__(self, entry, x, y, check_clean=True):
        self.entry = entry
        self.x = x
        self.y = y
        self.check_clean = check_clean


def main():
    ok = True

    # 1. Плоский blit, 1 столбец через шов: y=250, LEN=12 → seg1=6, seg2=6.
    pc1 = [(3, [(0, bytes(0xA0 + k for k in range(12)))])]
    def build1(cpu):
        return flat_desc(pc1)
    build1.entry = "_spr_blit"
    build1.x, build1.y = 0, 250
    build1.check_clean = True
    ok &= run_case("flat 1col seam y=250 LEN=12", build1, model_flat(0, 250, pc1))

    # 2. Две плоскости (П3+П0), 2 столбца, разный SHIFT: шов + не-шов.
    x2, y2 = 16, 248
    c0 = bytes(0x10 + k for k in range(10))   # SHIFT=2, LEN=10 → шов (L=5)
    c1 = bytes(0x80 + k for k in range(4))    # SHIFT=0, LEN=4  → без шва (L=7)
    pc2 = [(3, [(2, c0), (0, c1)]), (0, [(2, bytes(v | 0x01 for v in c0)),
                                         (0, bytes(v | 0x02 for v in c1))])]
    def build2(cpu):
        return flat_desc(pc2)
    build2.entry, build2.x, build2.y, build2.check_clean = "_spr_blit", x2, y2, True
    ok &= run_case("flat 2plane 2col mixed seam y=248", build2, model_flat(x2, y2, pc2))

    # 3. Регрессия без шва: y=100, SHIFT=4, LEN=24.
    pc3 = [(2, [(4, bytes(0xC0 + (k * 7) & 0xFF for k in range(24)))])]
    def build3(cpu):
        return flat_desc(pc3)
    build3.entry, build3.x, build3.y, build3.check_clean = "_spr_blit", 24, 100, True
    ok &= run_case("flat no-seam regression y=100 LEN=24", build3, model_flat(24, 100, pc3))

    # 4. Старт за швом: y=250, SHIFT=8 (строка 258 ≡ ring 2, offset 253), LEN=6.
    pc4 = [(1, [(8, bytes(0x33 + k for k in range(6)))])]
    def build4(cpu):
        return flat_desc(pc4)
    build4.entry, build4.x, build4.y, build4.check_clean = "_spr_blit", 8, 250, True
    ok &= run_case("flat start-below-seam y=250 SHIFT=8", build4, model_flat(8, 250, pc4))

    # 5. Максимальный LEN=32 ровно от шва: y=255 → L=0, seg1=1, seg2=31.
    pc5 = [(3, [(0, bytes(0x40 + (k * 3) & 0xFF for k in range(32)))])]
    def build5(cpu):
        return flat_desc(pc5)
    build5.entry, build5.x, build5.y, build5.check_clean = "_spr_blit", 0, 255, True
    ok &= run_case("flat LEN=32 at y=255 (seg1=1/seg2=31)", build5, model_flat(0, 255, pc5))

    # 6. Маска через шов: П3+П1, 2 столбца, фон — шахматка.
    x6, y6 = 8, 246
    tab = [(1, 14), (0, 9)]            # col0: L=8 → шов (14>9); col1: L=9 → шов? 9 == L+1=10? 9≤10 нет шва
    mask = bytes((0x5A if (k & 1) else 0xA5) for k in range(14 + 9))
    col_p3 = bytes(0xF0 | (k & 0x0F) for k in range(23))
    col_p1 = bytes(0x0F & ~k for k in range(23))
    bg = {}
    for ci, (s, l) in enumerate(tab):
        for k in range(l):
            for p in (3, 1):
                bg[ring_addr(x6, ci, y6 + s + k, p)] = (0x11 * ((k + ci) & 0xFF)) & 0xFF
    # фон и вне прогона — чтобы проверить, что маска его не тронула
    for a in range(0x8000, 0x10000):
        bg.setdefault(a, (a ^ (a >> 8)) & 0xFF)
    def build6(cpu):
        for a, v in bg.items():
            cpu.wb(a, v)
        return mask_desc(tab, mask, [col_p3, col_p1], [3, 1])
    build6.entry, build6.x, build6.y = "_spr_blit_mask", x6, y6
    build6.check_clean = False  # чистоту проверит model_mask по полному bg
    exp6 = model_mask(x6, y6, tab, mask, [col_p3, col_p1], [3, 1], bg)
    ok &= run_case("mask 2plane seam y=246 (col0 seg 9/5)", build6, exp6)

    # 7. Маска LEN=28 на шву: y=255, L=0 → seg1=1, seg2=27.
    x7, y7 = 0, 255
    tab7 = [(0, 28)]
    mask7 = bytes(0x3C if (k & 2) else 0xC3 for k in range(28))
    col7 = bytes(0x99 ^ k for k in range(28))
    bg7 = {ring_addr(x7, 0, y7 + k, 3): (0x7E - k) & 0xFF for k in range(28)}
    def build7(cpu):
        for a, v in bg7.items():
            cpu.wb(a, v)
        return mask_desc(tab7, mask7, [col7], [3])
    build7.entry, build7.x, build7.y = "_spr_blit_mask", x7, y7
    build7.check_clean = False
    exp7 = model_mask(x7, y7, tab7, mask7, [col7], [3], bg7)
    ok &= run_case("mask LEN=28 at y=255 (seg1=1/seg2=27)", build7, exp7)

    print("ALL PASS" if ok else "FAILURES PRESENT")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
