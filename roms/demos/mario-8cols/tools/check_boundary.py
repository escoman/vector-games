#!/usr/bin/env python3
"""check_boundary.py — кадр перехода окна: diff-рендер против эталона.

Сравнивает два способа нарисовать кадр cam=32 после сдвига базы окна 0->32:

  A. инкрементальный (как в игре): кадры 0..31 — diff-рендером, на cam=32
     НАСТОЯЩИЙ _bake_shift из ROM и diff-рендер поверх предыдущего кадра;
  B. эталон: чистый VRAM + полный render_window(cam, CAM_NO_REF).

Если A != B, печать показывает, в каких экранных колонках остались (или
появились лишние) тайлы. Исторически расхождение было ровно в нулевом блоке
по фоновым плоскостям: ref-указатель блока 0 считается как
tile_win + (old_cam - base)*LEVEL_ROWS, а на переходе вперёд old_cam = base-1,
то есть на 64 байта НИЖЕ окна — сравнение шло с мусором BSS, пустые клетки
«совпадали» и не стирались. Правка — колонка-страж tile_win_prevcol перед
tile_win (её заполняет bake_shift), см. main.c.

Проверка заодно подтверждает смежность: _tile_win_prevcol обязан лежать по
адресу _tile_win - LEVEL_ROWS, иначе ассемблер читает не то.

    python3 tools/check_boundary.py [CAM_ГРАНИЦА] [--raw | --noguard]
        --raw     — не перепекать окно (оставить старую базу)
        --noguard — сдвинуть базу, но колонку-страж занулить: воспроизводит
                    состояние «мусор вместо уехавшей колонки», т.е. исходный баг
"""
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "tools"))
from profile_scroll import (CAM_NO_REF, Rom, VIEW, call_asm,  # noqa: E402
                            call_cdecl, new_cpu, parse_incs, set_stride, vram_of)


def symbol_addrs(map_path: Path):
    sym = {}
    for line in map_path.read_text().splitlines():
        m = re.match(r"([A-Za-z_.$][\w.$]*)\s*=\s*\$([0-9A-Fa-f]+)\s*;\s*"
                     r"(addr|const)", line)
        if m:
            sym[m.group(1)] = int(m.group(2), 16)
    return sym


def diff_vram(got, exp):
    """Расхождения по (плоскость, экранный блок 0..31) -> число байт."""
    per = {}
    for addr in range(0x8000, 0x10000):
        i = addr - 0x8000
        if got[i] == exp[i]:
            continue
        rel = addr & 0x7FFF
        plane = rel >> 13                    # 0..3 = веса 8/4/2/1
        block = (rel & 0x1F00) >> 8          # 0..31 = X/8
        per[(plane, block)] = per.get((plane, block), 0) + 1
    return per


def main():
    raw = "--raw" in sys.argv[1:]            # не перепекать окно вовсе
    noguard = "--noguard" in sys.argv[1:]    # страж занулён = исходный баг
    args = [x for x in sys.argv[1:] if not x.startswith("--")]
    cam_b = int(args[0]) if args else 32
    map_path = HERE / "mario-8c.map"
    rom = Rom(HERE / "mario-8c.rom", map_path)
    lv = parse_incs(HERE / "include" / "level.inc")
    rows = lv["ROWS"]
    step = lv["WIN_STEP"]
    a = {k: rom.at(k) for k in ("_render_window", "_bake_window", "_bake_shift",
                                "_tile_win", "_tile_win_base", "_cam_row",
                                "_tile_stride")}

    sym = symbol_addrs(map_path)
    prev = sym.get("_tile_win_prevcol")
    print(f"переход окна: base {cam_b - step} -> {cam_b}, кадр cam={cam_b}, "
          f"старый cam={cam_b - 1}, cam_row=32, "
          f"режим {'БЕЗ перепечки' if raw else 'как в игре'}"
          f"{', страж занулён' if noguard else ''}")
    if prev is None:
        print("!!! в map нет _tile_win_prevcol — правка не собрана")
        return 2
    if prev + rows != a["_tile_win"]:
        print(f"!!! _tile_win_prevcol={prev:04X} не смежно с окном: "
              f"ожидаем {a['_tile_win'] - rows:04X}, разрыв "
              f"{a['_tile_win'] - prev} байт")
        return 2
    print(f"смежность OK: _tile_win_prevcol={prev:04X} .. "
          f"{prev + rows - 1:04X}, _tile_win={a['_tile_win']:04X}")

    # ---------- A. инкрементально, настоящими функциями из ROM ----------
    cpuA = new_cpu(rom)
    set_stride(cpuA, rom, rows)
    cpuA.wb(a["_cam_row"], 32)
    cpuA.ww(a["_tile_win_base"], 0)
    call_cdecl(cpuA, a["_bake_window"], [])
    call_asm(cpuA, a["_render_window"], [0, CAM_NO_REF, 0, VIEW])
    base = 0
    for c in range(1, cam_b + 1):
        nb = c & ~(step - 1)
        if nb != base and not raw:
            call_cdecl(cpuA, a["_bake_shift"], [nb])
            got_base = cpuA.rw(a["_tile_win_base"])
            assert got_base == nb, f"bake_shift не сдвинул базу: {got_base}"
            base = nb
            if noguard:
                cpuA.mem[prev:prev + rows] = bytes(rows)
        res = call_asm(cpuA, a["_render_window"], [c, c - 1, 0, VIEW])
        if c == cam_b:
            got = vram_of(cpuA)

    # ---------- B. эталон: чистый экран + полный рендер ----------
    cpuB = new_cpu(rom)
    set_stride(cpuB, rom, rows)
    cpuB.wb(a["_cam_row"], 32)
    cpuB.ww(a["_tile_win_base"], cam_b)
    call_cdecl(cpuB, a["_bake_window"], [])
    call_asm(cpuB, a["_render_window"], [cam_b, CAM_NO_REF, 0, VIEW])
    exp = vram_of(cpuB)

    # ---------- окно после сдвига == окно полной перепечки? ----------
    winA = cpuA.mem[a["_tile_win"]:a["_tile_win"] + lv["WIN_COLS"] * rows]
    winB = cpuB.mem[a["_tile_win"]:a["_tile_win"] + lv["WIN_COLS"] * rows]
    print(f"\nbake_shift даёт то же окно, что и полная перепечка: "
          f"{bytes(winA) == bytes(winB)}")
    pv = cpuA.mem[prev:prev + rows]
    print(f"колонка-страж после сдвига: {[hex(x) for x in pv[:8]]}… "
          f"(нулей не заполнена: {any(pv)})")

    d = diff_vram(got, exp)
    bad = sum(d.values())
    print(f"\nкадр перехода: {res.cyc:,} T, записей VRAM {res.vram:,}")
    if not bad:
        print("РАСХОЖДЕНИЙ НЕТ — кадр после перехода идентичен эталону")
        return 0
    print(f"РАСХОЖДЕНИЯ: {bad} байт VRAM")
    print(f"{'плоск.':>7} {'экран.колонка':>14} {'байт':>6}")
    for (plane, block), n in sorted(d.items()):
        print(f"{plane:>7} {block:>14} {n:>6}")
    print("плоскости 0,1 = фон (веса 8,4), 2,3 = персонаж (веса 2,1)")
    return 1


if __name__ == "__main__":
    sys.exit(main())
