#!/usr/bin/env python3
"""level_editor.py — редактор уровня Mario 16-цвет (Tkinter).

Запуск:  python3 tools/level_editor.py
Нужен Tkinter: sudo apt install python3-tk  (Pillow уже в зависимостях проекта).

Что умеет:
  * палитра всех тайлов (src/tiles/*.png) — клик выбирает кисть;
  * поле уровня (src/level.json) — ЛКМ рисует выбранным тайлом (и перетаскиванием),
    ПКМ берёт тайл под курсором в кисть;
  * свойства выбранного тайла (wall / platform / transparent) — галочки справа
    ИЛИ ПКМ на тайле карты (меню «сплошной/платформа/проходной»); применяются
    к тайлу целиком (во всех клетках уровня);
  * «Подсветить выбранный тайл» — жёлтая рамка на всех клетках текущего тайла;
  * галочка «Показать твёрдость» — полупрозрачная заливка на поле:
        без заливки — проходной,  красная — стена,  синяя — платформа;
  * Сохранение пишет src/level.json и src/tiles.json (после — `make`).

Источник истины — сами файлы; графика тайлов правится отдельно.
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

COLL_RED = (224, 58, 58)      # сплошной (wall)
COLL_BLUE = (58, 123, 224)    # платформа (platform)
HL_COLOR = (255, 212, 0)      # жёлтая рамка «это текущий тайл-кисть» на карте
OVERLAY_ALPHA = 0.45          # сила полупрозрачной заливки твёрдости (0..1)
GRID_LINE = (128, 128, 128, 128)   # сетка границ тайлов: серый, 50% прозрачности
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
        self.cols = self.level["cols"]
        self.rows = self.level["rows"]
        self.grid = self.level["grid"]              # col-major: grid[col*rows+row]
        self.tile_orig = self._load_tile_images()
        self.dirty = False
        self.selected = 0
        self.cell = 12
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
        ttk.Button(bar, text="Сохранить", command=self.save).pack(side=tk.LEFT, padx=(14, 4))
        self.status = ttk.Label(bar, text="готово")
        self.status.pack(side=tk.LEFT, padx=8)

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
            "Отметь галочками — применится ко\n"
            "всем клеткам этого тайла на карте.\n\n"
            "ЛКМ на карте — рисовать кистью.\n"
            "ПКМ на карте — меню: кисть/твёрдость.\n"
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
        50% прозрачности) поверх. Сетка НЕ пишется в self.screen, чтобы
        дорисовка одной клетки не стирала линии; толщина 1px при любом масштабе."""
        if not self.grid_var.get():
            return self.screen
        W, H = self.screen.size
        ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(ov)
        for x in range(0, W, self.cell):
            d.line([(x, 0), (x, H)], fill=GRID_LINE, width=1)
        for y in range(0, H, self.cell):
            d.line([(0, y), (W, y)], fill=GRID_LINE, width=1)
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
        self._paint(e)

    def _on_drag(self, e):
        self._paint(e)

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

    # ---- сохранение -------------------------------------------------------
    def save(self):
        self.level["grid"] = self.grid
        with open(os.path.join(SRC, "level.json"), "w") as f:
            json.dump(self.level, f)
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
