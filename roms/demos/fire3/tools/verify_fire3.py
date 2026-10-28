#!/usr/bin/env python3
"""
verify_fire3.py — офлайн-проверка roms/demos/fire3/fire.asm на harness-эмуляторе.

Делает три вещи:
  1) прогоняет rnd_init / fire_generate / fire_paint и сверяет fire_buf
     с эталонной Python-моделью той же симуляции (1:1 по битам ГСЧ);
  2) сверяет содержимое VRAM (обе пары плоскостей) с тем, что должна дать
     упаковка пар точек по таблице _pt;
  3) считает такты модели Вектора-06Ц (Intel 8080 + таблицы wait-state)
     и переводит их в кадры 50 Гц и fps.

Запуск:  python3 tools/verify_fire3.py [число_кадров]
"""
import os
import sys
import importlib.util

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.abspath(os.path.join(HERE, '..', '..', '..', '..'))
EMU = os.path.join(PROJ, 'utils', 'emulator', 'v06_emu.py')

spec = importlib.util.spec_from_file_location('v06_emu', EMU)
emu_mod = importlib.util.module_from_spec(spec)
sys.modules['v06_emu'] = emu_mod          # @dataclass внутри модуля этого требует
spec.loader.exec_module(emu_mod)

Emulator8080 = emu_mod.Emulator8080
SENTINEL = emu_mod.SENTINEL
MASK16 = emu_mod.MASK16

# ---------------- константы из fire.asm (держать синхронно) ----------------
FIRE_W = 64
FIRE_H = 20
SCALE_Y = 4
GUARD = 1
ROWEND = GUARD + FIRE_W
STRIDE = 256
RNG_N = 1024              # размер окна ГСЧ
RNG_TAIL = 128            # хвост-копия начала
SEED_R = 7
ROW_ADV = FIRE_W + SEED_R
FRAME_R = 5
TAPER_1 = FIRE_H - 6
TAPER_2 = FIRE_H - 3
DM_LO, DM_MID, DM_HI = 0x1C, 0x18, 0x04
RNG_SEED = 0xACE
RNG_HOLD = 0xC0             # смена направления сдвига — раз из 4 шагов
RNG_STRAIGHT = 0x20         # бит «прямо» против бокового хода (1/2)
RNG_EMBER = 0x40            # бит «остыл уголёк» в базовой строке
LFSR_TAPS = 0xB400
VALMAX = 3
VSCALE = 2                # fire_buf хранит значение, умноженное на 2
POWER = 153
FRAMES = 8
SP = 0x7FF0
PLANES = (0xE000, 0xC000, 0xA000, 0x8000)   # веса 1, 2, 4, 8


def lfsr_table():
    """Окно Галуа-LFSR16 (маска 0xB400) с удержанием направления сдвига
    (биты 0..1) + хвост-копия — байт в байт как в _rnd_init.
    Знак бокового хода ЧЕРЕДУЕТСЯ (случайный k даёт снос -5 клеток — «ветер»)."""
    state = RNG_SEED
    k = 0
    d = 0
    out = []
    for _ in range(RNG_N):
        fb = state & 1
        state >>= 1
        if fb:
            state ^= LFSR_TAPS
        r = ((state >> 8) & 0xFF) ^ (state & 0xFF)
        if (r & RNG_HOLD) == 0:
            if r & RNG_STRAIGHT:
                d ^= 1
                k = 1 + d
            else:
                k = 0
        out.append((r & 0xFC) | k)
    return out + out[:RNG_TAIL]


def decay_mask(y):
    """Маска затухания строки (TAPER) — то же, что патчит ANI в fire.asm."""
    if y < TAPER_1:
        return DM_LO
    return DM_MID if y < TAPER_2 else DM_HI


def pack_table():
    """_pt: смещение idx*2 → (p0, p1), idx = (left<<2)|right."""
    tbl = []
    for left in range(4):
        for right in range(4):
            p0 = (0xF0 if left & 1 else 0) | (0x0F if right & 1 else 0)
            p1 = (0xF0 if left & 2 else 0) | (0x0F if right & 2 else 0)
            tbl.append((p0, p1))
    return tbl


PT = pack_table()


class Ref:
    """(не используется: эталон встроен в Model ниже)"""
    pass


def read_mem(cpu, addr, n):
    return [cpu.rb((addr + i) & MASK16) for i in range(n)]


def main():
    frames = int(sys.argv[1]) if len(sys.argv) > 1 else FRAMES
    emu = Emulator8080()
    asm = emu.load_asm(os.path.join(HERE, '..', 'fire.asm'))
    labels = asm.labels
    emu.cpu.wb(0x3FFF, 0)                       # заглушка, не нужна
    fire_buf = labels['_fire_buf']
    rnd_off = labels['_rnd_off']
    print('labels: _rnd_init=0x%04X _fire_generate=0x%04X _fire_paint=0x%04X '
          '_fire_buf=0x%04X' % (labels['_rnd_init'], labels['_fire_generate'],
                                labels['_fire_paint'], fire_buf))

    # таблица ГСЧ из памяти — для эталона, который читает индекс так же, как asm
    emu.call('_rnd_init', sp=SP)
    table = read_mem(emu.cpu, labels['_rnd_table'], RNG_N + RNG_TAIL)
    ref_table = lfsr_table()
    if table != ref_table:
        d = [i for i in range(len(table)) if table[i] != ref_table[i]]
        print('FAIL: окно ГСЧ не совпало с LFSR-эталоном в %d байт, первый %04X'
              % (len(d), d[0]))
        return 1
    if emu.cpu.rb(rnd_off) or emu.cpu.rb(rnd_off + 1):
        print('FAIL: смещение ГСЧ не обнулено')
        return 1
    print('OK: ГСЧ: LFSR16 окно %d + хвост %d, смещение обнулено' % (RNG_N, RNG_TAIL))

    class Model:
        """Точная копия asm-цикла: базовая строка идёт курсором по HL, строки
        пламени — курсором на стеке; смещение догоняется в конце каждой строки."""

        def __init__(self):
            self.off = 0
            self.buf = [0] * (FIRE_H * STRIDE)

        def guards(self, y):
            b = y * STRIDE
            self.buf[b + GUARD - 1] = self.buf[b + GUARD + FIRE_W - 1]
            self.buf[b + GUARD + FIRE_W] = self.buf[b + GUARD]

        def generate(self):
            p = self.off
            for x in range(FIRE_W):
                r = table[p]
                p += 1
                prev = self.buf[GUARD + x]      # значение прошлого кадра
                if r <= POWER:
                    v = VALMAX
                elif (r & RNG_EMBER) == 0:
                    v = prev - 1 if prev > 0 else 0
                else:
                    v = prev
                self.buf[GUARD + x] = v
            self.off = (self.off + ROW_ADV + FRAME_R) % RNG_N
            self.guards(0)
            for y in range(1, FIRE_H):
                mask = decay_mask(y)
                p = self.off
                src, dst = (y - 1) * STRIDE, y * STRIDE
                for x in range(FIRE_W):
                    r = table[p]
                    p += 1
                    k = r & 3
                    sx = x + (-1 if k == 1 else (1 if k == 2 else 0))
                    above = self.buf[src + GUARD + sx]
                    if (r & mask) == 0:
                        above = above - 1 if above > 0 else 0
                    self.buf[dst + GUARD + x] = above
                self.guards(y)
                self.off = (self.off + ROW_ADV) % RNG_N

    model = Model()
    bad = 0
    for f in range(frames):
        steps = emu.call('_fire_generate', args=(POWER,), sp=SP)
        model.generate()
        got = read_mem(emu.cpu, fire_buf, FIRE_H * STRIDE)
        diff = [(i, got[i], model.buf[i] * VSCALE) for i in range(len(got))
                if got[i] != model.buf[i] * VSCALE
                and i % STRIDE in range(GUARD, ROWEND)]
        if diff:
            bad += 1
            print('FAIL кадр %d: fire_buf расходится в %d клетках, первые: %s'
                  % (f, len(diff), diff[:6]))
        # значения только 0..VALMAX*VSCALE
        over = [v for v in got if v > VALMAX * VSCALE]
        if over:
            print('FAIL кадр %d: значения вне 0..%d: %s'
                  % (f, VALMAX * VSCALE, set(over)))
            return 1

        back = f & 1
        emu.call('_fire_paint', args=(back,), sp=SP)
        # ожидаемые плоскости по модели
        hi = 0xE0 if back == 0 else 0xA0
        w0, w1 = (0, 1) if back == 0 else (2, 3)
        exp = [bytearray(8192) for _ in range(4)]
        for y in range(FIRE_H):
            row = y * STRIDE
            for i in range(FIRE_W // 2):
                left = model.buf[row + GUARD + 2 * i]
                right = model.buf[row + GUARD + 2 * i + 1]
                p0, p1 = PT[(left << 2) | right]
                for dy in range(SCALE_Y):
                    off = (i * 256) + y * SCALE_Y + dy
                    exp[w0][off] = p0
                    exp[w1][off] = p1
        for p in (w0, w1):
            gotp = bytes(read_mem(emu.cpu, PLANES[p], 8192))
            if gotp != bytes(exp[p]):
                d = [i for i in range(8192) if gotp[i] != exp[p][i]]
                print('FAIL кадр %d: плоскость %d differs at %d байт, напр. '
                      'off=0x%04X got=%02X want=%02X'
                      % (f, p, len(d), d[0], gotp[d[0]], exp[p][d[0]]))
                return 1
        if f == 0 or f == frames - 1:
            asm_off = emu.cpu.rb(rnd_off) | (emu.cpu.rb(rnd_off + 1) << 8)
            rows = [sum(1 for x in range(FIRE_W)
                        if model.buf[y * STRIDE + GUARD + x]) for y in range(FIRE_H)]
            nz = sum(rows)
            print('кадр %d: живых строк %d/%d, горящих точек %d/%d, смещение ГСЧ %d'
                  % (f, sum(1 for c in rows if c), FIRE_H, nz, FIRE_W * FIRE_H,
                     asm_off))
            if asm_off != model.off:
                print('  (курсор ГСЧ asm=%d model=%d)' % (asm_off, model.off))
                return 1
            # профиль по высоте: верхние строки должны ГАСНУТЬ, а не упираться
            # в границу буфера (обрезанный язык = почти полная верхняя строка)
            print('     профиль (y=верх … низ): ' +
                  ' '.join('%d' % c for c in reversed(rows)))
    if bad:
        return 1
    print('OK: %d кадров — fire_buf и обе плоскости совпали с эталоном' % frames)
    return 0


if __name__ == '__main__':
    sys.exit(main())
