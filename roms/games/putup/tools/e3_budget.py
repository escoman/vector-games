#!/usr/bin/env python3
"""Step E3-3 — бюджет кадра: сколько РАСТРОВОГО времени стоит плавная анимация врагов.

Секундомер — тот же, что у ROM: КР580ВИ53 ch1 (порт 0Ah), грузится 0x7500=29952
отсчётами в конце VBlank ISR, убывает до 0. 1 строка = 96 отсчётов, поле начинается
со строки 48 (4608 отсчётов). Отсчёт читается ровно как func_beam_count: LATCH
(OUT 08h=40h) + два IN 0Ah. Счётчик и луч ЗАМИРАЮТ вместе с CPU на breakpoint
(проверено: 1.5 с паузы -> frame и latch-байты не сдвинулись), поэтому дельта
«вход функции -> её RET» и есть стоковое raster-время без поправки на wall-clock.

RET-адрес берём из стека на входе (u16 по SP) и ставим временный breakpoint — так
не нужно угадывать границы функций в свободной конкатенации (локальные метки идут
вперемешку, measure по «следующему символу» неверен).

Что меряем:
  * стоимость функций (enemy_render и его фазы, рендер огня, герой, логика);
  * ОКНА ЗАПИСИ VRAM — func_draw_tile_at_ptr (стирание), func_render_tile_vram
    (выровненный блит), func_ed_blit3 (композит). Для каждого окна считаем полосу
    луча band_top..band_bot = 4608+768*row .. +1536 (тайл 2 строки) и относим к
    «до луча» / «после луча» / «пересечение» (риск разрыва тайла на кадр);
  * чем заканчивается кадр: финиш работы (граница кадра = lbl_main_game_loop, куда
    CPU приходит после hero-рендера, т.е. это конец работы кадра, а не его начало);
  * ПЕРЕПОЛНЕНИЕ РАСТРА: прерывание ВBlank, заставшее CPU за работой
    (debug_get_int_events: was_halt=false). Это и есть пропуск кадра (EI;HLT не успел
    уснуть к следующему ВBlank) -> игровой период вместо 12 кадров становится 13.
    Заодно считаем период тика: hw-кадры между вызовами func_game_update.

Запуск: python3 roms/games/putup/tools/e3_budget.py [КАДРОВ]

Регрессионный гейт (§4.2, дешёвая альтернатива растер-планировщику E3-5): после
всех замеров проверяется вердикт — МАКСIMUM длины работы кадра < бюджета (312
строк растра) и НИЛЬ пропущенных кадров. Нарушение -> RESULT: FAIL и ненулевой
код возврата, гейт можно гонять перед коммитами, трогать ROM не нужно.
"""
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.abspath(os.path.join(HERE, '..'))
ROOT = os.path.abspath(os.path.join(PROJECT, '..', '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'utils'))
from analyze.mcp_session import McpSession, bytes_of, to_addr  # noqa: E402

FRAMES = int(sys.argv[1]) if len(sys.argv) > 1 else 60
# PUTUP_ROM=... -- замер другой ROM (например baseline из git HEAD): символы, которых
# нет в layout этой сборки, просто не инструментруются (режим A/B по темпу).
ROM = os.environ.get('PUTUP_ROM') or os.path.join(PROJECT, 'putup_new.rom')
LAYOUT = os.environ.get('PUTUP_LAYOUT') or os.path.join(
    os.path.dirname(os.path.abspath(ROM)), 'tools', 'layout.json')
SYMS = json.load(open(LAYOUT))
SYMS = SYMS.get('symbols', SYMS)
ROM_BASE = 0x0100

LINE = 96                            # отсчётов секундомера на строку растра
FIELD_TOP = 48 * LINE                # 4608: от начала кадра до верхнего края поля
FRAME_LEN = 0x7500                   # 29952 отсчётов в кадре
HERO_MARGIN = 112 * LINE             # 10752: окно записи героя (MARGIN в guard'е)
VOFF_TOL = 7 * LINE                  # субпиксельный сдвиг тайла: до 7 строк

MAIN_LOOP = SYMS['lbl_main_game_loop']
INSTRUMENTS = {                      # имя -> адрес входа (отсутствующие пропускаются)
    n: SYMS[a] for n, a in (
        ('enemy_render', 'func_enemy_render'),
        ('erase_old', 'func_ed_erase_old'),
        ('build_cache', 'func_enemy_build_cache'),
        ('blit3', 'func_ed_blit3'),
        ('tile_at_ptr', 'func_draw_tile_at_ptr'),
        ('tile_vram', 'func_render_tile_vram'),
        ('render_all', 'func_render_all'),
        ('hero_render', 'func_hero_render'),
        ('hero_guard', 'func_raster_guard_hero'),
        ('game_update', 'func_game_update'),
    ) if a in SYMS
}
WRITERS = tuple(n for n in ('tile_at_ptr', 'tile_vram', 'blit3') if n in INSTRUMENTS)
# (row, voff) каждого писателя: erase читает координаты из var_ed_erase_rc и сдвиг
# var_ed_vo, блиты — из D/E и var_ed_newv
SCRATCH = 0x6A50
V_ED = 0x6A55                        # var_ed_vo   ( erase: смещение старого вида )
V_NEWV = 0x6A58                      # var_ed_newv ( draw : смещение нового вида )
V_ERASE_RC = 0x6A5E
GCODES = 0x6A5A                    # var_ed_gcodes: маркер «нашего» вызова tile_vram
DISP_RC = 0x6A37
DISP_HOFF = 0x6A3D
DISP_CODES = 0x6A44
ISLAND = SYMS['data_ram_init_image_08C3']
STATE1 = ISLAND + 0x57
STATE2 = ISLAND + 0x58
XC = ISLAND + 0x5C
YC = ISLAND + 0x5F

s = None

SYMS_SORTED = sorted((a, n) for n, a in SYMS.items() if isinstance(a, int))


def owner(addr):
    """имя ближайшего предшествующего символа (свободная конкатенация: локальные
    метки в layout не попадают, поэтому даёт имя функции, внутри которой адрес)."""
    import bisect
    i = bisect.bisect_right(SYMS_SORTED, (addr, '\uffff')) - 1
    return SYMS_SORTED[i][1] if i >= 0 and SYMS_SORTED[i][0] <= addr else '?'


def wait_pause(limit=25.0):
    t0 = time.time()
    while time.time() - t0 < limit:
        if not s.call("debug_is_running").get("running"):
            return True
        time.sleep(0.02)
    return False


def read(addr, n):
    return list(bytes_of(s.call("debug_read_memory", {"address": addr, "size": n})))


def write(addr, data):
    s.call("debug_write_memory", {"address": addr, "data": list(data)})


def regs():
    r = s.call("debug_get_registers")
    return {k.lower(): to_addr(v) for k, v in r.items() if isinstance(v, str)}
    # 'h'/'l' -> байты, 'hl' -> пара (для сравнения с адресом RAM нужен 'hl')


def elapsed():
    """(elapsed, frame): отсчёт ROM-овского секундомера + номер кадра из beam state.
    Номер кадра нужен, чтобы заметить перезагрузку cnt1 посреди замера (span > кадра)."""
    s.call("debug_write_io", {"port": 0x08, "value": 0x40})
    lo = to_addr(s.call("debug_read_io", {"port": 0x0A})['value'])
    hi = to_addr(s.call("debug_read_io", {"port": 0x0A})['value'])
    cnt = (FRAME_LEN - ((hi << 8) | lo)) & 0xFFFF
    return cnt, s.call("debug_get_beam_state")['frame']


def ret_addr():
    """адрес возврата = u16 по SP (функции 8080 вызываются CALL, не RST)."""
    sp = regs()['sp']
    return read(sp, 2)[0] | (read(sp + 1, 1)[0] << 8)


def writer_geom(name):
    """(row, voff) пишущего тайла на ВХОДЕ писателя.
    row=None — писатель вызван не из рендерера врагов (например перерисовка огня),
    его полоса здесь не считаем; row>=0x18 — тайл вне поля ( erase/draw guard'ы )."""
    r = regs()
    if name == 'tile_at_ptr':
        if r['hl'] != V_ERASE_RC:           # не наш вызов (erase_old пишет через него)
            return None, 0
        return read(V_ERASE_RC, 1)[0], read(V_ED, 1)[0]
    if name in ('tile_vram', 'blit3'):
        if name == 'tile_vram' and r['hl'] != GCODES:
            return None, 0                  # graphics-указатель не наш -> чужой вызов
        return r['e'], read(V_NEWV, 1)[0]
    return None, 0


class Meter:
    """Дельты «вход -> RET» по каждому инструменту. Дельта считается по секундомеру
    ROM; смена кадра между входом и выходом = переполнение, уходит в overrun.
    Для писателей дополнительно хранится геометрия (row, voff) окна записи."""

    def __init__(self):
        self.names = {}          # addr -> имя (вход или RET)
        self.open = {}           # имя -> [(elapsed, frame, row, voff)]
        self.costs = {}          # имя -> [(дельта, elapsed_входа, elapsed_выхода)]
        self.writes = {}         # имя писателя -> [(дельта, вход, выход, row, voff)]
        self.overrun = {}        # имя -> [(дельта, frame_входа, frame_выхода)]
        self.ret_of = {}         # имя -> {адреса RET}
        self.bps = set()

    def bp(self, addr, on=True):
        if on and addr not in self.bps:
            s.call("debug_set_breakpoint", {"address": addr})
            self.bps.add(addr)
        elif not on and addr in self.bps:
            s.call("debug_remove_breakpoint", {"address": addr})
            self.bps.discard(addr)

    def arm(self):
        for name, addr in INSTRUMENTS.items():
            self.names[addr] = name
            self.bp(addr)
            self.open.setdefault(name, [])
            self.costs.setdefault(name, [])
            self.overrun.setdefault(name, [])
            self.ret_of.setdefault(name, set())
            if name in WRITERS:
                self.writes.setdefault(name, [])

    def handle(self, pc, e, f):
        name = self.names.get(pc)
        if name is None or name == 'frame':            # граница кадра — не измеряем
            return name
        if pc in self.ret_of[name]:                     # выход
            stack = self.open[name]
            if not stack:
                return name
            e0, f0, row, voff = stack.pop()
            d = e - e0
            if f != f0 or d < 0:
                self.overrun[name].append((d, f0, f))
            elif name in WRITERS:
                self.writes[name].append((d, e0, e, row, voff))
            else:
                self.costs[name].append((d, e0, e))
            return name
        # вход: адрес возврата из стека, ставим на него bp
        row, voff = writer_geom(name) if name in WRITERS else (None, 0)
        r = ret_addr()
        self.open[name].append((e, f, row, voff))
        if r not in self.bps:
            self.bp(r)
            self.names[r] = name
            self.ret_of[name].add(r)
        return name

    def clear(self):
        """на границе кадра: незакрытые входы (досрочный RET guard'а) не наследуются"""
        for k in self.open:
            self.open[k] = []


def stats(v):
    if not v:
        return "нет событий"
    d = sorted(x[0] for x in v)
    p95 = d[min(len(d) - 1, int(len(d) * 0.95))]
    return (f"n={len(d):4d} медиана={d[len(d) // 2]:6d} p95={p95:6d} max={d[-1]:6d} "
            f"(строк: {d[len(d) // 2] / LINE:5.1f} / {p95 / LINE:5.1f} / "
            f"{d[-1] / LINE:5.1f})")


def classify(d, e0, e1, row, voff):
    """Отнести окно записи к полосу луча тайла. Полоса = 2 глиф-строки по 8 строк:
    band_top = 4608 + 768*row (+-субпиксельный voff), band_bot = band_top + 16*96.
    'до луча'   — вся запись завершилась, пока луч не вошёл в полосу;
    'после луча' — луч уже прошёл полосу до начала записи (обновление сохранилось бы
                  на следующий кадр, разрыва нет);
    'пересечение' — луч был в полосе во время записи -> тайл может оказаться
                    наполовину старым/новым (ровно тот случай, от которого защищает
                    func_raster_guard_hero у героя).
    Допуск VOFF_TOL = 7 строк в обе стороны (easing сдвигает тайл на <8 px)."""
    if row is None:
        return 'чужой вызов'
    if row >= 0x18:
        return 'вне поля'
    top = FIELD_TOP + 768 * row
    bot = top + 16 * LINE
    if e1 <= top + VOFF_TOL:
        return 'до луча'
    if e0 >= bot - VOFF_TOL:
        return 'после луча'
    return 'пересечение'


def main():
    global s
    notes = []
    s = McpSession(cwd=ROOT)
    s.start()
    m = Meter()
    frame_marks = []
    try:
        s.load_rom(ROM, org=ROM_BASE)
        s.call("debug_set_breakpoint", {"address": MAIN_LOOP})
        m.names[MAIN_LOOP] = 'frame'
        s.call("debug_run")
        time.sleep(0.3)
        s.call("debug_press_key", {"key": "SPACE"})
        assert wait_pause(), "игра не стартовала"
        INT = {'seq': 0}               # последний учтённый seq hardware-прерываний
        # стартовый бэклог прерываний (заставка/загрузка уровня, там CPU не спит в HLT)
        # не должен попасть в статистику пропусков: стартуем счётчик с текущего seq
        ev0 = s.call("debug_get_int_events", {"max_entries": 5000})['events']
        if ev0:
            INT['seq'] = int(ev0[-1]['seq'])
        m.arm()

        frames = 0
        cur = {}                    # открытый span enemy_render: {'s','ev'}
        spans = []                  # (старт, финиш, [события], верхняя строка, луч.кадр, финиш работы)
        blown = []                  # (индекс кадра, beam frame, ret_pc) - ВBlank застал CPU за работой
        tick_at = []                # beam frame на входе в func_game_update (период тика)

        def drain_ints(when):
            """Новые hardware-прерывания с момента последнего дренажа. was_halt=false =
            VBlank пришёлся на работающий CPU = пропуск кадра (бюджет раста исчерпан).
            Возвращает число пропусков в этом burst'е (для длины работы кадра)."""
            ev = s.call("debug_get_int_events", {"max_entries": 5000})['events']
            new = [x for x in ev if int(x['seq']) > INT['seq']]
            if ev:
                INT['seq'] = int(ev[-1]['seq'])
            cross = 0
            for x in new:
                if not x.get('was_halt'):
                    cross += 1
                    blown.append((when, int(x['frame']), to_addr(x['ret_pc'])))
            return cross

        def pump(stop_frames):
            """Гоняем CPU по breakpoint'ам, пока не наберём stop_frames границ кадра."""
            nonlocal frames, cur
            got = 0
            while got < stop_frames:
                s.call("debug_run")
                if not wait_pause():
                    print("нет событий — игра, похоже, закончилась")
                    return False
                r = regs()
                e, f = elapsed()
                name = m.handle(r['pc'], e, f)
                if name == 'game_update' and r['pc'] == INSTRUMENTS['game_update']:
                    tick_at.append(f)
                if name == 'enemy_render':
                    if r['pc'] in m.ret_of[name]:           # конец рендерера
                        cur['f'] = e
                    else:                                   # начало рендерера
                        cur = {'s': e, 'ev': []}
                elif name and 's' in cur and 'f' not in cur:
                    cur['ev'].append(name)
                if r['pc'] == MAIN_LOOP:
                    m.clear()       # досрочный выход guard'а не наследует стек
                    cross = drain_ints(len(frame_marks))
                    # длина работы burst'а: секундомер обнуляется на каждом VBlank, поэтому
                    # каждый пропущенный кадр добавляет полный кадр длины
                    work = e + cross * FRAME_LEN
                    if frame_marks and f - frame_marks[-1][1] >= 2:
                        # между двумя визитами в начало цикла луч сделал >=2 кадра
                        notes.append(f"кадр {len(frame_marks)}: луч "
                                     f"+{f - frame_marks[-1][1]}")
                    if 'f' in cur:
                        top = min(read(DISP_RC + 2, 1)[0], read(DISP_RC + 4, 1)[0])
                        spans.append((cur['s'], cur['f'], tuple(cur['ev']), top, f, work))
                    cur = {}
                    frame_marks.append((e, f, cross, work))
                    frames += 1
                    got += 1
            return True

        ok = pump(FRAMES)
        n_tick1 = len(tick_at)
        n_marks1 = len(frame_marks)

        # ---- пик: оба слота в одном кадре erase + пересборка + midpoint-блит ----
        # (только для сборки с E1/E2-рендерером: адреса scratch-переменных его)
        n_phase1 = len(spans)
        peak_costs, peak_writes = {}, {}
        if 'enemy_render' in INSTRUMENTS:
            peak_before = {k: len(v) for k, v in m.costs.items()}
            peak_w_before = {k: len(v) for k, v in m.writes.items()}
            for slot, st in ((1, STATE1), (2, STATE2)):
                write(st, [1])
                write(DISP_RC + slot * 2, [6, 10 + slot])
                write(DISP_HOFF + slot, [0])
                write(0x6A40 + slot, [0])
                write(DISP_CODES + slot * 4, [0, 0, 0, 0])
                write(YC + slot, [6])
                write(XC + slot, [11 + slot])   # ровно +1 колонка -> midpoint
            pump(6)
            peak_costs = {k: v[peak_before[k]:] for k, v in m.costs.items()}
            peak_writes = {k: v[peak_w_before[k]:] for k, v in m.writes.items()}
        else:
            peak_before = {k: len(v) for k, v in m.costs.items()}
            peak_w_before = {k: len(v) for k, v in m.writes.items()}
    finally:
        s.close()

    print(f"бюджет кадра, кадров промерено: {frames}")

    print("\n[1] стоимость функций (отсчёты секундомера; строки = /96; без синт. пика)")
    for name in tuple(INSTRUMENTS):
        n0 = peak_before.get(name, 0)
        w0 = peak_w_before.get(name, 0)
        v = (m.costs[name][:n0] +
             [(x[0], x[1], x[2]) for x in m.writes.get(name, [])[:w0]])
        print(f"  {name:13s} {stats(v)}")
        if m.overrun[name]:
            # span пересёк границу VBlank (cnt1 перезагружен). Где он случился —
            # в основном промере или в фазе синт. пика — по номеру луча: последние
            # n_marks1 границ кадра знают свои beam-frame (артефакт §4.4: span,
            # открытый ДО последнего ВBlank основного промера, — не пропуск игры).
            hi_main = frame_marks[n_marks1 - 1][1] if n_marks1 else -1
            det = ', '.join(
                f"(span {d} отсч., кадры {f0}->{f1}, "
                f"{'основной' if f0 <= hi_main else 'синт. пик'})"
                for (d, f0, f1) in m.overrun[name][:6])
            print(f"  {'':13s} !! переполнение кадра (cnt1 перезагружен в span'е): "
                  f"{len(m.overrun[name])} шт.: {det}")

    print("\n[2] кадры по классу работы enemy_render (без синтетического пика)")
    main_spans = spans[:n_phase1]
    if not main_spans:
        print("    нет enemy-спанов (сборка без func_enemy_render) — классы не считаются")
    cls = {'простой (без записи)': [], 'erase+выровненный': [], 'midpoint-блит': [],
           'пересборка кэша': []}
    for (s0, f0, ev, top, bf, end) in main_spans:
        if 'build_cache' in ev:
            k = 'пересборка кэша'
        elif 'blit3' in ev:
            k = 'midpoint-блит'
        elif 'erase_old' in ev:
            k = 'erase+выровненный'
        else:
            k = 'простой (без записи)'
        cls[k].append((s0, f0, f0 - s0, top, end))
    for k, v in cls.items():
        if v:
            d = sorted(x[2] for x in v)
            fin = sorted(x[4] for x in v)
            print(f"    {k:22s} n={len(d):3d} медиана={d[len(d) // 2]:6d} "
                  f"p95={d[min(len(d) - 1, int(len(d) * 0.95))]:6d} max={d[-1]:6d} "
                  f"({d[len(d) // 2] / LINE:5.1f} / {d[-1] / LINE:5.1f} строк) | "
                  f"длина работы кадра max={fin[-1]} ({fin[-1] / LINE:.1f} строк)")
    st = sorted(x[0] for x in main_spans)
    fi = sorted(x[1] for x in main_spans)
    if st:
        print(f"    старт рендерера: {st[len(st) // 2]}..{st[-1]} "
              f"(строка {st[len(st) // 2] / LINE:.1f}) | финиш: "
              f"{fi[len(fi) // 2]}..{fi[-1]} (строка {fi[-1] / LINE:.1f})")

    print("\n[3] окна записи VRAM против полосы луча (tearing; без синт. пика)")
    tot = {'до луча': 0, 'после луча': 0, 'пересечение': 0, 'чужой вызов': 0,
           'вне поля': 0}
    for name in WRITERS:
        c = {'до луча': 0, 'после луча': 0, 'пересечение': 0, 'чужой вызов': 0,
             'вне поля': 0}
        worst = []
        for (d, e0, e1, row, voff) in m.writes[name][:peak_w_before[name]]:
            k = classify(d, e0, e1, row, voff)
            c[k] += 1
            tot[k] += 1
            if k == 'пересечение':
                top = FIELD_TOP + 768 * max(row, 0)
                worst.append(min(e1, top + 16 * LINE) - max(e0, top))
        ours = c['до луча'] + c['после луча'] + c['пересечение']
        print(f"  {name:12s} n={sum(c.values()):4d} (наших {ours:4d}) "
              f"до={c['до луча']:4d} после={c['после луча']:4d} "
              f"ПЕРЕСЕЧЕНИЕ={c['пересечение']:4d} чужие={c['чужой вызов']:4d} "
              f"вне поля={c['вне поля']:4d}")
        if worst:
            w = sorted(worst)
            print(f"  {'':12s} длительность пересечения с лучом: "
                  f"медиана={w[len(w) // 2] / LINE:.1f} строк, max={w[-1] / LINE:.1f}")
    n_w = sum(len(v[:peak_w_before[k]]) for k, v in m.writes.items())
    print(f"  итого окон записи: {n_w}, из них через луч: {tot['пересечение']}")

    print("\n[4] длина работы кадра (EI;HLT -> обратный вход в lbl_main_game_loop)")
    marks = frame_marks[:n_marks1]
    fm = sorted(x[3] for x in marks)
    if not fm:
        print("  нет замеренных кадров")
        return 1
    late = [x for x in fm if x > FRAME_LEN - HERO_MARGIN]
    print(f"  работа кадра: медиана={fm[len(fm) // 2]} ({fm[len(fm) // 2] / LINE:.1f} "
          f"строк) p95={fm[int(len(fm) * 0.95)]} max={fm[-1]} "
          f"({fm[-1] / LINE:.1f} строк, кадр = {FRAME_LEN / LINE:.0f} строк)")
    print(f"  кадров, где работа закончилась позднее окна героя "
          f"(>{FRAME_LEN - HERO_MARGIN}): {len(late)} из {len(fm)}")
    over1 = [x for x in blown if x[0] < n_marks1]
    print(f"  ПРОПУЩЕННЫХ кадров (VBlank застал CPU за работой): {len(over1)} "
          f"из {len(fm)}")
    for (idx, bf, rpc) in over1[:14]:
        k, end = 'нет enemy_span', 0
        if idx < len(main_spans):
            (s0, f0, ev, top, bf2, end) = main_spans[idx]
            k = ('пересборка кэша' if 'build_cache' in ev else
                 ('midpoint-блит' if 'blit3' in ev else
                  ('erase+выровненный' if 'erase_old' in ev else 'простой')))
        print(f"    кадр {idx:3d}: класс={k:18s} длина работы {end:6d} "
              f"({end / LINE:5.1f} строк), PC в момент VBlank = {hex(rpc)} ({owner(rpc)})")
    tp = [b - a for a, b in zip(tick_at[:n_tick1], tick_at[1:n_tick1])]
    if tp:
        from collections import Counter
        print(f"  период тика (hw-кадры между func_game_update): "
              f"{dict(Counter(tp).most_common())} — норма 6+6 (12-кадровое окно)")
    logic = [x for x in m.costs['game_update'][:peak_before['game_update']]]
    print(f"  кадров с логикой (game_update): {len(logic)} из {len(fm)} "
          f"(ожидалось ~{len(fm) / 6:.0f}: 2 прохода на 12-кадровый тик)")

    print("\n[5] синтетический пик (оба слота: erase + пересборка кэша + midpoint-блит)")
    for name in ('enemy_render', 'build_cache', 'erase_old', 'blit3'):
        v = peak_costs.get(name, [])
        if v:
            mx = max(x[0] for x in v)
            print(f"    {name:13s} n={len(v)} max={mx:6d} отсчётов ({mx / LINE:.1f} строк)")
    for name in WRITERS:
        v = peak_writes.get(name, [])
        if v:
            mx = max(x[0] for x in v)
            print(f"    {name:13s} n={len(v)} max={mx:6d} отсчётов ({mx / LINE:.1f} строк)")
    for x in notes:
        print("ЗАМЕЧАНИЕ:", x)

    # ---- [6] регрессионный гейт: бюджет кадра не превышен, пропусков нет ----
    # Порог = FRAME_LEN (312 строк растра до следующего VBlank). Смысл: пока
    # max(работа кадра) < порога и blown пуст, 12-кадровый темп игры держится.
    max_work = fm[-1]
    print("\n[6] ГЕЙТ: работа кадра < бюджета и ноль пропусков")
    print(f"  max работы {max_work} ({max_work / LINE:.1f} строк) < "
          f"{FRAME_LEN} ({FRAME_LEN / LINE:.0f} строк)? "
          f"{'да' if max_work < FRAME_LEN else 'НЕТ'}; "
          f"пропусков {len(over1)} == 0? {'да' if not over1 else 'НЕТ'}")
    if max_work >= FRAME_LEN or over1:
        print("RESULT: FAIL")
        return 1
    print(f"RESULT: PASS (запас {FRAME_LEN - max_work} отсчётов = "
          f"{(FRAME_LEN - max_work) / LINE:.1f} строк)")
    return 0


if __name__ == '__main__':
    sys.exit(main())
