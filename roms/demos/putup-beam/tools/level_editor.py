#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Редактор карты демо putup-beam — окно Tkinter, правит level.inc.

Карта 16x32 клетки (256x512 px), код клетки = индекс bg_tiles[] из assets.inc
(см. tools/gen_assets.py) и одновременно код логики в main.c. Метаданные в том
же файле: спавн героя, выход, спавны/виды врагов. Превью рисуется настоящими
тайлами putup (gen_assets.editor_gfx: глифы + data_palette), поэтому карта в
окне выглядит ровно так, как её напечатает ROM.

Запуск:
    python3 tools/level_editor.py             # окно редактора
    python3 tools/level_editor.py --print     # ASCII-превью карты
    python3 tools/level_editor.py --check     # гейты (достижимость, спавны)

Нужны Tkinter и Pillow (биндинг Tk для Pillow — отдельный пакет):
    sudo apt install python3-tk python3-pil python3-pil.imagetk

Окно:
  * слева — палитра тайлов (клик = кисть) и маркеры (герой, выход, враги);
  * в центре — карта: ЛКМ рисует выбранным инструментом (протяжка — линия),
    ПКМ берёт код клетки под курсором в кисть, колесо — прокрутка;
  * справа — гейты и сводка (предметы, спавны, список кодов);
  * сверху — тулбар: сетка, твёрдость, невидимые клетки, спавны,
    масштаб, сохранить, проверить.

Невидимые в игре клетки 03h (невидимый блокиратор) и 05h (скрытый кирпич)
в ROM выглядят как пустота/обычный кирпич — глифы совпадают, — поэтому на
карте они накрыты серым квадратом с прозрачностью 25% (галочка «невидимые
03/05»). Механика в игре: нажатие сверху на 05h -> кубик «?» (04h), нажатие
на 04h -> случайный фрукт.

Клавиши: стрелки — курсор, Tab — следующая кисть, пробел — поставить,
H — спавн героя, E — выход, 1/2/3 — спавн врага, V — вид врага под курсором,
Del — стереть клетку (код 1), Ctrl+Z/Ctrl+Y — отмена/повтор,
Ctrl+S — сохранить, Ctrl+Q — выход, Esc — обычная кисть.

Гейты перед записью (level.check): герой не в твёрдой клетке, выход/предметы/
спавны достижимы flood-fill'ом от героя, виды врагов 0..2, все коды клеток
имеют графику в assets.inc. При ошибке файл не пишется.
"""
from __future__ import annotations

import argparse
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DEMO = os.path.dirname(HERE)
OUT_INC = os.path.join(DEMO, "level.inc")
sys.path.insert(0, HERE)

try:
    import gen_assets as G                    # noqa: E402  (графика для превью)
except Exception as exc:                      # pragma: no cover
    sys.exit("не загрузился tools/gen_assets.py: %s" % exc)

try:
    import tkinter as tk
    from tkinter import ttk, messagebox
except ImportError:                           # --print/--check работают и без Tk
    tk = None

try:
    from PIL import Image, ImageTk
except ImportError:                           # --print/--check работают и без PIL
    Image = ImageTk = None

# (код, символ ASCII-превью, подпись). Порядок = порядок кистей по Tab.
PALETTE = [
    (1,  ".", "пусто/проходимо"),
    (2,  "#", "кирпич (твёрдый)"),
    (5,  "%", "скрытый кирпич → «?» (твёрдый)"),
    (8,  "=", "стена с дырой (твёрдая)"),
    (4,  "?", "кубик «?» → фрукт (твёрдый)"),
    (3,  ",", "невидимый блокиратор"),
    (7,  "o", "яйцо-бонус"),
    (10, "k", "вишни"),
    (11, "K", "яблоко"),
    (12, "p", "ананас"),
    (13, "g", "виноград"),
    (14, "r", "кольцо (+1 жизнь)"),
    (0,  " ", "пустой тайл 0"),
    (24, "X", "замок/выход (твёрд до открытия)"),
]
CHAR2CODE = {ch: code for code, ch, _ in PALETTE if ch != " "}
CODE2CHAR = {code: ch for code, ch, _ in PALETTE}
TILE_NAME = {code: name for code, _ch, name in PALETTE}

SOLID = {2, 4, 5, 8}                 # твёрдое для героя (и врагов тоже)
ITEMS = {7, 10, 11, 12, 13, 14}      # предметы (KEY_CODE в main.c)
# Клетки, невидимые на экране (глифы тайлов визуально не отличаются от
# пустоты/кирпича), но важные для игры: 03h — невидимый блокиратор,
# 05h — скрытый кирпич. В редакторе помечаются серым квадратом 25%.
FAINT_CODES = {3, 5}
EXIT_CODE = 24                       # замок; при открытии -> 22/23
EXIT_PHASES = (22, 23)               # светлая/тёмная фазы открытого выхода
ENEMY_KIND_NAMES = ("ходок", "ворона", "вертолёт")
EMPTY_CODE = 1                       # «стереть» = проходимая пустая клетка

MAP_RE = re.compile(r"level_map\s*\[\s*\d+\s*\]\s*=\s*\{(.*?)\}\s*;", re.S)
ROWS_RE = re.compile(r"#define\s+LEVEL_ROWS\s+(\d+)")
COLS_RE = re.compile(r"#define\s+LEVEL_COLS\s+(\d+)")
INT_RE = re.compile(r"0[xX][0-9A-Fa-f]+|\d+")


def _ints(text):
    return [int(t, 0) for t in INT_RE.findall(text)]


class Level:
    """Карта + метаданные level.inc."""

    def __init__(self, rows=32, cols=16):
        self.rows, self.cols = rows, cols
        self.map = [[1] * cols for _ in range(rows)]
        self.hero = [1, 8]
        self.exit = [rows - 2, cols // 2]
        self.enemies = [[rows - 18, 5], [rows - 7, 5], [9, 5]]
        self.kinds = [0, 1, 2]
        self.header = []

    # ---------- чтение/запись ----------

    @classmethod
    def load(cls, path=OUT_INC):
        txt = open(path, encoding="utf-8").read()
        m_rows, m_cols = ROWS_RE.search(txt), COLS_RE.search(txt)
        lv = cls(int(m_rows.group(1)) if m_rows else 32,
                 int(m_cols.group(1)) if m_cols else 16)
        m = MAP_RE.search(txt)
        if not m:
            raise SystemExit("%s: не найден массив level_map[]" % path)
        vals = _ints(m.group(1))
        if len(vals) != lv.rows * lv.cols:
            raise SystemExit("%s: level_map: %d значений, ожидалось %d"
                             % (path, len(vals), lv.rows * lv.cols))
        lv.map = [vals[r * lv.cols:(r + 1) * lv.cols] for r in range(lv.rows)]

        def named(name, count):
            mm = re.search(name + r"\s*(\[[^=]*\])?\s*=\s*\{(.*?)\}\s*;", txt, re.S)
            if not mm:
                raise SystemExit("%s: не найден %s" % (path, name))
            v = _ints(mm.group(2))
            if len(v) != count:
                raise SystemExit("%s: %s: %d значений, ожидалось %d"
                                 % (path, name, len(v), count))
            return v

        lv.hero = named("level_hero_spawn", 2)
        lv.exit = named("level_exit", 2)
        en = named("level_enemy_spawns", 6)
        lv.enemies = [[en[2 * i], en[2 * i + 1]] for i in range(3)]
        lv.kinds = named("level_enemy_kinds", 3)
        head = txt.split("#ifndef LEVEL_INC")[0]
        lv.header = [ln for ln in head.splitlines() if ln.strip()]
        return lv

    def render(self):
        head = self.header or [
            "/* level.inc — карта демо putup-beam (правится tools/level_editor.py).",
            " * Карта 16x32 клетки; коды = индексы bg_tiles[] из assets.inc,",
            " * 24 = замок (твёрд до открытия, при открытии -> выход 22/23). */",
        ]
        out = list(head)
        out += ["#ifndef LEVEL_INC",
                "#define LEVEL_INC",
                "",
                "#define LEVEL_ROWS %d" % self.rows,
                "#define LEVEL_COLS %d" % self.cols,
                "",
                "static const unsigned char level_map[%d] = {"
                % (self.rows * self.cols)]
        for r in range(self.rows):
            out.append("    " + ", ".join("%2d" % v for v in self.map[r]) + ",")
        out += ["};",
                "",
                "/* (row, col) */",
                "static const unsigned char level_hero_spawn[2] = { %d, %d };"
                % tuple(self.hero),
                "static const unsigned char level_exit[2] = { %d, %d };"
                % tuple(self.exit),
                "static const unsigned char level_enemy_spawns[3][2] = {",
                "    { %d, %d }, { %d, %d }, { %d, %d }," % tuple(
                    [c for e in self.enemies for c in e]),
                "};",
                "/* вид врага: 0 ходок, 1 ворона, 2 вертолёт (enemy_frames) */",
                "static const unsigned char level_enemy_kinds[3] = { %d, %d, %d };"
                % tuple(self.kinds),
                "",
                "#endif /* LEVEL_INC */"]
        return "\n".join(out) + "\n"

    def save(self, path=OUT_INC):
        with open(path, "w", encoding="utf-8") as f:
            f.write(self.render())

    # ---------- гейты ----------

    def solid(self, r, c):
        if not (0 <= r < self.rows and 0 <= c < self.cols):
            return True
        return self.map[r][c] in SOLID

    def reach(self, start=None):
        start = tuple(start or self.hero)
        seen, stack = {start}, [start]
        while stack:
            r, c = stack.pop()
            for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nr, nc = r + dr, c + dc
                if not (0 <= nr < self.rows and 0 <= nc < self.cols):
                    continue
                if (nr, nc) in seen or self.map[nr][nc] in SOLID:
                    continue
                seen.add((nr, nc))
                stack.append((nr, nc))
        return seen

    def items(self):
        return [(r, c) for r in range(self.rows) for c in range(self.cols)
                if self.map[r][c] in ITEMS]

    def check(self, known=None):
        """-> (ошибки, предупреждения, достижимые клетки).

        known — коды, для которых assets.inc печатает графику (bg_tiles[N] !=
        bg_tile_000): код вне набора отрисуется пустым тайлом, это ошибка.
        """
        errs, warns = [], []
        reach = self.reach()
        hr, hc = self.hero
        if self.solid(hr, hc):
            errs.append("спавн героя (%d,%d) в твёрдой клетке" % (hr, hc))
        er, ec = self.exit
        nb = [(er + dr, ec + dc) for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1))]
        if not any(n in reach for n in nb):
            errs.append("выход (%d,%d) недостижим" % (er, ec))
        if not (0 <= er < self.rows and 0 <= ec < self.cols):
            errs.append("выход (%d,%d) вне карты" % (er, ec))
        for it in self.items():
            if it not in reach:
                errs.append("предмет %s недостижим" % (it,))
        for i, (r, c) in enumerate(self.enemies):
            if self.solid(r, c):
                errs.append("спавн врага %d (%d,%d) в твёрдой клетке" % (i + 1, r, c))
            elif (r, c) not in reach:
                errs.append("спавн врага %d (%d,%d) недостижим" % (i + 1, r, c))
            if self.kinds[i] not in (0, 1, 2):
                errs.append("вид врага %d = %d (нет такого)" % (i + 1, self.kinds[i]))
        if known is not None:
            for r in range(self.rows):
                for c in range(self.cols):
                    if self.map[r][c] not in known:
                        errs.append("код %02Xh в (%d,%d): нет графики в assets.inc"
                                    % (self.map[r][c], r, c))
        if not self.items():
            warns.append("на карте нет ни одного предмета — выход откроется сразу")
        return errs, warns, reach

    # ---------- текст ----------

    def ascii(self):
        lines = []
        for r in range(self.rows):
            row = ""
            for c in range(self.cols):
                if [r, c] == self.hero:
                    row += "H"
                elif [r, c] == self.exit:
                    row += "X"
                elif [r, c] in self.enemies:
                    row += str(self.enemies.index([r, c]) + 1)
                else:
                    row += CODE2CHAR.get(self.map[r][c], "?")
            lines.append("%2d %s" % (r, row))
        lines.append("   " + "".join(str(c % 10) for c in range(self.cols)))
        lines.append("легенда: " + ", ".join(
            "%s=%02Xh %s" % (ch, code, name) for code, ch, name in PALETTE))
        return "\n".join(lines)


class Editor:
    """Состояние редактора, отделённое от Tk (тестируется без экрана).

    Инструмент — строка: "tile:<код>", "hero", "exit", "enemy:<0..2>".
    Карта правится apply(); каждое изменение обёрнуто точкой отмены.
    """

    UNDO_MAX = 200

    def __init__(self, lv, path=OUT_INC):
        self.lv, self.path = lv, path
        self.cur = [lv.hero[0], lv.hero[1]]
        self.brush = 0
        self.tool = "tile:%d" % PALETTE[0][0]
        self.dirty = False
        self.msg = ""
        self.known = None            # коды с графикой (ставит окно)
        self._undo, self._redo = [], []

    # ---------- отмена/повтор ----------

    def _snapshot(self):
        lv = self.lv
        return ([list(row) for row in lv.map], list(lv.hero), list(lv.exit),
                [list(e) for e in lv.enemies], list(lv.kinds))

    def _restore(self, snap):
        m, hero, exit_, enemies, kinds = snap
        self.lv.map = [list(r) for r in m]
        self.lv.hero = list(hero)
        self.lv.exit = list(exit_)
        self.lv.enemies = [list(e) for e in enemies]
        self.lv.kinds = list(kinds)

    def push_undo(self):
        self._undo.append(self._snapshot())
        del self._undo[:-self.UNDO_MAX]
        self._redo.clear()

    def undo(self):
        if not self._undo:
            self.msg = "отменять нечего"
            return False
        self._redo.append(self._snapshot())
        self._restore(self._undo.pop())
        self.dirty = True
        self.msg = "отменено"
        return True

    def redo(self):
        if not self._redo:
            self.msg = "возвращать нечего"
            return False
        self._undo.append(self._snapshot())
        self._restore(self._redo.pop())
        self.dirty = True
        self.msg = "возвращено"
        return True

    # ---------- курсор/инструмент ----------

    def _clamp(self):
        self.cur[0] = max(0, min(self.lv.rows - 1, self.cur[0]))
        self.cur[1] = max(0, min(self.lv.cols - 1, self.cur[1]))

    def move(self, dr, dc):
        self.cur[0] += dr
        self.cur[1] += dc
        self._clamp()

    def set_cur(self, r, c):
        self.cur = [r, c]
        self._clamp()

    def set_tool(self, tool):
        if tool.startswith("tile:"):
            code = int(tool.split(":")[1])
            for i, (c, _ch, _n) in enumerate(PALETTE):
                if c == code:
                    self.brush = i
                    break
        self.tool = tool

    def next_brush(self, step=1):
        self.brush = (self.brush + step) % len(PALETTE)
        self.set_tool("tile:%d" % PALETTE[self.brush][0])
        self.msg = "кисть: %s (%02Xh) %s" % (PALETTE[self.brush][1],
                                            PALETTE[self.brush][0],
                                            PALETTE[self.brush][2])

    # ---------- правка ----------

    def apply(self, push=True):
        """Применить инструмент в курсоре. -> True, если карта изменилась."""
        if push:
            self.push_undo()
        lv = self.lv
        r, c = self.cur
        tool = self.tool
        before = self._snapshot()
        if tool.startswith("tile:"):
            code = int(tool.split(":")[1])
            if lv.map[r][c] != code:
                lv.map[r][c] = code
                self.dirty = True
            self.msg = "(%d,%d) = %02Xh %s" % (r, c, code,
                                              TILE_NAME.get(code, ""))
        elif tool == "hero":
            lv.hero = [r, c]
            self.dirty = True
            self.msg = "спавн героя: (%d,%d)" % (r, c)
        elif tool == "exit":
            lv.exit = [r, c]
            lv.map[r][c] = EXIT_CODE
            self.dirty = True
            self.msg = "выход: (%d,%d)" % (r, c)
        elif tool.startswith("enemy:"):
            i = int(tool.split(":")[1])
            lv.enemies[i] = [r, c]
            self.dirty = True
            self.msg = "враг %d (%s): (%d,%d)" % (
                i + 1, ENEMY_KIND_NAMES[lv.kinds[i]], r, c)
        changed = before != self._snapshot()
        if push and not changed:
            self._undo.pop()             # нажатие без изменений — не мусорим
        return changed

    def pick(self):
        """Пипетка: код клетки под курсором -> кисть (и в отмену не пишем)."""
        code = self.lv.map[self.cur[0]][self.cur[1]]
        self.set_tool("tile:%d" % code)
        self.msg = "кисть: %02Xh %s" % (code, TILE_NAME.get(code, "нет в палитре"))
        return code

    def set_kind(self, i, kind):
        self.push_undo()
        self.lv.kinds[i] = kind % len(ENEMY_KIND_NAMES)
        self.dirty = True
        self.msg = "враг %d: вид %s" % (i + 1, ENEMY_KIND_NAMES[self.lv.kinds[i]])

    def cycle_kind(self):
        """V: сменить вид врага, чей спавн стоит под курсором."""
        for i, e in enumerate(self.lv.enemies):
            if e == list(self.cur):
                self.set_kind(i, self.lv.kinds[i] + 1)
                return i
        self.msg = "под курсором нет спавна врага"
        return None

    def do_save(self):
        errs, warns, _ = self.lv.check(known=self.known)
        if warns:
            self.msg = "предупреждение: " + warns[0]
        if errs:
            self.msg = "НЕ сохранено: " + errs[0]
            return False
        self.lv.save(self.path)
        self.dirty = False
        self.msg = "сохранено: %s" % os.path.basename(self.path)
        return True

    # ---------- клавиши (модель; окно зовёт то же самое) ----------

    def key(self, k):
        """k — 'up'/'down'/'left'/'right'/'tab'/'enter'/'esc' или символ."""
        if k == "up":
            self.move(-1, 0)
        elif k == "down":
            self.move(1, 0)
        elif k == "left":
            self.move(0, -1)
        elif k == "right":
            self.move(0, 1)
        elif k == "tab":
            self.next_brush()
        elif k in ("enter", "space"):
            self.apply()
        elif k in ("s", "F2"):
            self.do_save()
        elif k == "esc":
            self.set_tool("tile:%d" % EMPTY_CODE)
            self.msg = "обычная кисть"
        elif k in ("h", "H"):
            self.set_tool("hero")
            self.apply()
        elif k in ("e", "E"):
            self.set_tool("exit")
            self.apply()
        elif k in ("1", "2", "3"):
            self.set_tool("enemy:%d" % (int(k) - 1))
            self.apply()
        elif k in ("v", "V"):
            self.cycle_kind()
        elif k in ("u", "U"):
            self.undo()
        elif k in CHAR2CODE:
            self.apply_code(CHAR2CODE[k])
        return self.dirty

    def apply_code(self, code):
        """Поставить конкретный код кистью (в тестах и по буквам палитры)."""
        self.push_undo()
        r, c = self.cur
        if self.lv.map[r][c] != code:
            self.lv.map[r][c] = code
            self.dirty = True
        self.set_tool("tile:%d" % code)
        self.msg = "(%d,%d) = %02Xh %s" % (r, c, code, TILE_NAME.get(code, ""))


# ---------- графика: cols (формат gen_assets) -> PIL ----------

def cols_image(cols, palette, alpha0=False):
    """cols[pi] = (left8, right8) сверху вниз -> PIL RGBA 16x16.

    Бит 7 байта — левый пиксель (как в VRAM); индекс палитры собирается из
    плоскостей: pi=0 — П3 (0x8000) ... pi=3 — П0 (0xE000), бит индекса 8>>pi.
    alpha0 — пиксели индекса 0 прозрачны (маска героя и врагов).
    """
    rgb = [((b & 7) * 255 // 7, ((b >> 3) & 7) * 255 // 7,
            ((b >> 6) & 3) * 255 // 3) for b in palette]
    img = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
    px = img.load()
    for y in range(16):
        for x in range(16):
            xb, m = x >> 3, 0x80 >> (x & 7)
            idx = 0
            for pi in range(4):
                if cols[pi][xb][y] & m:
                    idx |= 8 >> pi
            r, g, b = rgb[idx]
            px[x, y] = (r, g, b, 0 if (alpha0 and idx == 0) else 255)
    return img


def maximize(root):
    """Развернуть окно штатно (заголовок и work-area остаются у WM)."""
    for fn in (lambda: root.state("zoomed"),
               lambda: root.attributes("-zoomed", True)):
        try:
            fn()
            return
        except tk.TclError:
            pass


# ---------- окно ----------

GRID_C = "#2b3340"          # сетка тайлов
BLOCK_C = "#46536a"         # границы блоков 16 клеток (кольцо VRAM)
CURSOR_C = "#ffd040"        # курсор
MARK_HERO = "#ffffff"       # рамка спавна героя
MARK_ENEMY = "#ff5a5a"      # рамка спавна врага
MARK_EXIT = "#5ad2ff"       # рамка выхода
SOLID_C = "#ff3030"         # заливка твёрдости
FAINT_RGBA = (213, 218, 226, 64)  # серый 25% прозрачности (64/255)
FAINT_EDGE = "#9aa3b2"      # тонкая пунктирная рамка той же метки
CARD = 38                   # карточка в палитре, px (32 + поля)
THUMB = 32                  # картинка карточки, px
PAL_X, PAL_Y = 8, 22        # отступ сетки карточек (PAL_Y — под заголовком)
PAL_COLS = 4                # карточек в ряд


class LevelWindow:
    def __init__(self, root, ed):
        self.root = root
        self.ed = ed
        self.lv = ed.lv
        self.palette, self.cells, self.actors = G.editor_gfx()
        ed.known = set(self.cells)
        self.zoom = 24
        self._pil = {}           # (вид, индекс, px, alpha0) -> PIL.Image
        self._photo = {}         # (вид, индекс, px, alpha0) -> PhotoImage
        self._item = {}          # (r, c) -> id картинки клетки
        self._shown = {}         # (r, c) -> код, который сейчас нарисован
        self._cards = []         # (x0, y0, x1, y1, инструмент)
        self._card_rect = {}     # инструмент -> id рамки карточки
        self._cursor_id = None   # прямоугольник курсора (единственный на карте)
        self._stroke = False
        self.grid_var = tk.BooleanVar(value=True)
        self.solid_var = tk.BooleanVar(value=False)
        self.faint_var = tk.BooleanVar(value=True)
        self.spawn_var = tk.BooleanVar(value=True)
        self.zoom_var = tk.StringVar(value=str(self.zoom))
        self.kind_var = tk.StringVar(value=ENEMY_KIND_NAMES[0])
        self._build_menu()
        self._build_ui()
        self._build_palette()
        self._build_map()
        self.refresh_all()

    # ---------- картинки ----------

    def _tile_pil(self, code, px):
        key = ("tile", code, px, False)
        if key not in self._pil:
            cols = self.cells.get(code) or self.cells.get(0)
            self._pil[key] = cols_image(cols, self.palette).resize(
                (px, px), Image.NEAREST)
        return self._pil[key]

    def _tile_photo(self, code, px):
        key = ("tile", code, px, False)
        if key not in self._photo:
            self._photo[key] = ImageTk.PhotoImage(self._tile_pil(code, px))
        return self._photo[key]

    def _faint_photo(self, px):
        """Серый квадрат 25% прозрачности — метка невидимых клеток 03h/05h.

        Одна картинка на масштаб: Tk 8.6 композитит RGBA поверх уже
        нарисованной клетки, т.е. это честные 25% (=64/255), а не stipple.
        """
        key = ("faint", px, 0, True)
        if key not in self._photo:
            r, g, b, a = FAINT_RGBA
            self._photo[key] = ImageTk.PhotoImage(
                Image.new("RGBA", (px, px), (r, g, b, a)))
        return self._photo[key]

    def _actor_photo(self, kind, idx, px):
        key = (kind, idx, px, True)
        if key not in self._photo:
            if kind == "hero":
                cols = self.actors["hero"][idx]
            else:
                k, ph = idx
                cols = self.actors["enemy"][k][ph]
            img = cols_image(cols, self.palette, alpha0=True).resize(
                (px, px), Image.NEAREST)
            self._pil[key] = img
            self._photo[key] = ImageTk.PhotoImage(img)
        return self._photo[key]

    # ---------- меню/тулбар ----------

    def _build_menu(self):
        m = tk.Menu(self.root)
        f = tk.Menu(m, tearoff=0)
        f.add_command(label="Сохранить", accelerator="Ctrl+S", command=self.save)
        f.add_command(label="Перечитать level.inc", command=self.reload)
        f.add_separator()
        f.add_command(label="Выход", accelerator="Ctrl+Q", command=self.on_quit)
        m.add_cascade(label="Файл", menu=f)
        e = tk.Menu(m, tearoff=0)
        e.add_command(label="Отменить", accelerator="Ctrl+Z", command=self.undo)
        e.add_command(label="Вернуть", accelerator="Ctrl+Y", command=self.redo)
        m.add_cascade(label="Правка", menu=e)
        v = tk.Menu(m, tearoff=0)
        v.add_checkbutton(label="Сетка тайлов", variable=self.grid_var,
                          command=self._draw_overlay)
        v.add_checkbutton(label="Твёрдость (заливка)", variable=self.solid_var,
                          command=self._draw_overlay)
        v.add_checkbutton(label="Невидимые клетки 03/05 (серый 25%)",
                          variable=self.faint_var, command=self._draw_overlay)
        v.add_checkbutton(label="Спавны (герой/враги/выход)", variable=self.spawn_var,
                          command=self._draw_overlay)
        m.add_cascade(label="Вид", menu=v)
        h = tk.Menu(m, tearoff=0)
        h.add_command(label="Клавиши и мышь…", command=self.show_help)
        m.add_cascade(label="Справка", menu=h)
        self.root.config(menu=m)
        self._menu = m

    def _build_ui(self):
        self.root.title("Level Editor — putup-beam / Vector-06C")
        self.root.geometry("1180x820")

        bar = ttk.Frame(self.root, padding=(6, 6, 6, 2))
        bar.pack(side=tk.TOP, fill=tk.X)
        ttk.Button(bar, text="Сохранить", command=self.save).pack(side=tk.LEFT)
        ttk.Button(bar, text="Проверить", command=self.check).pack(
            side=tk.LEFT, padx=(4, 0))
        ttk.Button(bar, text="Перечитать", command=self.reload).pack(
            side=tk.LEFT, padx=(4, 0))
        ttk.Checkbutton(bar, text="сетка", variable=self.grid_var,
                        command=self._draw_overlay).pack(side=tk.LEFT, padx=(14, 0))
        ttk.Checkbutton(bar, text="твёрдость", variable=self.solid_var,
                        command=self._draw_overlay).pack(side=tk.LEFT, padx=(8, 0))
        ttk.Checkbutton(bar, text="невидимые 03/05", variable=self.faint_var,
                        command=self._draw_overlay).pack(side=tk.LEFT, padx=(8, 0))
        ttk.Checkbutton(bar, text="спавны", variable=self.spawn_var,
                        command=self._draw_overlay).pack(side=tk.LEFT, padx=(8, 0))
        ttk.Label(bar, text="  масштаб:").pack(side=tk.LEFT)
        z = ttk.OptionMenu(bar, self.zoom_var, str(self.zoom),
                           "16", "24", "32", "48", command=self._on_zoom)
        z.config(width=4)
        z.pack(side=tk.LEFT)
        ttk.Button(bar, text="Отменить", command=self.undo).pack(
            side=tk.LEFT, padx=(14, 0))
        ttk.Button(bar, text="Вернуть", command=self.redo).pack(
            side=tk.LEFT, padx=(4, 0))

        body = ttk.Frame(self.root)
        body.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        # слева: палитра (canvas со скроллом) + вид врага
        left = ttk.Frame(body, padding=(6, 4))
        left.pack(side=tk.LEFT, fill=tk.Y)
        palfr = ttk.Frame(left)
        palfr.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        self.pal = tk.Canvas(palfr, width=PAL_X * 2 + PAL_COLS * CARD + 6,
                             bg="#14181e", highlightthickness=0)
        psb = ttk.Scrollbar(palfr, orient=tk.VERTICAL, command=self.pal.yview)
        self.pal.config(yscrollcommand=psb.set)
        self.pal.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        psb.pack(side=tk.LEFT, fill=tk.Y)
        self.pal.bind("<Button-1>", self._on_pal_click)
        ttk.Label(left, text="вид врага (для инструмента «враг»):").pack(
            anchor=tk.W, pady=(6, 0))
        self.kind_box = ttk.Combobox(left, textvariable=self.kind_var,
                                     values=list(ENEMY_KIND_NAMES),
                                     state="readonly", width=14)
        self.kind_box.pack(anchor=tk.W, pady=(2, 0))
        self.kind_box.bind("<<ComboboxSelected>>", self._on_kind)

        # центр: карта со скроллбарами
        mid = ttk.Frame(body)
        mid.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        mid.columnconfigure(0, weight=1)
        mid.rowconfigure(0, weight=1)
        self.canvas = tk.Canvas(mid, bg="#171c23", highlightthickness=1,
                                highlightbackground="#3a4353")
        self.vsb = ttk.Scrollbar(mid, orient=tk.VERTICAL, command=self.canvas.yview)
        self.hsb = ttk.Scrollbar(mid, orient=tk.HORIZONTAL,
                                 command=self.canvas.xview)
        self.canvas.config(yscrollcommand=self.vsb.set, xscrollcommand=self.hsb.set)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.vsb.grid(row=0, column=1, sticky="ns")
        self.hsb.grid(row=1, column=0, sticky="ew")
        self.canvas.bind("<Button-1>", self._on_press)
        self.canvas.bind("<B1-Motion>", self._on_drag)
        self.canvas.bind("<Button-3>", self._on_pick)
        self.canvas.bind("<ButtonRelease-1>", self._on_release)
        self.canvas.bind("<Motion>", self._on_hover)
        self.canvas.bind("<MouseWheel>", self._on_wheel)
        self.canvas.bind("<Button-4>", lambda e: self._on_wheel(e, -1))
        self.canvas.bind("<Button-5>", lambda e: self._on_wheel(e, 1))

        # справа: гейты и сводка
        right = ttk.Frame(body, padding=(6, 4))
        right.pack(side=tk.LEFT, fill=tk.Y)
        ttk.Label(right, text="Сводка и гейты").pack(anchor=tk.W)
        self.info = tk.Text(right, width=38, height=30, wrap="word",
                            state="disabled", relief="flat", bg="#f4f6f8",
                            font=("TkFixedFont", 9))
        self.info.pack(fill=tk.BOTH, expand=True, pady=(2, 0))
        ttk.Button(right, text="Проверить гейты", command=self.check).pack(
            fill=tk.X, pady=(4, 0))
        ttk.Label(right, foreground="#666", justify=tk.LEFT, text=(
            "ЛКМ — рисовать (протяжка — линия)\n"
            "ПКМ — пипетка (код в кисть)\n"
            "колесо — прокрутка\n"
            "Tab — следующая кисть, Esc — пустая\n"
            "H/E/1..3 — спавн героя/выхода/врага\n"
            "V — вид врага под курсором\n"
            "Del — стереть клетку (код 1)\n"
            "Ctrl+Z / Ctrl+Y — отмена/повтор\n"
            "Ctrl+S — сохранить, Ctrl+Q — выход\n"
            "\n"
            "Серый квадрат 25%: 03h блокиратор\n"
            "и 05h скрытый кирпич — в игре они\n"
            "выглядят как пустота/кирпич.")).pack(anchor=tk.W, pady=(6, 0))

        # статус-строка
        st = ttk.Frame(self.root, padding=(6, 2, 6, 4))
        st.pack(side=tk.BOTTOM, fill=tk.X)
        self.status = ttk.Label(st, text="готово")
        self.status.pack(side=tk.LEFT)
        self.gate_lbl = ttk.Label(st, text="", foreground="#666")
        self.gate_lbl.pack(side=tk.RIGHT)

        self.root.bind("<Control-s>", lambda _e: self.save())
        self.root.bind("<Control-z>", lambda _e: self.undo())
        self.root.bind("<Control-y>", lambda _e: self.redo())
        self.root.bind("<Control-q>", lambda _e: self.on_quit())
        self.root.bind("<Escape>", lambda _e: self._key("esc"))
        self.root.bind("<Delete>", lambda _e: self._paint_code(EMPTY_CODE))
        self.root.bind("<BackSpace>", lambda _e: self._paint_code(EMPTY_CODE))
        self.root.protocol("WM_DELETE_WINDOW", self.on_quit)
        for seq, key in (("<Left>", "left"), ("<Right>", "right"),
                         ("<Up>", "up"), ("<Down>", "down"),
                         ("<Tab>", "tab"), ("<ISO_Left_Tab>", "prev-tab"),
                         ("<space>", "space"), ("<Return>", "enter")):
            self.root.bind(seq, lambda _e, k=key: self._key(k) or "break")
        for ch in ("h", "H", "e", "E", "1", "2", "3", "v", "V", "u", "U"):
            self.root.bind("<KeyPress-%s>" % ch,
                           lambda _e, k=ch: self._key(k))

    # ---------- палитра ----------

    def _palette_items(self):
        """-> [(x0, y0, x1, y1, tool, image_kind, key)] для рисования карточек."""
        out, i = [], 0
        for code, _ch, _name in PALETTE:
            col, row = i % PAL_COLS, i // PAL_COLS
            x = PAL_X + col * CARD
            y = PAL_Y + row * CARD
            out.append((x, y, x + CARD - 2, y + CARD - 2, "tile:%d" % code,
                        "tile", code))
            i += 1
        y = PAL_Y + ((i + PAL_COLS - 1) // PAL_COLS) * CARD + 40
        marks = [("hero", "герой", "hero", 0),
                 ("exit", "выход", "tile", EXIT_CODE)]
        marks += [("enemy:%d" % k, "враг %d" % (k + 1), "enemy", (k, 0))
                  for k in range(3)]
        for j, (tool, _title, kind, idx) in enumerate(marks):
            col, row = j % PAL_COLS, j // PAL_COLS
            x = PAL_X + col * CARD
            yy = y + row * CARD
            out.append((x, yy, x + CARD - 2, yy + CARD - 2, tool, kind, idx))
        return out

    def _build_palette(self):
        pal = self.pal
        pal.delete("all")
        self._cards, self._card_rect = [], {}
        items = self._palette_items()
        # заголовок над разделами рисуем по координатам первой карточки
        pal.create_text(PAL_X, PAL_Y - 8, text="тайлы — клик = кисть",
                        anchor="sw", fill="#9fb0c4",
                        font=("TkDefaultFont", 9, "bold"))
        n_tiles = len(PALETTE)
        y_marks = items[n_tiles][1] - 30
        pal.create_text(PAL_X, y_marks, text="маркеры — клик = инструмент",
                        anchor="sw", fill="#9fb0c4",
                        font=("TkDefaultFont", 9, "bold"))
        for x0, y0, x1, y1, tool, kind, idx in items:
            pal.create_rectangle(x0, y0, x1, y1, fill="#0a0d11", outline="")
            if kind == "tile":
                img = self._tile_photo(idx, THUMB)
                pal.create_image(x0 + 2, y0 + 2, anchor="nw", image=img)
                if self._tile_pil(idx, THUMB).getbbox() is None:
                    # чёрный тайл (0/1/3) — штрихуем, иначе карточка пустая
                    pal.create_line(x0 + 3, y1 - 3, x1 - 3, y0 + 3,
                                    fill="#333c48")
                    pal.create_line(x0 + 3, y0 + 3, x1 - 3, y1 - 3,
                                    fill="#333c48")
                code_txt = "X" if tool == "exit" else "%02X" % idx
            else:
                img = self._actor_photo("hero" if kind == "hero" else "enemy",
                                        idx, THUMB)
                pal.create_image(x0 + 2, y0 + 2, anchor="nw", image=img)
                if tool == "hero":
                    code_txt = "H"
                elif tool == "exit":
                    code_txt = "X"
                else:
                    code_txt = "%d" % (int(tool.split(":")[1]) + 1)
            pal.create_text(x1 - 2, y1 - 2, text=code_txt, anchor="se",
                            fill="#7f90a4", font=("TkFixedFont", 7))
            self._card_rect[tool] = pal.create_rectangle(
                x0, y0, x1, y1, outline="#333c48", width=1)
            self._cards.append((x0, y0, x1, y1, tool))
        pal.configure(scrollregion=pal.bbox("all"))
        self._mark_tool()

    def _on_pal_click(self, e):
        x, y = self.pal.canvasx(e.x), self.pal.canvasy(e.y)
        for x0, y0, x1, y1, tool in self._cards:
            if x0 <= x <= x1 and y0 <= y <= y1:
                self._set_tool(tool)
                return

    def _mark_tool(self):
        for tool, rid in self._card_rect.items():
            on = tool == self.ed.tool
            self.pal.itemconfig(rid, outline=CURSOR_C if on else "#333c48",
                                width=2 if on else 1)

    def _set_tool(self, tool):
        self.ed.set_tool(tool)
        self._mark_tool()
        if tool.startswith("enemy:"):
            i = int(tool.split(":")[1])
            self.kind_var.set(ENEMY_KIND_NAMES[self.lv.kinds[i]])
            self.kind_box.config(state="readonly")
        self._set_status()

    def _on_kind(self, _e=None):
        """Смена вида в списке: у выбранного инструмента-врага либо под курсором."""
        name = self.kind_var.get()
        if name not in ENEMY_KIND_NAMES:
            return
        kind = ENEMY_KIND_NAMES.index(name)
        if self.ed.tool.startswith("enemy:"):
            self.ed.set_kind(int(self.ed.tool.split(":")[1]), kind)
        else:
            hit = None
            for i, e in enumerate(self.lv.enemies):
                if e == list(self.ed.cur):
                    hit = i
            if hit is None:
                self._set_status("под курсором нет спавна врага")
                return
            self.ed.set_kind(hit, kind)
        self.refresh_after_edit()

    # ---------- карта ----------

    def _build_map(self):
        c = self.canvas
        c.delete("all")
        self._item, self._shown = {}, {}
        px = self.zoom
        for r in range(self.lv.rows):
            for col in range(self.lv.cols):
                code = self.lv.map[r][col]
                ph = self._tile_photo(code, px)
                self._item[(r, col)] = c.create_image(
                    col * px, r * px, anchor="nw", image=ph)
                self._shown[(r, col)] = code
        c.configure(scrollregion=(0, 0, self.lv.cols * px, self.lv.rows * px))
        self._draw_overlay()

    def _refresh_cell(self, r, col):
        code = self.lv.map[r][col]
        if self._shown.get((r, col)) == code:
            return
        ph = self._tile_photo(code, self.zoom)
        self.canvas.itemconfig(self._item[(r, col)], image=ph)
        self._shown[(r, col)] = code

    def _draw_overlay(self):
        """Сетка, заливка твёрдости, маркеры спавнов и курсор (тег "ov")."""
        c = self.canvas
        c.delete("ov")
        self._cursor_id = None
        px = self.zoom
        W, H = self.lv.cols * px, self.lv.rows * px
        if self.grid_var.get():
            for x in range(self.lv.cols + 1):
                c.create_line(x * px, 0, x * px, H, fill=GRID_C, tags="ov")
            for y in range(self.lv.rows + 1):
                # каждая 8-я линия — стык блоков 16x16 клеток (кольцо VRAM)
                wide = (y % 8) == 0
                c.create_line(0, y * px, W, y * px,
                              fill=BLOCK_C if wide else GRID_C, tags="ov")
        if self.solid_var.get():
            for r in range(self.lv.rows):
                for col in range(self.lv.cols):
                    code = self.lv.map[r][col]
                    if code in SOLID or code in (EXIT_CODE,) + EXIT_PHASES:
                        c.create_rectangle(col * px, r * px, (col + 1) * px,
                                           (r + 1) * px, fill=SOLID_C,
                                           stipple="gray25", outline="", tags="ov")
        if self.faint_var.get():
            # 03h/05h на экране не отличимы от пустоты/кирпича (глифы
            # совпадают), поэтому клетка накрывается серым квадратом с
            # прозрачностью 25% — картинка композитится поверх клетки.
            ph = self._faint_photo(px)
            for r in range(self.lv.rows):
                for col in range(self.lv.cols):
                    if self.lv.map[r][col] in FAINT_CODES:
                        c.create_image(col * px, r * px, anchor="nw",
                                       image=ph, tags="ov")
                        # рамка — чтобы клетка читалась и поверх яркого
                        # кирпича 05h, где 25% серого дают лишь лёгкий тон
                        c.create_rectangle(col * px, r * px, (col + 1) * px,
                                           (r + 1) * px, outline=FAINT_EDGE,
                                           dash=(2, 3), tags="ov")
        if self.spawn_var.get():
            for i, (r, col) in enumerate(self.lv.enemies):
                k = self.lv.kinds[i] if 0 <= self.lv.kinds[i] < 3 else 0
                ph = self._actor_photo("enemy", (k, 0), px)
                c.create_image(col * px, r * px, anchor="nw", image=ph, tags="ov")
                c.create_rectangle(col * px, r * px, (col + 1) * px, (r + 1) * px,
                                   outline=MARK_ENEMY, tags="ov")
                c.create_text(col * px + 2, r * px + 1, text=str(i + 1),
                              anchor="nw", fill=MARK_ENEMY,
                              font=("TkFixedFont", 8, "bold"), tags="ov")
            hr, hc = self.lv.hero
            ph = self._actor_photo("hero", 0, px)
            c.create_image(hc * px, hr * px, anchor="nw", image=ph, tags="ov")
            c.create_rectangle(hc * px, hr * px, (hc + 1) * px, (hr + 1) * px,
                               outline=MARK_HERO, width=2, tags="ov")
            er, ec = self.lv.exit
            c.create_rectangle(ec * px, er * px, (ec + 1) * px, (er + 1) * px,
                               outline=MARK_EXIT, width=2, dash=(3, 2), tags="ov")
        pr, pc = self.ed.cur
        self._cursor_id = c.create_rectangle(
            pc * px, pr * px, (pc + 1) * px, (pr + 1) * px,
            outline=CURSOR_C, width=2, tags="ov")

    def _place_cursor(self):
        """Движение курсора по карте — только его прямоугольник, без перерисовки
        всей сетки/маркеров (иначе каждый Motion перебирает тысячи айтемов)."""
        px = self.zoom
        pr, pc = self.ed.cur
        if self._cursor_id is None:
            self._cursor_id = self.canvas.create_rectangle(
                pc * px, pr * px, (pc + 1) * px, (pr + 1) * px,
                outline=CURSOR_C, width=2, tags="ov")
        else:
            self.canvas.coords(self._cursor_id, pc * px, pr * px,
                               (pc + 1) * px, (pr + 1) * px)

    # ---------- мышь ----------

    def _cell_at(self, e):
        x, y = self.canvas.canvasx(e.x), self.canvas.canvasy(e.y)
        col, r = int(x // self.zoom), int(y // self.zoom)
        if 0 <= r < self.lv.rows and 0 <= col < self.lv.cols:
            return r, col
        return None

    def _on_press(self, e):
        pos = self._cell_at(e)
        if pos is None:
            return
        self._stroke = True
        self.ed.push_undo()
        self._apply_at(pos, push=False)

    def _on_drag(self, e):
        pos = self._cell_at(e)
        if self._stroke and pos:
            self._apply_at(pos, push=False)

    def _on_release(self, _e):
        self._stroke = False

    def _on_hover(self, e):
        pos = self._cell_at(e)
        if pos and list(pos) != self.ed.cur:
            self.ed.set_cur(*pos)
            self._place_cursor()
            self._set_status()

    def _apply_at(self, pos, push=True):
        self.ed.set_cur(*pos)
        if self.ed.apply(push=push):
            self.refresh_after_edit()

    def _paint_code(self, code):
        self.ed.apply_code(code)        # точка отмены — внутри apply_code
        self.refresh_after_edit()

    def _on_pick(self, e):
        pos = self._cell_at(e)
        if pos is None:
            return
        self.ed.set_cur(*pos)
        self.ed.pick()
        self._mark_tool()
        self._set_status()

    def _on_wheel(self, e, delta=None):
        if delta is None:                        # Windows/mac
            delta = -1 if e.delta > 0 else 1
        self.canvas.yview_scroll(delta * 3, "units")

    def _on_zoom(self, _v=None):
        self.zoom = int(self.zoom_var.get())
        self.refresh_all()

    # ---------- обновление ----------

    def refresh_after_edit(self):
        """Перерисовать только то, что могло измениться."""
        for (r, col) in list(self._shown):
            self._refresh_cell(r, col)
        self._draw_overlay()
        self._set_status()
        self._fill_info()

    def refresh_all(self):
        self._build_map()
        self.refresh_after_edit()
        self._mark_tool()

    def _key(self, k):
        if k == "prev-tab":
            self.ed.next_brush(-1)
        else:
            self.ed.key(k)
        self.refresh_after_edit()
        self._mark_tool()

    def _sync_kind(self):
        """Список «вид врага» показывает вид того врага, с которым работаем:
        выбранного инструмента-врага, иначе — спавна под курсором."""
        if self.ed.tool.startswith("enemy:"):
            i = int(self.ed.tool.split(":")[1])
        else:
            i = next((j for j, e in enumerate(self.lv.enemies)
                      if e == list(self.ed.cur)), None)
        if i is not None:
            self.kind_var.set(ENEMY_KIND_NAMES[self.lv.kinds[i]])

    def _set_status(self, extra=None):
        self._sync_kind()
        r, col = self.ed.cur
        code = self.lv.map[r][col]
        tool = self.ed.tool
        if tool.startswith("tile:"):
            brush = "%02Xh %s" % (int(tool.split(":")[1]),
                                  TILE_NAME.get(int(tool.split(":")[1]), "?"))
        elif tool == "hero":
            brush = "герой"
        elif tool == "exit":
            brush = "выход"
        else:
            i = int(tool.split(":")[1])
            brush = "враг %d (%s)" % (i + 1, ENEMY_KIND_NAMES[self.lv.kinds[i]])
        msg = extra if extra is not None else self.ed.msg
        self.status.config(text="(%d,%d) · код %02Xh %s · кисть %s · %s%s"
                           % (r, col, code, TILE_NAME.get(code, "—"), brush,
                              msg, "  *" if self.ed.dirty else ""))

    def _fill_info(self):
        errs, warns, reach = self.lv.check(known=self.ed.known)
        rows = ["Гейты: %s" % ("OK" if not errs else "ОШИБОК %d" % len(errs))]
        rows += ["  ! " + e for e in errs[:6]]
        rows += ["  ~ " + w for w in warns]
        items = self.lv.items()
        kinds = sorted({self.lv.map[r][c] for r, c in items})
        rows += ["", "предметов: %d (%s)" % (
            len(items), ", ".join("%02Xh" % c for c in kinds)),
            "достижимо клеток: %d из %d" % (
                len(reach), self.lv.rows * self.lv.cols)]
        faint = [(r, c) for r in range(self.lv.rows)
                 for c in range(self.lv.cols) if self.lv.map[r][c] in FAINT_CODES]
        if faint:
            rows.append("скрытых клеток: %d (%s)" % (
                len(faint), ", ".join("%02Xh" % self.lv.map[r][c]
                                      for r, c in faint[:6])))
        rows.append("")
        rows.append("спавны:")
        rows.append("  герой   (%d,%d)" % tuple(self.lv.hero))
        rows.append("  выход   (%d,%d)" % tuple(self.lv.exit))
        for i, e in enumerate(self.lv.enemies):
            rows.append("  враг %d  (%d,%d) %s" % (
                i + 1, e[0], e[1], ENEMY_KIND_NAMES[self.lv.kinds[i]]))
        rows += ["", "коды клеток:"]
        rows += ["  %02Xh %s" % (code, name) for code, _ch, name in PALETTE]
        txt = "\n".join(rows)
        self.info.config(state="normal")
        self.info.delete("1.0", "end")
        self.info.insert("1.0", txt)
        self.info.config(state="disabled")
        self.gate_lbl.config(text="гейты: %s" % ("OK" if not errs
                                                 else "ошибки (%d)" % len(errs)))

    # ---------- команды ----------

    def check(self):
        errs, warns, _ = self.lv.check(known=self.ed.known)
        self._fill_info()
        if errs:
            messagebox.showerror("Гейты не пройдены", "\n".join(errs[:12]))
        else:
            messagebox.showinfo("Гейты",
                                "OK" + ("\n\n" + "\n".join(warns) if warns else ""))

    def save(self):
        if not self.ed.do_save():
            errs, _w, _r = self.lv.check(known=self.ed.known)
            self._set_status()
            messagebox.showerror("Не сохранено", "\n".join(errs[:12]))
            return
        self._set_status()
        self._fill_info()

    def undo(self):
        self.ed.undo()
        self.refresh_after_edit()

    def redo(self):
        self.ed.redo()
        self.refresh_after_edit()

    def reload(self):
        if self.ed.dirty and not messagebox.askyesno(
                "Перечитать", "Несохранённые правки будут потеряны. Продолжить?"):
            return
        self.lv = Level.load(self.ed.path)
        self.ed.lv = self.lv
        self.ed.cur = list(self.lv.hero)
        self.ed.dirty = False
        self.ed._undo.clear()
        self.ed._redo.clear()
        self.ed.msg = "перечитано: %s" % os.path.basename(self.ed.path)
        self._build_map()
        self.refresh_all()

    def on_quit(self):
        if self.ed.dirty and not messagebox.askyesno(
                "Выход", "Есть несохранённые изменения. Выйти?"):
            return
        self.root.destroy()

    def show_help(self):
        messagebox.showinfo("Редактор уровня putup-beam", (
            "Слева — палитра: клик по карточке включает инструмент.\n"
            "Карта: ЛКМ рисует, протяжка — линия; ПКМ — пипетка;\n"
            "колесо — прокрутка.\n\n"
            "Клавиши: стрелки — курсор, Tab/Shift+Tab — кисть,\n"
            "пробел — поставить, H — спавн героя, E — выход,\n"
            "1/2/3 — спавн врага, V — вид врага под курсором,\n"
            "Del — стереть (код 1), Ctrl+Z/Ctrl+Y — отмена/повтор,\n"
            "Ctrl+S — сохранить (с гейтами), Ctrl+Q — выход.\n\n"
            "Сохранение пишет level.inc только если гейты прошли:\n"
            "герой не в твёрдой клетке, выход/предметы/спавны\n"
            "достижимы, у всех кодов есть графика в assets.inc.\n"
            "После сохранения — make full."))


def run_gui(ed):
    if tk is None:
        sys.exit("Не найден Tkinter. Установка (Debian/Ubuntu):\n"
                 "  sudo apt install python3-tk\n"
                 "Перезапусти:  python3 tools/level_editor.py")
    if Image is None:
        sys.exit("Не найден Pillow с ImageTk. Установка (Debian/Ubuntu):\n"
                 "  sudo apt install python3-pil python3-pil.imagetk\n"
                 "Перезапусти:  python3 tools/level_editor.py")
    root = tk.Tk()
    try:
        ttk.Style().theme_use("clam")
    except tk.TclError:
        pass
    win = LevelWindow(root, ed)
    maximize(root)
    root.mainloop()
    return win


def known_codes():
    """Коды, для которых assets.inc печатает графику (или None, если нечем)."""
    try:
        return set(G.editor_gfx()[1])
    except Exception as exc:                     # pragma: no cover
        print("предупреждение: графика недоступна (%s)" % exc, file=sys.stderr)
        return None


def main():
    ap = argparse.ArgumentParser(description="редактор level.inc демо putup-beam")
    ap.add_argument("--map", default=OUT_INC, help="путь к level.inc")
    ap.add_argument("--print", action="store_true", help="ASCII-превью и выход")
    ap.add_argument("--check", action="store_true", help="прогнать гейты и выйти")
    args = ap.parse_args()

    lv = Level.load(args.map)
    if args.check or args.print:
        errs, warns, reach = lv.check(known=known_codes())
        print(lv.ascii())
        print("предметов: %d (%s)" % (len(lv.items()), ", ".join(
            "%02Xh" % c for c in sorted({lv.map[r][c] for r, c in lv.items()}))))
        print("достижимо клеток: %d" % len(reach))
        for w in warns:
            print("WARN:", w)
        for e in errs:
            print("FAIL:", e)
        print("гейты: %s" % ("OK" if not errs else "ОШИБКИ"))
        return 0 if not errs else 1
    ed = Editor(lv, args.map)
    ed.known = known_codes()
    run_gui(ed)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
