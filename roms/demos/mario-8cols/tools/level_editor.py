#!/usr/bin/env python3
"""level_editor.py — редактор уровня Mario 16-цвет (Tkinter).

Запуск:  python3 tools/level_editor.py
Нужен Tkinter: sudo apt install python3-tk  (Pillow уже в зависимостях проекта).

Два режима (переключатель «Режим» на панели):
  * Объекты (основной) — карта как список прямоугольников {t,x,y,w,h}.
    ЛКМ по пустому + протянуть — создать объект выбранным тайлом-кистью;
    ЛКМ по объекту + тянуть — переместить; Del/BackSpace — удалить выбранный;
    ПКМ — взять тайл под курсором в кисть. Рамки: бирюза — границы объектов,
    розовый — выделенный/создаваемый. Источник истины — src/objects.json.
  * Тайлы (фолбэк) — классическое по-тайловое рисование в сетку level.json
    (ЛКМ рисует, ПКМ берёт тайл). При сохранении правки пересегментируются
    в объекты.

ШТАМПЫ (составные объекты, там же, режим «Объекты»):
  * панель «Префабы» (src/prefabs.json) — монета, кубик «?», кирпич, земля,
    стена, облачко, облако 1/2/3 бугра + облако произвольной ширины, куст,
    площадка, труба вверх/вниз;
  * выбранный штамп рисуется на карте ПОЛУПРОЗРАЧНЫМ ПРИЗРАКОМ: тянешь мышью —
    размер живьём (растягиваются только строки/столбцы, помеченные stretch_x /
    stretch_y, шапка трубы, бугор облака и углы площадки остаются целыми);
  * «Повторять сеткой по области» — штамп ставится копиями по протянутой
    области с шагом X и Y (ряд монет, лесенка кубиков, поле кирпичей);
  * все прямоугольники одного штампа помечены полем g (номер группы): клик
    выделяет, тянет и удаляет ГРУППУ целиком. Поле g читает только редактор —
    gen_assets.pack_objects берёт t/x/y/w/h, формат objects.json и ROM не
    меняются.

ЛИМИТЫ: размеры карты и объекты проверяются формулами сборки (см. MAX_COLS и
_limits()), а не только рамками спинбоксов, — иначе 512x255 проходит редактор и
падает на make.

Прочее:
  * палитра всех тайлов (src/tiles/*.png) — клик выбирает кисть/тип объекта;
  * свойства тайла (wall / platform / transparent) — галочки справа или ПКМ;
  * «Показать твёрдость» — заливка: красная — стена, синяя — платформа;
  * Сохранение пишет src/objects.json, src/level.json (развёрнутая grid) и
    src/tiles.json (после — `make`).
"""
import json
import os
import re
import sys

try:
    import tkinter as tk
    from tkinter import ttk, messagebox
except ImportError:
    sys.exit("Не найден Tkinter. Установка (Debian/Ubuntu):\n"
             "  sudo apt install python3-tk\n"
             "Перезапусти:  python3 tools/level_editor.py")

try:
    from PIL import Image, ImageTk, ImageDraw
except ImportError:
    sys.exit("Не найден PIL.ImageTk (биндинг Tk для Pillow — отдельный пакет).\n"
             "Установка (Debian/Ubuntu):\n"
             "  sudo apt install python3-pil python3-pil.imagetk\n"
             "Перезапусти:  python3 tools/level_editor.py")

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.abspath(os.path.join(HERE, "..", "src"))
ROM = os.path.abspath(os.path.join(HERE, "..", "mario-8c.rom"))
MAP = os.path.abspath(os.path.join(HERE, "..", "mario-8c.map"))
LEVEL_INC = os.path.join(SRC, "level.inc")
PREFAB_FILE = os.path.join(SRC, "prefabs.json")

# Общие с генератором функции развёртки/сегментации объектов (один источник
# истины для логики карты — редактор и прошивка не разъезжаются).
sys.path.insert(0, HERE)
import gen_assets as G                                    # noqa: E402
from objects_from_grid import cover_rectangles            # noqa: E402

COLL_RED = (224, 58, 58)      # сплошной (wall)
COLL_BLUE = (58, 123, 224)    # платформа (platform)
HL_COLOR = (255, 212, 0)      # жёлтая рамка «это текущий тайл-кисть» на карте
OVERLAY_ALPHA = 0.45          # сила полупрозрачной заливки твёрдости (0..1)
GRID_LINE = (128, 128, 128, 128)   # сетка границ тайлов: серый, 50% прозрачности
OBJ_LINE = (78, 201, 176)     # бирюзовая рамка объекта (режим «Объекты»)
OBJ_SEL = (255, 90, 200)      # рамка выбранного объекта
SKY = (13, 26, 43)
PAL_THUMB = 32
PAL_COLS = 6
PAL_GAP = 6
TILE_PX = 8                  # сторона тайла в исходниках (src/tiles/*.png)
PF_THUMB = 3 * TILE_PX       # превью в панели: px на тайл (3 => тайл 24 px)
PF_COL_W = 236               # ширина строки панели префабов, px
STAMP_ALPHA = 130            # 0..255 непрозрачность призрака штампа на карте

# ---- Настоящие лимиты уровня (те же формулы, что в gen_assets.py) ----------
# Редактор обязан отсеять их ДО make: сборка падает на half-way, а перекос по
# ОЗУ вообще не ловится ничем, кроме «ROM не грузится».
MAX_COLS = 512               # pack_objects: x ≤ 511 (9-й бит в flags)
MAX_ROWS = 255               # pack_objects: y ≤ 255; tile_stride/cam_row — байт
MIN_COLS = 64                # RAM-окно tile_win = OBJ_WIN_COLS(64) колонок
MIN_ROWS = 32                # экран VIEW_ROWS = 32 строки, иначе камера негде
TILEMAP_LIMIT = 65535        # cols*rows: 16-битная адресация тайлкарты (asm)
TILE_INDEX_LIMIT = 127       # flags: tile & 0x7F
WIN_RAM_PER_ROW = 64         # tile_win[OBJ_WIN_COLS * LEVEL_ROWS] байт ОЗУ
OBJ_WIN_STEP = 32            # OBJ_WIN_BLOCKS = ceil(cols / step), +1 sentinel
OBJ_BYTES = 5                # obj_data: {flags,xlo,y,w,h} на объект
IMAGE_LIMIT = 0x7FFF + 1 - 0x0100      # 32512: код+константы+BSS ниже VRAM


def _defines(path, names):
    """#define из сгенерированного level.inc — чтобы смета отталкивалась от
    ПОСЛЕДНЕЙ реальной сборки, а не от «предпоследней + догадка»."""
    try:
        with open(path) as f:
            txt = f.read()
    except OSError:
        return {}
    out = {}
    for n in names:
        m = re.search(r"#define\s+%s\s+(\d+)" % n, txt)
        if m:
            out[n] = int(m.group(1))
    return out


def _spin(var, default, lo, hi):
    """Число из Spinbox: введённый руками мусор не должен ронять постановку
    штампа (команда у спинбоксов только на стрелках, не на вводе с клавиатуры)."""
    try:
        v = int(var.get())
    except (ValueError, tk.TclError):
        return default
    return max(lo, min(hi, v))


def frame_color(tile):
    """wall приоритетнее платформы; ни того ни другого — без рамки."""
    if tile.get("wall"):
        return COLL_RED
    if tile.get("platform"):
        return COLL_BLUE
    return None


# ---------------------------------------------------------------------------
# ШТАМПЫ: паттерн + растяжение -> сетка тайлов -> прямоугольники объектов
# ---------------------------------------------------------------------------

def stretch_axis(n_src, spec, n_dst):
    """Индексы строк/столбцов паттерна для размера n_dst.

    spec: None      — размер фиксирован (ничего не тянем);
          "all"     — замостить циклически (куст: чередование колонок 30,32);
          int k     — 9-slice: 0..k слева/сверху, k повторяется, k+1.. справа/
                      снизу. Так тянутся тело трубы (k = строка тела: шапка
                      остаётся целой) и рамка площадки (k = средний слой);
          [a, b]    — повторять ОКНО колонок a..b целиком (облако: единичка
                      [23,26] — «бугор»; углы слева и справа остаются целыми).
    """
    n_dst = max(1, n_dst)
    if spec is None:
        return list(range(min(n_src, n_dst)))
    if spec == "all":
        return [i % n_src for i in range(n_dst)]
    if isinstance(spec, (list, tuple)):
        b = max(int(spec[0]), min(int(spec[1]), n_src - 1))
        a = max(0, min(int(spec[0]), b))
        unit = list(range(a, b + 1))
        mid = max(1, n_dst - (n_src - len(unit)))
        return (list(range(a)) + [unit[i % len(unit)] for i in range(mid)]
                + list(range(b + 1, n_src)))
    k = max(0, min(n_src - 1, int(spec)))
    return (list(range(k + 1)) + [k] * max(0, n_dst - n_src)
            + list(range(k + 1, n_src)))


def stamp_size(pf, w, h):
    """Желаемый размер штампа -> допустимый (тянутся только оси со stretch)."""
    pat = pf["grid"]
    ph, pw = len(pat), len(pat[0])
    if pf.get("stretch_x") is None:
        w = pw
    else:
        w = max(int(pf.get("min_w", pw)), w)
    if pf.get("stretch_y") is None:
        h = ph
    else:
        h = max(int(pf.get("min_h", ph)), h)
    return min(w, MAX_COLS), min(h, MAX_ROWS)


def stamp_cells(pf, w, h):
    """Штамп + размер -> row-major сетка тайлов (0 = пропуск, небо)."""
    pat = pf["grid"]
    ph, pw = len(pat), len(pat[0])
    w, h = stamp_size(pf, w, h)
    rows = stretch_axis(ph, pf.get("stretch_y"), h)
    cols = stretch_axis(pw, pf.get("stretch_x"), w)
    return [[pat[r][c] for c in cols] for r in rows]


def stamp_objects(pf, x, y, w, h, gid):
    """Штамп в точке (x,y) -> список объектов objects.json.

    Разбивка на прямоугольники — та же cover_rectangles(), что строит карту из
    тайл-grid'а, поэтому набор прямоугольников идентичен ручной обводке тех же
    тайлов. Поле g — номер группы (только для редактора).
    """
    cells = stamp_cells(pf, w, h)
    sw, sh = len(cells[0]), len(cells)
    grid = [0] * (sw * sh)                            # col-major: grid[c*sh + r]
    for r in range(sh):
        for c in range(sw):
            grid[c * sh + r] = cells[r][c]
    out = []
    for o in cover_rectangles(sw, sh, grid):
        out.append({"t": o["t"], "x": o["x"] + x, "y": o["y"] + y,
                    "w": o["w"], "h": o["h"], "g": gid})
    return out


def stamp_points(pf, x0, y0, x1, y1, step_x, step_y, bounds=None):
    """Область + шаг -> [(точка вставки)] и размер копии («ряд/сетка с шагом»).

    В режиме повтора штамп НЕ растягивается: ставится нативным размером везде,
    где целиком влезает с шагом step_x по колонкам и step_y по строкам. Шаг 0 =
    ось не повторяется (копия одна). Узкую протяжку (ряд монет тянут по одной
    клетке высотой) расширяется до размера штампа — иначе однострочная область не
    вмещает двухстрочную монетку и из жеста не выходит ничего. bounds=(cols,rows)
    отсекает копии, не влезающие в карту (ряд не наезжает сам на себя у края).
    """
    w, h = stamp_size(pf, len(pf["grid"][0]), len(pf["grid"]))
    xa, ya, xb, yb = min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1)
    xe, ye = max(xb, xa + w - 1), max(yb, ya + h - 1)
    if bounds:
        xe, ye = min(xe, bounds[0] - 1), min(ye, bounds[1] - 1)
    xs = list(range(xa, xe + 1, step_x)) if step_x > 0 else [xa]
    ys = list(range(ya, ye + 1, step_y)) if step_y > 0 else [ya]
    pts = [(x, y) for y in ys for x in xs
           if x + w <= xe + 1 and y + h <= ye + 1]
    return (pts or [(xa, ya)]), (w, h)


class LevelEditor:
    def __init__(self, root):
        self.root = root
        root.title("Level Editor — Mario 16cols / Vector-06C")
        root.geometry("1200x760")

        self.level, self.tiles = self._load_json()
        self.cols = int(self.level["cols"])
        self.rows = int(self.level["rows"])
        self.objects = self._load_objects()          # источник истины (Фаза 2)
        self.grid = list(G.expand_objects(self.cols, self.rows, self.objects))
        self.tile_orig = self._load_tile_images()
        self.prefabs = self._load_prefabs()
        self.dirty = False
        self.selected = 0
        self.cell = 12
        self.mode = tk.StringVar(value="object")     # "object" | "tile"
        self.sel_obj = None                          # индекс выбранного объекта
        self.sel_grp = None                          # его группа (поле g) или None
        self.drag = None                             # состояние перетаскивания
        self.stamp = None                            # выбранный префаб или None
        self._ghosts = []                            # PhotoImage призраков штампа
        self.show_overlay = tk.BooleanVar(value=True)
        self.hl_var = tk.BooleanVar(value=True)
        self.grid_var = tk.BooleanVar(value=True)
        self._base = None                            # кэш сметы из map/rom

        self._build_ui()
        self._rebuild_scaled()
        self.render_all()
        self._update_budget()
        self.select_tile(0)

    # ---- загрузка ---------------------------------------------------------
    def _load_json(self):
        for fn in ("level.json", "tiles.json"):
            if not os.path.isfile(os.path.join(SRC, fn)):
                sys.exit(f"Нет {fn} — сначала: python3 tools/export_assets.py")
        with open(os.path.join(SRC, "level.json")) as f:
            level = json.load(f)
        with open(os.path.join(SRC, "tiles.json"), encoding="utf-8") as f:
            tiles = json.load(f)
        return level, tiles

    def _load_objects(self):
        """src/objects.json как источник карты; нет/не совпал — сегментировать grid."""
        p = os.path.join(SRC, "objects.json")
        if os.path.isfile(p):
            with open(p) as f:
                ov = json.load(f)
            if int(ov["cols"]) == self.cols and int(ov["rows"]) == self.rows:
                return ov["objects"]
        return cover_rectangles(self.cols, self.rows, self.level["grid"])

    def _load_tile_images(self):
        imgs = []
        for t in self.tiles["tiles"]:
            p = os.path.join(SRC, t["file"])
            imgs.append(Image.open(p).convert("RGB") if os.path.isfile(p)
                        else Image.new("RGB", (8, 8), SKY))
        return imgs

    def _load_prefabs(self):
        """src/prefabs.json — именованные составные объекты (штампы).

        Нет файла / битые индексы тайлов — не фатально: панель просто пустая,
        редактор остаётся тайло-кистным. Индексы вне набора отсекаем, чтобы
        опечатка в JSON не рендила traceback на первом же превью.
        """
        if not os.path.isfile(PREFAB_FILE):
            return []
        with open(PREFAB_FILE, encoding="utf-8") as f:
            data = json.load(f)
        n = len(self.tiles["tiles"])
        out = []
        for pf in data.get("prefabs", []):
            grid = pf.get("grid") or []
            if not grid or any(t < 0 or t >= n for row in grid for t in row):
                continue
            if len({len(row) for row in grid}) != 1:
                continue
            out.append(pf)
        return out

    def _next_gid(self):
        """Свободный номер группы (поле g в objects.json)."""
        return max([int(o["g"]) for o in self.objects if "g" in o],
                   default=0) + 1

    # ---- лимиты: те же формулы, что у сборки ------------------------------
    def _image_base(self):
        """Байт в образе, НЕ зависящих от размеров уровня: вершина образа из
        map-файла линковщика (__bss_clib_tail) минус то, что размером уровня и
        задано — tile_win (64·rows), obj_data (5·объектов), obj_start
        (2·(блоки+1)). Нет map — оценка по .rom (он = образ + векторная
        страница 0x0000..0x00FF); нет и ROM — None: смета не проверяется."""
        if self._base is not None:
            return self._base
        used = None
        try:
            with open(MAP, errors="ignore") as f:
                m = re.search(r"^__bss_clib_tail\s+=\s+\$([0-9A-Fa-f]+)",
                              f.read(), re.M)
            if m:
                used = int(m.group(1), 16) - 0x0100
        except OSError:
            pass
        if used is None:
            try:
                used = os.path.getsize(ROM) - 0x0100
            except OSError:
                return None
        d = _defines(LEVEL_INC, ("LEVEL_ROWS", "OBJ_COUNT", "OBJ_WIN_BLOCKS"))
        if len(d) != 3:
            return None
        base = used - (WIN_RAM_PER_ROW * d["LEVEL_ROWS"]
                       + OBJ_BYTES * d["OBJ_COUNT"]
                       + 2 * (d["OBJ_WIN_BLOCKS"] + 1))
        if base < 0:                           # map/rom расходится с level.inc
            return None
        self._base = base
        return base

    def _budget(self, cols, rows, n_objs):
        """Оценка размера образа (0x0100..0x7FFF) для таких размеров уровня;
        None — если опереться не на что (нет ни map, ни ROM)."""
        base = self._image_base()
        if base is None:
            return None
        blocks = (cols + OBJ_WIN_STEP - 1) // OBJ_WIN_STEP
        return (base + WIN_RAM_PER_ROW * rows + OBJ_BYTES * n_objs
                + 2 * (blocks + 1))

    def _limits(self, cols=None, rows=None, objs=None, n_objs=None):
        """Претензии к уровню — пустой список значит «make пройдёт». Формулы
        срисованы с gen_assets: pack_objects (t ≤ 127, x ≤ 511, y ≤ 255,
        0 < w,h ≤ 255), build_level (rows ≤ 255, cols·rows ≤ 65535) и смета
        образа, которую вообще никто, кроме загрузки на machine, не ловит.
        n_objs — сколько объектов класть в смету, когда сама проверка объектов
        ещё не к месту (ресайз: их обрезка — отдельный диалог)."""
        cols = self.cols if cols is None else int(cols)
        rows = self.rows if rows is None else int(rows)
        objs = self.objects if objs is None else objs
        n_objs = len(objs) if n_objs is None else n_objs
        bad = []
        if not MIN_COLS <= cols <= MAX_COLS:
            bad.append("Ширина %d: можно %d…%d (RAM-окно tile_win = %d колонок, "
                       "x ≤ 511 в объекте)" % (cols, MIN_COLS, MAX_COLS,
                                               WIN_RAM_PER_ROW))
        if not MIN_ROWS <= rows <= MAX_ROWS:
            bad.append("Высота %d: можно %d…%d (экран %d строки, y ≤ 255 — "
                       "байт в объекте)" % (rows, MIN_ROWS, MAX_ROWS, MIN_ROWS))
        if cols * rows > TILEMAP_LIMIT:
            bad.append("W×H = %d > %d — тайлкарта адресуется 16 битами"
                       % (cols * rows, TILEMAP_LIMIT))
        for i, o in enumerate(objs):
            t, x, y = int(o["t"]), int(o["x"]), int(o["y"])
            w, h = int(o["w"]), int(o["h"])
            if t < 0 or t > TILE_INDEX_LIMIT:
                bad.append("объект #%d: tile %d вне 0…%d (flags = tile & 0x7F)"
                           % (i, t, TILE_INDEX_LIMIT))
            elif not 0 < w <= 255 or not 0 < h <= 255:
                bad.append("объект #%d: w×h = %d×%d — и то и другое 1…255"
                           % (i, w, h))
            elif x < 0 or y < 0 or x + w > cols or y + h > rows:
                bad.append("объект #%d (tile %d) %d×%d в (%d,%d) лезет за карту "
                           "%d×%d — обрежь карту или двигай объект"
                           % (i, t, w, h, x, y, cols, rows))
            if bad:
                break                          # одна строка понятнее списка
        est = self._budget(cols, rows, n_objs)
        if est is not None and est > IMAGE_LIMIT:
            bad.append("образ ≈ %d Б > %d Б (0x0100…0x7FFF): tile_win жрёт %d Б "
                       "ОЗУ. Меньше строк H или меньше объектов." % (
                           est, IMAGE_LIMIT, WIN_RAM_PER_ROW * rows))
        return bad

    def _update_budget(self):
        est = self._budget(self.cols, self.rows, len(self.objects))
        self.budget_lbl.config(text=("смета образа ≈ %d / %d Б" % (est, IMAGE_LIMIT))
                               if est else "смета: нет mario-8c.map/.rom")

    # ---- UI ---------------------------------------------------------------
    def _build_ui(self):
        bar = ttk.Frame(self.root, padding=6)
        bar.pack(side=tk.TOP, fill=tk.X)
        ttk.Checkbutton(bar, text="Показать твёрдость",
                        variable=self.show_overlay,
                        command=self.render_all).pack(side=tk.LEFT)
        ttk.Checkbutton(bar, text="Подсветить выбранный тайл",
                        variable=self.hl_var,
                        command=self.render_all).pack(side=tk.LEFT, padx=(12, 0))
        ttk.Checkbutton(bar, text="Сетка тайлов",
                        variable=self.grid_var,
                        command=self.render_all).pack(side=tk.LEFT, padx=(12, 0))
        ttk.Label(bar, text="  Масштаб:").pack(side=tk.LEFT)
        self.zoom_var = tk.StringVar(value="12")
        z = ttk.OptionMenu(bar, self.zoom_var, "12", "8", "12", "16", "24",
                           command=self._on_zoom)
        z.config(width=5)
        z.pack(side=tk.LEFT)
        ttk.Label(bar, text="  Режим:").pack(side=tk.LEFT)
        ttk.Radiobutton(bar, text="Объекты", value="object", variable=self.mode,
                        command=self._on_mode).pack(side=tk.LEFT)
        ttk.Radiobutton(bar, text="Тайлы", value="tile", variable=self.mode,
                        command=self._on_mode).pack(side=tk.LEFT)
        ttk.Button(bar, text="Сохранить", command=self.save).pack(side=tk.LEFT, padx=(14, 4))
        self.status = ttk.Label(bar, text="готово")
        self.status.pack(side=tk.LEFT, padx=8)

        # вторая панель: ресайз карты + якорь содержимого
        bar2 = ttk.Frame(self.root, padding=(6, 0, 6, 6))
        bar2.pack(side=tk.TOP, fill=tk.X)
        ttk.Label(bar2, text="Размер карты:  W").pack(side=tk.LEFT)
        self.w_var = tk.IntVar(value=self.cols)
        ttk.Spinbox(bar2, from_=MIN_COLS, to=MAX_COLS, width=5,
                    textvariable=self.w_var).pack(side=tk.LEFT)
        ttk.Label(bar2, text="  H").pack(side=tk.LEFT)
        self.h_var = tk.IntVar(value=self.rows)
        ttk.Spinbox(bar2, from_=MIN_ROWS, to=MAX_ROWS, width=5,
                    textvariable=self.h_var).pack(side=tk.LEFT)
        ttk.Label(bar2, text="   прижать к:").pack(side=tk.LEFT, padx=(10, 0))
        self.anchor_v = tk.StringVar(value="низу")
        ttk.OptionMenu(bar2, self.anchor_v, "низу", "верху", "низу").pack(side=tk.LEFT)
        self.anchor_h = tk.StringVar(value="левому")
        ttk.OptionMenu(bar2, self.anchor_h, "левому", "левому",
                       "правому").pack(side=tk.LEFT)
        ttk.Button(bar2, text="Изменить размер",
                   command=self._on_resize).pack(side=tk.LEFT, padx=(10, 0))
        self.budget_lbl = ttk.Label(bar2, foreground="#777")
        self.budget_lbl.pack(side=tk.RIGHT, padx=6)
        ttk.Label(bar2, foreground="#777",
                  text="(новые поля — небо; %d..%d × %d..%d)" % (
                      MIN_COLS, MAX_COLS, MIN_ROWS, MAX_ROWS)).pack(side=tk.LEFT,
                                                                    padx=6)

        # третья панель: параметры штампа (префаба)
        bar3 = ttk.Frame(self.root, padding=(6, 0, 6, 6))
        bar3.pack(side=tk.TOP, fill=tk.X)
        ttk.Label(bar3, text="Штамп:").pack(side=tk.LEFT)
        self.stamp_lbl = ttk.Label(bar3, text="— (тайл-кисть)", width=22,
                                   foreground="#4ec9b0")
        self.stamp_lbl.pack(side=tk.LEFT)
        self.rep_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(bar3, text="повторять сеткой по области",
                        variable=self.rep_var,
                        command=self._on_stamp_opts).pack(side=tk.LEFT, padx=(8, 0))
        ttk.Label(bar3, text="  шаг X").pack(side=tk.LEFT)
        self.stepx_var = tk.IntVar(value=3)
        self.stepx_box = ttk.Spinbox(bar3, from_=1, to=64, width=4,
                                      textvariable=self.stepx_var,
                                      command=self._on_stamp_opts)
        self.stepx_box.pack(side=tk.LEFT)
        ttk.Label(bar3, text="  шаг Y").pack(side=tk.LEFT)
        self.stepy_var = tk.IntVar(value=0)
        self.stepy_box = ttk.Spinbox(bar3, from_=0, to=64, width=4,
                                      textvariable=self.stepy_var,
                                      command=self._on_stamp_opts)
        self.stepy_box.pack(side=tk.LEFT)
        ttk.Label(bar3, foreground="#777",
                  text="(шаг Y = 0 → только ряд; ЛКМ по пустой клетке — "
                       "протянуть область/размер)").pack(side=tk.LEFT, padx=6)
        ttk.Button(bar3, text="снять штамп",
                   command=self.clear_stamp).pack(side=tk.LEFT, padx=(8, 0))

        # легенда
        leg = ttk.Frame(self.root, padding=(8, 0, 8, 4))
        leg.pack(side=tk.TOP, fill=tk.X)
        ttk.Label(leg, text="проходной: без заливки    "
                           "сплошной (wall): красная заливка    "
                           "платформа: синяя заливка    "
                           "жёлтая рамка: текущий тайл").pack(side=tk.LEFT)

        body = ttk.Frame(self.root)
        body.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        # палитра слева: сверху тайлы, снизу префабы (штампы)
        left = ttk.Frame(body)
        left.pack(side=tk.LEFT, fill=tk.Y)
        pw = PAL_COLS * (PAL_THUMB + PAL_GAP) + PAL_GAP + 14
        pw = max(pw, PF_COL_W)
        ttk.Label(left, text="1) Клик по тайлу — выбрать кисть").pack(anchor=tk.W)
        palfr = ttk.Frame(left)
        palfr.pack(side=tk.TOP, fill=tk.X)
        self.pal = tk.Canvas(palfr, width=pw, height=300, bg="#242424",
                             highlightthickness=0)
        self.pal.pack(side=tk.LEFT, fill=tk.Y)
        psb = ttk.Scrollbar(palfr, orient=tk.VERTICAL, command=self.pal.yview)
        psb.pack(side=tk.LEFT, fill=tk.Y)
        self.pal.config(yscrollcommand=psb.set)
        self._build_palette()

        ttk.Label(left, text="2) Клик по префабу — штамп (группа тайлов)").pack(
            anchor=tk.W, pady=(6, 0))
        pffr = ttk.Frame(left)
        pffr.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        self.pfcv = tk.Canvas(pffr, width=pw, height=300, bg="#1e1e1e",
                              highlightthickness=0)
        self.pfcv.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        pfsb = ttk.Scrollbar(pffr, orient=tk.VERTICAL, command=self.pfcv.yview)
        pfsb.pack(side=tk.LEFT, fill=tk.Y)
        self.pfcv.config(yscrollcommand=pfsb.set)
        self._build_prefab_panel()

        # поле по центру (grid: полотно в (0,0), скроллбары у его краёв)
        mid = ttk.Frame(body)
        mid.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        mid.columnconfigure(0, weight=1)
        mid.rowconfigure(0, weight=1)
        self.canvas = tk.Canvas(mid, bg="#0d1a2b", highlightthickness=1,
                                highlightbackground="#444")
        self.vsb = ttk.Scrollbar(mid, orient=tk.VERTICAL, command=self.canvas.yview)
        self.hsb = ttk.Scrollbar(mid, orient=tk.HORIZONTAL, command=self.canvas.xview)
        self.canvas.config(yscrollcommand=self.vsb.set, xscrollcommand=self.hsb.set)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.vsb.grid(row=0, column=1, sticky="ns")
        self.hsb.grid(row=1, column=0, sticky="ew")
        self.canvas.bind("<Button-1>", self._on_click)
        self.canvas.bind("<B1-Motion>", self._on_drag)
        self.canvas.bind("<Button-3>", self._on_map_menu)
        self.canvas.bind("<MouseWheel>", self._on_wheel)
        self.canvas.bind("<Button-4>", lambda e: self._on_wheel(e, -1))
        self.canvas.bind("<Button-5>", lambda e: self._on_wheel(e, 1))
        self.canvas.bind("<ButtonRelease-1>", self._on_release)
        self.root.bind("<Delete>", self._del_selected)
        self.root.bind("<BackSpace>", self._del_selected)
        self.root.bind("<Escape>", self.clear_stamp)   # снять штамп

        # свойства справа
        right = ttk.Frame(body, padding=8)
        right.pack(side=tk.LEFT, fill=tk.Y)
        ttk.Label(right, text="3) Свойства выбранного тайла").pack(anchor=tk.W)
        self.prev = tk.Canvas(right, width=96, height=96, bg="#111",
                              highlightthickness=1, highlightbackground="#3a3a3a")
        self.prev.pack(pady=6)
        self.name_lbl = ttk.Label(right, text="—")
        self.name_lbl.pack()
        self.v_wall = tk.BooleanVar()
        self.v_plat = tk.BooleanVar()
        self.v_tran = tk.BooleanVar()
        for txt, var in (("сплошной (wall)", self.v_wall),
                         ("платформа (platform)", self.v_plat),
                         ("прозрачный (пусто)", self.v_tran)):
            ttk.Checkbutton(right, text=txt, variable=var,
                            command=self._edit_prop).pack(anchor=tk.W, pady=2)
        ttk.Label(right, foreground="#777", justify=tk.LEFT, text=(
            "Объекты: ЛКМ по пустому + тянуть —\n"
            "создать; по объекту — выделить/двинуть\n"
            "всю группу; Del — удалить группу.\n"
            "ПКМ — кисть/твёрдость/разгруппировать.\n\n"
            "Штамп выбран → ЛКМ всегда ставит его\n"
            "(тянется только stretch-оси; галочка\n"
            "«повторять» — сетка копий по области).\n"
            "Esc / «снять штамп» — вернуть перенос\n"
            "групп и обычную резинку.\n\n"
            "Тайлы: ЛКМ рисует кистью.\n"
            "После «Сохранить» — make.")).pack(anchor=tk.W, pady=(12, 0))

    def _build_palette(self):
        c = self.pal
        c.delete("all")
        self._pal_photos = []
        self._pal_sel = None
        for i, orig in enumerate(self.tile_orig):
            r, col = divmod(i, PAL_COLS)
            x = PAL_GAP + col * (PAL_THUMB + PAL_GAP)
            y = PAL_GAP + r * (PAL_THUMB + PAL_GAP)
            th = orig.resize((PAL_THUMB, PAL_THUMB), Image.NEAREST)
            photo = ImageTk.PhotoImage(th)
            self._pal_photos.append(photo)
            im = c.create_image(x, y, anchor=tk.NW, image=photo)
            c.tag_bind(im, "<Button-1>", lambda e, idx=i: self.select_tile(idx))
        c.configure(scrollregion=(0, 0, 0, PAL_GAP * 2 + (len(self.tile_orig) // PAL_COLS + 1)
                                  * (PAL_THUMB + PAL_GAP)))

    # ---- панель префабов --------------------------------------------------
    def _grid_image(self, cells, scale, alpha=255):
        """Сетка тайлов -> RGBA-картинка (0 = прозрачно). Один и тот же код для
        превью в панели (scale=PF_THUMB) и призрака на карте (scale=self.cell)."""
        w, h = len(cells[0]) * scale, len(cells) * scale
        im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        for r, row in enumerate(cells):
            for c, t in enumerate(row):
                if not t:
                    continue
                tile = self.scaled[t].convert("RGBA") if scale == self.cell \
                    else self.tile_orig[t].resize((scale, scale), Image.NEAREST)\
                                                      .convert("RGBA")
                if alpha < 255:
                    a = tile.getchannel("A").point(lambda v, a=alpha: v * a // 255)
                    tile.putalpha(a)
                im.paste(tile, (c * scale, r * scale), tile)
        return im

    def _build_prefab_panel(self):
        c = self.pfcv
        c.delete("all")
        self._pf_photos = []
        self._pf_rows = []
        self._pf_sel = None
        y = 6
        for i, pf in enumerate(self.prefabs):
            cells = stamp_cells(pf, len(pf["grid"][0]), len(pf["grid"]))
            im = self._grid_image(cells, PF_THUMB)
            photo = ImageTk.PhotoImage(im)
            self._pf_photos.append(photo)
            st = (("↔" if pf.get("stretch_x") else "")
                  + ("↕" if pf.get("stretch_y") else ""))
            line = "%s  %d×%d" % (pf["name"], len(cells[0]), len(cells))
            if st:
                line += "  тянется " + st
            c.create_text(6, y, anchor=tk.NW, text=line, fill="#ddd",
                          font=("DejaVu Sans", 9))
            c.create_image(6, y + 16, anchor=tk.NW, image=photo)
            row_h = 16 + im.height
            hit = c.create_rectangle(2, y - 3, PF_COL_W, y + row_h + 3,
                                     fill="", outline="")
            c.tag_bind(hit, "<Button-1>", lambda e, idx=i: self.select_stamp(idx))
            self._pf_rows.append((y - 3, y + row_h + 3))
            y += row_h + 10
        c.configure(scrollregion=(0, 0, PF_COL_W, y))
        self._update_prefab_sel()

    def _update_prefab_sel(self):
        c = self.pfcv
        if self._pf_sel:
            c.delete(self._pf_sel)
        self._pf_sel = None
        if self.stamp is None or self.stamp not in self.prefabs:
            return
        i = self.prefabs.index(self.stamp)
        y0, y1 = self._pf_rows[i]
        self._pf_sel = c.create_rectangle(2, y0, PF_COL_W, y1,
                                          outline="#4ec9b0", width=2)
        total = c.cget("scrollregion").split()[-1]
        if total and int(total) > 0:
            c.yview_moveto(min(1.0, max(0.0, (y0 - c.winfo_height() / 2)
                                        / int(total))))

    def select_stamp(self, i):
        """Выбрать штамп: он же и инструмент — ЛКМ на карте ставит префаб."""
        self.stamp = self.prefabs[i] if i is not None and i >= 0 else None
        self.sel_obj = None
        self.sel_grp = None
        self.stamp_lbl.config(text=(self.stamp["name"] if self.stamp
                                    else "— (тайл-кисть)"))
        self._update_prefab_sel()
        self._sync_step_state()
        self.render_all()

    def clear_stamp(self, _=None, silent=False):
        self.stamp = None
        self.stamp_lbl.config(text="— (тайл-кисть)")
        self._update_prefab_sel()
        self._sync_step_state()
        if not silent:
            self.render_all()

    def _on_stamp_opts(self):
        """Галочка/шаги меняют только будущую постановку — перерисовать призрак."""
        self._sync_step_state()
        self._clear_preview()
        self._draw_preview()

    def _sync_step_state(self):
        on = bool(self.stamp) and self.rep_var.get()
        state = tk.NORMAL if on else tk.DISABLED
        self.stepx_box.config(state=state)
        self.stepy_box.config(state=tk.NORMAL if on else tk.DISABLED)
        if not self.rep_var.get():
            self._clear_preview()
            self._draw_preview()

    # ---- рендер поля ------------------------------------------------------
    def _rebuild_scaled(self):
        self.scaled = [im.resize((self.cell, self.cell), Image.NEAREST)
                       for im in self.tile_orig]

    def _draw_cell(self, x0, y0, ti):
        """Клетка в self.screen (PIL): тайл + полупрозрачная заливка твёрдости
        (красная — стена, синяя — платформа) + жёлтая рамка текущего тайла."""
        self.screen.paste(self.scaled[ti], (x0, y0))
        if self.show_overlay.get():
            fc = frame_color(self.tiles["tiles"][ti])
            if fc:
                box = (x0, y0, x0 + self.cell, y0 + self.cell)
                region = self.screen.crop(box)
                tint = Image.new("RGB", (self.cell, self.cell), fc)
                self.screen.paste(Image.blend(region, tint, OVERLAY_ALPHA), (x0, y0))
        if self.hl_var.get() and ti == self.selected:
            ImageDraw.Draw(self.screen).rectangle(
                [x0, y0, x0 + self.cell - 1, y0 + self.cell - 1],
                outline=HL_COLOR, width=2)

    def render_all(self):
        W, H = self.cols * self.cell, self.rows * self.cell
        self.screen = Image.new("RGB", (W, H), SKY)
        for col in range(self.cols):
            base = col * self.rows
            for row in range(self.rows):
                self._draw_cell(col * self.cell, row * self.cell, self.grid[base + row])
        self.photo = ImageTk.PhotoImage(self._compose())
        c = self.canvas
        c.delete("all")
        c.create_image(0, 0, anchor=tk.NW, image=self.photo)
        c.configure(scrollregion=(0, 0, W, H))
        self._update_budget()
        self._render_preview()

    def _compose(self):
        """Финальная картинка = базовый экран + сетка границ тайлов (1px серый,
        50% прозрачности) + (в режиме объектов) рамки объектов поверх. Сетка
        НЕ пишется в self.screen, чтобы дорисовка одной клетки не стирала
        линии; толщина 1px при любом масштабе."""
        need_grid = self.grid_var.get()
        need_obj = self.mode.get() == "object"
        if not need_grid and not need_obj:
            return self.screen
        W, H = self.screen.size
        ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(ov)
        if need_grid:
            for x in range(0, W, self.cell):
                d.line([(x, 0), (x, H)], fill=GRID_LINE, width=1)
            for y in range(0, H, self.cell):
                d.line([(0, y), (W, y)], fill=GRID_LINE, width=1)
        if need_obj:
            grp = self.sel_grp
            for i, o in enumerate(self.objects):
                box = [o["x"] * self.cell, o["y"] * self.cell,
                       (o["x"] + o["w"]) * self.cell - 1,
                       (o["y"] + o["h"]) * self.cell - 1]
                sel = (i == self.sel_obj
                       or (grp is not None and o.get("g") == grp))
                color = OBJ_SEL if sel else OBJ_LINE
                d.rectangle(box, outline=color + (255,), width=2)
            if grp is not None:                    # контур всей группы
                mem = [i for i, o in enumerate(self.objects)
                       if o.get("g") == grp]
                if len(mem) > 1:
                    x, y, w, h = self._group_bbox(mem)
                    d.rectangle([x * self.cell - 1, y * self.cell - 1,
                                 (x + w) * self.cell, (y + h) * self.cell],
                                outline=OBJ_SEL + (120,), width=1)
        return Image.alpha_composite(self.screen.convert("RGBA"), ov).convert("RGB")

    def _repaint_cell(self, col, row):
        ti = self.grid[col * self.rows + row]
        self._draw_cell(col * self.cell, row * self.cell, ti)
        # ImageTk.PhotoImage.paste принимает только полный кадр (без box)
        self.photo.paste(self._compose())

    # ---- выбор/свойства ---------------------------------------------------
    def select_tile(self, i):
        """Выбрать тайл-кисть: подсветить в палитре, показать свойства,
        и (если вкл. подсветка) перерисовать карту с новой рамкой. Выбор
        тайла снимает штамп — это взаимоисключающие инструменты."""
        self.selected = i
        self.clear_stamp(silent=True)
        self._update_palette_sel()
        self._sync_panel()
        if self.hl_var.get():
            self.render_all()

    def _update_palette_sel(self):
        c = self.pal
        if self._pal_sel:
            c.delete(self._pal_sel)
        r, col = divmod(self.selected, PAL_COLS)
        x = PAL_GAP + col * (PAL_THUMB + PAL_GAP)
        y = PAL_GAP + r * (PAL_THUMB + PAL_GAP)
        self._pal_sel = c.create_rectangle(
            x - 2, y - 2, x + PAL_THUMB + 2, y + PAL_THUMB + 2,
            outline="#4ec9b0", width=2)
        total = c.cget("scrollregion").split()[-1]        # чтобы тайл был виден
        if total and int(total) > 0:
            c.yview_moveto(min(1.0, max(0.0, (y - c.winfo_height() / 2) / int(total))))

    def _sync_panel(self):
        t = self.tiles["tiles"][self.selected]
        self.v_wall.set(bool(t.get("wall")))
        self.v_plat.set(bool(t.get("platform")))
        self.v_tran.set(bool(t.get("transparent")))
        self.name_lbl.config(
            text=f"tile {self.selected} — {os.path.basename(t['file'])}")
        self._render_preview()

    def _render_preview(self):
        p = self.prev
        p.delete("all")
        th = self.tile_orig[self.selected].resize((96, 96), Image.NEAREST)
        self._prev_photo = ImageTk.PhotoImage(th)
        p.create_image(0, 0, anchor=tk.NW, image=self._prev_photo)

    def _apply_prop(self, t, mode):
        """mode: 'wall' | 'platform' | 'pass' — выставить биты твёрдости."""
        t["transparent"] = False
        if mode == "wall":
            t["wall"] = True; t["platform"] = False
        elif mode == "platform":
            t["wall"] = False; t["platform"] = True
        else:
            t["wall"] = False; t["platform"] = False

    def _edit_prop(self):
        """Галочки панели свойств для выбранного тайла."""
        t = self.tiles["tiles"][self.selected]
        t["wall"] = self.v_wall.get()
        t["platform"] = self.v_plat.get()
        t["transparent"] = self.v_tran.get()
        if t["transparent"]:                       # пустой тайл не может быть твёрдым
            t["wall"] = t["platform"] = False
            self.v_wall.set(False)
            self.v_plat.set(False)
        self._build_palette()
        self._update_palette_sel()
        self._render_preview()
        self.render_all()                          # оверлей во всех клетках
        self.dirty = True
        self._set_status("не сохранено")

    # ---- мышь на поле -----------------------------------------------------
    def _cell_at(self, e):
        cx = self.canvas.canvasx(e.x)
        cy = self.canvas.canvasy(e.y)
        col = int(cx // self.cell)
        row = int(cy // self.cell)
        if 0 <= col < self.cols and 0 <= row < self.rows:
            return col, row
        return None

    def _paint(self, e):
        c = self._cell_at(e)
        if not c:
            return
        col, row = c
        idx = col * self.rows + row
        if self.grid[idx] == self.selected:
            return
        self.grid[idx] = self.selected
        self._repaint_cell(col, row)
        self._set_status("не сохранено")
        self.dirty = True

    def _on_click(self, e):
        if self.mode.get() == "tile":
            self._paint(e)
            return
        c = self._cell_at(e)
        if not c:
            return
        col, row = c
        hit = self._obj_at(col, row)
        if self.stamp is not None:                 # штамп — кисть, важность выше:
            self.sel_obj = None                    # тянем размер/область даже поверх
            self.sel_grp = None                    # уже стоящих объектов
            self.drag = {"kind": "stamp", "x0": col, "y0": row,
                         "x1": col, "y1": row}
        elif hit is not None:                      # по объекту — тянем ГРУППУ
            self.sel_obj = hit
            self.sel_grp = self.objects[hit].get("g")
            idxs = sorted(self._group_idx(hit))
            self.drag = {"kind": "move", "index": hit, "idxs": idxs,
                         "grp": self.sel_grp if self.sel_grp is not None else "—",
                         "orig": [(self.objects[i]["x"], self.objects[i]["y"])
                                  for i in idxs],
                         "x0": col, "y0": row, "cx": col, "cy": row}
        else:                                        # по пустому — резинка-создание
            self.sel_obj = None
            self.sel_grp = None
            self.drag = {"kind": "create", "t": self.selected,
                         "x0": col, "y0": row, "x1": col, "y1": row}
        self._clear_preview()
        self._draw_preview()
        self.render_all()                          # показать рамку выделения

    def _on_drag(self, e):
        if self.mode.get() == "tile":
            self._paint(e)
            return
        if not self.drag:
            return
        c = self._cell_at(e)
        if not c:
            return
        col, row = c
        d = self.drag
        if d["kind"] in ("create", "stamp"):
            d["x1"], d["y1"] = col, row
        else:
            d["cx"], d["cy"] = col, row
        self._clear_preview()                      # двигается только контур,
        self._draw_preview()                       # печь — на отпускании

    def _on_release(self, e):
        if self.mode.get() != "object" or not self.drag:
            self.drag = None
            return
        d = self.drag
        self.drag = None
        self._clear_preview()
        c = self._cell_at(e)
        if d["kind"] == "stamp":
            self._place_stamp(d, c)
        elif d["kind"] == "create":
            x1, y1 = d["x1"], d["y1"]
            if c:
                x1, y1 = c
            x, y, w, h = self._norm_rect(d["x0"], d["y0"], x1, y1)
            if d["t"] != 0:                        # «небо» не заводим
                self.objects.append({"t": d["t"], "x": x, "y": y, "w": w, "h": h})
                self.sel_obj = len(self.objects) - 1
                self.sel_grp = None
        elif c:                                    # завершаем перемещение группы
            mem = d["idxs"]
            lo_x = min(x for x, _ in d["orig"])
            lo_y = min(y for _, y in d["orig"])
            hi_x = max(self.objects[i]["x"] + self.objects[i]["w"] - 1 for i in mem)
            hi_y = max(self.objects[i]["y"] + self.objects[i]["h"] - 1 for i in mem)
            dx = max(-lo_x, min(c[0] - d["x0"], self.cols - 1 - hi_x))
            dy = max(-lo_y, min(c[1] - d["y0"], self.rows - 1 - hi_y))
            for k, i in enumerate(mem):
                self.objects[i]["x"] = d["orig"][k][0] + dx
                self.objects[i]["y"] = d["orig"][k][1] + dy
        self._recompute_grid()
        self.dirty = True
        self._set_status("не сохранено")
        self.render_all()

    def _place_stamp(self, d, c):
        """Отпускание мыши над пустым с выбранным штампом: одна копия заданного
        размера ИЛИ сетка копий по области (если «повторять»). Все копии одного
        жеста получают общий номер группы — двигаются и удаляются вместе,
        распадаются через ПКМ «разгруппировать»."""
        pf = self.stamp
        x1, y1 = (c if c else (d["x1"], d["y1"]))
        x0, y0 = d["x0"], d["y0"]
        gid = self._next_gid()
        pts, (w, h) = self._stamp_layout(x0, y0, x1, y1)
        added = 0
        for (px, py) in pts:
            px = max(0, min(px, self.cols - w))
            py = max(0, min(py, self.rows - h))
            objs = stamp_objects(pf, px, py, w, h, gid)
            self.objects.extend(objs)
            added += len(objs)
        if added:
            self.sel_obj = len(self.objects) - 1
            self.sel_grp = gid
            self._set_status("%s: +%d объект(ов) группой %d — не сохранено"
                             % (pf["name"], added, gid))

    def _del_selected(self, _=None):
        if self.mode.get() != "object" or self.sel_obj is None:
            return
        mem = self._group_idx(self.sel_obj)
        self.objects = [o for i, o in enumerate(self.objects) if i not in mem]
        self.sel_obj = None
        self.sel_grp = None
        self._recompute_grid()
        self.dirty = True
        self._set_status("не сохранено")
        self.render_all()

    # ---- объектные хелперы ------------------------------------------------
    def _obj_at(self, col, row):
        """Индекс верхнего объекта на клетке (обратный обход: последние сверху)."""
        for i in range(len(self.objects) - 1, -1, -1):
            o = self.objects[i]
            if o["x"] <= col < o["x"] + o["w"] and o["y"] <= row < o["y"] + o["h"]:
                return i
        return None

    def _group_idx(self, i):
        """Множество индексов всех объектов группы, куда входит объект i
        (объект без поля g — группа из одного себя)."""
        g = self.objects[i].get("g")
        if g is None:
            return {i}
        return {j for j, o in enumerate(self.objects) if o.get("g") == g}

    def _group_bbox(self, idxs):
        """Ограничивающий прямоугольник группы в тайлах: (x, y, w, h)."""
        xs = [self.objects[i]["x"] for i in idxs]
        ys = [self.objects[i]["y"] for i in idxs]
        xe = [self.objects[i]["x"] + self.objects[i]["w"] for i in idxs]
        ye = [self.objects[i]["y"] + self.objects[i]["h"] for i in idxs]
        return (min(xs), min(ys), max(xe) - min(xs), max(ye) - min(ys))

    def _ungroup(self, i):
        """Разбить группу: объекты остаются на местах, но двигаются/удаляются
        поодиночке (полезно после «повторять сеткой», когда надо подвинуть одну
        монету)."""
        g = self.objects[i].get("g")
        if g is None:
            return
        for o in self.objects:
            if o.get("g") == g:
                del o["g"]
        self.sel_grp = None
        self.dirty = True
        self._set_status("группа %d разбита — не сохранено" % g)
        self.render_all()

    def _norm_rect(self, x0, y0, x1, y1):
        """Углы резинки -> (x, y, w, h) в тайлах (x=колонка, y=строка)."""
        return (min(x0, x1), min(y0, y1), abs(x1 - x0) + 1, abs(y1 - y0) + 1)

    def _recompute_grid(self):
        """grid производен от объектов — переразвернуть для рендера/коллизий."""
        self.grid = list(G.expand_objects(self.cols, self.rows, self.objects))

    def _draw_preview(self):
        """Резинка над картой: контур создаваемого короба, контур переносимой
        группы или ПОЛУПРОЗРАЧНЫЙ призрак штампа (живьём видно, как растянулась
        труба/куст и куда легли копии сетки)."""
        d = self.drag
        if not d:
            return
        if d["kind"] == "stamp" and self.stamp:
            self._draw_stamp_preview(d)
            return
        if d["kind"] == "create":
            boxes = [self._norm_rect(d["x0"], d["y0"], d["x1"], d["y1"])]
            x, y, w, h = boxes[0]
            self._set_status("кисть tile %d: %d×%d в (%d,%d)"
                             % (d["t"], w, h, x, y))
        else:                                      # перенос группы
            mem = d["idxs"]
            lo_x = min(x for x, _ in d["orig"])
            lo_y = min(y for _, y in d["orig"])
            hi_x = max(self.objects[i]["x"] + self.objects[i]["w"] - 1 for i in mem)
            hi_y = max(self.objects[i]["y"] + self.objects[i]["h"] - 1 for i in mem)
            dx = max(-lo_x, min(d["cx"] - d["x0"], self.cols - 1 - hi_x))
            dy = max(-lo_y, min(d["cy"] - d["y0"], self.rows - 1 - hi_y))
            boxes = [(self.objects[i]["x"] + dx, self.objects[i]["y"] + dy,
                      self.objects[i]["w"], self.objects[i]["h"]) for i in mem]
            self._set_status("группа %s: сдвиг %+d,%+d (%d rect)"
                             % (d.get("grp"), dx, dy, len(mem)))
        for (x, y, w, h) in boxes:
            self.canvas.create_rectangle(
                x * self.cell, y * self.cell,
                (x + w) * self.cell, (y + h) * self.cell,
                outline="#%02x%02x%02x" % OBJ_SEL, width=2, tags=("preview",))

    def _stamp_layout(self, x0, y0, x1, y1):
        """Жест мыши -> (точки вставки, размер копии): одна копия заданного
        размера ИЛИ сетка копий нативного. Общий для призрака и постановки —
        иначе предпросмотр будет расходиться с результатом."""
        pf = self.stamp
        if self.rep_var.get():
            sx = _spin(self.stepx_var, 3, 1, 64)
            sy = _spin(self.stepy_var, 0, 0, 64)
            return stamp_points(pf, x0, y0, x1, y1, sx, sy,
                                (self.cols, self.rows))
        return ([(min(x0, x1), min(y0, y1))],
                stamp_size(pf, abs(x1 - x0) + 1, abs(y1 - y0) + 1))

    def _draw_stamp_preview(self, d):
        pf = self.stamp
        x0, y0, x1, y1 = d["x0"], d["y0"], d["x1"], d["y1"]
        pts, (w, h) = self._stamp_layout(x0, y0, x1, y1)
        cells = stamp_cells(pf, w, h)
        im = self._grid_image(cells, self.cell, STAMP_ALPHA)
        photo = ImageTk.PhotoImage(im)
        self._ghosts.append(photo)                 # держать ссылку до сброса
        for (px, py) in pts:
            px = max(0, min(px, self.cols - w))
            py = max(0, min(py, self.rows - h))
            self.canvas.create_image(px * self.cell, py * self.cell,
                                     anchor=tk.NW, image=photo, tags=("preview",))
            self.canvas.create_rectangle(
                px * self.cell, py * self.cell,
                (px + w) * self.cell, (py + h) * self.cell,
                outline="#%02x%02x%02x" % OBJ_SEL, width=1, tags=("preview",))
        self._set_status("%s %d×%d → %d копий" % (pf["name"], w, h, len(pts)))

    def _clear_preview(self):
        self.canvas.delete("preview")
        self._ghosts = []

    def _on_map_menu(self, e):
        """ПКМ на карте: взять тайл под курсором в кисть + меню быстрых действий."""
        c = self._cell_at(e)
        if not c:
            return
        ti = self.grid[c[0] * self.rows + c[1]]
        self.select_tile(ti)
        hit = self._obj_at(c[0], c[1])
        g = self.objects[hit].get("g") if hit is not None else None
        m = tk.Menu(self.root, tearoff=0)
        m.add_command(label=f"Кисть: tile {ti}", state="disabled")
        m.add_separator()
        m.add_command(label="■ сплошной (стена)",
                      command=lambda: self._quick_prop(ti, "wall"))
        m.add_command(label="▬ платформа (опора)",
                      command=lambda: self._quick_prop(ti, "platform"))
        m.add_command(label="□ проходной",
                      command=lambda: self._quick_prop(ti, "pass"))
        if g is not None:
            m.add_separator()
            m.add_command(label="⌫ разгруппировать (группа %d)" % g,
                          command=lambda: self._ungroup(hit))
            m.add_command(label="✂ удалить группу",
                          command=lambda: self._del_group(hit))
        try:
            m.tk_popup(e.x_root, e.y_root)
        finally:
            m.grab_release()

    def _del_group(self, i):
        """Удалить группу из контекстного меню (Del требует предварительного
        клика, а здесь — сразу по тому, под чем курсор)."""
        mem = self._group_idx(i)
        self.objects = [o for j, o in enumerate(self.objects) if j not in mem]
        self.sel_obj = None
        self.sel_grp = None
        self._recompute_grid()
        self.dirty = True
        self._set_status("удалено %d объект(ов) — не сохранено" % len(mem))
        self.render_all()

    def _quick_prop(self, ti, mode):
        """Быстрая смена твёрдости тайла из контекстного меню."""
        self._apply_prop(self.tiles["tiles"][ti], mode)
        self.selected = ti
        self._build_palette()
        self._update_palette_sel()
        self._sync_panel()
        self.render_all()
        self.dirty = True
        self._set_status("не сохранено")

    def _on_wheel(self, e, delta=None):
        if delta is None:                          # Windows/mac
            delta = -1 if e.delta > 0 else 1
        self.canvas.yview_scroll(delta * 3, "units")

    def _on_zoom(self, _=None):
        self.cell = int(self.zoom_var.get())
        self._rebuild_scaled()
        self.render_all()

    def _on_mode(self):
        """Переключатель режимов. grid всегда производен: в «объекты» —
        пересегментируем тайловые правки; в «тайлы» — разворачиваем объекты
        в grid (фолбэк-рисование по-тайлово). Штамп и выделение группы
        в тайловом режиме бессмысленны — снимаем."""
        self.sel_obj = None
        self.sel_grp = None
        self.drag = None
        self._clear_preview()
        self.clear_stamp(silent=True)
        if self.mode.get() == "object":
            self.objects = cover_rectangles(self.cols, self.rows, self.grid)
        else:
            self._recompute_grid()
        self.render_all()

    # ---- ресайз карты -----------------------------------------------------
    def _on_resize(self):
        try:
            nc = int(self.w_var.get())
            nr = int(self.h_var.get())
        except (ValueError, tk.TclError):
            self._set_status("некорректный размер")
            nc, nr = self.cols, self.rows
            self.w_var.set(nc)
            self.h_var.set(nr)
            return
        # габариты и смета проверяем ДО обрезки: сами объекты сверяем позже
        # (они сдвинутся якорем), но в смету их число берём текущее
        bad = self._limits(nc, nr, [], n_objs=len(self.objects))
        if bad:
            messagebox.showerror("Размер не пройдёт сборку",
                                 "\n".join(bad)
                                 + "\n\nОставил %d×%d." % (self.cols, self.rows))
            self.w_var.set(self.cols)
            self.h_var.set(self.rows)
            return
        if nc == self.cols and nr == self.rows:
            self._set_status("размер не изменился")
            return
        r_off = (nr - self.rows) if self.anchor_v.get() == "низу" else 0
        c_off = (nc - self.cols) if self.anchor_h.get() == "правому" else 0
        cut = [o for o in self.objects
               if not (0 <= o["x"] + c_off and o["x"] + c_off + o["w"] <= nc
                       and 0 <= o["y"] + r_off
                       and o["y"] + r_off + o["h"] <= nr)]
        if cut and not messagebox.askyesno(
                "Обрезка", "За новые края выходят %d объект(ов) — при уменьшении "
                "они будут потеряны.\nОбрезать?" % len(cut), icon="warning"):
            self.w_var.set(self.cols)
            self.h_var.set(self.rows)
            return
        self._resize(nc, nr, self.anchor_v.get(), self.anchor_h.get())
        self.w_var.set(nc)
        self.h_var.set(nr)
        self._set_status(f"карта {nc}×{nr} — не забудь Сохранить")

    def _resize(self, new_cols, new_rows, v_anchor, h_anchor):
        """Изменить размер тайлкарты, прижав текущее содержимое к выбранной
        стороне. Пустые новые поля = тайл 0 (небо). При уменьшении — обрезка
        по противоположному краю.

        Хранилище col-major: grid[col*rows + row]; при смене rows меняется
        смысл индекса, поэтому перекладываем через 2D-промежуточный вид."""
        old_cols, old_rows = self.cols, self.rows
        old = self.grid
        new = [0] * (new_cols * new_rows)
        r_off = (new_rows - old_rows) if v_anchor == "низу" else 0
        c_off = (new_cols - old_cols) if h_anchor == "правому" else 0
        for c in range(old_cols):
            nc = c + c_off
            if nc < 0 or nc >= new_cols:
                continue
            src = c * old_rows
            dst = nc * new_rows
            for r in range(old_rows):
                nr = r + r_off
                if 0 <= nr < new_rows:
                    new[dst + nr] = old[src + r]
        self.cols, self.rows = new_cols, new_rows
        self.level["cols"] = new_cols
        self.level["rows"] = new_rows
        if self.mode.get() == "object":
            # объекты сдвигаем жёстко вместе с grid: пересегментация
            # cover_rectangles'ом перекроила бы разбивку куста/трубы на другие
            # прямоугольники и потеряла бы группы (поле g). Часть объекта за
            # новым краем — обрезаем w/h, остальное переразворачиваем в grid.
            out = []
            for o in self.objects:
                x, y, w, h = o["x"] + c_off, o["y"] + r_off, o["w"], o["h"]
                if x < 0:
                    w, x = w + x, 0
                if y < 0:
                    h, y = h + y, 0
                w, h = min(w, new_cols - x), min(h, new_rows - y)
                if w <= 0 or h <= 0:
                    continue
                n = {"t": o["t"], "x": x, "y": y, "w": w, "h": h}
                if "g" in o:
                    n["g"] = o["g"]
                out.append(n)
            self.objects = out
            self.sel_obj = self.sel_grp = None
            self._recompute_grid()
        else:
            self.grid = new
        self.level["grid"] = self.grid
        self.dirty = True
        self.render_all()

    # ---- сохранение -------------------------------------------------------
    def save(self):
        """Объекты — источник истины: пишем objects.json, а level.json —
        развёрнутая grid-картой копия (для фолбэка и парити-сверки). Запись
        блокируется, если уровень не пройдёт gen_assets (те же формулы)."""
        if self.mode.get() == "tile":
            self.objects = cover_rectangles(self.cols, self.rows, self.grid)
        bad = self._limits()
        if bad:
            messagebox.showerror(
                "Не сохраняется", "\n".join(bad) +
                "\n\ngen_assets упал бы на этих же формулах — правь карту/размер.")
            self._set_status("не сохранено: " + bad[0])
            return
        if self.mode.get() == "object":
            # переразвёртку — ПОСЛЕ проверки: объект за краем карты уронил бы
            # expand_objects traceback'ом вместо понятного диалога
            self._recompute_grid()
        self.level["cols"] = self.cols
        self.level["rows"] = self.rows
        self.level["grid"] = self.grid
        with open(os.path.join(SRC, "level.json"), "w") as f:
            json.dump(self.level, f)
        with open(os.path.join(SRC, "objects.json"), "w") as f:
            json.dump({"cols": self.cols, "rows": self.rows,
                       "tile": self.level.get("tile", 8),
                       "objects": self.objects}, f)
        with open(os.path.join(SRC, "tiles.json"), "w", encoding="utf-8") as f:
            json.dump(self.tiles, f, ensure_ascii=False, indent=1)
        self.dirty = False
        self._set_status("сохранено ✓ — выполни make")

    def _set_status(self, txt):
        self.status.config(text=txt)


def _maximize(root):
    """Штатная maximization: просим WM развернуть окно (заголовок остаётся,
    границы в work-area). Никакого geometry-форса на winfo_screenwidth/height:
    окно, ровно равное экрану, mutter рисует как fullscreen без рамок."""
    for fn in (lambda: root.state("zoomed"),
               lambda: root.attributes("-zoomed", True)):
        try:
            fn()
            return
        except tk.TclError:
            pass


def main():
    root = tk.Tk()
    app = LevelEditor(root)

    def on_close():
        if app.dirty and not messagebox.askyesno("Выход", "Есть несохранённые правки. Выйти?"):
            return
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_close)
    # развернуть ПОСЛЕ того, как WM отобразил окно (до map запрос zoomed теряется)
    root.after(120, lambda: _maximize(root))
    root.mainloop()


if __name__ == "__main__":
    main()
