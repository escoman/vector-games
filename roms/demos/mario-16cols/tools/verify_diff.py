#!/usr/bin/env python3
"""Проверка инкрементальной перерисовки из mario.asm на эмуляторе 8080.

Что проверяется (после перехода на палитру «небо = индекс 0» и дорисовку
разностью):

  0. И полный редрав, и разность обязаны совпадать с независимой моделью кадра
     на Python (tilemap + tileset), а не только с друг другом.
  1. Дорисовка разностью (шаг камеры +-1) обязана дать побайтово тот же кадр,
     что и полный редрав того же cam с чистого VRAM (чистый = 0 = небо);
     симметрично — влево.
  2. Частичное окно render_window(cam, old, blk0, nblk) трогает только блоки
     [blk0, blk0+nblk); остальной экран остаётся из старого кадра.
  3. mario_draw пишет строго в свои 2 блока x 4 плоскости x 16 строк, а
     mario_undraw возвращает VRAM побайтово в состояние до спрайта.
  4. Сквозной прогон кадров как в main.c (undraw -> diff -> draw) на финальных
     позициях совпадает с эталоном «полный редрав + спрайт».

Плюс печатается число VRAM-записей на шаг — сверка с расчётом (2835/шаг,
3456 первый экран, было 32768 на полный редрав).

Адреса берутся из mario.map, поэтому пересборка ROM инструмент не ломает.

    make all && python3 tools/verify_diff.py
"""
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..",
                                "..", "utils", "emulator"))
from v06_emu import Emulator8080                                # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ROM = os.path.join(HERE, "..", "mario.rom")
MAP = os.path.join(HERE, "..", "mario.map")

SP = 0x7FF0
CAM_NO_REF = 0xFFFF
VIEW_BLOCKS = 32
PLANES = (0x8000, 0xA000, 0xC000, 0xE000)


def load_map(path):
    """{символ: адрес} из карты sccz80."""
    syms = {}
    with open(path) as f:
        for line in f:
            m = re.match(r"^([A-Za-z_]\w*)\s*=\s*\$([0-9A-Fa-f]+)\s*;", line)
            if m:
                syms[m.group(1)] = int(m.group(2), 16)
    return syms


S = load_map(MAP)
if "_render_window" not in S:
    sys.exit("в mario.map нет _render_window — пересоберите ROM (make all)")


def sym(name):
    if name not in S:
        sys.exit(f"в mario.map нет символа {name} — пересоберите ROM")
    return S[name]


RENDER_WINDOW = sym("_render_window")
MARIO_DRAW = sym("_mario_draw")
MARIO_UNDRAW = sym("_mario_undraw")

# Разрешённые «низкие» записи: BSS (рабочие переменные) и стек. Запрет —
# всё, что ниже 0x0100 (вектора + startup): именно там был классический баг.
BSS = []
for kind in ("clib", "compiler", "data_compiler"):
    lo, hi = f"__bss_{kind}_head", f"__bss_{kind}_tail"
    if lo in S and hi in S:
        BSS.append((S[lo], S[hi]))
if not BSS:
    BSS.append((sym("__bss_clib_head"), sym("__bss_clib_tail")))
STACK_LO, STACK_HI = SP - 0x100, SP + 0x100


def outside_vram_ok(a):
    if STACK_LO <= a <= STACK_HI:
        return True
    return any(lo <= a < hi for lo, hi in BSS)

emu = Emulator8080()
emu.load_bytes(open(ROM, "rb").read(), 0x0100)
c = emu.cpu


# ---------------------------------------------------------------- вызовы ----
def clear_vram():
    c.mem[0x8000:0x10000] = bytes(0x8000)


def vram():
    return bytes(c.mem[0x8000:0x10000])


def render(cam, old_cam, blk0=0, nblk=VIEW_BLOCKS):
    """Вызов настоящего render_window; вернуть число записей в VRAM.

    Число инструкций кладётся в LAST_STEPS: эмулятор считает шаги, не такты,
    но от них тоже видно порядок скорости.
    """
    global LAST_STEPS
    c.reset_trace()
    # sccz80 пушит аргументы слева направо => в стеке обратный порядок.
    steps = emu.call(RENDER_WINDOW, args=(nblk, blk0, old_cam, cam), sp=SP,
                     max_steps=40_000_000)
    if c.pc != 0xFF00:
        sys.exit(f"render_window(cam={cam}, old={old_cam:#06x}, blk0={blk0}, "
                 f"nblk={nblk}) не вернулась: pc={c.pc:04X}")
    LAST_STEPS = steps
    return len(c.vram_trace)


LAST_STEPS = 0


def draw(x, y, spr):
    """Вызов настоящего mario_draw; вернуть список (адрес, значение) записей."""
    c.reset_trace()
    emu.call(MARIO_DRAW, args=(spr, y, x), sp=SP, max_steps=10_000_000)
    if c.pc != 0xFF00:
        sys.exit(f"mario_draw(x={x}, y={y}) не вернулась: pc={c.pc:04X}")
    return [(a, v) for (_s, _pc, a, _o, v) in c.write_trace]


def undraw():
    c.reset_trace()
    emu.call(MARIO_UNDRAW, args=(), sp=SP, max_steps=10_000_000)
    if c.pc != 0xFF00:
        sys.exit(f"mario_undraw не вернулась: pc={c.pc:04X}")
    return len(c.vram_trace)


def full_frame(cam, x, y, spr):
    """Эталон: чистый VRAM -> полный редрав -> спрайт."""
    clear_vram()
    render(cam, CAM_NO_REF)
    draw(x, y, spr)
    return vram()


# ------------------------------------------------------------ проверка ----
fails = []


def check(cond, msg):
    print(("  OK   " if cond else "  FAIL ") + msg)
    if not cond:
        fails.append(msg)


def merge_blocks(old_img, new_img, blocks):
    """Ожидаемый кадр после частичного редрава: блоки из new, прочее из old."""
    out = bytearray(old_img)
    for blk in blocks:
        for i, base in enumerate(PLANES):
            off = i * 0x2000 + blk * 256
            out[off:off + 256] = new_img[off:off + 256]
    return bytes(out)


def in_sprite_area(a, blk0, y):
    """Попадает ли запись под 16x16 спрайта в блоках blk0, blk0+1."""
    for i, base in enumerate(PLANES):
        if base <= a < base + 0x2000:
            blk = (a - base) // 256
            off = a & 0xFF
            top = 255 - y                     # байт верхней строки спрайта
            return (blk in (blk0, blk0 + 1) and top - 15 <= off <= top)
    return False


def model_frame(cam):
    """Независимая модель кадра: tilemap+tileset -> VRAM на Python."""
    data = open(ROM, "rb").read()
    ts, tm = data[sym("_tileset") - 0x0100:], data[sym("_tilemap") - 0x0100:]
    out = bytearray(0x8000)
    for blk in range(VIEW_BLOCKS):
        col = cam + blk
        for row in range(32):
            t = tm[col * 32 + row]
            for p, base in enumerate(PLANES):
                for j in range(8):
                    v = ts[t * 32 + p * 8 + j]
                    out[base - 0x8000 + blk * 256 + 255 - row * 8 - j] = v
    return bytes(out)


print(f"адреса: render_window={RENDER_WINDOW:04X} mario_draw={MARIO_DRAW:04X} "
      f"mario_undraw={MARIO_UNDRAW:04X}")

# --- 0. содержимое кадра против независимой модели (Python) ------------------
print("\n0. кадр совпадает с моделью на Python (не с самим собой)")
for cam in (0, 6, 24, 40):
    clear_vram()
    render(cam, CAM_NO_REF)
    check(vram() == model_frame(cam), f"cam={cam}: полный редрав == модель")
for cam in (7, 33):
    clear_vram()
    render(cam - 1, CAM_NO_REF)
    render(cam, cam - 1)
    check(vram() == model_frame(cam), f"cam={cam}: разность == модель")

# --- 1. первый экран ---------------------------------------------------------
print("\n1. первый экран и шаг скролла")
clear_vram()
first_writes = render(0, CAM_NO_REF)
check(first_writes < 4000, f"первый экран: {first_writes} записей "
                           f"(расчёт 3456, было 32768)")

K = 24
clear_vram()
render(0, CAM_NO_REF)
first_steps = LAST_STEPS
inc_right, inc_steps, inc_img = [], [], {}
for cam in range(1, K + 1):
    inc_right.append(render(cam, cam - 1))
    inc_steps.append(LAST_STEPS)
    inc_img[cam] = vram()
check(max(inc_right) < 6000,
      f"шаг вправо: записей/шаг мин {min(inc_right)}, "
      f"среднее {sum(inc_right)/len(inc_right):.0f}, макс {max(inc_right)} "
      f"(расчёт 2835)")
clear_vram()
render(K, CAM_NO_REF)
full_steps = LAST_STEPS
print(f"  инструкций: полный редрав {full_steps}, шаг скролла "
      f"в среднем {sum(inc_steps)/len(inc_steps):.0f}, "
      f"первый экран {first_steps}")

for cam in range(0, K + 1, 6):
    clear_vram()
    render(cam, CAM_NO_REF)
    ref = vram()
    got = ref if cam == 0 else inc_img[cam]
    label = ("первый кадр побайтово воспроизводим" if cam == 0
             else f"cam={cam}: разность == полный редрав")
    check(got == ref, label)

# влево
back, back_img = [], {}
for cam in range(K, K - 12, -1):
    back.append(render(cam - 1, cam))
    back_img[cam - 1] = vram()
check(sum(back) / len(back) < 6000,
      f"шаг влево: записей/шаг среднее {sum(back)/len(back):.0f}")
for cam in sorted(back_img):
    if cam % 6:
        continue
    clear_vram()
    render(cam, CAM_NO_REF)
    check(vram() == back_img[cam], f"cam={cam}: ход влево == полный редрав")

# --- 2. частичное окно -------------------------------------------------------
print("\n2. частичное окно (blk0, nblk)")
for old, cam, blk0, nblk in ((0, 1, 4, 4), (1, 2, 0, 8), (2, 3, 20, 12),
                             (5, 6, 31, 1)):
    clear_vram()
    render(old, CAM_NO_REF)
    old_img = vram()
    clear_vram()
    render(cam, CAM_NO_REF)
    new_img = vram()
    clear_vram()
    render(old, CAM_NO_REF)
    n = render(cam, old, blk0, nblk)
    want = merge_blocks(old_img, new_img, range(blk0, blk0 + nblk))
    check(vram() == want,
          f"кадры {old}->{cam}, окна блоков {blk0}..{blk0+nblk-1}: "
          f"тронуто ровно это окно (записей {n})")

# --- 3. спрайт: области и слепок --------------------------------------------
print("\n3. mario_draw / mario_undraw")
clear_vram()
render(5, CAM_NO_REF)
bg = vram()
for name, x, y in (("stand_r", 4 * 8, 208), ("jump_r", 12 * 8, 120),
                   ("duck_l", 16 * 8, 216), ("walk0_l", 30 * 8, 208)):
    spr = sym("_mario_" + name)
    writes = draw(x, y, spr)
    vram_writes = [(a, v) for a, v in writes if a >= 0x8000]
    low = [a for a, _ in writes if a < 0x0100]
    stray = [a for a, _ in writes if a < 0x8000 and not outside_vram_ok(a)]
    bad = [a for a, _ in vram_writes if not in_sprite_area(a, x // 8, y)]
    after = vram()
    touched = sum(1 for i in range(len(bg)) if after[i] != bg[i])
    check(not low, f"mario_{name} x={x} y={y}: никаких записов в нулевую страницу")
    check(not stray, f"mario_{name}: вне VRAM тронуты только BSS/стек"
                     f"{'' if not stray else ' -> ' + str([hex(a) for a in stray[:6]])}")
    check(not bad, f"mario_{name}: все {len(vram_writes)} VRAM-записей в пределах "
                   f"2x16 пикселей (слепок ещё {len(writes) - len(vram_writes)} в BSS)")
    check(touched > 0, f"mario_{name}: спрайт действительно что-то нарисовал "
                       f"({touched} байт)")
    n = undraw()
    check(vram() == bg, f"mario_{name}: undraw восстанавливает кадр побайтово "
                        f"(записей {n})")

# --- 4. сквозной прогон кадров в порядке main.c -----------------------------
print("\n4. кадры как в main.c: undraw -> diff -> draw")
STAND = sym("_mario_stand_r")
WALK0 = sym("_mario_walk0_r")
JUMP = sym("_mario_jump_r")

# сценарий: (cam, mblk, y, спрайт)
script = [(0, 4, 208, STAND)]
for i in range(1, 30):
    cam = min(i // 2, 12)
    mblk = min(4 + i - 2 * (i // 2), 20)
    y = 208 if i % 7 else 150
    spr = WALK0 if i % 3 else STAND
    script.append((cam, mblk, y, spr))

clear_vram()
render(script[0][0], CAM_NO_REF)
draw(script[0][1] * 8, script[0][2], script[0][3])
sampled = {}
for i in range(1, len(script)):
    cam, mblk, y, spr = script[i]
    pcam, pmblk, py, pspr = script[i - 1]
    undraw()
    if cam != pcam:
        if cam == pcam + 1 or pcam == cam + 1:
            render(cam, pcam)
        else:
            render(cam, CAM_NO_REF)
    draw(mblk * 8, y, spr)
    if i % 6 == 0:
        sampled[i] = vram()

bad_frames = []
for i, img in sampled.items():
    cam, mblk, y, spr = script[i]
    if full_frame(cam, mblk * 8, y, spr) != img:
        bad_frames.append(i)
check(not bad_frames,
      f"{len(sampled)} контрольных кадров из {len(script)}: инкрементальный "
      f"прогон == эталон{'' if not bad_frames else ' (расхождение на кадрах '
      + str(bad_frames) + ')'}")

print("\nИТОГ:", "FAIL" if fails else "PASS",
      f"({len(fails)} расхождений)")
sys.exit(1 if fails else 0)
