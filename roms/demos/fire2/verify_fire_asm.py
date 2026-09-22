#!/usr/bin/env python3
"""verify_fire_asm.py — прогон fire.asm в эмуляторе проекта (utils/emulator/v06_emu.py).

Сверяет НАСТОЯЩИЙ 8080-код (rnd_init/fire_generate/fire_render) с независимой
Python-реализацией C-алгоритма из main.c:
  1) rnd_table после rnd_init == эталон (LCG seed*251+73, >>8);
  2) fire_buf после каждого fire_generate == эталон (байт-в-байт);
  3) prev_buf == fire_buf после fire_render (теневой буфер синхронен);
  4) VRAM после прогона == полный рендер эталонного fire_buf (все 4 плоскости).

Важно: вызовы идут с sp=0x7FF0 (ниже VRAM 0x8000), иначе fire_render своими
записями в VRAM (вплоть до ~0xFF9F) затрёт стек/сентинел harness'а.
"""
import sys
from pathlib import Path

EMU_DIR = Path(__file__).resolve().parents[3] / "utils" / "emulator"
sys.path.insert(0, str(EMU_DIR))
import v06_emu  # noqa: E402
from v06_emu import Emulator8080  # noqa: E402

# Ассемблер v06_emu не знает несколько стандартных 8080-мнемоник, которые его
# же CPU исполняет (INX/DCX/SPHL). Локально (не трогая общий файл) дополняем
# ассемблер, чтобы он собирал настоящий рукописный ASM вроде fire.asm.
_RPS = v06_emu.RPS
_orig_ai = v06_emu.assemble_instruction


def _ai(line, symbols, unresolved_zero=False):
    r = _orig_ai(line, symbols, unresolved_zero)
    if r is not None:
        return r
    parts = line.strip().split(None, 1)
    if not parts:
        return None
    mn = parts[0].lower()
    ops = v06_emu.split_args(parts[1]) if len(parts) > 1 else []
    if mn == "inx" and ops and ops[0].lower() in _RPS:
        return [0x03 | (_RPS[ops[0].lower()] << 4)]
    if mn == "dcx" and ops and ops[0].lower() in _RPS:
        return [0x0B | (_RPS[ops[0].lower()] << 4)]
    if mn == "sphl":
        return [0xF9]
    return None


v06_emu.assemble_instruction = _ai

FIRE_W, FIRE_H = 64, 40
BUFLEN = (FIRE_W * FIRE_H) // 2      # 1280
POWER = 153
FRAMES = 6
SP = 0x7FF0
PLANES = (0xE000, 0xC000, 0xA000, 0x8000)


class Ref:
    """Точная копия C-алгоритма из main.c."""

    def __init__(self):
        self.table = [0] * 256
        seed, i = 0x1234, 0
        while True:
            seed = (seed * 251 + 73) & 0xFFFF
            self.table[i] = (seed >> 8) & 0xFF
            i = (i + 1) & 0xFF
            if i == 0:
                break
        self.idx = 0
        self.fire = [0] * BUFLEN

    def rnd(self):
        v = self.table[self.idx]
        self.idx = (self.idx + 1) & 0xFF
        return v

    def get(self, x, y):
        b = self.fire[(y << 5) + (x >> 1)]
        return (b >> 4) & 0xF if (x & 1) == 0 else b & 0xF

    def put(self, x, y, val):
        idx = (y << 5) + (x >> 1)
        b = self.fire[idx]
        self.fire[idx] = ((b & 0xF0) | (val & 0x0F)) if (x & 1) \
            else ((b & 0x0F) | ((val & 0x0F) << 4))

    def generate(self, power):
        for x in range(FIRE_W):                      # строка источников y=0
            if self.rnd() < power:
                self.put(x, 0, 15)
            elif self.rnd() > 128:
                cur = self.get(x, 0)
                self.put(x, 0, cur - 2 if cur > 2 else 0)
        for y in range(1, FIRE_H):
            self.idx = (self.idx + 7) & 0xFF         # rowbump
            for x in range(FIRE_W):
                sx = x + ((self.rnd() % 3) - 1)
                if sx < 0:
                    sx += FIRE_W
                elif sx >= FIRE_W:
                    sx -= FIRE_W
                above = self.get(sx, y - 1)
                decay = self.rnd() & 1
                if y >= FIRE_H // 2 and self.rnd() > 178:
                    decay += 1
                self.put(x, y, above - decay if above > decay else 0)


def expected_vram(fire):
    """Полный рендер fire_buf в VRAM (как fire_render без оптимизаций)."""
    vram = {}
    for idx, cur in enumerate(fire):
        col, fy = idx & 31, idx >> 5
        block = (col << 8) + (fy << 2)
        cl, cr = cur >> 4, cur & 0xF
        for p in range(4):
            bn = (((cl >> p) & 1) << 4) | ((cr >> p) & 1)
            val = bn * 0x0F
            for k in range(4):
                vram[PLANES[p] + block + k] = val
    return vram


def first_diff(a, b):
    for i in range(len(a)):
        if a[i] != b[i]:
            return i
    return -1


def main():
    here = Path(__file__).resolve().parent
    emu = Emulator8080()
    emu.load_asm(str(here / "fire.asm"))
    lab = emu.asm.labels
    a_fire, a_prev = lab["_fire_buf"], lab["_prev_buf"]
    a_table, a_mod3 = lab["_rnd_table"], lab["_rnd_mod3"]

    ref = Ref()

    # --- 1) rnd_init ---
    emu.call("_rnd_init", sp=SP, max_steps=3_000_000)
    tbl = list(emu.cpu.mem[a_table:a_table + 256])
    if tbl != ref.table:
        i = first_diff(tbl, ref.table)
        print(f"FAIL rnd_init: rnd_table[{i}] asm={tbl[i]:02X} ref={ref.table[i]:02X}")
        return 1
    mod3 = list(emu.cpu.mem[a_mod3:a_mod3 + 256])
    if mod3 != [v % 3 for v in range(256)]:
        print("FAIL rnd_init: rnd_mod3 != v%3")
        return 1
    fb = list(emu.cpu.mem[a_fire:a_fire + BUFLEN])
    pb = list(emu.cpu.mem[a_prev:a_prev + BUFLEN])
    if any(fb) or any(pb):
        print("FAIL rnd_init: fire_buf/prev_buf не обнулены")
        return 1
    print("OK  rnd_init: rnd_table[256], rnd_mod3[256], буферы обнулены")

    # --- 2..3) покадровая сверка ---
    for frame in range(FRAMES):
        emu.call("_fire_generate", args=(POWER,), sp=SP, max_steps=3_000_000)
        ref.generate(POWER)
        asm_fire = list(emu.cpu.mem[a_fire:a_fire + BUFLEN])
        if asm_fire != ref.fire:
            i = first_diff(asm_fire, ref.fire)
            y, x = (i * 2) // FIRE_W, (i * 2) % FIRE_W
            print(f"FAIL frame {frame}: fire_buf[{i}] (y~{y},x~{x}) "
                  f"asm={asm_fire[i]:02X} ref={ref.fire[i]:02X}")
            return 1

        emu.call("_fire_render", sp=SP, max_steps=3_000_000)
        asm_prev = list(emu.cpu.mem[a_prev:a_prev + BUFLEN])
        if asm_prev != asm_fire:
            i = first_diff(asm_prev, asm_fire)
            print(f"FAIL frame {frame}: prev_buf[{i}]={asm_prev[i]:02X} "
                  f"!= fire_buf[{i}]={asm_fire[i]:02X} (теневой буфер не синхронен)")
            return 1
        print(f"OK  frame {frame}: fire_buf == эталон, prev_buf == fire_buf")

    # --- 4) VRAM == полный рендер эталона ---
    exp = expected_vram(ref.fire)
    bad = 0
    for addr, val in exp.items():
        if emu.cpu.rb(addr) != val:
            if bad == 0:
                print(f"FAIL VRAM: [{addr:04X}] asm={emu.cpu.rb(addr):02X} exp={val:02X}")
            bad += 1
    if bad:
        print(f"FAIL VRAM: {bad} байт(а) не совпало")
        return 1
    print(f"OK  VRAM: {len(exp)} байт совпадают с полным рендером эталона")

    # --- визуальная проверка (яркость по строкам) ---
    print("\nСредняя яркость по строкам (y=0 — низ/источник, y=39 — верх):")
    for y in range(0, FIRE_H, 4):
        row = []
        for x in range(FIRE_W):
            row.append(ref.fire[(y << 5) + (x >> 1)] >> (4 if (x & 1) == 0 else 0) & 0xF)
        avg = sum(row) / len(row)
        bar = "#" * int(avg)
        print(f"  y={y:2d} avg={avg:4.1f} {bar}")

    print("\nVERIFY: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
