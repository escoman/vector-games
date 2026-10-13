#!/usr/bin/env python3
"""profile_scroll.py — T-состоянный профиль горизонтального скролла mario-8cols.

Гоняет НАСТОЯЩИЙ код из собранного ROM (mario-8c.rom + mario-8c.map) в
эмуляторе проекта (utils/emulator/v06_emu.py) и суммирует такты Intel 8080 по
трассе. Содержимое окна тайлкарты (tile_win) печётся Python-копией bake_* из
main.c, поэтому рендер видит ровно ту карту, что в игре.

Модель кадра ходьбы (как в main.c): Марио смещается на 1 тайловый столбец раз
в MOVE_DELAY кадров; камера идёт нога в ногу, значит render_window с diff по
одной колонке вызывается раз на два кадра. Спрафт рисуется каждый кадр, когда
что-то изменилось.

Запуск: python3 tools/profile_scroll.py [КАДРОВ] [sweep] [--rom ФАЙЛ --map ФАЙЛ]
"""
import re
import sys
from collections import Counter
from pathlib import Path
from types import SimpleNamespace

HERE = Path(__file__).resolve().parent.parent            # roms/demos/mario-8cols
ROOT = HERE.parents[2]                                   # корень vector-games
sys.path.insert(0, str(ROOT / "utils" / "emulator"))
from v06_emu import CPU8080, SENTINEL                   # noqa: E402

CAM_NO_REF = 0xFFFF
VIEW = 32
SP = 0x7E00               # стек ниже VRAM и выше ROM/BSS (0x0100..0x4654)
# Бюджет кадра ВЕКТОРА: 59 904 такта CPU на кадр при 50 Гц (docs/VECTOR_VERIFIED.md:
# «59904 такт/кадр × 50 Гц ≈ 3 МГц»), а не миллион.
FRAME_T_BUDGET = 59_904

# Wait states видеоконтроллера (таблица EMU80 VectorCpuWaits::getCpuWaitStates,
# см. docs/VECTOR_VERIFIED.md §4.4.2): индекс = базовые такты Intel 8080.
# Без них офлайн-профиль занижает реальную цену кадра на ~25-30%.
WAITS = [0, 0, 0, 0, 0, 3, 0, 1, 0, 0, 2, 5, 0, 3, 0, 0, 4, 7, 6]


def wait_cycles(c: int) -> int:
    return c + (WAITS[c] if c < len(WAITS) else 0)

# ---------------- такты Intel 8080 (таблица как в roms/demos/fire2) ---------
_3BYTE = {0x01, 0x11, 0x21, 0x31, 0x22, 0x2A, 0x32, 0x3A, 0xCD, 0xC3,
          0xC2, 0xCA, 0xD2, 0xDA, 0xE2, 0xEA, 0xF2, 0xFA,
          0xC4, 0xCC, 0xD4, 0xDC, 0xFF}
_2BYTE = {0x06, 0x0E, 0x16, 0x1E, 0x26, 0x2E, 0x36, 0x3E,
          0xC6, 0xCE, 0xD6, 0xDE, 0xE6, 0xEE, 0xF6, 0xFE}


def ilen(op: int) -> int:
    if op in _3BYTE:
        return 3
    if op in _2BYTE:
        return 2
    return 1


def cycles(op: int, taken: bool) -> int:
    hi, lo = op >> 6, op & 7
    if op in (0x3A, 0x32):
        return 13                     # LDA/STA abs
    if op in (0x2A, 0x22):
        return 16                     # LHLD/SHLD abs
    if op == 0x00:
        return 4
    if op == 0x76:
        return 7
    if 0x40 <= op <= 0x7F:
        if lo == 6 or (op >> 3) & 7 == 6:
            return 7                  # MOV r,M / MOV M,r
        return 5
    if 0x80 <= op <= 0xBF:
        return 7 if lo == 6 else 4    # ALU M / ALU r
    if hi == 0:
        return {1: 10, 2: 7, 3: 5,
                4: 10 if (op >> 3) & 7 == 6 else 5,
                5: 10 if (op >> 3) & 7 == 6 else 5,
                6: 10 if (op >> 3) & 7 == 6 else 7,
                9: 10}.get(lo, 4)
    if op in (0xC9, 0xD9, 0xE9, 0xF9, 0xFB, 0xF3, 0x7B, 0x73, 0x7A, 0x72):
        return 5 if op == 0xE9 else 4
    return {0: 11 if taken else 5, 1: 10, 2: 10 if taken else 7,
            3: 10 if op == 0xC3 else 17, 4: 17 if taken else 11,
            5: 11, 6: 7, 7: 11}.get(lo, 4)


MNEM = {0x3A: "lda", 0x32: "sta", 0x2A: "lhld", 0x22: "shld", 0x1A: "ldax d",
        0x0A: "ldax b", 0x12: "stax d", 0x02: "stax b", 0x0B: "dcx d",
        0x13: "dex? 0x13", 0x23: "inx h", 0x1B: "dcx d", 0x05: "dcr b",
        0xC2: "jp nz", 0xCA: "jp z", 0x09: "dad b", 0x19: "dad d",
        0x29: "dad h", 0x39: "dad sp", 0xCD: "call", 0xC9: "ret",
        0xC3: "jmp", 0xBE: "cmp m", 0xB6: "ora m", 0xD6: "sui",
        0x7C: "mov a,h", 0x7D: "mov a,l", 0x44: "mov b,h", 0x4D: "mov c,l",
        0x67: "mov h,a", 0x6F: "mov l,a", 0x5F: "mov e,a", 0x57: "mov d,a",
        0x77: "mov m,a", 0x7F: "mov a,a", 0x47: "mov b,a", 0x4F: "mov c,a",
        0xC5: "push b", 0xD5: "push d", 0xE5: "push h", 0xE1: "pop h",
        0xF1: "pop af", 0xD1: "pop d", 0xB7: "ora a", 0xA7: "ana a",
        0x37: "stc", 0x3F: "cmc", 0x07: "rlc", 0x0F: "rrc", 0x17: "ral",
        0x1F: "rar", 0x87: "add a", 0x8F: "adc a", 0x97: "sub a",
        0x9F: "sbb a", 0xB3: "ora e", 0xB1: "ora c", 0xA9: "xor c",
        0x0C: "inr c", 0x1C: "inr e", 0x2C: "inr l", 0x3C: "inr a",
        0x14: "inr d", 0x04: "inr b", 0x24: "inr h", 0x34: "inr m",
        0x0D: "dcr c", 0x1D: "dcr e", 0x2D: "dcr l", 0x3D: "dcr a",
        0x25: "dcr h", 0x35: "dcr m", 0x0E: "mvi c", 0x16: "mvi d",
        0x1E: "mvi e", 0x26: "mvi h", 0x2E: "mvi l", 0x3E: "mvi a",
        0x06: "mvi b", 0x36: "mvi m", 0x01: "lxi b", 0x11: "lxi d",
        0x21: "lxi h", 0x31: "lxi sp", 0xEB: "xchg", 0xD5: "push d",
        0xE3: "xthl", 0xE5: "push h", 0xF5: "push psw", 0xE6: "ani",
        0xFE: "cpi", 0xC6: "aci", 0xCE: "aci", 0xDE: "sbi", 0xEE: "xri",
        0xF6: "ori", 0xDB: "in", 0xD3: "out", 0x76: "halt", 0x00: "nop",
        0xC7: "rst 0", 0xCF: "rst 1", 0xD7: "rst 2", 0xDF: "rst 3",
        0xE7: "rst 4", 0xEF: "rst 5", 0xF7: "rst 6", 0xFF: "rst 7"}


def mnem(op):
    return MNEM.get(op, f"{op:02X}")


def category(op: int) -> str:
    hi, lo = op >> 6, op & 7
    if op in (0x22, 0x2A, 0x32, 0x3A):
        return "память-абс (LDA/STA/LHLD/SHLD)"
    if op in (0x02, 0x12, 0x0A, 0x1A) or (0x40 <= op <= 0x7F and (lo == 6 or (op >> 3) & 7 == 6)):
        return "память-косв (LDAX/STAX/MOV r,M)"
    if op in (0x09, 0x19, 0x29, 0x39):
        return "DAD"
    if op == 0xC9 or (hi == 3 and lo in (0, 2, 3, 7)):
        return "переходы (JMP/Jc/RET)"
    if op == 0xCD or (hi == 3 and lo == 4):
        return "вызовы (CALL)"
    if hi == 3 and lo in (1, 5):
        return "стек (PUSH/POP)"
    if 0x80 <= op <= 0xBF or (op in _2BYTE and lo == 6):
        return "ALU (cmp/add/sub/logic)"
    if 0x40 <= op <= 0x7F:
        return "MOV r,r"
    if lo in (4, 5) and hi != 3:
        return "INR/DCR"
    if lo == 3:
        return "INX/DCX"
    if lo == 1:
        return "LXI"
    if lo == 6 and hi != 3:
        return "MVI"
    return "прочее"


# ---------------- ROM и карта ----------------
class Rom:
    def __init__(self, rom_path: Path, map_path: Path):
        self.data = rom_path.read_bytes()
        self.sym = {}
        self.symbols = []            # (addr, name, module) публичных меток
        for line in map_path.read_text().splitlines():
            m = re.match(r"([A-Za-z_.$][\w.$]*)\s*=\s*\$([0-9A-Fa-f]+)\s*;\s*"
                         r"(addr|const)(?:,\s*(\w+))?\s*,\s*([^,]*),\s*([^,]*),\s*([^;]*)", line)
            if not m:
                continue
            name, addr, kind, _, mod, src, loc = m.groups()
            self.sym[name] = int(addr, 16)
            if kind == "addr" and not name.startswith(("__", "_d", "_t")):
                self.symbols.append((int(addr, 16), name, mod or ""))
        self.symbols.sort()

    def at(self, name):
        return self.sym[name]

    def spans(self, lo, hi):
        """Метки в адресном диапазоне [lo,hi] — для разбивки по участкам кода."""
        return [(a, n) for a, n, _ in self.symbols if lo <= a <= hi]

    def label_at(self, pc):
        prev = None
        for a, n, mod in self.symbols:
            if a <= pc:
                prev = (a, n, mod)
            elif prev:
                return prev
        return prev


# ---------------- level.inc ----------------
def parse_incs(path: Path):
    txt = path.read_text()

    def arr(name):
        m = re.search(r"const\s+unsigned\s+(?:int|char)\s+" + name +
                      r"\s*(?:\[\d*\])?\s*=\s*\{(.*?)\};", txt, re.S)
        vals = []
        for part in m.group(1).split(","):
            part = part.split("/*")[0].strip()
            if part:
                vals.append(int(part, 0))
        return vals

    def num(name):
        return int(re.search(r"#define\s+" + name + r"\s+(\d+)", txt).group(1), 0)

    return {
        "COLS": num("LEVEL_COLS"), "ROWS": num("LEVEL_ROWS"),
        "WIN_COLS": num("OBJ_WIN_COLS"), "WIN_STEP": num("OBJ_WIN_STEP"),
        "WIN_BLOCKS": num("OBJ_WIN_BLOCKS"), "PF_BACK": num("PF_BACK"),
        "tileset": arr("tileset"), "pf_data": arr("pf_data"),
        "pf_rects": arr("pf_rects"), "pf_var_ofs": arr("pf_var_ofs"),
        "pf_var_n": arr("pf_var_n"), "pf_start": arr("pf_start"),
        "tile_nz": arr("tile_nz"), "pair_top": arr("pair_top"),
    }


# ---------------- Python-копия bake_* (для состояния окна) ----------------
def bake_groups(win, base, wstart, wend, lv):
    rows = lv["ROWS"]
    b0 = wstart >> 5
    b1 = (wend - 1) >> 5
    back = lv["PF_BACK"]
    b0 = b0 - back if b0 > back else 0
    b1 = min(b1, lv["WIN_BLOCKS"] - 1)
    end = lv["pf_start"][b1 + 1]
    pd, pr = lv["pf_data"], lv["pf_rects"]
    for i in range(lv["pf_start"][b0], end):
        p = pd[i * 4:i * 4 + 4]
        x = p[1] | ((p[0] & 0x80) << 1)
        y = p[2]
        v = (p[0] & 0x7F) | ((p[3] & 0x1F) << 7)
        vofs = lv["pf_var_ofs"][v]
        for rc in range(lv["pf_var_n"][v]):
            o = pr[(vofs + rc) * 5:(vofs + rc) * 5 + 5]
            c0 = max(min(x + o[1], wend), wstart)
            c1 = min(x + o[1] + o[3], wend)
            if c0 >= c1:
                continue
            nrows = min(o[4], rows - y - o[2])
            t = o[0]
            q0 = (c0 - base) * rows + y + o[2]        # левый верх прямоугольника
            for c in range(c1 - c0):                  # col += LEVEL_ROWS
                for r in range(nrows):
                    win[q0 + c * rows + r] = t


def bake_window(lv, base):
    win = [0] * (lv["WIN_COLS"] * lv["ROWS"])
    bake_groups(win, base, base, base + lv["WIN_COLS"], lv)
    return win


def bake_shift(win, base, nb, lv):
    """Копия bake_shift: 1 — инкрементально, None — нужен полный bake."""
    rows, step = lv["ROWS"], lv["WIN_STEP"]
    if nb == base + step:
        for c in range(step):
            for r in range(rows):
                win[c * rows + r] = win[(step + c) * rows + r]
        for c in range(step, lv["WIN_COLS"]):
            for r in range(rows):
                win[c * rows + r] = 0
        bake_groups(win, nb, nb + step, nb + lv["WIN_COLS"], lv)
        return nb
    if nb + step == base:
        for c in range(step):
            for r in range(rows):
                win[(step + c) * rows + r] = win[c * rows + r]
        for c in range(step):
            for r in range(rows):
                win[c * rows + r] = 0
        bake_groups(win, nb, nb, nb + step, lv)
        return nb
    return None


def set_stride(cpu, rom, rows):
    """Выставить шаг колонки окна так, как это делает main() на старте:
    _tile_stride = rows, _tile_stride_shl = log2(rows) (0xFF, если не степень
    двойки). BSS при --no-crt не обнуляется, а тесты зовут рендер напрямую (не
    через main), поэтому без показателя степени _mulshift множит на мусор.
    """
    cpu.wb(rom.at("_tile_stride"), rows)
    shl = rom.sym.get("_tile_stride_shl")
    if shl is not None:
        s = 0
        while s < 8 and (1 << s) < rows:
            s += 1
        cpu.wb(shl, s if (1 << s) == rows else 0xFF)


def install_window(cpu, a, win, base, lv, prevcol=None):
    """Занести запечённое окно и его базу в память эмулируемого ROM.

    prevcol — МИРОВАЯ колонка base-1 в колонку-страж tile_win_prevcol
    (в игре её заполняет bake_shift). Без неё diff на кадре перехода окна
    читает мусор и недооценивает число грязных клеток нулевого блока.
    """
    tw = a["_tile_win"]
    if prevcol is not None:
        cpu.mem[tw - lv["ROWS"]:tw] = bytes(prevcol)
    n = lv["WIN_COLS"] * lv["ROWS"]
    cpu.mem[tw:tw + n] = bytes(win)
    cpu.ww(a["_tile_win_base"], base)


def outgoing_col(win, base, nb, lv):
    """Колонка, которую bake_shift обязан сохранить в страже при сдвиге вперёд."""
    rows, step = lv["ROWS"], lv["WIN_STEP"]
    if nb == base + step:
        return win[(step - 1) * rows:step * rows]
    return None


def vram_of(cpu):
    """Снимок VRAM (0x8000..0xFFFF) — то, что реально видит луч."""
    return bytes(cpu.mem[0x8000:0x10000])


# ---------------- вызовы ----------------
class ProfCPU(CPU8080):
    """CPU без накопления трасс.

    v06_emu.CPU8080.wb() дописывает кортеж в write_trace на КАЖДУЮ запись в
    память (хоть трасса включена, хоть нет), а trace хранит по два snapshot-dict
    на инструкцию. На проходе камеры по уровню это раздувает RAM до гигабайт и
    роняет не только процесс, но и IDE. Здесь считается только число записей.
    """

    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        self.vram_wr = 0

    def wb(self, addr, val):
        addr &= 0xFFFF
        self.mem[addr] = val & 0xFF
        if addr >= 0x8000:                # все 4 плоскости VRAM
            self.vram_wr += 1


def new_cpu(rom: Rom):
    cpu = ProfCPU()
    for i, b in enumerate(rom.data):
        if b:
            CPU8080.wb(cpu, 0x0100 + i, b)   # загрузка ROM не в счёт VRAM-записей
    cpu.vram_wr = 0
    return cpu


def run_prof(cpu, stop_pc, max_steps=4_000_000):
    """Шаг за шагом, такты 8080 + wait states агрегируются сразу (трасса не ведётся)."""
    n = cyc = base = 0
    per_pc, per_cat, per_op, op_cnt = Counter(), Counter(), Counter(), Counter()
    mem, step = cpu.mem, cpu.step
    for _ in range(max_steps):
        if cpu.pc == stop_pc or cpu.halted:
            break
        pc0 = cpu.pc
        op = mem[pc0]
        if step():
            break
        b = cycles(op, cpu.pc != pc0 + ilen(op))
        n += 1
        base += b
        c = wait_cycles(b)
        cyc += c
        per_pc[pc0] += c
        per_cat[category(op)] += c
        per_op[op] += c
        op_cnt[op] += 1
    else:
        raise TimeoutError(f"лимит {max_steps} шагов, PC=0x{cpu.pc:04X}")
    return SimpleNamespace(instr=n, cyc=cyc, base=base, per_pc=per_pc,
                           per_cat=per_cat, per_op=per_op, op_cnt=op_cnt,
                           vram=cpu.vram_wr)


def push_args(cpu, sp, args):
    """sccz80 classic пушит параметры СЛЕВА НАПРАВО, поэтому arg0 — дальше всех
    от SP, а последний аргумент лежит по sp+2 (см. комментарии в mario.asm:
    nblk (sp+2), blk0 (sp+4), old_cam (sp+6), cam (sp+8)). Оба соглашения
    (cdecl и __z88dk_callee) раскладку аргументов одинаковую, различается лишь то,
    кто чистит стек — для замеров тактов это неважно.
    """
    top = sp
    for a in args:
        top -= 2
        CPU8080.ww(cpu, top, a & 0xFFFF)      # без счёта VRAM: это стек
    top -= 2
    CPU8080.ww(cpu, top, SENTINEL)            # фейковый адрес возврата
    return top


def call_asm(cpu, addr, args, sp=SP):
    """Вызов __z88dk_callee из mario.asm."""
    cpu.halted = False
    cpu.pc = addr
    cpu.sp = push_args(cpu, sp, args)
    cpu.vram_wr = 0
    res = run_prof(cpu, SENTINEL)
    cpu.sp = sp
    return res


def call_cdecl(cpu, addr, args, sp=SP):
    """Вызов C-функции (sccz80 cdecl)."""
    return call_asm(cpu, addr, args, sp)


def region_of(pc, regions):
    """Имя участка кода, которому принадлежит pc (regions отсортированы по addr)."""
    name = "(вне меток)"
    for a, n in regions:
        if a <= pc:
            name = n
        else:
            break
    return name


def region_totals(per_pc, regions):
    """Суммарные такты по участкам кода."""
    agg = Counter()
    for pc, c in per_pc.items():
        agg[region_of(pc, regions)] += c
    return agg


def show(title, res, regions=None, top=14):
    print(f"\n=== {title} ===")
    line = (f"инструкций {res.instr:,}   тактов {res.cyc:,} "
            f"(голых {res.base:,} + wait states {res.cyc - res.base:,})   "
            f"T/инстр {res.cyc / max(res.instr, 1):.2f}   "
            f"{100 * res.cyc / FRAME_T_BUDGET:.0f}% кадра")
    if res.vram:
        line += f"   записей VRAM {res.vram:,}"
    print(line)
    print("категории:")
    for k, c in sorted(res.per_cat.items(), key=lambda kv: -kv[1])[:9]:
        print(f"  {c:>9,}  {100 * c / res.cyc:5.1f}%  {k}")
    if regions:
        print("участки кода (по меткам карты):")
        agg = region_totals(res.per_pc, regions)
        for k, c in sorted(agg.items(), key=lambda kv: -kv[1])[:14]:
            print(f"  {c:>9,}  {100 * c / res.cyc:5.1f}%  {k}")
    print(f"top-{top} опкодов по тактам:")
    for op, c in sorted(res.per_op.items(), key=lambda kv: -kv[1])[:top]:
        print(f"  {c:>9,}  {100 * c / res.cyc:5.1f}%  x{res.op_cnt[op]:<7,} {mnem(op)}")
    return res.cyc, res.per_pc


def env_only_sweep():
    return "sweep" in sys.argv[1:]


def rom_paths():
    """--rom ФАЙЛ --map ФАЙЛ: профилировать произвольную сборку (например,
    эталонную до оптимизации) теми же замерами. По умолчанию — local build."""
    args = sys.argv[1:]

    def opt(flag, dflt):
        return args[args.index(flag) + 1] if flag in args else dflt

    return (Path(opt("--rom", HERE / "mario-8c.rom")),
            Path(opt("--map", HERE / "mario-8c.map")))


def render_syms(rom):
    """Метки горячего пути горизонтального скролла: от умножителя шага окна
    до _render_rowband (multiplicand/mulshift/mulstride, render_window,
    rw_block, rw_put_cell, rw_copy8)."""
    return rom.spans(rom.at("_mulstride"), rom.at("_render_rowband") - 1)


def region_totals_from_trace(trace, regions):    # совместимость со старым API
    agg = Counter()
    for e in trace:
        op = e["opcode"]
        pc = e["pre"]["pc"]
        taken = e["post"]["pc"] != pc + ilen(op)
        agg[region_of(pc, regions)] += cycles(op, taken)
    return agg


def sweep(cpu, rom, a, lv, rows):
    """Пошаговый проход камеры по всему уровню: T на каждый сдвиг + разбивка."""
    rw_syms = render_syms(rom)
    base = 0
    win = bake_window(lv, 0)
    install_window(cpu, a, win, base, lv)
    max_cam = lv["COLS"] - VIEW
    print(f"\n=== ПРОХОД КАМЕРЫ 0..{max_cam} (по одному шагу скролла) ===")
    scan_k = put_k = copy_k = 0
    rows_out = []
    for cam in range(max_cam):
        nb = (cam + 1) & ~(lv["WIN_STEP"] - 1)
        if nb != base:
            prev = outgoing_col(win, base, nb, lv)
            nbb = bake_shift(win, base, nb, lv)
            if nbb is None:
                win = bake_window(lv, nb)
                prev = None
            base = nb
            install_window(cpu, a, win, base, lv, prev)
        res = call_asm(cpu, a["_render_window"], [cam + 1, cam, 0, VIEW])
        c = res.cyc
        agg = region_totals(res.per_pc, rw_syms)
        scan = agg.get("rw_scan", 0) + agg.get("rw_scan_next", 0) + \
            agg.get("rw_topset", 0) + agg.get("rw_top0", 0) + agg.get("rw_blk_ret", 0)
        put = agg.get("_rw_put_cell", 0) + agg.get("rw_p0w", 0) + agg.get("rw_p1", 0)
        copy = agg.get("_rw_copy8", 0)
        scan_k += scan
        put_k += put
        copy_k += copy
        wb_cnt = res.vram
        rows_out.append((cam + 1, c, wb_cnt, scan, put, copy, res.instr))
        if (cam + 1) % 8 == 0:
            print(f"  cam={cam + 1:>4}: {c:>8,} T  (скан {100 * scan // max(c,1)}%, "
                  f"put {100 * put // max(c,1)}%, copy {100 * copy // max(c,1)}%) "
                  f"записей VRAM {wb_cnt:,}", flush=True)
    rows_out.sort(key=lambda t: -t[1])
    print("\nхудшие 12 шагов скролла:")
    for cam, c, wbn, scan, put, copy, n in rows_out[:12]:
        print(f"  cam={cam:>4} {c:>9,} T  записей {wbn:>5,}  "
              f"скан {scan:>8,} ({100 * scan // c}%)  put {put:>7,}  copy {copy:>7,}")
    print("лучшие 6:")
    for cam, c, wbn, scan, put, copy, n in rows_out[-6:]:
        print(f"  cam={cam:>4} {c:>9,} T  записей {wbn:>5,}  скан {scan:>8,}  put {put:>7,}")
    tot = sum(t[1] for t in rows_out)
    wb_tot = sum(t[2] for t in rows_out)
    print(f"\nИТОГО по уровню: {tot:,} T на {max_cam} шагов, среднее {tot // max_cam:,} T/шаг "
          f"({tot / max_cam / FRAME_T_BUDGET:.2f} кадра на шаг), макс {rows_out[0][1]:,} T "
          f"({rows_out[0][1] / FRAME_T_BUDGET:.2f} кадра)")
    print(f"разбивка в среднем на шаг: скан/обход {scan_k // max_cam:,} T "
          f"({100 * scan_k // tot}%), put_cell {put_k // max_cam:,} T ({100 * put_k // tot}%), "
          f"copy8 {copy_k // max_cam:,} T ({100 * copy_k // tot}%)")
    print(f"записей VRAM в среднем {wb_tot // max_cam:,} байт/шаг, "
          f"{tot // max(wb_tot, 1)} T на один байт VRAM в среднем")


def main():
    raw = sys.argv[1:]
    only_sweep = "sweep" in raw               # и с --rom/--map тоже
    rom_path, map_path = rom_paths()
    pos = [x for x in raw if x != "sweep" and not x.startswith("--")]
    for flag in ("--rom", "--map"):          # значения флагов не позиционные
        if flag in raw and raw[raw.index(flag) + 1] in pos:
            pos.remove(raw[raw.index(flag) + 1])
    frames = 100 if only_sweep else (int(pos[0]) if pos else 240)
    rom = Rom(rom_path, map_path)
    lv = parse_incs(HERE / "src" / "level.inc")
    rows = lv["ROWS"]
    print(f"ROM {rom_path.name} {len(rom.data)} байт, LEVEL {lv['COLS']}x{rows}, "
          f"окно {lv['WIN_COLS']} кол. шаг {lv['WIN_STEP']}, "
          f"бюджет кадра {FRAME_T_BUDGET:,} T (59 904 тактов CPU при 50 Гц, "
          f"wait states видеоконтроллера учтены)")

    a = {k: rom.at(k) for k in ("_render_window", "_render_rowband", "_mario_draw",
                                "_mario_undraw", "_mario_stand_r", "_mario_walk1_r",
                                "_bake_groups", "_bake_shift", "_bake_window",
                                "_solid_at", "_tile_win", "_tile_win_base",
                                "_cam_row", "_tile_stride", "_tileset", "_pair_top")}
    cpu = new_cpu(rom)
    set_stride(cpu, rom, rows)
    cpu.wb(a["_cam_row"], 32)

    if only_sweep:
        sweep(cpu, rom, a, lv, rows)
        return

    rw_syms = render_syms(rom)
    print("метки mario.asm: " + ", ".join(f"{n}@{x:04X}" for x, n in rw_syms))

    # --- базовые замеры ---
    win = bake_window(lv, 0)
    install_window(cpu, a, win, 0, lv)
    show("render_window: ПЕРВЫЙ ЭКРАН (cam=0, old=CAM_NO_REF, 32 блока)",
         call_asm(cpu, a["_render_window"], [0, CAM_NO_REF, 0, VIEW]),
         regions=rw_syms)

    show("render_window: скролл cam 0->1 (diff)",
         call_asm(cpu, a["_render_window"], [1, 0, 0, VIEW]),
         regions=rw_syms)

    show("mario_draw 16x16", call_asm(cpu, a["_mario_draw"],
                                      [40, 80, a["_mario_stand_r"]]))
    show("mario_undraw", call_asm(cpu, a["_mario_undraw"], []))
    show("render_rowband (одна мировая строка, 32 колонки)",
         call_asm(cpu, a["_render_rowband"], [32, 0]), regions=rw_syms)

    # нижняя граница: если бы от рисовалась только новая колонка (сдвиг VRAM
    # не вариант, но это полезно сравнить с полной разностью по 32 блокам)
    show("render_window: ОДНА новая колонка (cam 0->1, blk0=31, nblk=1)",
         call_asm(cpu, a["_render_window"], [1, 0, 31, 1]), regions=rw_syms)
    show("bake_window() — полная перепечка окна (C, случай прыжка камеры)",
         call_cdecl(cpu, a["_bake_window"], []))

    # --- модель ходьбы: камера +1 колонку каждые MOVE_DELAY кадров ---
    cam, base = 0, 0
    win = bake_window(lv, 0)
    per_frame = []
    t_draw = call_asm(cpu, a["_mario_draw"],
                      [40, 80, a["_mario_walk1_r"]]).cyc
    t_undraw = call_asm(cpu, a["_mario_undraw"], []).cyc
    sprite_cost = t_draw + t_undraw
    for f in range(frames):
        if f % 2 == 1:                      # кадр, когда камера сдвинулась
            oc = cam
            cam += 1
            nb = cam & ~(lv["WIN_STEP"] - 1)
            bake_t = 0
            if nb != base:
                nbb = bake_shift(win, base, nb, lv)
                if nbb is None:
                    win = bake_window(lv, nb)
                    bake_t = call_cdecl(cpu, a["_bake_window"], []).cyc
                else:
                    # ценим именно _bake_shift: в него входит memmove пережившей
                    # половины окна, копирование уехавшей колонки в страж и
                    # запекание новой
                    bake_t = call_cdecl(cpu, a["_bake_shift"], [nb]).cyc
                base = nb
                # ROM-версия bake_* уже обновила tile_win и tile_win_prevcol в
                # памяти; ставим поверх Python-модель (она байт-в-байт совпадает,
                # см. tools/check_bake.py), а страж не трогаем — егоfillит
                # вызванный выше ROM _bake_shift
                install_window(cpu, a, win, base, lv)
            res = call_asm(cpu, a["_render_window"], [cam, oc, 0, VIEW])
            per_frame.append((f, cam, res.cyc, bake_t, sprite_cost, res.vram))
        else:
            per_frame.append((f, cam, 0, 0, sprite_cost, 0))
    tot = sum(p[2] + p[3] + p[4] for p in per_frame)
    worst = max(per_frame, key=lambda p: p[2] + p[3] + p[4])
    print(f"\n=== ХОДЬБА ВПРАВО {frames} кадров ({frames // 2} шагов камеры) ===")
    print(f"всего {tot:,} T, среднее {tot // frames:,} T/кадр "
          f"({tot / frames / FRAME_T_BUDGET:.2f} кадра, "
          f"{100 * tot / frames / FRAME_T_BUDGET:.0f}% бюджета)")
    print(f"спрайт (undraw+draw) каждый кадр: {sprite_cost:,} T")
    print(f"худший кадр #{worst[0]} cam={worst[1]}: render {worst[2]:,} T + "
          f"bake {worst[3]:,} T + спрайт {worst[4]:,} T "
          f"= {worst[2] + worst[3] + worst[4]:,} T "
          f"({(worst[2] + worst[3] + worst[4]) / FRAME_T_BUDGET:.2f} кадра)")
    scroll_costs = sorted((p[2] for p in per_frame if p[2]), reverse=True)
    if scroll_costs:
        print(f"render_window при скролле: макс {scroll_costs[0]:,} "
              f"({scroll_costs[0] / FRAME_T_BUDGET:.2f} кадра) "
              f"медиана {scroll_costs[len(scroll_costs)//2]:,} "
              f"({scroll_costs[len(scroll_costs)//2] / FRAME_T_BUDGET:.2f} кадра) "
              f"мин {scroll_costs[-1]:,} T")
    bakes = [p for p in per_frame if p[3]]
    for p in bakes[:4]:
        print(f"  перепечка окна на cam={p[1]}: bake {p[3]:,} T + render {p[2]:,} T "
              f"= {p[2] + p[3] + p[4]:,} T за один кадр "
              f"({(p[2] + p[3] + p[4]) / FRAME_T_BUDGET:.1f} кадров)")

    # детальный разбор шаблонного шага скролла
    scrolls = [p for p in per_frame if p[2]]
    mid = sorted(scrolls, key=lambda p: p[2])[len(scrolls) // 2] if scrolls else None
    if mid:
        c = mid[1]
        show(f"render_window: шаблонный шаг скролла (cam={c})",
             call_asm(cpu, a["_render_window"], [c, c - 1, 0, VIEW]),
             regions=rw_syms)

    # --- C-侧 hot path ---
    # bake_groups/bake_shift — static с негласным контрактом: параметры это
    # МИРОВЫЕ колонки, а пишут они по (c0 - tile_win_base) [main.c:221]. После
    # обхода камеры база равна 96, и вызов bake_groups(32,64) уводит указатель
    # за окно (запись в мусор), а bake_shift(32) вообще выходит по ветке
    # «прыжок». Поэтому возвращаем окно к базе 0 и меряем консистентный вызов.
    win = bake_window(lv, 0)
    install_window(cpu, a, win, 0, lv, outgoing_col(win, 0, 32, lv))
    show("solid_at (одна проверка коллизии)", call_cdecl(cpu, a["_solid_at"], [4, 60]))
    show("bake_groups(32,64) — запекание половины окна (C)",
         call_cdecl(cpu, a["_bake_groups"], [32, 64]))
    show("bake_shift(32) — сдвиг окна на шаг (C, включая bake_groups)",
         call_cdecl(cpu, a["_bake_shift"], [32]))

    # --- проход по всему уровню: стоимость каждого шага скролла ---
    if "sweep" in raw:
        sweep(cpu, rom, a, lv, rows)


if __name__ == "__main__":
    main()
