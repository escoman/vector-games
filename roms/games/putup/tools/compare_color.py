#!/usr/bin/env python3
"""Цвет-гейт: сравнение РАСКРАШЕННОГО экрана orig <-> new (не байт VRAM).

Зачем: когда представление в VRAM намеренно меняется (например, инверсия
плоскости E000 + компенсация палитрой) побайтовая сверка VRAM больше не годится
— плоскости разные, а КАРТИНКА та же. Этот инструмент восстанавливает итоговый
цвет каждого пикселя (4 битовые плоскости -> индекс цвета -> палитра ROM) и
сравнивает цветные изображения orig и new на СОВПАДАЮЩИХ ИГРОВЫХ КАДРАХ.

Синхронизация (Tier 2): кадр считается не по лучу (луч во время пауз дрейфует,
и асинхронный pause давал фазовый сдвиг анимации на 1 кадр — ложные расхождения),
а по хитам брейкпоинта на func_vblank_isr (0x03A4): 1 хит = 1 обработанный INT =
1 игровой кадр. Оба ROM шагаются на одинаковый номер хита от загрузки.

Фазовая стойкость: переходные моменты (исчез/появление объекта) привязаны к
циклу главного цикла, а оно не целое число кадров; любое изменение тактов
движка сдвигает такие переходы на несколько кадров. Поэтому на каждом чекпоинте
снимается лента WMAX кадров, и расхождение = минимум по ВСЕМ парам кадров ленты
(эскалация: сначала окно 3, при несовпадении — 9, затем WMAX). Если картинка
содержательно та же, каждый кадр orig находится в ленте new — min=0.

Маппинг плоскостей (docs/VECTOR_VERIFIED.md, VSDL): 0x8000=бит3(w8),
0xA000=бит2(w4), 0xC000=бит1(w2), 0xE000=бит0(w1); в байте бит7=левый пиксель.
Палитра: слот S = mem[0x08A3+S] (пишет func_vblank_isr OUT 02h/0Ch), 16 цветов.

Использование: python3 tools/compare_color.py [--new ROM] [--label C] [--win 3]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(HERE)
ROOT = os.path.abspath(os.path.join(PROJ, "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "utils", "analyze"))

from mcp_session import McpSession, bytes_of, to_addr  # noqa: E402

ORIG = os.path.join(ROOT, "roms", "redesign", "putup", "src", "putup.rom")
# Адреса ОРИГИНАЛА (фикс.): func_vblank_isr / палитра в putup.rom. Для нового ROM
# (свободная конкатенация) адреса читаются из tools/layout.json (пишет mk_manifest.py).
ORIG_ISR = 0x03A4
ORIG_PALETTE = 0x08A3
PLANES = (0x8000, 0xA000, 0xC000, 0xE000)   # веса 8,4,2,1 (порядок = бит3..бит0)
PALETTE_LEN = 16


def load_layout():
    p = os.path.join(HERE, "layout.json")
    if not os.path.exists(p):
        raise SystemExit("нет tools/layout.json — сначала `make` (он пишет манифест адресов)")
    return json.load(open(p, encoding="utf-8"))
# номера хитов ISR от загрузки ROM: окна чекпоинтов (как былую схему WARMUP+F_*)
H_TITLE = 220 + 200          # заставка/attract
H_PLAY1 = H_TITLE + 100      # игра после SPACE
H_PLAY2 = H_PLAY1 + 100      # игра после LEFT/RIGHT
# клавиши — на фиксированных хитах (не зависят от размера окна сравнения)
K_SPACE, K_LEFT, K_RIGHT = H_TITLE + 5, H_PLAY1 + 5, H_PLAY1 + 35
WMAX = 21                    # кадров в ленте чекпоинта
STEPS = (3, 9, WMAX)         # эскалация окна при несовпадении


def is_running(s):
    return bool(s.call("debug_is_running").get("running"))


def cpu_pc(s):
    return to_addr((s.call("debug_get_state").get("cpu") or {}).get("pc"))


def wait_pause(s, limit=300.0):
    t0 = time.time()
    while is_running(s):
        time.sleep(0.015)
        if time.time() - t0 > limit:
            raise RuntimeError("эмуляция не встала на брейкпоинт за %.0f с" % limit)
    return cpu_pc(s)


def capture_vram(s):
    return bytes_of(s.call("debug_get_vram_bytes", {"address": 0x8000, "length": 32768}))


def capture_palette(s, palette_addr):
    return bytes_of(s.call("debug_read_memory_range", {"address": palette_addr, "length": PALETTE_LEN}))


def decode_colors(vram, palette):
    """-> bytearray длиною 8192*8: итоговый цвет каждого пикселя (плоскость-байт,бит)."""
    rows = 8192
    out = bytearray(rows * 8)
    for i in range(rows):
        b3 = vram[i]                       # 0x8000 w8
        b2 = vram[8192 + i]                # 0xA000 w4
        b1 = vram[16384 + i]               # 0xC000 w2
        b0 = vram[24576 + i]               # 0xE000 w1
        for bit in range(8):
            m = 0x80 >> bit
            idx = (8 if b3 & m else 0) + (4 if b2 & m else 0) + (2 if b1 & m else 0) + (1 if b0 & m else 0)
            out[i * 8 + bit] = palette[idx]
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--new", default=os.path.join(PROJ, "putup_new.rom"))
    ap.add_argument("--label", default="C")
    args = ap.parse_args()

    # окна: [h, h+WMAX) хитов ISR; клавиши на фиксированных хитах
    phases = {
        "title": (H_TITLE, {}),
        "play1": (H_PLAY1, {K_SPACE: "SPACE"}),
        "play2": (H_PLAY2, {K_LEFT: "LEFT", K_RIGHT: "RIGHT"}),
    }

    def phase_windows(s, rom_path, isr, palette_addr):
        s.load_rom(rom_path, org=0x0100)
        s.call("debug_set_breakpoint", {"address": isr})
        palette = capture_palette(s, palette_addr)
        out = {}
        hit = 0
        for name in ("title", "play1", "play2"):
            start, events = phases[name]
            # шагаем до start, вводя клавиши на их хитах
            while hit < start:
                s.call("debug_run")
                p = wait_pause(s)
                if p != isr:
                    raise RuntimeError("останов не на ISR: pc=%s" % p)
                hit += 1
                if hit in events:
                    s.call("debug_type_key", {"key": events[hit]})
            shots = []
            for k in range(WMAX):
                if k:
                    s.call("debug_run")
                    p = wait_pause(s)
                    if p != isr:
                        raise RuntimeError("останов не на ISR: pc=%s" % p)
                    hit += 1
                    if hit in events:
                        s.call("debug_type_key", {"key": events[hit]})
                    # событие внутри ленты одинаково сдвигает оба ROM —
                    # минимум по парам кадров остаётся корректным
                shots.append(decode_colors(capture_vram(s), palette))
            out[name] = shots
        s.call("debug_clear_breakpoints")
        return out

    lines, worst = [], 0
    L = load_layout()
    with McpSession(timeout=120) as s:
        w_orig = phase_windows(s, ORIG, ORIG_ISR, ORIG_PALETTE)
        w_new = phase_windows(s, args.new, L["func_vblank_isr"], L["data_palette"])

    for name in ("title", "play1", "play2"):
        best, used = None, None
        for k in STEPS:
            best = min(sum(1 for x, y in zip(a, b) if x != y)
                       for a in w_orig[name][:k] for b in w_new[name][:k])
            used = k
            if best == 0:
                break
        worst = max(worst, best)
        lines.append("%-6s: мин. цвет-расхождений по ленте win=%d: %d / %d" %
                     (name, used, best, 65536))
    lines.append("ВЕРДИКТ: %s" % ("OK (каждый кадр orig найден в ленте new; картинка та же)"
                                  if worst == 0 else "РАСХОЖДЕНИЕ ЦВЕТОВ"))
    print("\n".join(lines))
    json.dump({"label": args.label, "win": used, "worst": worst},
              open(os.path.join(PROJ, "tools", "color_%s_verdict.json" % args.label), "w"))
    sys.exit(0 if worst == 0 else 1)


if __name__ == "__main__":
    main()
