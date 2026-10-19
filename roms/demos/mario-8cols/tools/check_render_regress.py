#!/usr/bin/env python3
"""check_render_regress.py — контрольные суммы VRAM по шагам скролла.

Гоняет реальный ROM шагами скролла (как в игре: diff-рендер каждого кадра поверх
прошлого) и печатает хэш VRAM после каждого шага. Снимки двух сборок (до/после
оптимизации) должны давать ОДИНАКОВЫЕ строки везде, кроме кадра перехода окна
(cam кратно OBJ_WIN_STEP) — там правка бага намеренно меняет картинку.

    python3 tools/check_render_regress.py [ROM MAP] [ШАГОВ]
"""
import hashlib
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HERE / "tools"))
from profile_scroll import (CAM_NO_REF, Rom, VIEW, bake_shift, bake_window,  # noqa: E402
                            call_asm, install_window, new_cpu, outgoing_col,
                            parse_incs, set_stride, vram_of)


def main():
    rom_path = Path(sys.argv[1]) if len(sys.argv) > 1 else HERE / "mario-8c.rom"
    map_path = Path(sys.argv[2]) if len(sys.argv) > 2 else HERE / "mario-8c.map"
    steps = int(sys.argv[3]) if len(sys.argv) > 3 else 40
    print(f"# ROM {rom_path} ({rom_path.stat().st_size} байт), шагов {steps}")
    rom = Rom(rom_path, map_path)
    lv = parse_incs(HERE / "include" / "level.inc")
    rows = lv["ROWS"]
    a = {k: rom.at(k) for k in ("_render_window", "_render_rowband", "_tile_win",
                                "_tile_win_base", "_cam_row", "_tile_stride")}
    cpu = new_cpu(rom)
    set_stride(cpu, rom, rows)
    cpu.wb(a["_cam_row"], 32)
    base = 0
    win = bake_window(lv, base)
    install_window(cpu, a, win, base, lv)
    call_asm(cpu, a["_render_window"], [0, CAM_NO_REF, 0, VIEW])
    print(f"cam  0 base  0 row32 {hashlib.sha1(vram_of(cpu)).hexdigest()[:16]}")
    cam, cam_row = 0, 32
    for c in range(1, steps + 1):
        nb = c & ~(lv["WIN_STEP"] - 1)
        if nb != base:
            # страж читаем ДО сдвига: bake_shift правит win на месте
            pc = outgoing_col(win, base, nb, lv)
            if bake_shift(win, base, nb, lv) is None:
                win = bake_window(lv, nb)
                install_window(cpu, a, win, nb, lv)
            else:
                # колонку-страж (то, что в исправленной сборке кладёт
                # bake_shift) ставим обеим сборкам — иначе паритет проверялся
                # бы над мусором BSS, а не над одним и тем же входом
                install_window(cpu, a, win, nb, lv, prevcol=pc)
            base = nb
        call_asm(cpu, a["_render_window"], [c, c - 1, 0, VIEW])
        cam = c
        print(f"cam {c:>3} base {base:>3} row{cam_row:<3} "
              f"{hashlib.sha1(vram_of(cpu)).hexdigest()[:16]}")
    # Покрытие cam_row на горизонтальных шагах: и выровненных по байту,
    # и нет. Любая оптимизация, которая читает cam_row (сдвиг окна, пропуск
    # строк, маска-фильтр), обязана давать тот же VRAM при любом cam_row —
    # вход одинаков для baseline и кандидата, поэтому расхождение хэша сразу
    # указывает на ошибку сдвига/клипа. (#1 - маска грязных строк - измерена и
    # откачена, см. docs/OPTIMIZATION.MD «Не прошло»; покрытие оставлено.)
    for cam_row in (0, 4, 8, 13, 16, 27):
        cpu.wb(a["_cam_row"], cam_row)
        for _ in range(3):
            cam += 1
            nb = cam & ~(lv["WIN_STEP"] - 1)
            if nb != base:
                pc = outgoing_col(win, base, nb, lv)
                if bake_shift(win, base, nb, lv) is None:
                    win = bake_window(lv, nb)
                    install_window(cpu, a, win, nb, lv)
                else:
                    install_window(cpu, a, win, nb, lv, prevcol=pc)
                base = nb
            call_asm(cpu, a["_render_window"], [cam, cam - 1, 0, VIEW])
            print(f"cam {cam:>3} base {base:>3} row{cam_row:<3} "
                  f"{hashlib.sha1(vram_of(cpu)).hexdigest()[:16]}")
    cpu.wb(a["_cam_row"], 32)
    cam_row = 32
    # вертикальная составляющая: одна открытая полоса + diff-кадр.
    # world_row передаём СВОИМ ходом, а cam — последний отрисованный: с чужим
    # cam local = cam - base уйдёт за окно, и чтение мусора за его пределами
    # сравнивало бы не рендер, а байты кодового сегмента двух сборок.
    for r in (30, 31, 33, 48, 0, 32):
        cam_row = r
        cpu.wb(a["_cam_row"], r)
        call_asm(cpu, a["_render_rowband"], [r, cam])
        print(f"rb  {r:>3} base {base:>3} row{cam_row:<3} "
              f"{hashlib.sha1(vram_of(cpu)).hexdigest()[:16]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
