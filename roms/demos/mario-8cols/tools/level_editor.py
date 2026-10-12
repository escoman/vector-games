#!/usr/bin/env python3
"""level_editor.py — редактор уровня Mario 16-цвет (Tkinter).

Запуск:  python3 tools/level_editor.py
Нужен Tkinter: sudo apt install python3-tk  (Pillow уже в зависимостях проекта).

МОДЕЛЬ: уровень — список ЭКземПЛЯРОВ префабов (src/objects.json v2), а не тайлы
и не прямоугольники:
    {"pf": "Труба вверх", "x": 44, "y": 56, "h": 6}
w/h есть только у тянущихся осей; остальное — нативный размер префаба. Тайловая
сетка (grid) ПРОИЗВОДНА: PL.expand_instances разворачивает список по порядку.
Порядок списка = z-order: первый печатается первым, последний — поверх.

ЧТО УМЕТ:
  * палитра = библиотека префабов (src/prefabs.json, группы по section);
    секция «одиночные» (авто-тайлы «Тайл N») в палитре не показывается вовсе —
    уровнем правят целыми объектами, а не отдельными плитками;
  * клик по карточке префаба ВКЛЮЧАЕТ штамп (он же инструмент), клик по той же
    карточке ВЫКЛЮЧАЕТ: инструмент живёт в палитре, отдельная кнопка «снять»
    ему не нужна (Esc тоже работает); выбранный штамп помечен рамкой карточки;
  * ЛКМ выбранным штампом ставит ЦЕЛЫЙ префаб, протяжка задаёт размер там, где
    оси помечены stretch_x/stretch_y (шапка трубы, бугор облака, углы не рвутся);
  * «повторять сеткой по области» — N экземпляров одного префаба с шагом X/Y;
  * ЛКМ по готовому экземпляру — выделить и двигать ЦЕЛИКОМ (хит-тест сверху
    вниз: кто поверх, того и берём); Del — удалить; ПКМ — меню («растянуть
    до» — размер стоявшего, «заменить объект…» — он же на том же месте, но
    другим префабом или одиночным тайлом, наверх/вниз/дублировать/удалить,
    там же твёрдость тайла под курсором); любое нажатие куда угодно в окне —
    и клик по карте, и клик по палитре/панели/тулбару, и клавиша — меню
    закрывают: висящее поверх другой карты меню бесполезно;
  * PgUp/PgDn (Ctrl+↑/↓) — переставить экземпляр в списке, то есть z-order;
  * протяжка ЛКМ по пустому месту (без штампа) — РАМКА группового выделения,
    средней кнопкой рамка тянется откуда угодно, хоть над объектами:
    попадает всё, что рамка ЗАДЕЛА (не обязательно целиком в ней); Del
    удаляет группу целиком, тянуть за любой член группы — двигает группу,
    Shift-клик и Shift-протяжка добавляют к группе, Ctrl+A — выделить всё;
  * панель «На карте» — список экземпляров в z-order, двойной клик переносит
    камеру на экземпляр (счётчики и топ префабов убраны, смета — в тулбаре);
  * «Изменить размеры карты…» — отдельное окно с W/H и якорем содержимого;
  * «Редактор префабов…» открывает отдельным процессом tools/prefab_editor.py,
    «⟳ префабы» перечитывает библиотеку после правок в нём.

z-order и блоки: ROM печёт окно по 32-колоночным блокам, и внутри блока порядок
задаёт список. Если два перекрывающихся экземпляра лежат в РАЗНЫХ блоках, их
порядок наложения в ROM задаёт блок, а не список — редактор считает такие
расхождения (z-conflict) и показывает их в статусе и при сохранении.

ЛИМИТЫ: размеры карты и экземпляры проверяются формулами сборки (см. MAX_COLS и
_limits()), а не только рамками спинбоксов, — иначе 512x255 проходит редактор и
падает на make. Смета образа = база из mario-8c.map + tile_win (64·rows) +
pf_data (4·экземпляров) + словарь вариантов (3·вариантов + 5·rect'ов) + pf_start.

Сохранение пишет src/objects.json (v2), src/level.json (cols/rows/grid — для
совместимости генератора и фолбэка) и src/tiles.json (твёрдость). src/prefabs.json
перезаписывается только если «заменить на тайл» завёл в библиотеке новый
одиночный тайл — без этого объекты на карте висели бы на несуществующем префабе.
Ничего не пишет, если валидация или парити не прошли. После — `make`.
"""
import json
import os
import re
import subprocess
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
sys.path.insert(0, HERE)

# prefablib — общий с окном префабов и генератором движок: пути, лимиты сборки,
# загрузка тайлов и библиотеки, экземпляры, растяжение штампа, словарь вариантов.
# Окно уровня обязано сидеть на ТОЙ ЖЕ копии логики карты, что и gen_assets:
# иначе превью редактора разойдётся с тем, что напечатает ROM.
import gen_assets as G                                     # noqa: E402
from prefablib import (                                    # noqa: E402,F401
    SRC as PF_SRC, ROM, MAP, LEVEL_INC, PREFAB_FILE, TILES_FILE, LEVEL_FILE,
    OBJECTS_FILE, SKY, COLL_RED, COLL_BLUE, TILE_PX, PF_SECTIONS, MAX_COLS,
    MAX_ROWS, MIN_COLS, MIN_ROWS, TILEMAP_LIMIT, TILE_INDEX_LIMIT, MAX_VARIANTS,
    WIN_RAM_PER_ROW, OBJ_WIN_STEP, OBJ_BYTES, INST_BYTES, RECT_BYTES,
    VAR_BYTES, IMAGE_LIMIT, defines, load_level, load_tiles, tile_props,
    load_tile_images, frame_color, load_prefabs, save_prefabs, stretch_axis,
    stamp_size, stamp_cells, stamp_objects, stamp_points, match_grid, grow_fit,
    single_tile_prefab, single_tile_stretchable, section_of, instance_size,
    load_instances, save_instances, expand_instances, expand_by_blocks,
    build_variants, variants_bytes, level_bytes, validate_instances)
from uiutil import maximize as _maximize                  # noqa: E402

OVERLAY_ALPHA = 0.45          # сила полупрозрачной заливки твёрдости (0..1)
GRID_LINE = (128, 128, 128, 128)   # сетка границ тайлов: серый, 50% прозрачности
BLOCK_LINE = (176, 176, 190, 255)  # границы 32-колоночных блоков: жирнее (2 px)
#                                   и полностью непрозрачны — тайловая сетка лишь 50%
OBJ_LINE = (78, 201, 176)     # бирюзовая рамка экземпляра
OBJ_SEL = (255, 90, 200)      # рамка выбранного экземпляра
OBJ_WARN = (255, 150, 60)     # рамка: у экземпляра есть z-конфликт с блоком
OBJ_BROKEN = (220, 40, 40)    # рамка: экземпляр ссылается на несуществующий префаб
BROKEN_SECTION = "битые ссылки"   # служебная секция плейсхолдеров: вне PF_SECTIONS,
#                                   в палитру не попадает
PAL_THUMB = 32
PAL_GAP = 6
PF_THUMB = 3 * TILE_PX       # превью в палитре: px на тайл (3 => тайл 24 px)
PF_COL_W = 236               # ширина строки палитры префабов, px
PF_HDR_H = 18                # высота строки «— раздел —» в палитре (как в редакторе
#                               префабов)
PF_SEC_GAP = 14              # пустая строка МЕЖДУ разделами палитры
STAMP_ALPHA = 130            # 0..255 непрозрачность призрака штампа на карте
SINGLE_SECTION = "одиночные"  # секция авто-префабов «Тайл N» (фильтр по умолчанию)
_UNSET = object()            # _set_sel(i): группа = ровно один якорь
SHIFT_MASK = 0x0001          # e.state: бит Shift (он же «добавить к группе»)


def _spin(var, default, lo, hi):
    """Число из Spinbox: введённый руками мусор не должен ронять постановку
    штампа (команда у спинбоксов только на стрелках, не на вводе с клавиатуры)."""
    try:
        v = int(var.get())
    except (ValueError, tk.TclError):
        return default
    return max(lo, min(hi, v))


def _in_menu_tree(menu, widget):
    """Нажатие пришло по самому меню или по его каскаду (подменю — дети menu).
    Пункты рисует виджет Menu, своих детей-виджетов у него нет, поэтому
    достаточно пройтись по master'ам: клик по списку — дело самого меню,
    редактору там нечего разрушать (меню, уничтоженное в момент нажатия, свою
    команду не доигрывает)."""
    while isinstance(widget, tk.Misc):
        if widget is menu:
            return True
        widget = widget.master
    return False


class LevelEditor:
    def __init__(self, root):
        self.root = root
        root.title("Level Editor — Mario 16cols / Vector-06C")
        root.geometry("1200x760")

        self.level, self.tiles = self._load_json()
        self.cols = int(self.level["cols"])
        self.rows = int(self.level["rows"])
        self.tile_orig = self._load_tile_images()
        self.prefabs = self._load_prefabs()
        self.by_name = {pf["name"]: pf for pf in self.prefabs}
        self.inst = self._load_instances()          # источник истины (v2)
        self.broken = {}                            # имя -> число висячих ссылок
        self._broken_warned = False                 # диалог — один раз за сессию
        self._sync_broken(warn=True)                # плейсхолдеры + предупреждение
        self.grid = bytearray()                     # производная тайлкарта
        self.dirty = False
        self.cell = 12
        self.sel = None                             # индекс выбранного экземпляра
        self.sel_group = set()          # все выделенные рамкой (sel — якорь)
        self.drag = None                            # состояние перетаскивания
        self.stamp = None                           # выбранный префаб или None
        self.zdiff = 0                              # клеток с z-конфликтом блоков
        self._ghosts = []                           # PhotoImage призраков штампа
        self._resize_win = None                     # окно «Размеры карты» (одно)
        self._map_menu = None                       # открытый ПКМ-меню (одно)
        self.pf_added = []                          # одиночные тайлы, заведённые тут
        # твёрдость по умолчанию скрыта: на целой карте она превращается в кашу
        # из красных/синих пятен, а правится она и из ПКМ
        self.show_overlay = tk.BooleanVar(value=False)
        self.grid_var = tk.BooleanVar(value=True)
        self._base = None                           # кэш сметы из map/rom
        self._vars = None                           # кэш словаря вариантов
        self._pending = ""                          # статус до появления labels

        self._build_ui()
        self._recompute_grid()
        self._rebuild_scaled()
        self.render_all()
        self._refresh_map_panel()
        self._update_budget()
        self._set_status(self._pending or "готово")

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

    def _load_instances(self):
        """src/objects.json v2 — список экземпляров. Нет файла (или старая
        версия) — пустой список: mигрировать карту умеет tools/prefab_migrate.py,
        редактор же не имеет права молча выбрасывать то, чего не понимает
        (load_instances на v1 сам падает с внятным сообщением)."""
        cols, rows, inst = load_instances()
        if inst is None:
            self._pending = ("objects.json нет: пустая карта (миграция: "
                             "tools/prefab_migrate.py)")
            return []
        if (cols, rows) != (self.cols, self.rows):
            messagebox.showwarning(
                "Размер карты",
                "objects.json: %d×%d, а level.json: %d×%d — взялся размер из "
                "level.json, экземпляры могут не влезать в карту."
                % (cols, rows, self.cols, self.rows))
        return [dict(i) for i in inst]

    def _load_tile_images(self):
        imgs = []
        for t in self.tiles["tiles"]:
            p = os.path.join(SRC, t["file"])
            imgs.append(Image.open(p).convert("RGB") if os.path.isfile(p)
                        else Image.new("RGB", (8, 8), SKY))
        return imgs

    def _load_prefabs(self):
        """src/prefabs.json — именованные составные объекты (штампы).

        Нет файла / битые индексы тайлов — не фатально: палитра просто пустая,
        но и ставить тогда нечего. Индексы вне набора отсекаем, чтобы опечатка в
        JSON не рендила traceback на первом же превью.
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

    # ---- словарь вариантов (для лимитов и счётчиков) ----------------------
    def _variants(self):
        """Варианты (префаб, w, h) для ТЕКУЩЕГО списка — кэш до следующей правки."""
        if self._vars is None:
            self._vars = build_variants(self.prefabs, self.inst)
        return self._vars[0]

    def _touch(self):
        """Правка модели: смета/варианты/grid пересчитываются заново."""
        self._vars = None
        self.dirty = True

    # ---- лимиты: те же формулы, что у сборки ------------------------------
    def _image_base(self):
        """Байт в образе, НЕ зависящих от размеров уровня: вершина образа из
        map-файла линковщика (__bss_clib_tail) минус то, что размером уровня и
        задано — tile_win (64·rows), pf_data (4·экземпляров), словари вариантов
        (3·вариантов + 5·rect'ов) и pf_start (2·(блоки+1)). Нет map — оценка по
        .rom (он = образ + векторная страница 0x0000..0x00FF); нет и ROM — None:
        смета не проверяется."""
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
        d = defines(LEVEL_INC, ("LEVEL_ROWS", "PF_COUNT", "PF_VARIANTS",
                                "PF_RECTS", "OBJ_WIN_BLOCKS"))
        if len(d) != 5:
            return None
        blocks = d["OBJ_WIN_BLOCKS"]
        base = used - (WIN_RAM_PER_ROW * d["LEVEL_ROWS"]
                       + INST_BYTES * d["PF_COUNT"]
                       + VAR_BYTES * d["PF_VARIANTS"]
                       + RECT_BYTES * d["PF_RECTS"]
                       + 2 * (blocks + 1))
        if base < 0:                           # map/rom расходится с level.inc
            return None
        self._base = base
        return base

    def _budget(self, cols, rows, inst, variants):
        """Оценка размера образа (0x0100..0x7FFF) для таких карты и списка;
        None — если опереться не на что (нет ни map, ни ROM)."""
        base = self._image_base()
        if base is None:
            return None
        blocks = (cols + OBJ_WIN_STEP - 1) // OBJ_WIN_STEP
        return (base + WIN_RAM_PER_ROW * rows + level_bytes(inst, variants)
                + 2 * (blocks + 1))

    def _limits(self, cols=None, rows=None, inst=None):
        """Претензии к уровню — пустой список значит «make пройдёт». Формулы
        срисованы с gen_assets: validate_instances (id варианта 12 бит, x ≤ 511,
        y/w/h байты, экземпляр целиком в карте), build_level (rows ≤ 255,
        cols·rows ≤ 65535) и смета образа, которую вообще никто, кроме загрузки
        на machine, не ловит."""
        cols = self.cols if cols is None else int(cols)
        rows = self.rows if rows is None else int(rows)
        inst = self.inst if inst is None else inst
        bad = []
        if not MIN_COLS <= cols <= MAX_COLS:
            bad.append("Ширина %d: можно %d…%d (RAM-окно tile_win = %d колонок, "
                       "x ≤ 511 в экземпляре)" % (cols, MIN_COLS, MAX_COLS,
                                                  WIN_RAM_PER_ROW))
        if not MIN_ROWS <= rows <= MAX_ROWS:
            bad.append("Высота %d: можно %d…%d (экран %d строки, y ≤ 255 — "
                       "байт в экземпляре)" % (rows, MIN_ROWS, MAX_ROWS, MIN_ROWS))
        if cols * rows > TILEMAP_LIMIT:
            bad.append("W×H = %d > %d — тайлкарта адресуется 16 битами"
                       % (cols * rows, TILEMAP_LIMIT))
        if bad:
            return bad
        errs = validate_instances(cols, rows, self.prefabs, inst)
        if errs:
            bad.append(errs[0] if len(errs) == 1
                       else "%s (и ещё %d таких)" % (errs[0], len(errs) - 1))
            return bad
        variants = build_variants(self.prefabs, inst)[0]
        est = self._budget(cols, rows, inst, variants)
        if est is not None and est > IMAGE_LIMIT:
            bad.append("образ ≈ %d Б > %d Б (0x0100…0x7FFF): tile_win жрёт %d Б "
                       "ОЗУ, словарь — %d Б. Меньше строк H или меньше "
                       "экземпляров." % (est, IMAGE_LIMIT, WIN_RAM_PER_ROW * rows,
                                         variants_bytes(variants)))
        return bad

    def _update_budget(self):
        self._sync_size_lbl()
        est = self._budget(self.cols, self.rows, self.inst, self._variants())
        self.budget_lbl.config(
            text=("смета образа ≈ %d / %d Б · %d экз. / %d вариантов"
                  % (est, IMAGE_LIMIT, len(self.inst), len(self._variants())))
            if est else "смета: нет mario-8c.map/.rom")

    def _sync_size_lbl(self):
        """Текущий размер карты рядом с кнопкой ресайза: без него окно
        «Изменить размеры» открывается вслепую."""
        self.size_lbl.config(
            text="карта %d×%d · лимиты %d..%d × %d..%d"
            % (self.cols, self.rows, MIN_COLS, MAX_COLS, MIN_ROWS, MAX_ROWS))

    # ---- UI ---------------------------------------------------------------
    def _build_ui(self):
        bar = ttk.Frame(self.root, padding=6)
        bar.pack(side=tk.TOP, fill=tk.X)
        ttk.Checkbutton(bar, text="Показать твёрдость",
                        variable=self.show_overlay,
                        command=self.render_all).pack(side=tk.LEFT)
        ttk.Checkbutton(bar, text="Сетка тайлов",
                        variable=self.grid_var,
                        command=self.render_all).pack(side=tk.LEFT, padx=(12, 0))
        ttk.Label(bar, text="  Масштаб:").pack(side=tk.LEFT)
        self.zoom_var = tk.StringVar(value="12")
        z = ttk.OptionMenu(bar, self.zoom_var, "12", "8", "12", "16", "24",
                           command=self._on_zoom)
        z.config(width=5)
        z.pack(side=tk.LEFT)
        ttk.Button(bar, text="Сохранить", command=self.save).pack(side=tk.LEFT,
                                                                  padx=(14, 4))
        self.status = ttk.Label(bar, text="готово")
        self.status.pack(side=tk.LEFT, padx=8)

        # вторая панель: размеры карты правятся ОТДЕЛЬНЫМ окном (в тулбаре
        # только кнопка: spinbox'ы размера иначе живут рядом с рабочими
        # инструментами и просятся в случайный клик)
        bar2 = ttk.Frame(self.root, padding=(6, 0, 6, 6))
        bar2.pack(side=tk.TOP, fill=tk.X)
        ttk.Button(bar2, text="Изменить размеры карты…",
                   command=self._open_resize).pack(side=tk.LEFT)
        self.size_lbl = ttk.Label(bar2, foreground="#777")
        self.size_lbl.pack(side=tk.LEFT, padx=8)
        self.budget_lbl = ttk.Label(bar2, foreground="#777")
        self.budget_lbl.pack(side=tk.RIGHT, padx=6)
        self._sync_size_lbl()

        # третья панель: параметры штампа (префаба). Самого штампа тут нет —
        # он включается кликом по карточке палитры и там же виден рамкой
        bar3 = ttk.Frame(self.root, padding=(6, 0, 6, 6))
        bar3.pack(side=tk.TOP, fill=tk.X)
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
        ttk.Button(bar3, text="Редактор префабов…",
                   command=self.open_prefab_editor).pack(side=tk.LEFT, padx=(14, 0))
        ttk.Button(bar3, text="⟳ префабы",
                   command=self.reload_prefabs).pack(side=tk.LEFT, padx=(4, 0))

        # легенда
        leg = ttk.Frame(self.root, padding=(8, 0, 8, 4))
        leg.pack(side=tk.TOP, fill=tk.X)
        ttk.Label(leg, text="проходной: без заливки    "
                           "сплошной (wall): красная заливка    "
                           "платформа: синяя заливка    "
                           "рамка: выбранный экземпляр").pack(side=tk.LEFT)

        body = ttk.Frame(self.root)
        body.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        # слева: палитра префабов (единственный инструмент постановки)
        left = ttk.Frame(body)
        left.pack(side=tk.LEFT, fill=tk.Y)
        pw = PF_COL_W
        ttk.Label(left, text="Префабы — клик ставит ЦЕЛЫЙ объект").pack(anchor=tk.W)
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
        # средняя кнопка — рамка, всегда рамка: на плотной карте пустую клетку
        # под курсором найти сложно, а выделять надо поверх уже стоящих объектов
        self.canvas.bind("<Button-2>", lambda e: self._on_click(e, box=True))
        self.canvas.bind("<B2-Motion>", self._on_drag)
        self.canvas.bind("<ButtonRelease-2>", self._on_release)
        self.canvas.bind("<MouseWheel>", self._on_wheel)
        self.canvas.bind("<Button-4>", lambda e: self._on_wheel(e, -1))
        self.canvas.bind("<Button-5>", lambda e: self._on_wheel(e, 1))
        self.canvas.bind("<ButtonRelease-1>", self._on_release)
        # Любое нажатие куда угодно в окне — снять контекстное меню: оно живёт
        # в отдельном окне, и раньше клик по тулбару, палитре или «На карте»
        # его не трогал — висело уже поверх другого объекта.
        self.root.bind_all("<ButtonPress>", self._on_any_press, add="+")
        self.root.bind_all("<KeyPress>", lambda _e: self._close_menu(), add="+")
        self.root.bind("<Delete>", self._del_selected)
        self.root.bind("<BackSpace>", self._del_selected)
        self.root.bind("<Escape>", self._on_escape)   # снять штамп и рамку
        for key, step in (("<Next>", +1), ("<Prior>", -1),
                          ("<Control-Down>", +1), ("<Control-Up>", -1)):
            self.root.bind(key, lambda e, s=step: self._move_z(s))
        self.root.bind("<Control-d>", lambda e: self._dup_selected())
        self.root.bind("<Control-a>", lambda e: self._select_all())

        # справа — только «На карте»: панель свойств тайла убрана вместе с
        # картинкой (твёрдость правится из ПКМ-меню на карте)
        right = ttk.Frame(body, padding=8)
        right.pack(side=tk.LEFT, fill=tk.Y)
        self._build_map_panel(right)
        ttk.Label(right, foreground="#777", justify=tk.LEFT, text=(
            "ЛКМ по экземпляру — выделить, тянуть —\n"
            "двигать целый префаб; Del — удалить.\n"
            "Протяжка по пустому месту (или средней\n"
            "кнопкой — откуда угодно) — рамка: в неё\n"
            "попадают все задетые объекты, Del снимает\n"
            "всю группу, тянуть за любой — двигает все,\n"
            "Shift — добавить к группе, Ctrl+A — всё.\n"
            "Клик по карточке — штамп вкл/выкл; со\n"
            "штампом ЛКМ ставит объект (тянутся\n"
            "только stretch-оси; «повторять» — сетка\n"
            "копий). Размер стоявшего — ПКМ по нему\n"
            "→ «растянуть до»; им же объект меняется\n"
            "на другой («заменить объект…»: из\n"
            "библиотеки или на одиночный тайл).\n"
            "PgUp/PgDn — z-order (вниз = поверх),\n"
            "Ctrl+D — дубликат; ПКМ — меню, в нём\n"
            "и твёрдость тайла под курсором; любое\n"
            "нажатие мимо меню его закрывает.\n"
            "Двойной клик в списке «На карте» —\n"
            "перейти к экземпляру.\n\n"
            "После «Сохранить» — make.")).pack(anchor=tk.W, pady=(12, 0))

    # ---- палитра префабов -------------------------------------------------
    def _pf_list(self):
        """Префабы палитры: группировка по секциям (PF_SECTIONS), внутри секции —
        по имени. Секция «одиночные» (авто-тайлы «Тайл N») не показывается вовсе:
        уровнем правят целыми объектами, а не отдельными плитками."""
        by_name = lambda pf: (pf.get("name") or "").lower()
        pool = [pf for pf in self.prefabs if not pf.get("_broken")]
        known = [pf for pf in pool if section_of(pf) in PF_SECTIONS]
        out = []
        for sec in PF_SECTIONS:
            if sec == SINGLE_SECTION:
                continue
            out.extend(sorted((pf for pf in known if section_of(pf) == sec),
                              key=by_name))
        # секции нет в PF_SECTIONS — в конец, тоже по имени
        out.extend(sorted((pf for pf in pool
                           if section_of(pf) not in PF_SECTIONS),
                          key=by_name))
        return out

    def _grid_image(self, cells, scale, alpha=255):
        """Сетка тайлов -> RGBA-картинка (0 = прозрачно). Один и тот же код для
        превью в палитре (scale=PF_THUMB) и призрака на карте (scale=self.cell)."""
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
        self._pf_shown = self._pf_list()
        y = 6
        sec = None
        for i, pf in enumerate(self._pf_shown):
            s = section_of(pf)
            if s != sec:
                if sec is not None:
                    y += PF_SEC_GAP        # пустая строка перед новым разделом
                sec = s
                # заголовок по центру колонки (как в редакторе префабов): он не
                # привязан к строке префаба и на левом краю читается ещё одной
                # карточкой
                c.create_text(PF_COL_W // 2, y, anchor=tk.N,
                              text="— " + s + " —", fill="#888",
                              font=("DejaVu Sans", 9, "bold"))
                y += PF_HDR_H
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
        if sec is not None:
            y += PF_SEC_GAP                # и после последнего раздела
        c.configure(scrollregion=(0, 0, PF_COL_W, y))
        self._update_prefab_sel()

    def _update_prefab_sel(self):
        c = self.pfcv
        if self._pf_sel:
            c.delete(self._pf_sel)
        self._pf_sel = None
        if self.stamp is None or self.stamp not in self._pf_shown:
            return
        i = self._pf_shown.index(self.stamp)
        y0, y1 = self._pf_rows[i]
        self._pf_sel = c.create_rectangle(2, y0, PF_COL_W, y1,
                                          outline="#4ec9b0", width=2)
        total = c.cget("scrollregion").split()[-1]
        if total and int(total) > 0:
            c.yview_moveto(min(1.0, max(0.0, (y0 - c.winfo_height() / 2)
                                        / int(total))))

    def select_stamp(self, i):
        """Клик по карточке: включить штамп, а по уже выбранной — выключить.
        Инструмент и так видно по рамке карточки, поэтому вторая кнопка
        «снять штамп» была чистым дублем рядом с Esc.
        Выделение стоявшего экземпляра снимается: править чужой объект и
        ставить новый одним кликом нельзя."""
        if i is None or not 0 <= i < len(self._pf_shown):
            self.clear_stamp()
            return
        pf = self._pf_shown[i]
        if self.stamp is not None and self.stamp["name"] == pf["name"]:
            self.clear_stamp()
            self._set_status("штамп снят")
            return
        self.stamp = pf
        self._set_sel(None)
        self._update_prefab_sel()
        self._sync_step_state()
        self.render_all()
        self._sync_map_sel()
        self._set_status("штамп «%s» · %s — ЛКМ по карте ставит его"
                         % (pf["name"], self._stretch_hint(pf)))

    @staticmethod
    def _stretch_hint(pf):
        """Оси растяжения одной строкой — в статус после выбора штампа."""
        st = (("↔" if pf.get("stretch_x") else "")
              + ("↕" if pf.get("stretch_y") else ""))
        return "тянется " + st if st else "штатный размер"

    def clear_stamp(self, _=None, silent=False):
        self.stamp = None
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
        self.stepy_box.config(state=state)

    def open_prefab_editor(self):
        """Окно префабов — ОТДЕЛЬНЫМ процессом: своё Tk-приложение, своё
        состояние библиотеки, никаких общих с картой структур."""
        try:
            subprocess.Popen([sys.executable,
                              os.path.join(HERE, "prefab_editor.py")],
                             cwd=os.path.abspath(os.path.join(HERE, "..")))
        except OSError as exc:
            messagebox.showerror("Редактор префабов", str(exc))
            return
        self._set_status("окно префабов открыто — после правок «⟳ префабы»")

    def reload_prefabs(self):
        """Перечитать src/prefabs.json (например, после окна префабов).

        Экземпляры, ссылающиеся на исчезнувшие префабы, НЕ удаляем молча:
        определение такого префаба остаётся в памяти (и уедет в prefabs.json
        при сохранении) — иначе _recompute_grid падает KeyError по мёртвому
        имени, и «⟳» роняет редактор. Так же выживают одиночные тайлы,
        заведённые заменой и ещё не записанные в файл."""
        old = {pf["name"]: pf for pf in self.prefabs}
        n0 = len(self.prefabs)
        self.prefabs = self._load_prefabs()
        self.by_name = {pf["name"]: pf for pf in self.prefabs}
        self.pf_added = []      # перечитали файл — то, что не сохранено, сгорело
        used = {o["pf"] for o in self.inst}
        kept = [pf for name, pf in sorted(old.items())
                if name not in self.by_name and name in used]
        if kept:
            self.prefabs += kept
            self.by_name.update({pf["name"]: pf for pf in kept})
            self.pf_added += kept
        # штамп перепривязать к новому dict'y ДО пересборки палитры: рамка
        # ищет его в списке карточек, а старый экземпляр там не живёт
        if self.stamp is not None:
            self.stamp = self.by_name.get(self.stamp["name"])
        self._touch()
        self._build_prefab_panel()
        self._recompute_grid()
        self.render_all()
        self._refresh_map_panel()
        self._set_status("префабы: было %d, стало %d%s — не сохранено"
                         % (n0, len(self.prefabs),
                            " · %d держим: на них стоят экземпляры"
                            % len(kept) if kept else ""))

    # ---- рендер поля ------------------------------------------------------
    def _rebuild_scaled(self):
        self.scaled = [im.resize((self.cell, self.cell), Image.NEAREST)
                       for im in self.tile_orig]

    def _draw_cell(self, x0, y0, ti):
        """Клетка в self.screen (PIL): тайл + полупрозрачная заливка твёрдости
        (красная — стена, синяя — платформа), если оверлей включён."""
        self.screen.paste(self.scaled[ti], (x0, y0))
        if self.show_overlay.get():
            fc = frame_color(self.tiles["tiles"][ti])
            if fc:
                box = (x0, y0, x0 + self.cell, y0 + self.cell)
                region = self.screen.crop(box)
                tint = Image.new("RGB", (self.cell, self.cell), fc)
                self.screen.paste(Image.blend(region, tint, OVERLAY_ALPHA), (x0, y0))

    def render_all(self):
        W, H = self.cols * self.cell, self.rows * self.cell
        self.screen = Image.new("RGB", (W, H), SKY)
        for col in range(self.cols):
            base = col * self.rows
            for row in range(self.rows):
                self._draw_cell(col * self.cell, row * self.cell,
                                self.grid[base + row])
        self.photo = ImageTk.PhotoImage(self._compose())
        c = self.canvas
        c.delete("all")
        c.create_image(0, 0, anchor=tk.NW, image=self.photo)
        c.configure(scrollregion=(0, 0, W, H))
        self._update_budget()

    def _compose(self):
        """Финальная картинка = базовый экран + сетка границ тайлов (1px серый,
        50%) + рамки экземпляров поверх. Рамки НЕ в self.screen: дорисовка
        клетки не должна стирать линии. Цвет: бирюзовый — просто экземпляр,
        оранжевый — у него есть z-конфликт с другим блоком, розовый — выбран."""
        need_grid = self.grid_var.get()
        W, H = self.screen.size
        if not need_grid and not self.inst:
            return self.screen
        ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(ov)
        if need_grid:
            for x in range(0, W, self.cell):
                # каждая OBJ_WIN_STEP-я колонка — шов блока (x>>5 меняет
                # номер блока, а блок задаёт порядок наложения в ROM): его
                # линию ведём жирнее (2 px) и плотнее тайловой сетки
                if (x // self.cell) % OBJ_WIN_STEP == 0:
                    d.line([(x, 0), (x, H)], fill=BLOCK_LINE, width=2)
                else:
                    d.line([(x, 0), (x, H)], fill=GRID_LINE, width=1)
            for y in range(0, H, self.cell):
                d.line([(0, y), (W, y)], fill=GRID_LINE, width=1)
        warn = self._conflict_set()
        for i, (x, y, w, h) in enumerate(self._boxes):
            box = [x * self.cell, y * self.cell,
                   (x + w) * self.cell - 1, (y + h) * self.cell - 1]
            color = OBJ_SEL if i in self.sel_group else (
                OBJ_BROKEN if self.inst[i]["pf"] in self.broken else
                OBJ_WARN if i in warn else OBJ_LINE)
            d.rectangle(box, outline=color + (255,), width=2)
        return Image.alpha_composite(self.screen.convert("RGBA"), ov).convert("RGB")

    def _sync_broken(self, warn=False):
        """Старт/редакт с висячей ссылкой (префаб переименовали или удалили, а
        уровень не обновили): НЕ падаем KeyError. Заводим безобидный плейсхолдер
        (пустой штамп 1×1, вне палитры), чтобы все lookup'ы by имени разрешились,
        помечаем такие экземпляры красной рамкой и один раз предупреждаем.
        Лечится: вернуть префабу то имя (правильно — переименовать В редакторе
        префабов, он прошивает уровень) либо переназначить объект. Пока не
        долечено — make собьётся (validate_instances назовёт эти же имена)."""
        real = {pf["name"] for pf in self.prefabs if not pf.get("_broken")}
        broken = {}
        for o in self.inst:
            if o["pf"] not in real:
                broken[o["pf"]] = broken.get(o["pf"], 0) + 1
        self.broken = broken
        for nm in broken:
            if nm not in self.by_name:
                pf = {"name": nm, "section": BROKEN_SECTION,
                      "grid": [[0]], "_broken": True}
                self.prefabs.append(pf)
                self.by_name[nm] = pf
        if warn and broken and not self._broken_warned:
            self._broken_warned = True
            lines = "\n".join("  • %s — %d экз." % (n, c)
                              for n, c in sorted(broken.items()))
            messagebox.showwarning(
                "Битые ссылки на префабы",
                "Экземпляры ссылаются на префабы, которых нет в библиотеке "
                "(их переименовали или удалили):\n\n%s\n\nПоказаны красной "
                "рамкой без тайлов. Верните префабам эти имена или переназначьте "
                "объекты. Правильное переименование, само прошивающее уровень, "
                "— в редакторе префабов (Сохранить)." % lines)

    # ---- экземплярная модель ----------------------------------------------
    def _recompute_grid(self):
        """grid производен от списка экземпляров и равен ТОМУ, что печатает ROM:
        развёртка по 32-колоночным блокам (expand_by_blocks = сортировка
        генератора). Отличие от «чистого» порядка списка — z-конфликт; считаем
        его, чтобы не выдавать превью, которого железка не повторит."""
        prefabs, inst = self.prefabs, self.inst
        self._sync_broken()                 # держать плейсхолдеры/red-рамки в тоне
        self.grid = bytearray(expand_by_blocks(self.cols, self.rows,
                                               prefabs, inst))
        nat = expand_instances(self.cols, self.rows, prefabs, inst)
        self.zdiff = sum(1 for a, b in zip(nat, self.grid) if a != b)
        self._boxes = [self._bbox(o) for o in inst]
        self._conf_cache = None

    def _bbox(self, inst):
        """Габарит экземпляра в тайлах: (x, y, w, h); w/h с учётом растяжения."""
        pf = self.by_name[inst["pf"]]
        w, h = instance_size(pf, inst)
        return int(inst["x"]), int(inst["y"]), w, h

    def _conflict_set(self):
        """Индексы экземпляров, у которых пересечение с экземпляром из ДРУГОГО
        якорного блока: генератор сортирует по x//32 (якорь), поэтому порядок
        наложения такой пары задаёт блок, а не список.

        Перебор по x с выходом за правый край: пересечься могут только объекты,
        чей x-start попал в габарит, то есть O(n·k) вместо O(n²) (k — ширина
        самого широкого префаба)."""
        if self._conf_cache is None:
            out = set()
            boxes = self._boxes
            order = sorted(range(len(boxes)), key=lambda i: boxes[i][0])
            n = len(order)
            for a in range(n):
                i = order[a]
                x, y, w, h = boxes[i]
                bi = x // OBJ_WIN_STEP
                for p in range(a + 1, n):
                    j = order[p]
                    xx, yy, ww, hh = boxes[j]
                    if xx >= x + w:
                        break
                    if bi == xx // OBJ_WIN_STEP:
                        continue
                    if yy >= y + h or y >= yy + hh:
                        continue
                    out.add(i)
                    out.add(j)
            self._conf_cache = out
        return self._conf_cache

    def _conflicts_of(self, i):
        """Список «конкурентов» экземпляра i (для статуса и контекстного меню)."""
        x, y, w, h = self._boxes[i]
        b = x // OBJ_WIN_STEP
        out = []
        for j, (xx, yy, ww, hh) in enumerate(self._boxes):
            if j == i or xx // OBJ_WIN_STEP == b:
                continue
            if (xx >= x + w or x >= xx + ww
                    or yy >= y + h or y >= yy + hh):
                continue
            out.append(j)
        return out

    def _mk_inst(self, pf, x, y, w, h):
        """Экземпляр по схеме v2: w/h пишем ТОЛЬКО когда они отличаются от
        нативного размера префаба — иначе в JSON лишний шум, а ROM и так берёт
        нативный."""
        nw, nh = stamp_size(pf, len(pf["grid"][0]), len(pf["grid"]))
        inst = {"pf": pf["name"], "x": int(x), "y": int(y)}
        if w != nw:
            inst["w"] = int(w)
        if h != nh:
            inst["h"] = int(h)
        return inst

    def _inst_at(self, col, row):
        """Хит-тест сверху вниз (обратный порядок списка = кто поверх).
        Сначала — по реальным тайлам префаба, потом по габариту: внутри
        «вырезов» составного объекта кликать тоже надо по нему."""
        miss = None
        for j in range(len(self.inst) - 1, -1, -1):
            x, y, w, h = self._boxes[j]
            if not (x <= col < x + w and y <= row < y + h):
                continue
            if miss is None:
                miss = j
            cells = stamp_cells(self.by_name[self.inst[j]["pf"]], w, h)
            if cells[row - y][col - x]:
                return j
        return miss

    def _after_edit(self, msg="не сохранено"):
        """Любая правка списка: кэш вариантов дохнет, grid и панель — пересобрать."""
        self._touch()
        self._recompute_grid()
        self.render_all()
        self._refresh_map_panel()
        self._set_status(msg)

    def _sel_inst(self):
        return None if self.sel is None else self.inst[self.sel]

    def _set_sel(self, i, group=_UNSET):
        """Выделение: self.sel — якорь (его крутят PgUp, его дублируют Ctrl+D,
        его показывает панель), self.sel_group — всё, что обведено рамкой и что
        снимает Del. По умолчанию группа = ровно якорь: одиночный клик по
        другому объекту обязан сбросить рамку прошлой протяжки, иначе Del
        удалил бы то, что уже и не выбрано.

        Индексы — позиции в списке, а список правят (удаление, перестановка),
        поэтому группа нигде дольше одного жеста не живёт и за краем не висит."""
        self.sel = i if i is None or 0 <= i < len(self.inst) else None
        if group is _UNSET:
            self.sel_group = {self.sel} if self.sel is not None else set()
        else:
            self.sel_group = {j for j in group if 0 <= j < len(self.inst)}
            if self.sel is not None:
                self.sel_group.add(self.sel)

    def _group_idx(self):
        """Индексы группы по порядку списка (первый = самый нижний слой)."""
        return sorted(self.sel_group & set(range(len(self.inst))))

    def _select_all(self, _=None):
        """Ctrl+A: выделить всю карту — обычно затем, чтобы снести Del'ем."""
        self._set_sel(self.sel if self.sel is not None
                      else (len(self.inst) - 1 if self.inst else None),
                      group=set(range(len(self.inst))))
        self.render_all()
        self._sync_map_sel()
        self._set_status("выделено %d экз. — Ctrl+D и Del работают по группе"
                         % len(self.sel_group))

    def _del_selected(self, _=None):
        """Del по ГРУППЕ: рамку протянули — снимаем всё, что в неё попало.
        Удаляем с конца списка, чтобы индексы предыдущих членов не съехали."""
        grp = self._group_idx()
        if not grp:
            return
        names = {self.inst[i]["pf"] for i in grp}
        for i in reversed(grp):
            del self.inst[i]
        anchor = min(grp[-1], len(self.inst) - 1) if self.inst else None
        self._set_sel(anchor)
        self._after_edit("удалено %d экз. (%s) — не сохранено"
                         % (len(grp), ", ".join(sorted(names)) if len(names) <= 3
                            else "%d разных префабов" % len(names)))
        self._sync_map_sel()

    def _dup_selected(self, _=None):
        """Копия экземпляра с шагом в 1 тайл и ВСЕГДА в конце списка — то есть
        поверх оригинала: задумка в том, чтобы наслоить, а не засыпать."""
        if self.sel is None:
            return
        o = dict(self.inst[self.sel])
        o["x"] = min(self.cols - 1, int(o["x"]) + 1)
        o["y"] = min(self.rows - 1, int(o["y"]) + 1)
        self.inst.append(o)
        self._set_sel(len(self.inst) - 1)
        self._after_edit("дубликат #%d — не сохранено" % self.sel)
        self._sync_map_sel()

    @staticmethod
    def _native(pf):
        """Нативный размер префаба с учётом min_w/min_h — тот же, что берёт
        _mk_inst, поэтому «вернуть нативный» чистит w/h из JSON."""
        return stamp_size(pf, len(pf["grid"][0]), len(pf["grid"]))

    def _size_choices(self, i):
        """Готовые размеры стоявшего экземпляра: нативный и размеры соседей по
        тому же префабу. Мост в 22 клетки проще сделать таким же, как соседний
        мост, чем вспоминать число; список усекается, чтобы меню не распухло
        на сотню строк на полном уровне."""
        o = self.inst[i]
        pf = self.by_name[o["pf"]]
        if pf.get("stretch_x") is None and pf.get("stretch_y") is None:
            return []
        cur = self._boxes[i][2:]
        out = {self._native(pf), tuple(cur)}
        for other in self.inst:
            if other["pf"] == o["pf"]:
                out.add(tuple(self._bbox(other)[2:]))
        return [s for s in sorted(out) if s != tuple(cur)][:12]

    def _resize_inst(self, i, nw, nh):
        """Растянуть стоящий экземпляр: тот же префаб, тот же левый верхний
        угол — меняются только stretch-оси. Раньше это значило «удали и
        поставь заново»: для объекта в 40 тайлов это потеря пары минут, а
        новый экземпляр ещё и уезжает на вершину списка, то есть сбивает
        порядок наслоения."""
        o = self.inst[i]
        pf = self.by_name[o["pf"]]
        nw, nh = stamp_size(pf, int(nw), int(nh))   # не-тяжимая ось вернётся в нативу
        x, y = int(o["x"]), int(o["y"])
        if x + nw > self.cols or y + nh > self.rows:
            self._set_status("не влезает: (%d,%d) + %d×%d > карта %d×%d"
                             % (x, y, nw, nh, self.cols, self.rows))
            return False
        snap = dict(o)
        nat = self._native(pf)
        o.pop("w", None)
        o.pop("h", None)
        if nw != nat[0]:
            o["w"] = nw
        if nh != nat[1]:
            o["h"] = nh
        bad = self._limits()                        # новый размер = новый вариант
        if bad:
            o.clear()
            o.update(snap)
            self._set_status("не применено: " + bad[0])
            return False
        self._set_sel(i)
        self._after_edit("%s #%d: размер %d×%d — не сохранено"
                         % (o["pf"], i, nw, nh))
        self._sync_map_sel()
        return True

    def _ask_size(self, i):
        """Окно «задать размер»: произвольные W/H стоявшего экземпляра
        (готовые размеры соседей живут в меню, тут — число с клавиатуры).
        Ось без stretch заблокирована: её редактор не имеет права менять."""
        o = self.inst[i]
        pf = self.by_name[o["pf"]]
        x, y, w, h = self._boxes[i]
        nat = self._native(pf)
        win = tk.Toplevel(self.root)
        win.title("Размер · %s #%d" % (o["pf"], i))
        win.transient(self.root)
        body = ttk.Frame(win, padding=10)
        body.pack(fill=tk.BOTH, expand=True)
        vals = []
        for row, (lbl, val, lo, hi, can) in enumerate((
                ("ширина (тайлов) ", w, nat[0], self.cols - x,
                 pf.get("stretch_x") is not None),
                ("высота (тайлов)", h, nat[1], self.rows - y,
                 pf.get("stretch_y") is not None))):
            ttk.Label(body, text=lbl).grid(row=row, column=0, sticky="w")
            v = tk.IntVar(value=int(val))
            box = ttk.Spinbox(body, from_=lo, to=hi, width=6, textvariable=v)
            box.grid(row=row, column=1, sticky="w", padx=(8, 0))
            if not can:
                box.config(state="disabled")
            vals.append(v)
        ttk.Label(body, foreground="#777", justify=tk.LEFT,
                  text="растёт из левого верхнего угла;\n"
                       "упрётся в край карты — не применит"
                  ).grid(row=2, column=0, columnspan=2, sticky="w", pady=(8, 0))

        def do_apply():
            try:
                nw, nh = vals[0].get(), vals[1].get()
            except (ValueError, tk.TclError):
                messagebox.showerror("Размер", "нужно целое число тайлов")
                return
            if self._resize_inst(i, nw, nh):
                win.destroy()

        btns = ttk.Frame(win, padding=(10, 0, 10, 10))
        btns.pack(fill=tk.X)
        ttk.Button(btns, text="Изменить", command=do_apply).pack(side=tk.RIGHT)
        ttk.Button(btns, text="Отмена",
                   command=win.destroy).pack(side=tk.RIGHT, padx=(0, 6))
        win.bind("<Return>", lambda _e: do_apply())
        win.bind("<Escape>", lambda _e: win.destroy())

    # ---- замена стоявшего экземпляра ------------------------------------
    def _thumb(self, pf, maxw=PF_COL_W - 16):
        """Миниатюра префаба в нативном размере, но не шире колонки: длинная
        поверхность иначе вылезет за карточку."""
        nc, nr = len(pf["grid"][0]), len(pf["grid"])
        sc = max(2, min(PF_THUMB, maxw // max(nc, 1)))
        return self._grid_image(stamp_cells(pf, nc, nr), sc)

    def _single_by_tile(self):
        """1×1-префабы секции «одиночные» по индексу тайла: они и есть ответ на
        «поставить просто тайл». Имя у них человеческое («Земля (тянется)»),
        поэтому ищем по сетке, а не по имени."""
        out = {}
        for pf in self.prefabs:
            g = pf["grid"]
            if (section_of(pf) == SINGLE_SECTION
                    and len(g) == 1 and len(g[0]) == 1):
                out.setdefault(int(g[0][0]), pf)
        return out

    def _add_single(self, t):
        """Завести одиночный тайл, которого миграция не породила (тот же
        авто-префаб, что и у неё), и запомнить, что prefabs.json надо писать."""
        pf = single_tile_stretchable(t)
        self.prefabs.append(pf)
        self.by_name[pf["name"]] = pf
        self.pf_added.append(pf)
        self._touch()
        return pf

    def _replace_inst(self, i, name):
        """Заменить стоящий экземпляр ДРУГИМ префабом, сохранив левый верхний
        угол. Это не «удалить и поставить»: объект остаётся на своём месте в
        списке, то есть не меняет z-order. Размер берётся нативный: w/h старого
        объекта новому обычно не подходят, а тянуть их — отдельное действие."""
        o = self.inst[i]
        if o["pf"] == name:
            self._set_status("#%d и так %s" % (i, name))
            return False
        pf = self.by_name.get(name)
        if pf is None:
            self._set_status("нет префаба «%s» — «⟳ префабы»" % name)
            return False
        nw, nh = self._native(pf)
        snap = dict(o)
        x = max(0, min(int(o["x"]), self.cols - nw))
        y = max(0, min(int(o["y"]), self.rows - nh))
        o.clear()
        o.update({"pf": name, "x": x, "y": y})
        bad = self._limits()                     # новый объект = новый вариант
        if bad:
            o.clear()
            o.update(snap)
            self._set_status("не применено: " + bad[0])
            return False
        self._set_sel(i)
        self._after_edit("#%d: %s → %s (%d×%d)%s — не сохранено"
                         % (i, snap["pf"], name, nw, nh,
                            "" if (x, y) == (int(snap["x"]), int(snap["y"]))
                            else " сдвинут в карту"))
        self._sync_map_sel()
        return True

    def _replace_tile(self, i):
        """«Заменить на одиночный тайл»: сетка тайлов набора — как палитра
        тайлов, только меняет стоящий экземпляр, а не красит клетку."""
        have = self._single_by_tile()
        cards = []
        for t in range(len(self.tiles["tiles"])):
            im = self.tile_orig[t].resize((PF_THUMB, PF_THUMB), Image.NEAREST)
            pf = have.get(t)
            cards.append((im, "%d · %s" % (t, pf["name"] if pf else "создать"),
                          t))
        self._pick_win(
            "Заменить #%d на тайл" % i,
            "экземпляр станет одиночным тайлом в том же углу\n"
            "«создать» = тайла в библиотеке нет — заведу «Тайл N» и запишу "
            "в prefabs.json",
            cards, lambda t: self._replace_with_tile(i, t), cols=5, cw=150)

    def _replace_with_tile(self, i, t):
        pf = self._single_by_tile().get(t)
        if pf is None:
            if not messagebox.askyesno(
                    "Новый префаб",
                    "Одиночного тайла %d в библиотеке нет.\n"
                    "Завести «Тайл %d» (тянется по обеим осям) и заменить им?"
                    % (t, t)):
                return
            pf = self._add_single(t)
            self._set_status("библиотека: +«%s» — сохранится в prefabs.json"
                             % pf["name"])
        self._replace_inst(i, pf["name"])

    def _replace_prefab(self, i):
        """«Заменить на объект из библиотеки»: карточки палитры (одиночные
        тайлы — в соседнем пункте меню, дублировать их тут не за чем)."""
        cards = []
        for pf in self._pf_list():
            cards.append((self._thumb(pf),
                          "%s %d×%d" % (pf["name"], len(pf["grid"][0]),
                                        len(pf["grid"])), pf["name"]))
        self._pick_win(
            "Заменить #%d на объект" % i,
            "тот же левый верхний угол, размер — нативный\n"
            "тянуть потом: ПКМ по нему → «растянуть до»",
            cards, lambda name: self._replace_inst(i, name), cols=1)

    def _pick_win(self, title, prompt, cards, on_pick, cols=1, cw=PF_COL_W):
        """Окно выбора карточкой: сетка миниатюр, клик — взять. Общее для обеих
        замен: второй раз раскладывать canvas по строкам незачем."""
        win = tk.Toplevel(self.root)
        win.title(title)
        win.transient(self.root)
        ttk.Label(win, text=prompt, padding=(8, 6, 8, 0),
                  justify=tk.LEFT).pack(anchor=tk.W)
        fr = ttk.Frame(win, padding=6)
        fr.pack(fill=tk.BOTH, expand=True)
        cv = tk.Canvas(fr, bg="#1e1e1e", highlightthickness=0)
        sb = ttk.Scrollbar(fr, orient=tk.VERTICAL, command=cv.yview)
        cv.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb.pack(side=tk.LEFT, fill=tk.Y)
        cv.config(yscrollcommand=sb.set)
        photos = []
        y = 6
        for r in range(0, len(cards), cols):
            row = cards[r:r + cols]
            hh = max(im.height for im, _, _ in row) + 22
            for ci, (im, label, payload) in enumerate(row):
                x = 6 + ci * cw
                photos.append(ImageTk.PhotoImage(im))
                cv.create_image(x, y, anchor=tk.NW, image=photos[-1])
                cv.create_text(x, y + im.height + 3, anchor=tk.NW, text=label,
                               fill="#ddd", font=("DejaVu Sans", 8))
                hit = cv.create_rectangle(x - 4, y - 4, x + cw - 6, y - 4 + hh,
                                          fill="", outline="")
                cv.tag_bind(hit, "<Button-1>", lambda _e, p=payload:
                            self._pick_take(win, on_pick, p))
            y += hh + 6
        wide = cols * cw + 8
        cv.configure(scrollregion=(0, 0, wide, y + 4))
        cv.config(width=wide, height=min(y + 8, 540))

        def wheel(e, d=None):
            cv.yview_scroll((d if d is not None
                             else (-1 if e.delta > 0 else 1)) * 3, "units")

        cv.bind("<Button-4>", lambda e: wheel(e, -1))
        cv.bind("<Button-5>", lambda e: wheel(e, 1))
        cv.bind("<MouseWheel>", wheel)
        win.bind("<Escape>", lambda _e: win.destroy())
        win._photos = photos              # PhotoImage обязаны пережить раскладку
        # окно там, где курсор: выбирать надо для того объекта, на который
        # смотрели, а не туда, куда забросит WM
        win.update_idletasks()
        scr_w = self.root.winfo_screenwidth()
        scr_h = self.root.winfo_screenheight()
        win.geometry("+%d+%d" % (
            max(0, min(self.root.winfo_pointerx(),
                       scr_w - win.winfo_reqwidth() - 8)),
            max(0, min(self.root.winfo_pointery(),
                       scr_h - win.winfo_reqheight() - 32))))
        return win

    def _pick_take(self, win, on_pick, payload):
        win.destroy()
        on_pick(payload)

    def _move_z(self, step):
        """Сдвинуть экземпляр в списке: +1 = позже = ПОВЕРХ (PgUp, Ctrl+↓),
        −1 = под (PgDn, Ctrl+↑). За границу блока экземпляр уезжает вместе с
        x — тогда порядок ему задаст новый блок."""
        if self.sel is None:
            return
        i = self.sel
        j = i + step
        if not 0 <= j < len(self.inst):
            self._set_status("#%d уже %s" % (i, "поверх всех" if step > 0
                                             else "под всеми"))
            return
        self.inst[i], self.inst[j] = self.inst[j], self.inst[i]
        self._set_sel(j)
        self._after_edit("z-order: #%d → #%d (%s) — не сохранено"
                         % (i, j, "поверх" if step > 0 else "под"))
        self._sync_map_sel()

    def _to_top(self, i=None):
        self._to_end(i, True)

    def _to_bottom(self, i=None):
        self._to_end(i, False)

    def _to_end(self, i, top):
        """«наверх»/«вниз» из контекстного меню: снять экземпляр и поставить
        его в конец/начало списка."""
        i = self.sel if i is None else i
        if i is None:
            return
        o = self.inst.pop(i)
        if top:
            self.inst.append(o)
        else:
            self.inst.insert(0, o)
        self._set_sel(len(self.inst) - 1 if top else 0)
        self._after_edit("%s: #%d → #%d — не сохранено"
                         % ("наверх" if top else "вниз", i, self.sel))
        self._sync_map_sel()

    # ---- панель «На карте» -------------------------------------------------
    def _build_map_panel(self, right):
        """Только список экземпляров. Счётчики («N экз. · N вар. · словарь
        N Б» и топ-5 префабов) убраны: смета и так в тулбаре, а 800 строк
        списка без текста поверх экрана читаются лучше."""
        self.map_box = ttk.LabelFrame(right, text="На карте", padding=6)
        self.map_box.pack(fill=tk.BOTH, expand=True, pady=(10, 0))
        row = ttk.Frame(self.map_box)
        row.pack(fill=tk.BOTH, expand=True)
        self.map_list = ttk.Treeview(row, columns=("#", "pf", "xy", "size"),
                                     show="headings", height=12,
                                     # extended, а не browse: Ctrl/Shift-клик по
                                     # строкам должен выделять столько же,
                                     # сколько рамка на карте
                                     selectmode="extended")
        for cid, txt, wid in (("#", "#", 44), ("pf", "префаб", 130),
                              ("xy", "x,y", 62), ("size", "w×h", 46)):
            self.map_list.heading(cid, text=txt)
            self.map_list.column(cid, width=wid, anchor=tk.W)
        sb = ttk.Scrollbar(row, orient=tk.VERTICAL, command=self.map_list.yview)
        self.map_list.config(yscrollcommand=sb.set)
        self.map_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb.pack(side=tk.LEFT, fill=tk.Y)
        self.map_list.bind("<<TreeviewSelect>>", self._on_panel_sel)
        self.map_list.bind("<Double-1>", lambda e: self._jump_to())
        self._panel_sync = False

    def _refresh_map_panel(self):
        """Список = z-order, сверху вниз по экрану: последний (поверх всех) в
        конце. 800+ строк пересобираем на каждую правку — Treeview это терпит."""
        if not hasattr(self, "map_list") or not hasattr(self, "_boxes"):
            return
        # предупреждение о z-конфликте остаётся: в заголовке рамки и оранжевой
        # рамкой экземпляра на поле
        self.map_box.config(
            text="На карте · ⚠ %d клеток с z-конфликтом" % self.zdiff
            if self.zdiff else "На карте")
        kids = self.map_list.get_children()
        if kids:
            self.map_list.delete(*kids)
        self._panel_sync = True
        try:
            for i, o in enumerate(self.inst):
                x, y, w, h = self._boxes[i]
                self.map_list.insert("", tk.END, iid=str(i),
                                     values=("#%d" % i, o["pf"],
                                             "%d,%d" % (x, y),
                                             "%d×%d" % (w, h)))
            if self.sel_group:
                grp = [str(i) for i in self._group_idx()]
                self.map_list.selection_add(*grp)
                if self.sel is not None:
                    self.map_list.see(str(self.sel))
        finally:
            self._panel_sync = False

    def _sync_map_sel(self):
        if not hasattr(self, "map_list") or self._panel_sync:
            return
        self._set_sel(self.sel, group=set(self.sel_group))   # за краем списка — долой
        self._panel_sync = True
        try:
            self.map_list.selection_remove(*self.map_list.selection())
            grp = [str(i) for i in self._group_idx()]
            if grp:
                self.map_list.selection_add(*grp)
            if self.sel is not None:
                self.map_list.see(str(self.sel))
        except tk.TclError:
            pass
        finally:
            self._panel_sync = False

    def _on_panel_sel(self, _e=None):
        """Клик по строке = выделение на карте (рамка + перерисовка). Сколько
        строк взято — столько и выделено: панель и рамка мыши живут одним
        набором индексов."""
        if self._panel_sync:
            return
        sel = [int(s) for s in self.map_list.selection()]
        if sel:
            self._set_sel(sel[-1], group=set(sel))   # якорь = верхний по z
        else:
            self._set_sel(None)
        self.render_all()
        if not self.sel_group:
            return
        x, y, w, h = self._boxes[self.sel]
        conf = len(self._conflicts_of(self.sel))
        head = ("#%d %s в (%d,%d) %d×%d"
                % (self.sel, self.inst[self.sel]["pf"], x, y, w, h))
        self._set_status("%s%s%s" % (
            head, " · перекрывает %d из другого блока" % conf if conf else "",
            " · всего в группе %d — Del снимает все" % len(self.sel_group)
            if len(self.sel_group) > 1 else ""))

    def _jump_to(self):
        """Двойной клик в списке: выделить экземпляр и подвести к нему окно
        карты (центр на нём), на любом зуме."""
        sel = self.map_list.selection()
        if not sel:
            return
        i = int(sel[0])
        self._set_sel(i)
        x, y, w, h = self._boxes[i]
        W, H = self.cols * self.cell, self.rows * self.cell
        cw = max(1, self.canvas.winfo_width())
        ch = max(1, self.canvas.winfo_height())
        self.render_all()
        if W > cw:
            self.canvas.xview_moveto(max(0.0, min(1.0, ((x + w / 2.0) * self.cell
                                                        - cw / 2.0) / (W - cw))))
        if H > ch:
            self.canvas.yview_moveto(max(0.0, min(1.0, ((y + h / 2.0) * self.cell
                                                        - ch / 2.0) / (H - ch))))
        self._sync_map_sel()
        self._on_panel_sel()

    # ---- твёрдость тайла --------------------------------------------------
    def _apply_prop(self, t, mode):
        """mode: 'wall' | 'platform' | 'pass' — выставить биты твёрдости."""
        t["transparent"] = False
        if mode == "wall":
            t["wall"] = True; t["platform"] = False
        elif mode == "platform":
            t["wall"] = False; t["platform"] = True
        else:
            t["wall"] = False; t["platform"] = False

    def _quick_prop(self, ti, mode):
        """Смена твёрдости тайла из контекстного меню: оно и есть единственный
        редактор твёрдости (панели свойств с картинкой больше нет)."""
        self._apply_prop(self.tiles["tiles"][ti], mode)
        self.dirty = True
        self.render_all()                          # оверлей во всех клетках
        self._set_status("tile %d: твёрдость — не сохранено" % ti)

    # ---- мышь на поле -----------------------------------------------------
    def _cell_at(self, e):
        cx = self.canvas.canvasx(e.x)
        cy = self.canvas.canvasy(e.y)
        col = int(cx // self.cell)
        row = int(cy // self.cell)
        if 0 <= col < self.cols and 0 <= row < self.rows:
            return col, row
        return None

    def _del_only(self, i):
        """Удалить ровно ОДИН экземпляр из меню, даже если рамкой взята группа:
        пункт меню назван индексом, значит и удалить он должен его, а не всё."""
        self._set_sel(i)
        self._del_selected()

    def _unselect(self):
        """Снять выделение, штамп не трогая (он отвязан: им правят клик по
        карточке и Esc)."""
        self._set_sel(None)
        self.render_all()
        self._sync_map_sel()
        self._set_status("выделение снято")

    def _on_escape(self, _=None):
        """Esc — отмена жеста целиком: и штамп выключить, и рамку снять. Состояния
        у них разные, но клавиша у пользователя одна. Текущую протяжку тоже
        сбрасываем: иначе Esc между нажатием и отпусканием оставляет в drag
        штамп, которого уже нет, — и отпускание мыши падает на пустом pf."""
        self._close_menu()
        had = bool(self.sel_group)
        self.drag = None
        self.clear_stamp(silent=True)
        self._set_sel(None)
        self.render_all()
        self._sync_map_sel()
        if had:
            self._set_status("штамп и выделение сняты")

    def _on_click(self, e, box=False):
        """Жест левой кнопкой: штамп — протянуть размер, пустая клетка — рамка
        выделения, объект — выделить и двигать. box=True (средняя кнопка) —
        рамка в любой точке, хоть над объектом и хоть с включённым штампом."""
        c = self._cell_at(e)
        if not c:
            return
        self._close_menu()            # клик по карте — открытое меню уже не нужно
        col, row = c
        add = bool(getattr(e, "state", 0) & SHIFT_MASK)   # Shift = дописать к группе
        if self.stamp is not None and not box:     # штамп — инструмент: тянем
            self._set_sel(None)                    # размер/область даже поверх
            self.drag = {"kind": "stamp", "x0": col, "y0": row,
                         "x1": col, "y1": row}     # уже стоящих экземпляров
        else:
            hit = None if box else self._inst_at(col, row)
            if hit is None:
                # пустая клетка — начало рамки; раньше клик сюда просто
                # снимал выделение, а выделять было чем только один объект
                self.drag = {"kind": "box", "x0": col, "y0": row,
                             "x1": col, "y1": row, "add": add,
                             "base": set(self.sel_group) if add else set()}
                if not add:
                    self._set_sel(None)
            elif add:
                grp = set(self.sel_group)
                if hit in grp:
                    grp.discard(hit)               # Shift по своему — снять с группы
                    rest = sorted(grp)
                    self._set_sel(rest[-1] if rest else None, group=grp)
                else:
                    self._set_sel(hit, group=grp | {hit})
                self.drag = None
            else:
                grp = self._group_idx()
                # взялись за члена группы — двигаем всю группу, а не его одного
                idxs = grp if hit in self.sel_group and len(grp) > 1 else [hit]
                self._set_sel(hit, group=set(idxs))
                self.drag = {"kind": "move", "index": hit, "idxs": idxs,
                             "x0": col, "y0": row, "cx": col, "cy": row}
        self._clear_preview()
        self._draw_preview()
        self.render_all()
        self._sync_map_sel()

    def _on_drag(self, e):
        if not self.drag:
            return
        c = self._cell_at(e)
        if not c:
            return
        col, row = c
        d = self.drag
        if d["kind"] in ("stamp", "box"):
            d["x1"], d["y1"] = col, row
        else:
            d["cx"], d["cy"] = col, row
        self._clear_preview()                      # двигается только контур,
        self._draw_preview()                       # печь — на отпускании

    def _on_release(self, e):
        if not self.drag:
            return
        d = self.drag
        self.drag = None
        self._clear_preview()
        c = self._cell_at(e)
        if d["kind"] == "stamp":
            self._place_stamp(d, c)
        elif d["kind"] == "box":
            self._finish_box(d, c)
        elif c:
            self._move_group(d, c)
        else:
            self.render_all()

    def _group_shift(self, idxs, x0, y0, cx, cy):
        """Общий сдвиг группы: урезан так, чтобы ЗА КРАЙ КАРТЫ не вылез ни один
        её член, — иначе группа разъехалась бы по краям на части."""
        dx, dy = cx - x0, cy - y0
        for i in idxs:
            x, y, w, h = self._boxes[i]
            dx = max(-x, min(dx, self.cols - x - w))
            dy = max(-y, min(dy, self.rows - y - h))
        return dx, dy

    def _move_group(self, d, c):
        """Отпустить протяжку по объекту: сдвинуть всю группу на один вектор."""
        idxs = d["idxs"]
        dx, dy = self._group_shift(idxs, d["x0"], d["y0"], c[0], c[1])
        self._set_sel(d["index"], group=set(self.sel_group))
        if not (dx or dy):
            self.render_all()
            return
        for i in idxs:
            self.inst[i]["x"] = int(self.inst[i]["x"]) + dx
            self.inst[i]["y"] = int(self.inst[i]["y"]) + dy
        self._touch()
        self._recompute_grid()
        conf = any(self._conflicts_of(i) for i in idxs)
        self.render_all()
        self._refresh_map_panel()
        anchor = self.inst[d["index"]]
        self._set_status("%s → (%d,%d)%s — не сохранено"
                         % ("%d экз. группы" % len(idxs) if len(idxs) > 1
                            else anchor["pf"], int(anchor["x"]),
                            int(anchor["y"]),
                            " · z-конфликт с блоком" if conf else ""))
        self._sync_map_sel()

    def _box_hits(self, x0, y0, x1, y1):
        """Экземпляры, которые рамка ЗАДЕЛА (пересечение габаритов, а не
        «целиком внутри»): длинную поверхность во всю карту иначе нельзя взять
        рамкой, которая ниже её."""
        return {i for i, (x, y, w, h) in enumerate(self._boxes)
                if x <= x1 and x + w > x0 and y <= y1 and y + h > y0}

    def _draw_box_preview(self, d):
        """Рамка группового выделения: пунктир + подсвеченные габариты того, что
        в неё уже попало, и счётчик в статусе — «сколько возьмёт» видно до
        отпускания кнопки."""
        x0, x1 = sorted((d["x0"], d["x1"]))
        y0, y1 = sorted((d["y0"], d["y1"]))
        hits = self._box_hits(x0, y0, x1, y1) | (d["base"] if d["add"] else set())
        for i in sorted(hits):
            x, y, w, h = self._boxes[i]
            self._box_outline(x, y, w, h, OBJ_SEL, 1)
        self.canvas.create_rectangle(x0 * self.cell, y0 * self.cell,
                                     (x1 + 1) * self.cell - 1,
                                     (y1 + 1) * self.cell - 1,
                                     outline="#%02x%02x%02x" % OBJ_SEL,
                                     dash=(4, 3), width=2, tags=("preview",))
        self._set_status("рамка %d×%d → %d экз.%s"
                         % (x1 - x0 + 1, y1 - y0 + 1, len(hits),
                            " (к группе)" if d["add"] else ""))

    def _finish_box(self, d, c):
        """Отпустить рамку: стать выделенными. Клик без протяжки = рамка в одну
        клетку, то есть обычный клик по пустому месту, который выделение и
        снимает."""
        x1, y1 = (c if c else (d["x1"], d["y1"]))
        x0, x1 = sorted((d["x0"], x1))
        y0, y1 = sorted((d["y0"], y1))
        in_frame = self._box_hits(x0, y0, x1, y1)
        hits = (in_frame | d["base"]) if d["add"] else in_frame
        # якорь — самый верхний по z из попавших в рамку: его и крутят PgUp/Ctrl+D
        taken = sorted(in_frame)
        keep = self.sel if self.sel in hits else None
        self._set_sel(taken[-1] if taken else keep, group=hits)
        self.render_all()
        self._sync_map_sel()
        self._set_status("в рамке %d экз. — Del удалит все, тянуть за любой — "
                         "двигает все" % len(self.sel_group)
                         if self.sel_group else "в рамке никого — выделение снято")

    def _stamp_layout(self, x0, y0, x1, y1):
        """Жест мыши -> (точки вставки, размер копии): один экземпляр заданного
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

    def _place_stamp(self, d, c):
        """Отпускание мыши с выбранным штампом: ОДИН экземпляр заданного размера
        или сетка экземпляров по области. Каждый — запись в конце списка, то
        есть поверх всех."""
        pf = self.stamp
        if pf is None:                       # штамп выключили, не отпуская кнопку
            self.render_all()
            return
        x1, y1 = (c if c else (d["x1"], d["y1"]))
        pts, (w, h) = self._stamp_layout(d["x0"], d["y0"], x1, y1)
        added = 0
        for (px, py) in pts:
            px = max(0, min(px, self.cols - w))
            py = max(0, min(py, self.rows - h))
            self.inst.append(self._mk_inst(pf, px, py, w, h))
            added += 1
        if not added:
            return
        self._set_sel(len(self.inst) - 1)
        self._after_edit("%s: +%d экз. (%d×%d) — не сохранено"
                         % (pf["name"], added, w, h))
        self._sync_map_sel()

    def _draw_preview(self):
        """Резинка над картой: ПОЛУПРОЗРАЧНЫЙ призрак штампа (живьём видно, как
        растянулась труба/куст и куда легли копии сетки), пунктир рамки
        группового выделения или контур переносимой группы."""
        d = self.drag
        if not d:
            return
        if d["kind"] == "stamp":
            self._draw_stamp_preview(d)
            return
        if d["kind"] == "box":
            self._draw_box_preview(d)
            return
        dx, dy = self._group_shift(d["idxs"], d["x0"], d["y0"], d["cx"], d["cy"])
        for i in d["idxs"]:
            x, y, w, h = self._boxes[i]
            self._box_outline(x + dx, y + dy, w, h, OBJ_SEL, 2)
        self._set_status("%s: сдвиг %+d,%+d"
                         % ("%d экз. группы" % len(d["idxs"])
                            if len(d["idxs"]) > 1 else self.inst[d["index"]]["pf"],
                            dx, dy))

    def _draw_stamp_preview(self, d):
        pf = self.stamp
        if pf is None:
            return
        pts, (w, h) = self._stamp_layout(d["x0"], d["y0"], d["x1"], d["y1"])
        cells = stamp_cells(pf, w, h)
        im = self._grid_image(cells, self.cell, STAMP_ALPHA)
        photo = ImageTk.PhotoImage(im)
        self._ghosts.append(photo)                 # держать ссылку до сброса
        for (px, py) in pts:
            px = max(0, min(px, self.cols - w))
            py = max(0, min(py, self.rows - h))
            self.canvas.create_image(px * self.cell, py * self.cell,
                                     anchor=tk.NW, image=photo, tags=("preview",))
            self._box_outline(px, py, w, h, OBJ_SEL, 1)
        self._set_status("%s %d×%d → %d экз." % (pf["name"], w, h, len(pts)))

    def _box_outline(self, x, y, w, h, color, width):
        self.canvas.create_rectangle(x * self.cell, y * self.cell,
                                     (x + w) * self.cell, (y + h) * self.cell,
                                     outline="#%02x%02x%02x" % color,
                                     width=width, tags=("preview",))

    def _clear_preview(self):
        self.canvas.delete("preview")
        self._ghosts = []

    def _on_map_menu(self, e):
        """ПКМ: меню быстрого действия. Над экземпляром — z-order/замена/
        дубликат/удаление, над тайлом — его твёрдость (ставим-то мы целые
        объекты). Любая команда снимает меню с экрана ДО работы: перерисовка
        карты под открытым попапом на части WM его не закрывает, и меню
        оставалось висеть поверх уже другого объекта."""
        self._close_menu()
        c = self._cell_at(e)
        if not c:
            return
        ti = self.grid[c[0] * self.rows + c[1]]
        hit = self._inst_at(*c)
        m = tk.Menu(self.root, tearoff=0)
        m.add_command(label=f"tile {ti} под курсором", state="disabled")
        m.add_separator()
        m.add_command(label="■ сплошной (стена)",
                      command=lambda: self._menu_act(self._quick_prop, ti, "wall"))
        m.add_command(label="▬ платформа (опора)",
                      command=lambda: self._menu_act(self._quick_prop, ti,
                                                     "platform"))
        m.add_command(label="□ проходной",
                      command=lambda: self._menu_act(self._quick_prop, ti, "pass"))
        if hit is not None:
            o = self.inst[hit]
            x, y, w, h = self._boxes[hit]
            m.add_separator()
            m.add_command(label="#%d %s (%d×%d)" % (hit, o["pf"], w, h),
                          state="disabled")
            if hit not in self.sel_group:
                # ПКМ по своему из группы группу не сбрасывает: иначе «удалить
                # всё выделенное» было бы недостижимо из меню
                self._set_sel(hit)
            sizes = self._size_choices(hit)
            if sizes:
                sub = tk.Menu(m, tearoff=0)
                for s in sizes:
                    sub.add_command(label="%d×%d" % s, command=lambda v=s:
                                    self._menu_act(self._resize_inst, hit, *v))
                sub.add_separator()
                sub.add_command(label="задать…", command=lambda:
                                self._menu_act(self._ask_size, hit))
                m.add_cascade(label="растянуть до", menu=sub)
            rep = tk.Menu(m, tearoff=0)
            rep.add_command(label="…на одиночный тайл",
                            command=lambda: self._menu_act(self._replace_tile,
                                                           hit))
            rep.add_command(label="…на объект из библиотеки",
                            command=lambda: self._menu_act(self._replace_prefab,
                                                           hit))
            m.add_cascade(label="⟲ заменить объект…", menu=rep)
            conf = self._conflicts_of(hit)
            if conf:
                m.add_command(
                    label="⚠ %d экз. из другого блока (порядок задаёт блок)"
                          % len(conf), state="disabled")
            m.add_command(label="▲ наверх (поверх всех)",
                          command=lambda: self._menu_act(self._to_top, hit))
            m.add_command(label="▼ вниз (под всех)",
                          command=lambda: self._menu_act(self._to_bottom, hit))
            m.add_command(label="⧉ дублировать (Ctrl+D)",
                          command=lambda: self._menu_act(self._dup_selected))
            grp = self._group_idx()
            if len(grp) > 1 and hit in self.sel_group:
                m.add_command(label="✂ удалить группу · %d экз. (Del)"
                              % len(grp),
                              command=lambda: self._menu_act(self._del_selected))
                m.add_command(label="☆ снять выделение (Esc)",
                              command=lambda: self._menu_act(self._unselect))
            m.add_command(label="✂ удалить #%d (Del)" % hit,
                          command=lambda: self._menu_act(self._del_only, hit))
        self._map_menu = m
        m.bind("<Unmap>", lambda _e, w=m: self._forget_menu(w))
        try:
            m.tk_popup(e.x_root, e.y_root)
        finally:
            m.grab_release()
        self.render_all()
        self._sync_map_sel()

    def _on_any_press(self, e):
        """Меню закрывается любым нажатием, а не только кликом по карте. Двое
        исключений:
          * нажатие по самому меню (или его каскаду) — там Tk сам разберётся,
            наш _close_menu пришёл бы ДО команды пункта и съел бы её;
          * кнопки 1/2/3 по карте — их уже обработали _on_click (он меню
            закрывает) и _on_map_menu (он его перекладывает); глобальный
            обработчик идёт ПОСЛЕ связки виджета и закрыл бы только что
            открытое меню. Колесо по карте не исключение: под курсором
            уехала бы уже другая клетка.
        Прочие кнопки и места (тулбар, палитра, «На карте», диалоги) — меню
        больше не нужно, убираем."""
        m = self._map_menu
        if m is None:
            return
        if _in_menu_tree(m, e.widget):
            return
        if e.widget is self.canvas and getattr(e, "num", 0) in (1, 2, 3):
            return
        self._close_menu()

    def _menu_act(self, fn, *args):
        """Команда ПКМ: сначала убрать меню, потом работать (см. _on_map_menu)."""
        self._close_menu()
        fn(*args)

    def _close_menu(self):
        """Снять висящее на экране контекстное меню."""
        m = self._map_menu
        if m is None:
            return
        self._map_menu = None
        try:
            m.unpost()
        except tk.TclError:
            pass
        self._forget_menu(m)

    def _forget_menu(self, m):
        """Уничтожить меню после того, как его закрыли. Раньше каждый ПКМ
        оставлял в root ещё один виджет Menu: за сеанс их копилось по сотне, а
        последнее ещё и продолжало висеть над картой."""
        if self._map_menu is m:
            self._map_menu = None
        try:
            m.after_idle(m.destroy)   # destroy из своей же команды роняет Tk
        except tk.TclError:
            pass

    # ---- прокрутка/зум ----------------------------------------------------
    def _on_wheel(self, e, delta=None):
        if delta is None:                          # Windows/mac
            delta = -1 if e.delta > 0 else 1
        self.canvas.yview_scroll(delta * 3, "units")

    def _on_zoom(self, _=None):
        self.cell = int(self.zoom_var.get())
        self._rebuild_scaled()
        self.render_all()

    # ---- ресайз карты -----------------------------------------------------
    def _shifted(self, new_cols, new_rows, c_off, r_off):
        """Экземпляры, сдвинутые якорем: ЦЕЛИКОМ. То, что после сдвига не влезает
        в карту, не обрезается (префаб — не прямоугольник тайлов, его полровка
        бессмысленна), а теряется; список потерянных возвращаем для диалога."""
        keep, lost = [], []
        for o in self.inst:
            x, y, w, h = self._bbox(o)
            nx, ny = x + c_off, y + r_off
            if 0 <= nx and nx + w <= new_cols and 0 <= ny and ny + h <= new_rows:
                n = dict(o)
                n["x"], n["y"] = nx, ny
                keep.append(n)
            else:
                lost.append(o)
        return keep, lost

    def _apply_resize(self, nc, nr, anch_h="левому", anch_v="низу"):
        """Сменить размер карты. True — применён, False — отменён или не прошёл
        бы сборку; по этому признаку окно ресайза и закрывается."""
        c_off = (nc - self.cols) if anch_h == "правому" else 0
        r_off = (nr - self.rows) if anch_v == "низу" else 0
        keep, lost = self._shifted(nc, nr, c_off, r_off)
        bad = self._limits(nc, nr, keep)
        if bad:
            messagebox.showerror("Размер не пройдёт сборку",
                                 "\n".join(bad)
                                 + "\n\nОставил %d×%d." % (self.cols, self.rows))
            return False
        if nc == self.cols and nr == self.rows:
            self._set_status("размер не изменился")
            return False
        if lost and not messagebox.askyesno(
                "Обрезка", "За новые края выходят %d целых экземпляров — они "
                "будут потеряны (префабы не разрезаем).\nОбрезать?" % len(lost),
                icon="warning"):
            return False
        self._resize(nc, nr, keep)
        self._set_status("карта %d×%d — не забудь Сохранить" % (nc, nr))
        return True

    def _open_resize(self):
        """Окно размеров карты. Отдельное, а не spinbox'ы в тулбаре: ресайз —
        правка с потерей экземпляров за краем, и случайный клик по полю ввода
        рядом с рабочими инструментами этого права не стоит."""
        if self._resize_win is not None and self._resize_win.winfo_exists():
            self._resize_win.lift()
            return
        win = tk.Toplevel(self.root)
        self._resize_win = win
        win.title("Размеры карты")
        win.transient(self.root)
        body = ttk.Frame(win, padding=12)
        body.pack(fill=tk.BOTH, expand=True)
        ttk.Label(body, text="Карта сейчас: %d×%d" % (self.cols, self.rows),
                  foreground="#777").pack(anchor=tk.W)
        gr = ttk.Frame(body)
        gr.pack(fill=tk.X, pady=(8, 0))
        wv = tk.IntVar(value=self.cols)
        hv = tk.IntVar(value=self.rows)
        for r, lab, var, lo, hi in ((0, "Ширина, колонок", wv, MIN_COLS, MAX_COLS),
                                    (1, "Высота, строк", hv, MIN_ROWS, MAX_ROWS)):
            ttk.Label(gr, text=lab).grid(row=r, column=0, sticky=tk.W, pady=2)
            ttk.Spinbox(gr, from_=lo, to=hi, width=8, textvariable=var).grid(
                row=r, column=1, sticky=tk.E, padx=(14, 0), pady=2)
        gr.columnconfigure(0, weight=1)
        ar = ttk.Frame(body)
        ar.pack(fill=tk.X, pady=(8, 0))
        ttk.Label(ar, text="прижать содержимое:").pack(anchor=tk.W)
        av = tk.StringVar(value="низу")
        ah = tk.StringVar(value="левому")
        row = ttk.Frame(ar)
        row.pack(fill=tk.X, pady=2)
        ttk.Label(row, text="по вертикали").pack(side=tk.LEFT)
        ttk.OptionMenu(row, av, "низу", "верху", "низу").pack(side=tk.LEFT, padx=6)
        ttk.Label(row, text="  по горизонтали").pack(side=tk.LEFT)
        ttk.OptionMenu(row, ah, "левому", "левому", "правому").pack(
            side=tk.LEFT, padx=6)
        hint = ("Лимиты %d…%d × %d…%d. Тяжёлые края (справа/снизу) при\n"
                "жатии к верху/левому остаются нетронутыми; целые\n"
                "экземпляры за новым краем теряются — префабы не режем."
                % (MIN_COLS, MAX_COLS, MIN_ROWS, MAX_ROWS))
        ttk.Label(body, foreground="#777", justify=tk.LEFT,
                  text=hint).pack(anchor=tk.W, pady=(8, 0))
        btns = ttk.Frame(body)
        btns.pack(fill=tk.X, pady=(12, 0))

        def apply():
            try:
                nc, nr = int(wv.get()), int(hv.get())
            except (ValueError, tk.TclError):
                messagebox.showerror("Размеры", "Ширина и высота — целые числа.",
                                     parent=win)
                return
            if self._apply_resize(nc, nr, ah.get(), av.get()):
                win.destroy()

        ttk.Button(btns, text="Изменить", command=apply).pack(side=tk.RIGHT)
        ttk.Button(btns, text="Отмена", command=win.destroy).pack(
            side=tk.RIGHT, padx=(0, 6))
        win.bind("<Return>", lambda _e: apply())
        win.bind("<Escape>", lambda _e: win.destroy())

    def _resize(self, new_cols, new_rows, keep):
        """Новый размер + уже сдвинутый якорем список; grid — переразвернуть."""
        self.cols, self.rows = new_cols, new_rows
        self.level["cols"] = new_cols
        self.level["rows"] = new_rows
        self.inst = keep
        self._set_sel(None)
        self._touch()
        self._recompute_grid()
        self.render_all()
        self._refresh_map_panel()

    # ---- сохранение -------------------------------------------------------
    def _rom_order(self):
        """Порядок, в котором список уйдёт в ROM: (32-колоночный блок, номер в
        списке). Сортировка стабильна, поэтому внутри блока z-order сохраняется."""
        return sorted(range(len(self.inst)),
                      key=lambda i: (int(self.inst[i]["x"]) // OBJ_WIN_STEP, i))

    def _rom_parity(self):
        """Проверка «редактор == генератор» ДО записи: упаковать список тем же
        pack_instances и прочитать обратно байт в байт (x/y/id варианта)."""
        errs = []
        order = self._rom_order()
        variants, ids = build_variants(self.prefabs, self.inst)
        seq = [self.inst[i] for i in order]
        vid = [ids[i] for i in order]
        try:
            packed = G.pack_instances(seq, vid)
        except SystemExit as exc:                  # pack_instances сам выходит
            return ["gen_assets: %s" % exc]
        for k, o in enumerate(seq):
            b = packed[4 * k:4 * k + 4]
            v = (b[0] & 0x7F) | ((b[3] & 0x1F) << 7)
            x = ((b[0] >> 7) & 1) << 8 | b[1]
            if (v, x, b[2]) != (vid[k], int(o["x"]), int(o["y"])):
                errs.append("#%d: ROM-код %s != экземпляр %s"
                            % (order[k], (v, x, b[2]), (vid[k], o["x"], o["y"])))
        starts = G.block_starts(seq, self.cols)
        if starts[-1] != len(seq):
            errs.append("pf_start: sentinel %d != %d экземпляров"
                        % (starts[-1], len(seq)))
        return errs

    def save(self):
        """Экземпляры — источник истины: пишем objects.json (v2), а level.json —
        развёрнутая ROM-порядком сетка (фолбэк генератора и парити-сверка).
        Запись блокируется, если уровень не проходит gen_assets: те же лимиты
        плюс проверка упаковки в 4 Б и round-trip."""
        bad = self._limits()
        if bad:
            messagebox.showerror(
                "Не сохраняется", "\n".join(bad) +
                "\n\ngen_assets упал бы на этих же формулах — правь карту/размер.")
            self._set_status("не сохранено: " + bad[0])
            return
        errs = self._rom_parity()
        if errs:
            messagebox.showerror("Парити с генератором", "\n".join(errs[:5]))
            self._set_status("не сохранено: парити не прошло")
            return
        if self.zdiff and not messagebox.askyesno(
                "z-конфликт", "Экземпляры пересекают границы 32-колоночных "
                "блоков: в %d клетках порядок наложения в ROM задаст блок, а не "
                "список (на превью видно ровно то, что напечатает ROM).\n"
                "Сохранить?" % self.zdiff):
            self._set_status("не сохранено: z-конфликт")
            return
        if self.pf_added:
            # библиотека: «заменить на тайл» дописал в неё одиночный тайл —
            # без prefabs.json объекты на карте остались бы висячими
            save_prefabs(self.prefabs, PREFAB_FILE)
        save_instances(self.cols, self.rows, self.inst)
        self.level["cols"] = self.cols
        self.level["rows"] = self.rows
        self.level["grid"] = list(self.grid)
        with open(os.path.join(SRC, "level.json"), "w") as f:
            json.dump(self.level, f)
        with open(os.path.join(SRC, "tiles.json"), "w", encoding="utf-8") as f:
            json.dump(self.tiles, f, ensure_ascii=False, indent=1)
        self.dirty = False
        added = len(self.pf_added)
        self.pf_added = []
        self._set_status("сохранено ✓ — выполни make"
                         + (" · prefabs.json: +%d" % added if added else ""))

    def _set_status(self, txt):
        self.status.config(text=txt)


def main():
    root = tk.Tk()
    app = LevelEditor(root)

    def on_close():
        if app.dirty and not messagebox.askyesno("Выход",
                                                 "Есть несохранённые правки. Выйти?"):
            return
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_close)
    # развернуть ПОСЛЕ того, как WM отобразил окно (до map запрос zoomed теряется)
    root.after(120, lambda: _maximize(root))
    root.mainloop()


if __name__ == "__main__":
    main()
