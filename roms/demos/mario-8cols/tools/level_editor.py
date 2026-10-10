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

Прочее:
  * палитра всех тайлов (src/tiles/*.png) — клик выбирает кисть/тип объекта;
  * свойства тайла (wall / platform / transparent) — галочки справа или ПКМ;
  * «Показать твёрдость» — заливка: красная — стена, синяя — платформа;
  * Сохранение пишет src/objects.json, src/level.json (развёрнутая grid) и
    src/tiles.json (после — `make`).
"""
import json
import os
import sys

try:
    import tkinter as tk
    from tkinter import ttk
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


def frame_color(tile):
    """wall приоритетнее платформы; ни того ни другого — без рамки."""
    if tile.get("wall"):
        return COLL_RED
    if tile.get("platform"):
        return COLL_BLUE
    return None


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
        self.dirty = False
        self.selected = 0
        self.cell = 12
        self.mode = tk.StringVar(value="object")     # "object" | "tile"
        self.sel_obj = None                          # индекс выбранного объекта
        self.drag = None                             # состояние перетаскивания
        self.show_overlay = tk.BooleanVar(value=True)
        self.hl_var = tk.BooleanVar(value=True)
        self.grid_var = tk.BooleanVar(value=True)

        self._build_ui()
        self._rebuild_scaled()
        self.render_all()
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
        ttk.Spinbox(bar2, from_=1, to=512, width=5,
                    textvariable=self.w_var).pack(side=tk.LEFT)
        ttk.Label(bar2, text="  H").pack(side=tk.LEFT)
        self.h_var = tk.IntVar(value=self.rows)
        ttk.Spinbox(bar2, from_=1, to=255, width=5,
                    textvariable=self.h_var).pack(side=tk.LEFT)
        ttk.Label(bar2, text="   прижать к:").pack(side=tk.LEFT, padx=(10, 0))
        self.anchor_v = tk.StringVar(value="низу")
        ttk.OptionMenu(bar2, self.anchor_v, "низу", "верху", "низу").pack(side=tk.LEFT)
        self.anchor_h = tk.StringVar(value="левому")
        ttk.OptionMenu(bar2, self.anchor_h, "левому", "левому",
                       "правому").pack(side=tk.LEFT)
        ttk.Button(bar2, text="Изменить размер",
                   command=self._on_resize).pack(side=tk.LEFT, padx=(10, 0))
        ttk.Label(bar2, foreground="#777",
                  text="(новые поля — небо)").pack(side=tk.LEFT, padx=6)

        # легенда
        leg = ttk.Frame(self.root, padding=(8, 0, 8, 4))
        leg.pack(side=tk.TOP, fill=tk.X)
        ttk.Label(leg, text="проходной: без заливки    "
                           "сплошной (wall): красная заливка    "
                           "платформа: синяя заливка    "
                           "жёлтая рамка: текущий тайл").pack(side=tk.LEFT)

        body = ttk.Frame(self.root)
        body.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        # палитра слева
        left = ttk.Frame(body)
        left.pack(side=tk.LEFT, fill=tk.Y)
        ttk.Label(left, text="1) Клик по тайлу — выбрать кисть").pack(anchor=tk.W)
        pw = PAL_COLS * (PAL_THUMB + PAL_GAP) + PAL_GAP + 14
        self.pal = tk.Canvas(left, width=pw, height=640, bg="#242424",
                             highlightthickness=0)
        self.pal.pack(side=tk.LEFT, fill=tk.Y, expand=True)
        psb = ttk.Scrollbar(left, orient=tk.VERTICAL, command=self.pal.yview)
        psb.pack(side=tk.LEFT, fill=tk.Y)
        self.pal.config(yscrollcommand=psb.set)
        self._build_palette()

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

        # свойства справа
        right = ttk.Frame(body, padding=8)
        right.pack(side=tk.LEFT, fill=tk.Y)
        ttk.Label(right, text="2) Свойства выбранного тайла").pack(anchor=tk.W)
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
            "создать; по объекту — выделить/двинуть;\n"
            "Del — удалить.  ПКМ — кисть/твёрдость.\n\n"
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
            for i, o in enumerate(self.objects):
                box = [o["x"] * self.cell, o["y"] * self.cell,
                       (o["x"] + o["w"]) * self.cell - 1,
                       (o["y"] + o["h"]) * self.cell - 1]
                color = OBJ_SEL if i == self.sel_obj else OBJ_LINE
                d.rectangle(box, outline=color + (255,), width=2)
        return Image.alpha_composite(self.screen.convert("RGBA"), ov).convert("RGB")

    def _repaint_cell(self, col, row):
        ti = self.grid[col * self.rows + row]
        self._draw_cell(col * self.cell, row * self.cell, ti)
        # ImageTk.PhotoImage.paste принимает только полный кадр (без box)
        self.photo.paste(self._compose())

    # ---- выбор/свойства ---------------------------------------------------
    def select_tile(self, i):
        """Выбрать тайл-кисть: подсветить в палитре, показать свойства,
        и (если вкл. подсветка) перерисовать карту с новой рамкой."""
        self.selected = i
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
        if hit is not None:                       # по объекту — выделяем и тянем
            self.sel_obj = hit
            o = self.objects[hit]
            self.drag = {"kind": "move", "index": hit,
                         "dx": col - o["x"], "dy": row - o["y"],
                         "cx": col, "cy": row}
        else:                                     # по пустому — резинка-создание
            self.sel_obj = None
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
        if d["kind"] == "create":
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
        if d["kind"] == "create":
            x1, y1 = d["x1"], d["y1"]
            if c:
                x1, y1 = c
            x, y, w, h = self._norm_rect(d["x0"], d["y0"], x1, y1)
            if d["t"] != 0:                        # «небо» не заводим
                self.objects.append({"t": d["t"], "x": x, "y": y, "w": w, "h": h})
                self.sel_obj = len(self.objects) - 1
        elif c:                                    # завершаем перемещение
            o = self.objects[d["index"]]
            o["x"] = max(0, min(self.cols - o["w"], c[0] - d["dx"]))
            o["y"] = max(0, min(self.rows - o["h"], c[1] - d["dy"]))
        self._recompute_grid()
        self.dirty = True
        self._set_status("не сохранено")
        self.render_all()

    def _del_selected(self, _=None):
        if self.mode.get() != "object" or self.sel_obj is None:
            return
        del self.objects[self.sel_obj]
        self.sel_obj = None
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

    def _norm_rect(self, x0, y0, x1, y1):
        """Углы резинки -> (x, y, w, h) в тайлах (x=колонка, y=строка)."""
        return (min(x0, x1), min(y0, y1), abs(x1 - x0) + 1, abs(y1 - y0) + 1)

    def _recompute_grid(self):
        """grid производен от объектов — переразвернуть для рендера/коллизий."""
        self.grid = list(G.expand_objects(self.cols, self.rows, self.objects))

    def _draw_preview(self):
        d = self.drag
        if not d:
            return
        if d["kind"] == "create":
            x, y, w, h = self._norm_rect(d["x0"], d["y0"], d["x1"], d["y1"])
        else:
            o = self.objects[d["index"]]
            x = max(0, min(self.cols - o["w"], d["cx"] - d["dx"]))
            y = max(0, min(self.rows - o["h"], d["cy"] - d["dy"]))
            w, h = o["w"], o["h"]
        self.canvas.create_rectangle(
            x * self.cell, y * self.cell,
            (x + w) * self.cell, (y + h) * self.cell,
            outline="#%02x%02x%02x" % OBJ_SEL, width=2, tags=("preview",))

    def _clear_preview(self):
        self.canvas.delete("preview")

    def _on_map_menu(self, e):
        """ПКМ на карте: взять тайл под курсором в кисть + меню быстрых действий."""
        c = self._cell_at(e)
        if not c:
            return
        ti = self.grid[c[0] * self.rows + c[1]]
        self.select_tile(ti)
        m = tk.Menu(self.root, tearoff=0)
        m.add_command(label=f"Кисть: tile {ti}", state="disabled")
        m.add_separator()
        m.add_command(label="■ сплошной (стена)",
                      command=lambda: self._quick_prop(ti, "wall"))
        m.add_command(label="▬ платформа (опора)",
                      command=lambda: self._quick_prop(ti, "platform"))
        m.add_command(label="□ проходной",
                      command=lambda: self._quick_prop(ti, "pass"))
        try:
            m.tk_popup(e.x_root, e.y_root)
        finally:
            m.grab_release()

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
        в grid (фолбэк-рисование по-тайлово)."""
        self.sel_obj = None
        self.drag = None
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
            return
        nc = max(1, min(512, nc))
        nr = max(1, min(255, nr))
        if nc == self.cols and nr == self.rows:
            self._set_status("размер не изменился")
            self.w_var.set(nc)
            self.h_var.set(nr)
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
        self.grid = new
        self.level["cols"] = new_cols
        self.level["rows"] = new_rows
        self.level["grid"] = new
        # в режиме объектов сдвиг grid делаем и для объектов (иначе save
        # перезтёр бы ресайз, развернув старые координаты в новые рамки)
        if self.mode.get() == "object":
            self.objects = cover_rectangles(new_cols, new_rows, new)
            self.sel_obj = None
        self.dirty = True
        self.render_all()

    # ---- сохранение -------------------------------------------------------
    def save(self):
        """Объекты — источник истины: пишем objects.json, а level.json —
        развёрнутая grid-картой копия (для фолбэка и парити-сверки)."""
        if self.mode.get() == "tile":
            self.objects = cover_rectangles(self.cols, self.rows, self.grid)
        else:
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
    from tkinter import messagebox
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
