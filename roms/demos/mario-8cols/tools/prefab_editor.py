#!/usr/bin/env python3
"""prefab_editor.py — редактор библиотеки префабов (assets/prefabs.json).

Открывается НЕЗАВИСИМО от окна уровня:  python3 tools/prefab_editor.py
(в окне уровня есть кнопка «Редактор префабов» — она запускает это окно
отдельным процессом, общего состояния между окнами нет).

Экран (слева направо):
  1) библиотека, сгруппированная по секциям (рельеф / блоки / декор /
    одиночные), с чистыми картинками (без оверлея твёрдости), нативным
    размером и марками «↔/↕» тянущихся осей;
  2) палитра assets/tiles/*.png ЗНАЧЕНИЯМИ ТВЁРДОСТИ (красная рамка — стена,
    синяя — платформа, фиолетовая — и то и другое, штриховка — прозрачный),
    плюс крупное превью наведённого тайла;
  3) ХОЛСТ ПРЕФАБА: рисуем тайлами, ЛКМ ставит выбранный тайл
    (протяжка — заливку прямоугольником), ПКМ берёт тайл под курсором,
    Shift+ЛКМ — «стереть» (тайл 0 = небо). Под холстом — легенда твёрдости,
    масштаб и размер паттерна (добор пустотой справа/снизу, обрезка там же);
    всю высоту холст не тянет: излишек колонки делит с превью (п. 4) в
    пропорции ASSEMBLY_SHARE:PREVIEW_SHARE, иначе под паттерн ростом в
    2-3 тайла висело бы ~650 px пустоты;
  4) панель растяжения — stretch_x / stretch_y ∈ {нет, замостить, 9-slice k,
    окно [a,b]} + min_w/min_h, а рядом превью «как будет при w×h»: видно, что
    шапка трубы, углы площадки и бугры облака не рвутся.

Твёрдость (wall/platform/transparent) здесь ТОЛЬКО показывается: источник
истины — assets/tiles.json, её правят галочками в окне уровня.

Сохранение — атомарная запись assets/prefabs.json (tmp + os.replace) схемой v2,
которую читают окно уровня, скрипт миграции карты и генератор. Кнопка
«ROM-вид» разбивает префаб на прямоугольники и считает цену в байтах: вариант
словаря 3 Б + 5 Б на каждый прямоугольник разбивки (см. prefablib:
VAR_BYTES / RECT_BYTES).
"""
import os
import sys
import textwrap

try:
    import tkinter as tk
    from tkinter import ttk, messagebox
except ImportError:
    sys.exit("Не найден Tkinter. Установка (Debian/Ubuntu):\n"
             "  sudo apt install python3-tk\n"
             "Перезапусти:  python3 tools/prefab_editor.py")

try:
    from PIL import Image, ImageTk, ImageDraw
except ImportError:
    sys.exit("Не найден PIL.ImageTk (биндинг Tk для Pillow — отдельный пакет).\n"
             "Установка (Debian/Ubuntu):\n"
             "  sudo apt install python3-pil python3-pil.imagetk\n"
             "Перезапусти:  python3 tools/prefab_editor.py")

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from prefablib import (                                     # noqa: E402
    PREFAB_FILE, OBJECTS_FILE, TILES_FILE, SKY, COLL_RED, COLL_BLUE, PF_SECTIONS,
    MAX_COLS, MAX_ROWS, TILE_INDEX_LIMIT, MAX_VARIANTS, INST_BYTES, RECT_BYTES, VAR_BYTES,
    load_tiles, tile_props, load_tile_images, load_prefabs, load_instances,
    prefab_comment,
    save_prefabs, save_instances, section_of, sort_key_prefabs, stamp_size,
    stamp_cells, stamp_objects)
from uiutil import maximize                                # noqa: E402

CELL = 24                      # сторона тайла на холсте, px (зум из списка)
CELL_CHOICES = ("8", "12", "16", "24", "32")
PF_COL_W = 250                 # ширина строки библиотеки, px
PF_HDR_H = 18                  # высота строки «— раздел —» в списке
PF_SEC_GAP = 14                # пустая строка МЕЖДУ разделами списка
PREV_MIN_H = 140               # минимальная высота превью «при w×h», px
ASSEMBLY_MIN_H = 120           # нижняя граница высоты холста, px (5 тайлов по
#                               CELL): холст скроллируется, «место под весь
#                               паттерн» ему не нужен; без этой цифры Tk просит
#                               265 px, а менеджер геометрии сверх запроса
#                               раздаёт только ИЗБЫТОК — его и делят веса рядов
ASSEMBLY_SHARE = 7             # как делится ИЗБЫТОК высоты колонки между холстом
PREVIEW_SHARE = 3              # сборки и превью: 7:3 — это минус четверть
#                               высоты холста на развёрнутом окне (мерил
#                               .scratch/prefab_layout_probe.py на 800 и 1030
#                               px; 3:1 даёт только −20%)
PAL_THUMB = 32
PAL_COLS = 4
PAL_GAP = 6
PAL_LBL_W = 22                 # ширина подписи под палитрой, в символах: всё, что
                               # длиннее, переносится строкой, а не растягивает
                               # панель (иначе она дёргает окно на каждом выборе
                               # тайла); 22 — максимум, при котором подпись ещё
                               # умещается в ширину сетки тайлов с прокруткой
PREV_SCALE = 8                 # превью «как будет при w×h»: не используется,
                               # масштаб берём из «Масштаб» (self.cell)
HL_COLOR = (255, 212, 0)       # жёлтая рамка «это текущая кисть»
SEL_COLOR = (78, 201, 176)     # бирюза: выбранный префаб в списке
VIOLET = (186, 85, 211)        # wall + platform
HATCH = (200, 200, 200)        # штриховка прозрачного тайла
EMPTY_A = (30, 30, 34)         # «пусто» (тайл 0): шахматка из двух тонов
EMPTY_B = (40, 40, 46)
GRID_LINE = (128, 128, 128)
STRETCH_MODES = ("нет", "замостить", "9-slice", "окно")
STRETCH_MODE_W = 12           # фиксированная ширина переключателя режима: без неё
                              # OptionMenu то расширяется под «замостить», то
                              # сжимается под «нет» — и всё слева дёргается
STRETCH_HELP = (
    "режимы оси (X — ширина/столбцы, Y — высота/строки):\n"
    "  нет        — ось не тянется, размер фиксирован;\n"
    "  замостить  — паттерн циклически повторяется целиком;\n"
    "  9-slice k  — колонки/строки 0..k целые, k тянется, далее хвост;\n"
    "  окно [a,b] — повторяется только окно a..b, углы целые.\n"
    "k — граница шапки (9-slice); a, b — границы окна;\n"
    "min — минимальный размер штампа по этой оси (в тайлах).")

# ---------------------------------------------------------------------------
# Палитра ограничена набором тайлов: t — полный байт rect'а (0..255), но зашить
# в ROM можно только те, что реально есть в tiles.json (валидация t < n_tiles).
MAX_PAT = 64                   # паттерн шире/выше 64 тайлов всё равно не нужен:
#                               тянется stretch, а не раздутым шаблоном


def hx(color):
    """PIL-кортеж -> цвет Tk: canvas принимает только строки, а палитра
    твёрдости живёт кортежами (общие с окном уровня из prefablib)."""
    return "#%02x%02x%02x" % tuple(color)


def hardness_of(props, t):
    """(цвет заливки, буквенный бейдж, подпись) по свойствам тайла."""
    p = props.get(t) or {}
    wall = bool(p.get("wall"))
    plat = bool(p.get("platform"))
    tran = bool(p.get("transparent"))
    if tran:
        return None, "∅", "прозрачный (небо)"
    if wall and plat:
        return VIOLET, "СП", "стена + платформа"
    if wall:
        return COLL_RED, "С", "стена (непроходимо)"
    if plat:
        return COLL_BLUE, "П", "платформа (one-way)"
    return None, "·", "проходной"


class PrefabEditor:
    def __init__(self, root, path=PREFAB_FILE):
        self.root = root
        self.path = path
        root.title("Префабы — библиотека уровня Mario 8cols / Vector-06C")
        root.geometry("1280x800")

        self.tiles_meta = load_tiles(TILES_FILE)
        self.n_tiles = len(self.tiles_meta["tiles"])
        self.props = tile_props(self.tiles_meta)
        self.tile_orig = load_tile_images(self.tiles_meta)
        self.prefabs = sort_key_prefabs(load_prefabs(self.path, self.n_tiles))
        # имена, с которыми библиотека лежит на диске: по ним (=id объекта)
        # отслеживаем переименования, чтобы прошить уровень при сохранении
        self._orig_name = {id(pf): pf["name"] for pf in self.prefabs}
        self.comment = prefab_comment(self.path)   # _comment переносим как есть
        self.cur = None                  # редактируемый префаб (ссылка в списке)
        self.selected = 0                # тайл-кисть
        self.cell = CELL
        self.dirty = False
        self.drag = None                # ((col,row), shift) — начало протяжки
        self._photos = []                # держать ImageTk.PhotoImage (иначе GC)
        self._loading_panel = False       # чтобы command не писал обратно в файл

        self._build_ui()
        if self.prefabs:
            self.select(0)
        self._sync()

    # ---- каркас окна ------------------------------------------------------
    def _build_ui(self):
        bar = ttk.Frame(self.root, padding=6)
        bar.pack(side=tk.TOP, fill=tk.X)
        self.btn_new = ttk.Button(bar, text="новый", command=self.new_pf)
        self.btn_new.pack(side=tk.LEFT)
        self.btn_dup = ttk.Button(bar, text="дубликат", command=self.dup_pf)
        self.btn_dup.pack(side=tk.LEFT, padx=(4, 0))
        self.btn_del = ttk.Button(bar, text="удалить", command=self.del_pf)
        self.btn_del.pack(side=tk.LEFT, padx=(4, 0))
        ttk.Label(bar, text="  имя").pack(side=tk.LEFT)
        self.name_var = tk.StringVar()
        self.name_box = ttk.Entry(bar, textvariable=self.name_var, width=24)
        self.name_box.pack(side=tk.LEFT)
        self.name_box.bind("<Return>", self._apply_name)
        self.name_box.bind("<FocusOut>", self._apply_name)
        ttk.Label(bar, text="  секция").pack(side=tk.LEFT)
        self.sec_var = tk.StringVar()
        self.sec_box = ttk.OptionMenu(bar, self.sec_var, "декор", *PF_SECTIONS,
                                      command=self._apply_section)
        self.sec_box.pack(side=tk.LEFT)
        self.size_lbl = ttk.Label(bar, text="—", width=16, foreground="#777")
        self.size_lbl.pack(side=tk.LEFT, padx=8)
        ttk.Button(bar, text="ROM-вид", command=self.rom_view).pack(
            side=tk.LEFT, padx=(8, 0))
        ttk.Button(bar, text="Сохранить", command=self.save).pack(
            side=tk.LEFT, padx=(12, 4))
        self.show_solo = tk.BooleanVar(value=False)
        ttk.Checkbutton(bar, text="показывать одиночные тайлы",
                        variable=self.show_solo,
                        command=self._build_list).pack(side=tk.LEFT, padx=(6, 0))
        self.status = ttk.Label(bar, text="готово", foreground="#777")
        self.status.pack(side=tk.RIGHT, padx=6)

        body = ttk.Frame(self.root)
        body.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        # слева — библиотека
        left = ttk.Frame(body)
        left.pack(side=tk.LEFT, fill=tk.Y)
        ttk.Label(left, text="1) Префабы (клик — редактировать)").pack(anchor=tk.W)
        lfr = ttk.Frame(left)
        lfr.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        self.lcv = tk.Canvas(lfr, width=PF_COL_W, height=520, bg="#1e1e1e",
                             highlightthickness=0)
        self.lcv.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        lsb = ttk.Scrollbar(lfr, orient=tk.VERTICAL, command=self.lcv.yview)
        lsb.pack(side=tk.LEFT, fill=tk.Y)
        self.lcv.config(yscrollcommand=lsb.set)
        self._build_list()

        # справа — палитра тайлов, у самого правого края окна. Пакуем ДО
        # центра: pack отдаёт место тем, кто заявился раньше, иначе
        # растянувшийся холст вытеснил бы палитру за окно.
        right = ttk.Frame(body)
        right.pack(side=tk.RIGHT, fill=tk.Y)
        ttk.Label(right, text="2) Тайлы (рамка = твёрдость)").pack(anchor=tk.W)
        pfr = ttk.Frame(right)
        pfr.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        pw = PAL_COLS * (PAL_THUMB + PAL_GAP) + PAL_GAP + 14
        self.pal = tk.Canvas(pfr, width=pw, height=420, bg="#242424",
                             highlightthickness=0)
        self.pal.pack(side=tk.LEFT, fill=tk.Y)
        psb = ttk.Scrollbar(pfr, orient=tk.VERTICAL, command=self.pal.yview)
        psb.pack(side=tk.LEFT, fill=tk.Y)
        self.pal.config(yscrollcommand=psb.set)
        self.pal_prev = tk.Canvas(right, width=96, height=96, bg="#111",
                                 highlightthickness=1,
                                 highlightbackground="#3a3a3a")
        self.pal_prev.pack(pady=6)
        self.pal_lbl = ttk.Label(right, text="—", justify=tk.LEFT,
                                 width=PAL_LBL_W)
        self.pal_lbl.pack(anchor=tk.W)
        self._build_palette()

        # центр — холст префаба + панель растяжения + превью
        mid = ttk.Frame(body)
        mid.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=8)
        # Колонку раскладываем grid'ом, а не pack'ом: только grid умеет делить
        # свободную высоту ПО ПРОПОРЦИИ. Pack с expand=True отдавал холсту
        # ВЕСЬ остаток развёрнутого окна: ~650 px под паттерн ростом в 2-3
        # тайла. Четверть этого холст уступает превью «при w×h» (rows: 0
        # подпись, 1 холст, 2 легенда, 3 масштабы, 4 растяжение, 5 превью).
        mid.columnconfigure(0, weight=1)
        mid.grid_rowconfigure(1, weight=ASSEMBLY_SHARE)
        mid.grid_rowconfigure(5, weight=PREVIEW_SHARE)
        row = ttk.Frame(mid)
        row.grid(row=0, column=0, sticky="w")
        ttk.Label(row, text="3) Холст: ЛКМ — ставить (тянуть = прямоугольник), "
                            "ПКМ — взять тайл, Shift+ЛКМ — стереть").pack(
            side=tk.LEFT)

        cfr = ttk.Frame(mid)
        cfr.grid(row=1, column=0, sticky="nsew")
        self.canvas = tk.Canvas(cfr, height=ASSEMBLY_MIN_H, bg="#0d1a2b",
                                highlightthickness=1,
                                highlightbackground="#444")
        self.cvsb = ttk.Scrollbar(cfr, orient=tk.VERTICAL, command=self.canvas.yview)
        self.chsb = ttk.Scrollbar(cfr, orient=tk.HORIZONTAL, command=self.canvas.xview)
        self.canvas.config(yscrollcommand=self.cvsb.set,
                           xscrollcommand=self.chsb.set)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.cvsb.grid(row=0, column=1, sticky="ns")
        self.chsb.grid(row=1, column=0, sticky="ew")
        cfr.columnconfigure(0, weight=1)
        cfr.rowconfigure(0, weight=1)
        self.canvas.bind("<Button-1>", self._on_click)
        self.canvas.bind("<B1-Motion>", self._on_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_release)
        self.canvas.bind("<Button-3>", self._on_pick)
        self.canvas.bind("<MouseWheel>", self._on_wheel)
        self.canvas.bind("<Button-4>", lambda e: self._on_wheel(e, -1))
        self.canvas.bind("<Button-5>", lambda e: self._on_wheel(e, 1))

        # под холстом: легенда твёрдости, отдельным рядом — масштаб и размер
        # паттерна (в одну строку они не влезают и уезжают за край окна)
        leg = ttk.Frame(mid, padding=(4, 2))
        leg.grid(row=2, column=0, sticky="ew")
        self._leg = tk.Canvas(leg, width=620, height=20, highlightthickness=0)
        self._leg.pack(side=tk.LEFT)
        self._draw_legend()
        opts = ttk.Frame(mid, padding=(4, 0))
        opts.grid(row=3, column=0, sticky="ew")
        ttk.Label(opts, text="масштаб").pack(side=tk.LEFT)
        self.zoom_var = tk.StringVar(value=str(CELL))
        z = ttk.OptionMenu(opts, self.zoom_var, str(CELL), *CELL_CHOICES,
                           command=self._on_zoom)
        z.config(width=4)
        z.pack(side=tk.LEFT, padx=(2, 0))
        ttk.Label(opts, text="   паттерн W").pack(side=tk.LEFT, padx=(10, 0))
        self.w_var = tk.IntVar(value=1)
        self.w_box = ttk.Spinbox(opts, from_=1, to=MAX_PAT, width=4,
                                 textvariable=self.w_var, command=self._resize)
        self.w_box.pack(side=tk.LEFT)
        ttk.Label(opts, text="  H").pack(side=tk.LEFT)
        self.h_var = tk.IntVar(value=1)
        self.h_box = ttk.Spinbox(opts, from_=1, to=MAX_PAT, width=4,
                                 textvariable=self.h_var, command=self._resize)
        self.h_box.pack(side=tk.LEFT)
        ttk.Label(opts, foreground="#777",
                  text="(добор пустотой и обрезка — справа/снизу)").pack(
            side=tk.LEFT, padx=6)

        self._build_stretch(mid)

        self.root.bind("<Control-s>", lambda e: self.save())
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_stretch(self, parent):
        """Панель растяжения: spec по каждой оси + min + превью w×h.

        Ряды 4 и 5 той же сетки, что и холст: панель остаётся своей
        запрашиваемой высоты, а освобождённая холстом четверть уходит ряду 5,
        где превью тянется на всю высоту. Справа от органов управления —
        постоянная пояснялка про режимы и k/a/b/min (раньше на её месте
        висело сменяющееся поле «здесь: N rect …», которое путало вместо
        того, чтобы объяснять)."""
        fr = ttk.LabelFrame(parent, text="4) Растяжение (как паттерн ведёт себя при "
                                       "размере ≠ нативному)", padding=6)
        fr.grid(row=4, column=0, sticky="ew", pady=(6, 0))
        ctl = ttk.Frame(fr)                    # левая колонка: сами органы
        ctl.pack(side=tk.LEFT, fill=tk.X)
        self.sv = {}
        for axis, lab in (("x", "ось X (ширина)"), ("y", "ось Y (высота)")):
            r = ttk.Frame(ctl)
            r.pack(side=tk.TOP, fill=tk.X, pady=1)
            ttk.Label(r, text=lab, width=14, anchor=tk.W).pack(side=tk.LEFT)
            mode = tk.StringVar(value="нет")
            om = ttk.OptionMenu(r, mode, "нет", *STRETCH_MODES,
                                command=self._apply_stretch)
            om.config(width=STRETCH_MODE_W)    # фикс. ширина: иначе переключатель
            om.pack(side=tk.LEFT)              # тянет за собой всё слева
            k = tk.IntVar(value=0)
            ttk.Label(r, text="k").pack(side=tk.LEFT, padx=(8, 0))
            kb = ttk.Spinbox(r, from_=0, to=MAX_PAT - 1, width=3, textvariable=k,
                             command=self._apply_stretch)
            kb.pack(side=tk.LEFT)
            a = tk.IntVar(value=0)
            b = tk.IntVar(value=0)
            ttk.Label(r, text="окно a").pack(side=tk.LEFT, padx=(8, 0))
            ab = ttk.Spinbox(r, from_=0, to=MAX_PAT - 1, width=3, textvariable=a,
                             command=self._apply_stretch)
            ab.pack(side=tk.LEFT)
            ttk.Label(r, text="b").pack(side=tk.LEFT)
            bb = ttk.Spinbox(r, from_=0, to=MAX_PAT - 1, width=3, textvariable=b,
                             command=self._apply_stretch)
            bb.pack(side=tk.LEFT)
            mn = tk.IntVar(value=1)
            ttk.Label(r, text="min").pack(side=tk.LEFT, padx=(8, 0))
            mb = ttk.Spinbox(r, from_=1, to=MAX_PAT * 8, width=4, textvariable=mn,
                             command=self._apply_stretch)
            mb.pack(side=tk.LEFT)
            self.sv[axis] = (mode, k, a, b, mn, (kb, ab, bb, mb))

        pr = ttk.Frame(ctl)
        pr.pack(side=tk.TOP, fill=tk.X, pady=(6, 0))
        ttk.Label(pr, text="превью при").pack(side=tk.LEFT)
        self.pw_var = tk.IntVar(value=12)
        ttk.Spinbox(pr, from_=1, to=MAX_COLS, width=4, textvariable=self.pw_var,
                    command=self._sync_preview).pack(side=tk.LEFT)
        ttk.Label(pr, text="×").pack(side=tk.LEFT)
        self.ph_var = tk.IntVar(value=6)
        ttk.Spinbox(pr, from_=1, to=MAX_ROWS, width=4, textvariable=self.ph_var,
                    command=self._sync_preview).pack(side=tk.LEFT)
        ttk.Label(pr, text="(слева — нативный размер; тянутся только оси со "
                            "stretch)").pack(side=tk.LEFT, padx=6)

        ttk.Label(fr, text=STRETCH_HELP, justify=tk.LEFT, foreground="#888",
                  font=("DejaVu Sans", 8)).pack(side=tk.LEFT, padx=(14, 0))

        self.pfr = ttk.Frame(parent)
        self.pfr.grid(row=5, column=0, sticky="nsew", pady=(4, 0))
        self.pfcv = tk.Canvas(self.pfr, height=PREV_MIN_H, bg="#0d1a2b",
                              highlightthickness=1, highlightbackground="#333")
        self.pfcv.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.pfcv.bind("<Configure>", self._on_prev_size)

    def _draw_legend(self):
        c = self._leg
        c.delete("all")
        x = 2
        items = [(COLL_RED, "стена"), (COLL_BLUE, "платформа"),
                 (VIOLET, "стена+платформа"), (None, "проходной")]
        for color, text in items:
            c.create_rectangle(x, 3, x + 14, 17,
                               fill=hx(color) if color else "#0d1a2b",
                               outline="#666")
            c.create_text(x + 19, 10, anchor=tk.W, text=text, fill="#bbb",
                          font=("DejaVu Sans", 9))
            x += 19 + 8 * len(text) + 26
        # штриховка = прозрачный
        c.create_rectangle(x, 3, x + 14, 17, fill="#0d1a2b", outline="#666")
        for i in range(0, 20, 5):
            c.create_line(x + i, 17, x + i + 14, 3, fill="#999")
        c.create_text(x + 19, 10, anchor=tk.W, text="прозрачный", fill="#bbb",
                      font=("DejaVu Sans", 9))

    # ---- библиотека -------------------------------------------------------
    def _visible(self):
        """Список строк панели: [(индекс в self.prefabs, префаб)], с фильтром
        секции «одиночные» (их ~сотня, они закрывают нормальные префабы)."""
        out = []
        for i, pf in enumerate(self.prefabs):
            if section_of(pf) == "одиночные" and not self.show_solo.get():
                continue
            out.append((i, pf))
        return out

    def _build_list(self):
        c = self.lcv
        c.delete("all")
        self._list_photos = []
        self._rows = []
        y = 6
        last_sec = None
        for i, pf in self._visible():
            sec = section_of(pf)
            if sec != last_sec:
                if last_sec is not None:
                    y += PF_SEC_GAP        # пустая строка после предыдущего раздела
                # заголовок по центру колонки: он не привязан к строке
                # префаба и на левом краю читался как ещё одна карточка
                c.create_text(PF_COL_W // 2, y, anchor=tk.N, text="— " + sec + " —",
                              fill="#888", font=("DejaVu Sans", 9, "bold"))
                y += PF_HDR_H
                last_sec = sec
            cells = stamp_cells(pf, len(pf["grid"][0]), len(pf["grid"]))
            scale = max(6, min(16, 180 // max(len(cells[0]), len(cells))))
            # в списке — чистые картинки: твёрдость смотрят на холсте и в
            # палитре, здесь она лишь перекрашивает узнаваемые тайлы
            im = self._grid_image(cells, scale, hardness=False)
            photo = ImageTk.PhotoImage(im)
            self._list_photos.append(photo)
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
            c.tag_bind(hit, "<Button-1>", lambda e, idx=i: self.select(idx))
            self._rows.append((i, y - 3, y + row_h + 3))
            y += row_h + 10
        if last_sec is not None:
            y += PF_SEC_GAP                # и после последнего раздела
        c.configure(scrollregion=(0, 0, PF_COL_W, y))
        self._update_list_sel()

    def select(self, i):
        """Открыть префаб на редактировании: холст, панель растяжения, превью."""
        if i is None or not (0 <= i < len(self.prefabs)):
            self.cur = None
        else:
            self.cur = self.prefabs[i]
        self._sync()
        self._update_list_sel()

    def _update_list_sel(self):
        c = self.lcv
        if getattr(self, "_list_sel", None):
            c.delete(self._list_sel)
        self._list_sel = None
        if self.cur is None or self.cur not in self.prefabs:
            return
        i = self.prefabs.index(self.cur)
        for idx, y0, y1 in self._rows:
            if idx == i:
                self._list_sel = c.create_rectangle(2, y0, PF_COL_W, y1,
                                                    outline=hx(SEL_COLOR),
                                                    width=2)
                self._ensure_row_visible(y0, y1)
                break

    def _ensure_row_visible(self, y0, y1):
        """Подтащить список к строке, только если её правда не видно.

        Центрировать «всегда» нельзя: до map окна winfo_height() = 1, и
        прокрутка уезжала на ~20 px вниз, где под край уходил заголовок
        раздела над первым префабом."""
        c = self.lcv
        h = c.winfo_height()
        total = int((c.cget("scrollregion") or "0 0 0 0").split()[-1] or 0)
        if h <= 1 or total <= h:
            return
        top, bot = [int(f * total) for f in c.yview()]
        if y0 < top or y1 > bot:
            c.yview_moveto(min(1.0, max(0.0, (y0 - h / 2) / total)))

    # ---- элементы библиотеки ---------------------------------------------
    def new_pf(self):
        pf = {"name": self._free_name("Новый префаб"), "section": "декор",
              "grid": [[0, 0, 0], [0, 0, 0]]}
        self.prefabs.append(pf)
        self._build_list()
        self.select(self.prefabs.index(pf))
        self._touch("новый префаб: %s" % pf["name"])

    def dup_pf(self):
        if self.cur is None:
            return
        import copy
        pf = copy.deepcopy(self.cur)
        pf["name"] = self._free_name(pf["name"] + " копия")
        self.prefabs.insert(self.prefabs.index(self.cur) + 1, pf)
        self._build_list()
        self.select(self.prefabs.index(pf))
        self._touch("дубликат: %s" % pf["name"])

    def del_pf(self):
        if self.cur is None:
            return
        if not messagebox.askyesno("Удалить", "Удалить префаб «%s» из "
                                             "библиотеки?" % self.cur["name"]):
            return
        i = self.prefabs.index(self.cur)
        self.prefabs.pop(i)
        self._build_list()
        self.select(min(i, len(self.prefabs) - 1) if self.prefabs else None)
        self._touch("префаб удалён")

    def _free_name(self, base):
        have = {pf.get("name") for pf in self.prefabs}
        if base not in have:
            return base
        n = 2
        while "%s %d" % (base, n) in have:
            n += 1
        return "%s %d" % (base, n)

    def _apply_name(self, _=None):
        if self.cur is None:
            return
        name = self.name_var.get().strip()
        if not name:
            self.name_var.set(self.cur["name"])
            return
        if name != self.cur["name"]:
            self.cur["name"] = name
            self._build_list()
            self._touch("переименован в «%s»" % name)

    def _apply_section(self, _=None):
        if self.cur is None:
            return
        self.cur["section"] = self.sec_var.get()
        self._build_list()
        self._update_list_sel()
        self._touch("секция: %s" % self.cur["section"])

    def _resize(self):
        """Новый размер паттерна: добор пустотой справа/снизу, обрезка
        справа/снизу. Заодно клампим stretch-параметры в новые границы."""
        if self.cur is None:
            return
        w = max(1, min(MAX_PAT, self.w_var.get() if self._ok(self.w_var) else 1))
        h = max(1, min(MAX_PAT, self.h_var.get() if self._ok(self.h_var) else 1))
        g = self.cur["grid"]
        for row in g:
            del row[w:]
        while len(g) < h:
            g.append([0] * w)
        del g[h:]
        for row in g:
            while len(row) < w:
                row.append(0)
        self._apply_stretch()
        self._sync()
        self._build_list()
        self._touch("размер паттерна %d×%d" % (w, h))

    @staticmethod
    def _ok(var):
        try:
            var.get()
            return True
        except tk.TclError:
            return False

    # ---- холст ------------------------------------------------------------
    def _grid_image(self, cells, scale, hardness=True):
        """row-major сетка -> картинка (пусто = шахматка, тайл = тайл +
        оверлей твёрдости). Тот же код для списка, холста и превью."""
        w, h = len(cells[0]) * scale, len(cells) * scale
        im = Image.new("RGB", (w, h), SKY)
        for r, row in enumerate(cells):
            for c, t in enumerate(row):
                x0, y0 = c * scale, r * scale
                if t == 0:
                    im.paste(Image.new("RGB", (scale, scale),
                                       EMPTY_A if (r + c) % 2 else EMPTY_B),
                             (x0, y0))
                    continue
                tile = self.tile_orig[t].resize((scale, scale), Image.NEAREST)
                im.paste(tile, (x0, y0))
                if hardness:
                    color, badge, _ = hardness_of(self.props, t)
                    if color:
                        blend = Image.blend(im.crop((x0, y0, x0 + scale,
                                                      y0 + scale)),
                                            Image.new("RGB", (scale, scale),
                                                      color), 0.45)
                        im.paste(blend, (x0, y0))
                    elif (self.props.get(t) or {}).get("transparent"):
                        d = ImageDraw.Draw(im)
                        for i in range(-scale, scale * 2, 6):
                            d.line([(x0 + i, y0 + scale), (x0 + i + scale, y0)],
                                   fill=HATCH)
        return im

    def _cell_at(self, e):
        if self.cur is None:
            return None
        col = int(self.canvas.canvasx(e.x) // self.cell)
        row = int(self.canvas.canvasy(e.y) // self.cell)
        g = self.cur["grid"]
        if 0 <= row < len(g) and 0 <= col < len(g[0]):
            return col, row
        return None

    def _paint(self, e):
        c = self._cell_at(e)
        if not c or self.cur is None:
            return
        col, row = c
        g = self.cur["grid"]
        t = 0 if (e.state & 1) else self.selected      # Shift = стереть
        if g[row][col] == t:
            return
        g[row][col] = t
        self._repaint()
        self._touch("тайл %d в (%d,%d)" % (t, col, row))

    def _repaint(self):
        """Быстрая дорисовка: пересобрать картинку целиком (паттерн маленький)
        и залить в тот же PhotoImage — без мигания и без новых объектов."""
        if not getattr(self, "_cv_photo", None):
            self.render()
            self._cv_photo = self._cv_photos[0] if self._cv_photos else None
            return
        self._cv_photo.paste(self._compose())

    def _compose(self):
        cells = self.cur["grid"]
        im = self._grid_image(cells, self.cell)
        W, H = im.size
        ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(ov)
        s = self.cell
        for x in range(0, W + 1, s):
            d.line([(x, 0), (x, H)], fill=GRID_LINE + (120,), width=1)
        for y in range(0, H + 1, s):
            d.line([(0, y), (W, y)], fill=GRID_LINE + (120,), width=1)
        if self.cur.get("stretch_x"):
            d.line([(0, H - 1), (W, H - 1)], fill=(78, 201, 176, 255), width=1)
        if self.cur.get("stretch_y"):
            d.line([(W - 1, 0), (W - 1, H)], fill=(78, 201, 176, 255), width=1)
        return Image.alpha_composite(im.convert("RGBA"), ov).convert("RGB")

    def render(self):
        c = self.canvas
        c.delete("all")
        self._cv_photos = []
        self._cv_photo = None
        if self.cur is None:
            c.configure(scrollregion=(0, 0, 0, 0))
            return
        im = self._compose()
        photo = ImageTk.PhotoImage(im)
        self._cv_photos.append(photo)
        self._cv_photo = photo
        c.create_image(0, 0, anchor=tk.NW, image=photo)
        c.configure(scrollregion=(0, 0, im.width, im.height))

    # ---- мышь: одиночная постановка и прямоугольник ----------------------
    def _on_click(self, e):
        self.drag = (self._cell_at(e), e.state & 1)
        self._paint(e)

    def _on_drag(self, e):
        if not getattr(self, "drag", None):
            return
        start, shift = self.drag
        c = self._cell_at(e)
        if not start or not c or self.cur is None:
            return
        (x0, y0), (x1, y1) = start, c
        t = 0 if shift else self.selected
        g = self.cur["grid"]
        for r in range(min(y0, y1), max(y0, y1) + 1):
            for col in range(min(x0, x1), max(x0, x1) + 1):
                g[r][col] = t
        self._repaint()

    def _on_release(self, e):
        if getattr(self, "drag", None):
            self.drag = None
            self._build_list()
            self._sync_preview()
            self._touch("штамп %s" % self.cur["name"])

    def _on_pick(self, e):
        """ПКМ — взять тайл под курсором в кисть (как в окне уровня)."""
        c = self._cell_at(e)
        if not c or self.cur is None:
            return
        t = self.cur["grid"][c[1]][c[0]]
        if t:
            self.selected = t
            self._update_pal_sel()
            self._sync_palette_label()

    def _on_wheel(self, e, d=1):
        """Колесо — прокрутка холста; Shift+колесо — горизонтальная. Для Linux
        (Button-4/5) delta нулевой, направление приходит в d."""
        steps = int(e.delta / 120) if e.delta else d
        (self.canvas.xview_scroll if (e.state & 1) else self.canvas.yview_scroll)(
            steps, "units")

    def _on_zoom(self, v):
        try:
            self.cell = max(4, min(64, int(v)))
        except ValueError:
            return
        self.render()
        self._sync_preview()

    # ---- палитра ----------------------------------------------------------
    def _build_palette(self):
        c = self.pal
        c.delete("all")
        self._pal_photos = []
        self._pal_sel = None
        for i, orig in enumerate(self.tile_orig):
            x, y = self._pal_xy(i)
            th = orig.resize((PAL_THUMB, PAL_THUMB), Image.NEAREST).convert("RGB")
            color, badge, _ = hardness_of(self.props, i)
            if color:
                th = Image.blend(th, Image.new("RGB", (PAL_THUMB, PAL_THUMB),
                                               color), 0.35)
            elif (self.props.get(i) or {}).get("transparent"):
                d0 = ImageDraw.Draw(th)
                for j in range(-PAL_THUMB, PAL_THUMB * 2, 8):
                    d0.line([(j, PAL_THUMB), (j + PAL_THUMB, 0)], fill=HATCH)
            photo = ImageTk.PhotoImage(th)
            self._pal_photos.append(photo)
            im = c.create_image(x, y, anchor=tk.NW, image=photo)
            frame = hx(color) if color else ("#444" if (self.props.get(i) or {})
                                             .get("transparent") else "#777")
            c.create_rectangle(x - 1, y - 1, x + PAL_THUMB + 1,
                               y + PAL_THUMB + 1, outline=frame, width=2)
            if badge and badge != "·":
                c.create_text(x + PAL_THUMB - 5, y + 5, anchor=tk.NE, text=badge,
                              fill="#fff", font=("DejaVu Sans", 7, "bold"))
            c.create_text(x, y + PAL_THUMB + 1, anchor=tk.NW, text=str(i),
                          fill="#999", font=("DejaVu Sans", 7))
            c.tag_bind(im, "<Button-1>", lambda e, idx=i: self.select_tile(idx))
            c.tag_bind(im, "<Enter>", lambda e, idx=i: self._hover(idx))
            c.tag_bind(im, "<Leave>", lambda e: self._hover(self.selected))
        rows = len(self.tile_orig) // PAL_COLS + 1
        c.configure(scrollregion=(0, 0, 0, PAL_GAP * 2 + rows * (PAL_THUMB + 14)))
        self._update_pal_sel()

    @staticmethod
    def _pal_xy(i):
        """Координаты тайла в палитре: строка на 14 px выше превью (подпись
        индекса), колонка — PAL_COLS. Одна формула на отрисовку и на рамку
        выбора — иначе жёлтая рамка уезжает от тайла."""
        r, col = divmod(i, PAL_COLS)
        return (PAL_GAP + col * (PAL_THUMB + PAL_GAP),
                PAL_GAP + r * (PAL_THUMB + 14))

    def select_tile(self, i):
        self.selected = i
        self._update_pal_sel()
        self._sync_palette_label()

    def _update_pal_sel(self):
        c = self.pal
        if self._pal_sel:
            c.delete(self._pal_sel)
        x, y = self._pal_xy(self.selected)
        self._pal_sel = c.create_rectangle(x - 4, y - 4, x + PAL_THUMB + 4,
                                          y + PAL_THUMB + 4,
                                          outline=hx(HL_COLOR), width=2)
        total = c.cget("scrollregion").split()[-1]
        h = c.winfo_height()
        if total and int(total) > 0 and h > 1:
            c.yview_moveto(min(1.0, max(0.0, (y - h / 2) / int(total))))
        self._hover(self.selected)

    def _hover(self, i):
        self._hover_idx = i
        self._sync_palette_label()

    def _sync_palette_label(self):
        i = getattr(self, "_hover_idx", self.selected)
        t = self.tiles_meta["tiles"][i]
        color, badge, text = hardness_of(self.props, i)
        p = self.pal_prev
        p.delete("all")
        th = self.tile_orig[i].resize((96, 96), Image.NEAREST).convert("RGB")
        if color:
            th = Image.blend(th, Image.new("RGB", (96, 96), color), 0.4)
        self._prev_photo = ImageTk.PhotoImage(th)
        p.create_image(0, 0, anchor=tk.NW, image=self._prev_photo)
        # каждая смысловая строка переносится отдельно: иначе длинный файл или
        # «стена + платформа» растягивают панель палитры и она дёргается
        whole = "tile %d\nфайл: %s\nтвёрдость: %s [%s]" % (
            i, os.path.basename(t["file"]), text, badge)
        self.pal_lbl.config(text="\n".join(
            textwrap.fill(line, PAL_LBL_W) for line in whole.split("\n")))

    # ---- панель растяжения ------------------------------------------------
    def _sync(self):
        """Обновить ВСЕ виджеты под текущий префаб (имя, секция, размер,
        спинбоксы stretch, превью, холст)."""
        if self.cur is None:
            for w in (self.name_box, self.sec_box, self.w_box, self.h_box):
                w.config(state=tk.DISABLED)
            for axis in self.sv:                       # значения не трогаем:
                for box in self.sv[axis][5]:           # IntVar с "" падает на get
                    box.config(state=tk.DISABLED)
            self.size_lbl.config(text="—")
            self.render()
            self._sync_preview()
            return
        for w in (self.name_box, self.sec_box, self.w_box, self.h_box):
            w.config(state=tk.NORMAL)
        self._loading_panel = True
        try:
            g = self.cur["grid"]
            self.name_var.set(self.cur["name"])
            self.sec_var.set(section_of(self.cur))
            self.w_var.set(len(g[0]))
            self.h_var.set(len(g))
            for axis, key, n in (("x", "stretch_x", len(g[0])),
                                 ("y", "stretch_y", len(g))):
                mode, k, a, b, mn, boxes = self.sv[axis]
                spec = self.cur.get(key)
                if spec is None:
                    mode.set("нет")
                elif spec == "all":
                    mode.set("замостить")
                elif isinstance(spec, (list, tuple)):
                    mode.set("окно")
                    a.set(int(spec[0]))
                    b.set(int(spec[1]))
                else:
                    mode.set("9-slice")
                    k.set(int(spec))
                mn.set(int(self.cur.get("min_" + ("w" if axis == "x" else "h"), n)))
                for box in boxes:
                    box.config(state=tk.NORMAL if spec is not None
                               else tk.DISABLED)
        finally:
            self._loading_panel = False
        self.size_lbl.config(text="паттерн %d×%d" % (len(g[0]), len(g)))
        self.render()
        self._sync_preview()

    def _apply_stretch(self, _=None):
        if self.cur is None or self._loading_panel:
            return
        g = self.cur["grid"]
        n = {"x": len(g[0]), "y": len(g)}
        # имена полей — схема v2 (min_w/min_h их читает stamp_size), не min_x
        for axis, key, mkey in (("x", "stretch_x", "min_w"),
                                ("y", "stretch_y", "min_h")):
            mode, k, a, b, mn, _boxes = self.sv[axis]
            m = mode.get()
            if m == "нет":
                self.cur.pop(key, None)
                self.cur.pop(mkey, None)
            elif m == "замостить":
                self.cur[key] = "all"
                self.cur[mkey] = max(1, self._ival(mn, n[axis]))
            elif m == "9-slice":
                self.cur[key] = max(0, min(n[axis] - 1, self._ival(k, 0)))
                self.cur[mkey] = max(1, self._ival(mn, n[axis]))
            else:                                     # окно [a,b]
                lo = max(0, min(n[axis] - 1, self._ival(a, 0)))
                hi = max(lo, min(n[axis] - 1, self._ival(b, lo)))
                self.cur[key] = [lo, hi]
                self.cur[mkey] = max(1, self._ival(mn, n[axis]))
        self._sync_preview()
        self._build_list()
        self._touch("растяжение обновлено")

    @staticmethod
    def _ival(var, default):
        try:
            return int(var.get())
        except (ValueError, tk.TclError):
            return default

    def _prev_top(self, img_h):
        """Верх блока превью: прижат к началу поля (отступ 2 px). Раньше
        картинка центрировалась по высоте ряда 5 — из-за этого образцы висели
        посреди поля; теперь масштаб берётся из «Масштаб», и превью может быть
        выше ряда, поэтому держим его у верхней границы (переполнение уходит
        в скролл)."""
        return 2

    def _on_prev_size(self, e):
        """Превью перерисовываем, только когда изменилась ВЫСОТА: картинка
        центрируется по ней, а гонять тяжёлую пересборку ImageTk на каждом
        пикселе ширины незачем."""
        if e.height != getattr(self, "_prev_h", None):
            self._prev_h = e.height
            self._sync_preview()

    def _sync_preview(self):
        """Превью «как будет при w×h» рядом с нативным размером."""
        self.pfcv.delete("all")
        self._prev_photos = []
        if self.cur is None:
            return
        pf = self.cur
        nat_w, nat_h = len(pf["grid"][0]), len(pf["grid"])
        w, h = stamp_size(pf, self._ival(self.pw_var, nat_w),
                          self._ival(self.ph_var, nat_h))
        base = self._grid_image(stamp_cells(pf, nat_w, nat_h), self.cell,
                                hardness=False)
        big = self._grid_image(stamp_cells(pf, w, h), self.cell, hardness=False)
        p1 = ImageTk.PhotoImage(base)
        p2 = ImageTk.PhotoImage(big)
        self._prev_photos += [p1, p2]
        img_h = max(base.height, big.height)
        top = self._prev_top(img_h)
        self.pfcv.create_text(2, top, anchor=tk.NW, text="нативный %d×%d" % (
            nat_w, nat_h), fill="#888", font=("DejaVu Sans", 8))
        self.pfcv.create_image(2, top + 12, anchor=tk.NW, image=p1)
        # запас по подписям, а не по картинке: узкий паттерн (труба 4×3)
        # иначе две подписи слипаются в «нативный 4×3при 4×8»
        x = 2 + max(base.width, 80) + 24
        self.pfcv.create_text(x, top, anchor=tk.NW, text="при %d×%d" % (w, h),
                              fill="#888", font=("DejaVu Sans", 8))
        self.pfcv.create_image(x, top + 12, anchor=tk.NW, image=p2)
        self.pfcv.configure(scrollregion=(0, 0, x + big.width + 4,
                                          top + 12 + img_h + 6))

    # ---- ROM-вид ----------------------------------------------------------
    def rom_view(self):
        if self.cur is None:
            return
        pf = self.cur
        nat_w, nat_h = len(pf["grid"][0]), len(pf["grid"])
        rects = stamp_objects(pf, 0, 0, nat_w, nat_h)
        win = tk.Toplevel(self.root)
        win.title("ROM-вид: %s" % pf["name"])
        txt = tk.Text(win, width=64, height=24, font=("DejaVu Sans Mono", 9),
                      bg="#141414", fg="#ddd", insertbackground="#ddd")
        sb = ttk.Scrollbar(win, orient=tk.VERTICAL, command=txt.yview)
        txt.config(yscrollcommand=sb.set)
        txt.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb.pack(side=tk.LEFT, fill=tk.Y)
        txt.insert(tk.END, "Вариант «%s» %d×%d (нативный)\n" % (
            pf["name"], nat_w, nat_h))
        txt.insert(tk.END, "  таблица варианта: ofs(u16)+n(u8) = %d Б\n"
                   "  прямоугольники разбивки:\n" % VAR_BYTES)
        for i, r in enumerate(rects):
            txt.insert(tk.END, "    [%2d] t=%-3d dx=%-3d dy=%-3d w=%-3d h=%-3d"
                       "  %d Б\n" % (i, r["t"], r["x"], r["y"], r["w"], r["h"],
                                      RECT_BYTES))
        lib_rects = sum(len(stamp_objects(p, 0, 0, len(p["grid"][0]),
                                          len(p["grid"])))
                        for p in self.prefabs if p.get("grid"))
        body = VAR_BYTES + RECT_BYTES * len(rects)
        total = VAR_BYTES * len(self.prefabs) + RECT_BYTES * lib_rects
        txt.insert(tk.END, "\nитог по этому префабу: %d rect → %d Б словаря"
                   " + %d Б на каждый экземпляр на карте\n" % (
                       len(rects), body, INST_BYTES))
        txt.insert(tk.END, "вся библиотека (%d префабов, %d rect): %d Б "
                   "словаря\n" % (len(self.prefabs), lib_rects, total))
        txt.insert(tk.END, "\nлимиты: вариант ≤ %d (id 12 бит), тайл ≤ %d "
                   "(в наборе %d, макс индекс %d), x ≤ %d, y ≤ %d\nразмер rect — "
                   "байт, потому и паттерн, и stretch-размер ограничены %d×%d\n" % (
                       MAX_VARIANTS, TILE_INDEX_LIMIT, self.n_tiles,
                       self.n_tiles - 1, MAX_COLS - 1,
                       MAX_ROWS - 1, MAX_COLS - 1, MAX_ROWS - 1))
        txt.config(state=tk.DISABLED)

    # ---- валидация/запись -------------------------------------------------
    def _validate(self):
        bad = []
        have = set()
        for i, pf in enumerate(self.prefabs):
            name = (pf.get("name") or "").strip()
            g = pf.get("grid") or []
            tag = "#%d «%s»" % (i, name or "?")
            if not name:
                bad.append("%s: пустое имя" % tag)
            if name in have:
                bad.append("%s: такое имя уже в библиотеке" % tag)
            have.add(name)
            if not g:
                bad.append("%s: пустой паттерн" % tag)
                continue
            if len({len(row) for row in g}) != 1:
                bad.append("%s: строки разной длины" % tag)
            for row in g:
                for t in row:
                    if not isinstance(t, int) or isinstance(t, bool) or t < 0:
                        bad.append("%s: тайл %r — не положительное число" % (tag, t))
                        break
                    if t > TILE_INDEX_LIMIT:
                        bad.append("%s: тайл %d > %d — не влезает в байт rect'а"
                                   % (tag, t, TILE_INDEX_LIMIT))
                        break
                    if t >= self.n_tiles:
                        bad.append("%s: тайла %d нет в наборе (всего %d, "
                                   "макс индекс %d) — в ROM tileset/tile_solid "
                                   "столько записей, ссылка вылезет за границу"
                                   % (tag, t, self.n_tiles, self.n_tiles - 1))
                        break
                else:
                    continue
                break                      # одна претензия на паттерн: дальше мусор
            if not (1 <= len(g[0]) <= MAX_COLS and 1 <= len(g) <= MAX_ROWS):
                bad.append("%s: паттерн %d×%d вне карты (%d×%d)" % (
                    tag, len(g[0]), len(g), MAX_COLS, MAX_ROWS))
            for axis, key, n in (("x", "stretch_x", len(g[0])),
                                 ("y", "stretch_y", len(g))):
                mkey = "min_" + ("w" if axis == "x" else "h")
                spec = pf.get(key)
                if spec is None:
                    continue
                if isinstance(spec, (list, tuple)):
                    if len(spec) != 2 or not all(isinstance(v, int) for v in spec):
                        bad.append("%s: %s = %r — нужно [a, b] из целых"
                                   % (tag, key, spec))
                    elif not 0 <= spec[0] <= spec[1] < n:
                        bad.append("%s: окно %s [%d,%d] вне 0…%d" % (
                            tag, key, spec[0], spec[1], n - 1))
                elif spec != "all":
                    if not isinstance(spec, int) or not 0 <= spec < n:
                        bad.append("%s: %s = %r — нужно 0…%d или «all»"
                                   % (tag, key, spec, n - 1))
                if int(pf.get(mkey, n)) > (MAX_COLS if axis == "x"
                                          else MAX_ROWS):
                    bad.append("%s: %s больше карты" % (tag, mkey))
        return bad

    def save(self, _=None):
        bad = self._validate()
        if bad:
            messagebox.showerror("Не сохраняется", "\n".join(bad[:8]))
            self._touch("не сохранено: %d замечания" % len(bad))
            return False
        renames = self._collect_renames()
        save_prefabs(self.prefabs, self.path, comment=self.comment)
        rewired = self._propagate_renames(renames)
        self._orig_name = {id(pf): pf["name"] for pf in self.prefabs}
        self.dirty = False
        msg = "записано %d префабов в %s" % (
            len(self.prefabs), os.path.relpath(self.path))
        if rewired:
            msg += " · переименования прошиты в objects.json (%d экз.)" % rewired
        self.status.config(text=msg)
        return True

    def _collect_renames(self):
        """Переименования с момента загрузки/прошлого сохранения: имя на диске
        (по id объекта) != текущее, и старое имя больше никем не занято. Имя —
        единственный ключ связи уровня с библиотекой, поэтому его смену надо
        прошивать в objects.json, иначе редактор уровня и make упадут на висячей
        ссылке. -> {старое: новое}."""
        cur = {pf["name"] for pf in self.prefabs}
        renames = {}
        for pf in self.prefabs:
            old = self._orig_name.get(id(pf))
            if old is not None and old != pf["name"] and old not in cur:
                renames[old] = pf["name"]
        return renames

    def _propagate_renames(self, renames):
        """Перешить экземпляры уровня со старых имён на новые (assets/objects.json).
        -> сколько экземпляров изменено."""
        if not renames or not os.path.isfile(OBJECTS_FILE):
            return 0
        cols, rows, inst = load_instances()
        if inst is None:
            return 0
        changed = 0
        for o in inst:
            new = renames.get(o["pf"])
            if new:
                o["pf"] = new
                changed += 1
        if changed:
            save_instances(cols, rows, inst)
        return changed

    def _touch(self, text):
        self.dirty = True
        self.status.config(text=text + "  ·  не сохранено")

    def _on_close(self):
        if self.dirty and not messagebox.askyesno(
                "Закрыть", "Библиотека изменена и не сохранена.\n"
                          "Сохранить перед закрытием?"):
            if not messagebox.askyesno("Закрыть", "Тогда выйти БЕЗ сохранения?"):
                return
            self.root.destroy()
            return
        if self.dirty:
            self.save()
        self.root.destroy()


def main():
    root = tk.Tk()
    try:
        root.call("tk", "scaling", 1.2)
    except tk.TclError:
        pass
    PrefabEditor(root)
    # развернуть ПОСЛЕ того, как WM отобразил окно (до map запрос zoomed теряется)
    root.after(120, lambda: maximize(root))
    root.mainloop()


if __name__ == "__main__":
    main()
