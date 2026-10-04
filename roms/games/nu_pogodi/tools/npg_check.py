#!/usr/bin/env python3
"""npg_check.py — функциональная проверка nu_pogodi.rom на v06c-mcp.

Смысл проверки: плоскость сегментов (вес 1, 0xE000) обязана в любой
«тихой» точке кадра быть ровно объединением тех битмапов, которые лежат в
слотах slot_blob[]. Это одновременно проверяет и блиттер (адресация,
порядок бит), и модель слотов (никаких висящих кусков после стирания), и
логику вывода.

    make -C roms/games/nu_pogodi consist KEEP_MAP=1   # ROM + карта с адресами
    python3 roms/games/nu_pogodi/tools/npg_check.py boot        # меню: PC, кадры, PNG
    python3 roms/games/nu_pogodi/tools/npg_check.py play [кадров]  # Ф1, потом N кадров с инвариантом
    python3 roms/games/nu_pogodi/tools/npg_check.py remap       # Ф3 и четыре назначения клавиш
    python3 roms/games/nu_pogodi/tools/npg_check.py keys        # матрица клавиатуры

Скриншоты — .scratch/shots/npg_*.png (серое поле = вес пикселя по плоскостям).
"""
import json
import os
import sys
import time


def find_root(start):
    """Корень репозитория — предок, в котором лежит lib/v06.h."""
    d = start
    while True:
        if os.path.isfile(os.path.join(d, "lib", "v06.h")):
            return d
        up = os.path.dirname(d)
        if up == d:
            raise SystemExit("не найден корень проекта от " + start)
        d = up


ROOT = find_root(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "utils"))
from analyze.mcp_session import McpSession, bytes_of, to_addr  # noqa: E402
SERVER = json.load(open(os.path.join(ROOT, ".qoder/mcp.json")))["mcpServers"]["vector-debugger"]["command"]
ROM = os.path.join(ROOT, "roms/games/nu_pogodi/nu_pogodi.rom")
MAPFILE = os.path.join(ROOT, "roms/games/nu_pogodi/nu_pogodi.map")

INK = 0xE000          # плоскость сегментов
SLOTS = 32


def symbols():
    out = {}
    for line in open(MAPFILE):
        name, _, rest = line.partition("=")
        body = rest.split(";")
        if len(body) < 2:
            continue
        val = body[0].strip()
        if val.startswith("$"):
            out[name.strip()] = int(val[1:], 16)
    return out


def session():
    s = McpSession(server=SERVER, timeout=90.0)
    s.start()
    s.load_rom(ROM, org=0x0100)
    return s


def rd(s, addr, n):
    return bytes_of(s.call("debug_read_memory_range", address=addr, length=n))


def u16(b, off=0):
    return b[off] | (b[off + 1] << 8)


class Rom:
    """Blob-данные берём из файла ROM (он статичен), адрес = org + смещение."""

    def __init__(self, s, sym):
        self.org = 0x0100
        self.data = open(ROM, "rb").read()
        self.cache = {}

    def blob(self, addr):
        if addr in self.cache:
            return self.cache[addr]
        h = self.read(addr, 4)
        x0, y0, wb, hgt = h[0], h[1], h[2], h[3]
        px = self.read(addr + 4, wb * hgt)
        b = (x0, y0, wb, hgt, px)
        self.cache[addr] = b
        return b

    def read(self, addr, n):
        return self.data[addr - self.org:addr - self.org + n]


def paint(plane, blob):
    """Наложить битмап на плоскость (bytearray из 8192 байт, индекс = блок*256+(255-y))."""
    x0, y0, wb, hgt, px = blob
    blk = x0 >> 3
    if (blk + wb > 32) or y0 + hgt > 256:
        raise ValueError("сегмент за экраном: x0=%d y0=%d wb=%d h=%d" %
                         (x0, y0, wb, hgt))
    for c in range(wb):
        base = (blk + c) * 256 + (255 - y0)
        for r in range(hgt):
            plane[base - r] |= px[c * hgt + r]


def expected(rm, slots):
    plane = bytearray(8192)
    for i, ptr in enumerate(slots):
        if ptr:
            try:
                paint(plane, rm.blob(ptr))
            except ValueError as e:
                raise ValueError("слот %d (ptr=%04X): %s" % (i, ptr, e)) from e
    return plane


def state(s, sym):
    m = rd(s, sym["_state"], 0x40)          # state..wolf? читаем блок переменных целиком
    return m


def snapshot(s, sym, rm):
    slots = []
    b = rd(s, sym["_slot_blob"], SLOTS * 2)
    for i in range(SLOTS):
        slots.append(u16(b, i * 2))
    ink = rd(s, INK, 8192)
    g = {
        "state": rd(s, sym["_state"], 1)[0],
        "wolf": rd(s, sym["_wolf_position"], 1)[0],
        "life": rd(s, sym["_life_count"], 1)[0],
        "score": u16(rd(s, sym["_score"], 2)),
        "rabbit": rd(s, sym["_rabbit_visible"], 1)[0],
        "needed": rd(s, sym["_eggs_needed"], 1)[0],
        "cursor": rd(s, sym["_groove_cursor"], 1)[0],
        "frames": u16(rd(s, sym["_frame_count"], 2)),
        "grooves": list(rd(s, sym["_groove"], 20)),
        "slots": slots,
        "ink": ink,
    }
    return g


def diff(exp, ink):
    """Список расхождений: (адрес плоскости, ожидалось, стало)."""
    out = []
    for i in range(8192):
        e, a = exp[i], ink[i]
        if e != a:
            out.append((i, e, a))
    return out


def where(i):
    blk, off = divmod(i, 256)
    return "x=%d y=%d" % (blk * 8, 255 - off)


def png(name, planes):
    """planes: dict вес -> 8192 байт. Рендер 256x256 в grayscale по индексу палитры."""
    try:
        from PIL import Image
    except ImportError:
        print("PIL нет — PNG не сохранить")
        return None
    px = bytearray(256 * 256)
    for y in range(256):
        for blk in range(32):
            i = blk * 256 + (255 - y)
            for b in range(8):
                x = blk * 8 + (7 - b)     # MSB — левый пиксель
                idx = 0
                for w, plane in planes.items():
                    if plane[i] >> b & 1:
                        idx |= w
                px[y * 256 + x] = idx * 17
    img = Image.frombytes("L", (256, 256), bytes(px))
    img = img.resize((512, 512), Image.NEAREST)
    path = os.path.join(ROOT, ".scratch/shots", "npg_%s.png" % name)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    img.save(path)
    return path


BP = None            # адрес точки останова (начало input() — кадр уже отрисован)


def wait_bp(s, limit=5.0):
    """Ждём остановки на breakpoint. True — упёрлись, False — таймаут."""
    t0 = time.time()
    while time.time() - t0 < limit:
        if not s.call("debug_is_running")["running"]:
            return s.call("debug_get_cpu_state")["pc"]
        time.sleep(0.002)
    return None


# Клавиша эмулятора для пары (строка матрицы, бит колонки). ↖ — это F7,
# СТР — F8 (см. vendor/v06c-emu/src/keyboard.h: 0x101 и 0x102).
EMU_KEY = {(0, 0x01): "TAB", (0, 0x02): "PS", (0, 0x04): "ENTER",
           (0, 0x08): "BACKSPACE", (0, 0x10): "LEFT", (0, 0x20): "UP",
           (0, 0x40): "RIGHT", (0, 0x80): "DOWN",
           (1, 0x01): "F7", (1, 0x02): "F8", (1, 0x04): "ESCAPE",
           (1, 0x08): "F1", (1, 0x10): "F2", (1, 0x20): "F3",
           (1, 0x40): "F4", (1, 0x80): "F5"}


# Строки 2..7 матрицы — печатные символы. Копия key_chars из main.c.
MAT_CHARS = ("01234567" "89:;,.=/" "@ABCDEFG" "HIJKLMNO" "PQRSTUVW" "XYZ[\\]~ ")
# Глифов этих символов в font8x8 нет, игра подписывает их словами.
assert len(MAT_CHARS) == 48, len(MAT_CHARS)
MAT_NAME = {"/": "SLASH", "\\": "KOSA", "~": "TILDE", " ": "SPC"}


def pos_name(row, bit):
    """Название клавиши по (строка матрицы, бит колонки)."""
    if row < 2:
        return EMU_KEY[(row, bit)]
    c = MAT_CHARS[(row - 2) * 8 + bit.bit_length() - 1]
    return MAT_NAME.get(c, c)


def pos_keys(g):
    """Имена клавиш по текущему назначению (после переназначения — новые)."""
    return [pos_name(r, b) for r, b in zip(g["key_row"], g["key_bit"])]


def play(s, sym, rm, frames, autostart=True):
    global BP
    BP = sym["_input"]
    s.call("debug_set_breakpoint", address=BP)
    s.call("debug_run")
    if wait_bp(s) is None:
        print("точка останова не сработала")
        return
    if autostart:
        # Пока CPU стоит, эмулятор не сканирует клавиатуру: нажатие видно
        # только тому input(), который выполнится после debug_run. Поэтому
        # отпускаем Ф1 лишь через кадр после нажатия.
        s.call("debug_press_key", key="F1")
        s.call("debug_run")
        wait_bp(s)
        s.call("debug_release_key", key="F1")

    held = None
    base = None
    bad = 0
    last_seen = None
    catches = []
    states = {}
    for i in range(frames):
        blob, base = read_vars(s, sym)
        ink = rd(s, INK, 8192)
        g = decode(blob, base, sym)
        keys = pos_keys(g)
        exp = expected(rm, g["slots"])
        d = diff(exp, ink)
        if d:
            bad += 1
            if bad <= 3:
                for j, e, a in d[:6]:
                    print("  КАДР %d: %s exp=%02X got=%02X" % (i, where(j), e, a))
        states[g["state"]] = states.get(g["state"], 0) + 1
        if g["state"] == 0 and i > 4:
            print("  КАДР %d: игра упала в меню (life=%d score=%d)" % (i, g["life"], g["score"]))
        if base is None:
            base = g["score"]
        elif g["score"] != last_seen:
            catches.append((i, g["score"], g["life"]))
        last_seen = g["score"]

        # автоигрок: куда сейчас падает яйцо с края — туда и ставим волка
        want = None
        for p in range(4):
            if g["grooves"][p * 5 + 4]:
                want = p
                break
        if want is None:
            for p in range(4):
                if g["grooves"][p * 5 + 3]:
                    want = p
                    break
        if want is not None and want != held:
            if held is not None:
                s.call("debug_release_key", key=keys[held])
            s.call("debug_press_key", key=keys[want])
            held = want

        if i % 60 == 0:
            print("  кадр %3d: state=%d score=%d life=%d wolf=%d needed=%d speed16=%d"
                  % (i, g["state"], g["score"], g["life"], g["wolf"], g["needed"], g["speed16"]))

        s.call("debug_run")
        if wait_bp(s) is None:
            print("остановка не пришла на кадре %d" % i)
            break

    if held is not None:
        s.call("debug_release_key", key=pos_keys(g)[held])
    print("кадров %d, расхождений плоскости %d, состояния %s" % (frames, bad, states))
    print("ловля (кадр, счёт, жизни): %s" % (catches[-14:],))
    g = decode(*read_vars(s, sym), sym)
    print("итог: score=%d life=%d wolf=%d needed=%d cursor=%d"
          % (g["score"], g["life"], g["wolf"], g["needed"], g["cursor"]))
    return g, bad, catches


def decode(blob, base, sym):
    """Разбор снимка RAM из блока переменных main.c (base = начало .data)."""
    def u8(name):
        return blob[sym[name] - base]

    def u16v(name):
        return u16(blob, sym[name] - base)

    slots = [u16(blob, sym["_slot_blob"] - base + i * 2) for i in range(SLOTS)]
    return {
        "slots": slots,
        "state": u8("_state"),
        "game_type": u8("_game_type"),
        "wolf": u8("_wolf_position"),
        "grooves": list(blob[sym["_groove"] - base:sym["_groove"] - base + 20]),
        "new_egg": list(blob[sym["_new_egg"] - base:sym["_new_egg"] - base + 4]),
        "needed": u8("_eggs_needed"),
        "cursor": u8("_groove_cursor"),
        "prev_new": u8("_previous_new_egg"),
        "life": u8("_life_count"),
        "score": u16v("_score"),
        "rounds": u16v("_rounds"),
        "speed16": u16v("_speed16"),
        "game_timer": u16v("_game_timer"),
        "factor5": u8("_factor5"),
        "remap": u8("_remap"),
        # key_row/key_bit — инициализированные данные, они ниже _slot_blob
        "key_row": list(blob[sym["_key_row"] - base:sym["_key_row"] - base + 4]),
        "key_bit": list(blob[sym["_key_bit"] - base:sym["_key_bit"] - base + 4]),
    }


def read_vars(s, sym):
    """Снимок блока переменных main.c: данные + bss. (blob, base)."""
    base = sym["__data_compiler_head"]
    n = sym["__bss_compiler_tail"] - base
    return rd(s, base, n), base


def dump(s, sym, rm, frames):
    """Постатейный слепок жёлобов: видно, как яйцо идёт к краю."""
    s.call("debug_set_breakpoint", address=sym["_input"])
    s.call("debug_run")
    if wait_bp(s) is None:
        print("точка останова не сработала")
        return
    s.call("debug_press_key", key="F1")
    s.call("debug_run")
    wait_bp(s)
    s.call("debug_release_key", key="F1")
    names = ["LU", "LD", "RU", "RD"]      # по номерам POS_LU/POS_LD/POS_RU/POS_RD
    for i in range(frames):
        g = decode(*read_vars(s, sym), sym)
        grid = " ".join("%s[%d%d%d%d%d]" % (names[p], *g["grooves"][p * 5:p * 5 + 5])
                        for p in range(4))
        print("%3d cur=%d new=%s on=%d score=%d life=%d wolf=%s | %s"
              % (i, g["cursor"], g["new_egg"], sum(g["grooves"]),
                 g["score"], g["life"], names[g["wolf"]], grid))
        s.call("debug_run")
        if wait_bp(s) is None:
            print("остановка не пришла на кадре %d" % i)
            break


def main():
    what = sys.argv[1] if len(sys.argv) > 1 else "boot"
    s = session()
    sym = symbols()

    if what == "keys":
        print(json.dumps(s.call("debug_list_keys"), indent=1))
        return

    rm = Rom(s, sym)

    if what == "dump":
        n = int(sys.argv[2]) if len(sys.argv) > 2 else 100
        s.call("debug_run")
        time.sleep(0.3)
        s.call("debug_pause")
        dump(s, sym, rm, n)
        s.call("debug_pause")
        s.close()
        return

    if what == "play":
        n = int(sys.argv[2]) if len(sys.argv) > 2 else 300
        s.call("debug_run")
        time.sleep(0.3)
        s.call("debug_pause")
        play(s, sym, rm, n)
        g = decode(*read_vars(s, sym), sym)
        planes = {8: rd(s, 0x8000, 8192), 4: rd(s, 0xA000, 8192),
                  2: rd(s, 0xC000, 8192), 1: rd(s, INK, 8192)}
        print("PNG:", png("play", planes))
        s.call("debug_pause")
        s.close()
        return

    if what == "remap":
        # включение -> четыре назначения -> отмена кнопками -> назначаем ещё
        # раз -> столкновение (F8 уже занят) -> отмена
        seq = ["F3", "A", "S", "D", "F",
               "F3", "Q", "W", "E", "R",
               "F3", "F8", "F3"]
        s.call("debug_set_breakpoint", address=sym["_input"])
        s.call("debug_run")
        if wait_bp(s) is None:
            print("точка останова не сработала")
            return
        for key in seq:
            s.call("debug_press_key", key=key)
            s.call("debug_run")
            wait_bp(s)
            s.call("debug_release_key", key=key)
            s.call("debug_run")
            wait_bp(s)
            g = decode(*read_vars(s, sym), sym)
            print("%-4s remap=%d keys=%s state=%d" %
                  (key, g["remap"], pos_keys(g), g["state"]))
        planes = {8: rd(s, 0x8000, 8192), 4: rd(s, 0xA000, 8192),
                  2: rd(s, 0xC000, 8192), 1: rd(s, INK, 8192)}
        print("PNG:", png("remap", planes))
        s.call("debug_pause")
        s.close()
        return

    print("run ->", s.call("debug_run"))
    # Первый to_menu() распаковывает 24 КБ фона — это ~55 кадров (1,1 с),
    # поэтому короткий sleep ловит экран посреди распаковки.
    time.sleep(2.5)
    s.call("debug_pause")
    st = s.call("debug_get_state")
    print("pc:", st["cpu"]["pc"], "sp:", st["cpu"]["sp"], "iff:", st["cpu"]["iff"])
    g = snapshot(s, sym, rm)
    print("menu: state=%d wolf=%d life=%d score=%d frames=%d slots=%s"
          % (g["state"], g["wolf"], g["life"], g["score"], g["frames"],
             " ".join("%04X" % p if p else "----" for p in g["slots"])))
    exp = expected(rm, g["slots"])
    d = diff(exp, g["ink"])
    print("инвариант плоскости: %d расхождений" % len(d))
    for i, e, a in d[:10]:
        print("   %s exp=%02X got=%02X" % (where(i), e, a))
    print("PNG:", png("menu", {8: rd(s, 0x8000, 8192), 4: rd(s, 0xA000, 8192),
                               2: rd(s, 0xC000, 8192), 1: g["ink"]}))
    s.close()


if __name__ == "__main__":
    main()
