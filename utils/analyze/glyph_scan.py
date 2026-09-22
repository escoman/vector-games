"""Глифы и тайлы: байты → PNG без распознавания (ТЗ §23).

Модуль делает ровно две вещи:

    1. нарезает блок фиксированной длины на глифы (stride × size);
    2. рисует каждый глиф растром и сохраняет PNG.

OCR нет: «это буква А» здесь никто не решает. Из детерминированных признаков
наружу идут только чернила (доля установленных битов), хэш растра и список
дубликатов — по ним AI ищет совпадения с символами в строках.

Разложения битовых плоскостей (`--layout`):

    planar       plane0 rows…, plane1 rows…        (putup: 4×8 байт на глиф,
                                                    Stage 7: копирование
                                                    4×8 в 4 плоскости VRAM)
    interleaved  row: plane0,plane1,plane2,plane3  (построчно)
    mono         1 bpp, по байту на строку

Ширине глифа w ≤ 8 соответствует один байт строки; w = 16 — два байта.
Пиксель получает 4-битный индекс цвета из четырёх плоскостей (Vector-06C:
0x8000=plane3 MSB … 0xE000=plane0 LSB, docs/VECTOR_VERIFIED.md).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys

from analyze.mcp_session import addr_hex, envelope, open_session
from analyze.memory_diff import ImageSource, RuntimeSource
from analyze.probe import run_for
from analyze.rdb import Rdb

PLANES = 4


def _load_pil():
    try:
        from PIL import Image
        return Image
    except ImportError:                                    # pragma: no cover
        raise SystemExit("нужен Pillow (python3 -m pip install pillow) — "
                         "PNG рисовать нечем")


def rows_per_glyph(width, height):
    return int(height)


def unpack_plane(data, offset, width, height, bytes_per_row):
    """Плоскость → список строк битов. Байт строки = биты p..p+width-1."""
    rows = []
    for row in range(height):
        base = offset + row * bytes_per_row
        bits = []
        for byte_index in range(bytes_per_row):
            byte = data[base + byte_index] if base + byte_index < len(data) else 0
            bits.extend((byte >> bit) & 1 for bit in range(7, -1, -1))
        rows.append(bits[:width])
    return rows


def glyph_planes(data, start, width, height, layout, stride):
    """Разложить байты глифа на 4 плоскости (для mono — одну)."""
    bytes_per_row = max(1, (width + 7) // 8)
    plane_size = bytes_per_row * height
    planes = []
    if layout == "planar":
        for plane in range(PLANES):
            planes.append(unpack_plane(data, start + plane * plane_size,
                                       width, height, bytes_per_row))
    elif layout == "interleaved":
        for plane in range(PLANES):
            rows = []
            for row in range(height):
                offset = start + row * PLANES * bytes_per_row + plane * bytes_per_row
                rows.append(unpack_plane(data, offset, width, 1,
                                         bytes_per_row)[0])
            planes.append(rows)
    else:                                                  # mono
        planes.append(unpack_plane(data, start, width, height, bytes_per_row))
    return planes


def compose(planes, width, height):
    """Плоскости → матрица 4-битных индексов цвета."""
    grid = []
    for row in range(height):
        line = []
        for col in range(width):
            value = 0
            for index, plane in enumerate(planes):
                bit = plane[row][col] if row < len(plane) and col < len(plane[row]) \
                    else 0
                value |= bit << (PLANES - 1 - index)
            line.append(value)
        grid.append(line)
    return grid


def ink_share(grid):
    total = sum(1 for row in grid for value in row)
    count = sum(1 for row in grid for value in row if value)
    return round(count / total, 4) if total else 0.0


def save_png(Image, grid, path, scale=4, palette=None):
    width = len(grid[0]) if grid else 0
    height = len(grid)
    image = Image.new("P", (width * scale, height * scale))
    colors = palette or default_palette()
    flat = []
    for value in colors:
        flat.extend(value)
    while len(flat) < 256 * 3:
        flat.extend((0, 0, 0))
    image.putpalette(flat)
    for y, row in enumerate(grid):
        for x, value in enumerate(row):
            for dy in range(scale):
                for dx in range(scale):
                    image.putpixel((x * scale + dx, y * scale + dy), value)
    image.save(path)
    return path


def default_palette():
    """4 плоскости → 16 индексов. Конкретные RGB — только для readability:
    настоящая палитра Vector-06C в отчёте не утверждается."""
    base = [(0, 0, 0), (0, 0, 255), (0, 255, 0), (0, 255, 255),
            (255, 0, 0), (255, 0, 255), (255, 255, 0), (255, 255, 255)]
    return [rgb for rgb in base] + [tuple(min(255, c // 2) for c in rgb)
                                    for rgb in base]


def strip_png(Image, grids, path, scale=4, gap=1):
    """Все глифы одной полосы — чтобы глазами сравнивать повторы."""
    if not grids:
        return None
    width, height = len(grids[0][0]), len(grids[0])
    total_w = (width + gap) * len(grids) * scale
    image = Image.new("L", (total_w, (height + gap) * scale), 255)
    for index, grid in enumerate(grids):
        for y, row in enumerate(grid):
            for x, value in enumerate(row):
                shade = 0 if value else 255
                for dy in range(scale):
                    for dx in range(scale):
                        image.putpixel(((index * (width + gap) + x) * scale + dx,
                                        (y * scale) + dy), shade)
    image.save(path)
    return path


def scan_block(data, base, count, stride, width, height, layout, size=None):
    """Нарезка блока на глифы + хэши (повторы — детерминированный признак)."""
    size = size or stride
    out = []
    for index in range(count):
        start = index * stride
        if start + size > len(data):
            break
        planes = glyph_planes(data, start, width, height, layout, stride)
        grid = compose(planes, width, height)
        raw = bytes(data[start:start + size])
        out.append({
            "index": index,
            "address": addr_hex(base + start),
            "bytes": raw.hex().upper(),
            "sha1": hashlib.sha1(raw).hexdigest()[:12],
            "ink_share": ink_share(grid),
            "grid": grid,
        })
    return out


def duplicate_groups(entries):
    groups = {}
    for entry in entries:
        groups.setdefault(entry["sha1"], []).append(entry["index"])
    return [{"sha1": sha, "count": len(idxs), "indices": idxs,
             "addresses": [entries[i]["address"] for i in idxs]}
            for sha, idxs in sorted(groups.items()) if len(idxs) > 1]


class GlyphScanner:
    def __init__(self, session, cache=None, out_dir=None):
        self.session = session
        self.cache = cache
        self.out_dir = out_dir

    def run(self, source, address, count, width=8, height=8, layout="planar",
            stride=None, scale=4, save=True, name_prefix=None):
        stride = stride or ((width + 7) // 8) * height * (1 if layout == "mono"
                                                          else PLANES)
        span = stride * count
        data = source.read(address, address + span - 1)
        entries = scan_block(data, address, count, stride, width, height,
                             layout, size=stride)
        Image = _load_pil()
        prefix = name_prefix or "%s_%s_%dx%d_%s" % (
            os.path.splitext(os.path.basename(getattr(source, "path",
                                                      "runtime")))[0],
            addr_hex(address), width, height, layout)
        if save and self.out_dir:
            os.makedirs(self.out_dir, exist_ok=True)
            for entry in entries:
                path = os.path.join(self.out_dir, "%s_%03d.png" % (prefix,
                                                                   entry["index"]))
                save_png(Image, entry["grid"], path, scale)
                entry["png"] = path
            strip_png(Image, [e["grid"] for e in entries],
                      os.path.join(self.out_dir, "%s_strip.png" % prefix), scale)
        for entry in entries:
            entry.pop("grid", None)
        return {
            "address": addr_hex(address),
            "memory_source": source.kind,
            "layout": layout, "width": width, "height": height,
            "stride": stride, "count_requested": count, "count": len(entries),
            "entries": entries,
            "duplicates": duplicate_groups(entries),
            "status": "CANDIDATE",
            "note": "никакого OCR: растр и хэши — наблюдения, символы назначает AI",
        }


def main(argv=None):
    parser = argparse.ArgumentParser(prog="analyze.glyph_scan",
                                     description="Глифы/тайлы → PNG (без OCR)")
    parser.add_argument("--rom", required=True)
    parser.add_argument("--org", type=lambda s: int(s, 0), default=0x0100)
    parser.add_argument("--address", required=True)
    parser.add_argument("--count", type=int, default=16)
    parser.add_argument("--width", type=int, default=8)
    parser.add_argument("--height", type=int, default=8)
    parser.add_argument("--layout", default="planar",
                        choices=("planar", "interleaved", "mono"))
    parser.add_argument("--stride", type=lambda s: int(s, 0), default=None)
    parser.add_argument("--scale", type=int, default=4)
    parser.add_argument("--rdb", default=None,
                        help="сверка: какой RDB-объект накрывает блок")
    parser.add_argument("--runtime", action="store_true",
                        help="читать из RAM-адресов эмулятора, а не из образа")
    parser.add_argument("--run", type=float, default=0.0,
                        help="секунд прогона перед чтением RUNTIME "
                             "(без запуска RAM пуста)")
    parser.add_argument("--out", default=None, help="куда класть PNG")
    parser.add_argument("--no-save", action="store_true")
    parser.add_argument("--cache", default=None)
    parser.add_argument("--server", default=None)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    session, cache = open_session(rom=args.rom, org=args.org, server=args.server,
                                  cache_dir=args.cache)
    try:
        address = int(args.address, 0)
        if args.runtime:
            if args.run:
                # Глифы в RAM появляются только после того, как ROM сам их
                # туда положил; читать RUNTIME без прогона — путь к нулям.
                run_for(session, cache, rom=args.rom, org=args.org,
                        seconds=args.run)
            source = RuntimeSource(session, cache)
        else:
            source = ImageSource(args.rom, args.org)
        out_dir = args.out or os.path.join(cache.root if cache else ".", "glyphs")
        scanner = GlyphScanner(session, cache, out_dir=out_dir)
        result = scanner.run(source, address, args.count, width=args.width,
                             height=args.height, layout=args.layout,
                             stride=args.stride, scale=args.scale,
                             save=not args.no_save)
        rdb = Rdb.load(args.rdb) if args.rdb else Rdb.from_session(session)
        obj = rdb.at(address)
        result["rdb_object"] = obj.name if obj else None
        result["rdb_type"] = obj.type if obj else None
        result = envelope(
            result, module="glyph_scan", session=session, cache=cache,
            verdict="%d глиф(а) из %d, групп повторов %d, источник %s"
                    % (result["count"], result["count_requested"],
                       len(result["duplicates"]), result["memory_source"]),
            note="растровые признаки: доля закрашенного, совпадающие блоки; "
                 "глифы не угадываются и в текст не распознаются")
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print("глифов: %d, повторов групп: %d, out=%s"
                  % (result["count"], len(result["duplicates"]), out_dir))
            for entry in result["entries"][:20]:
                print("  %-8s ink=%-6s %s" % (entry["address"],
                                              entry["ink_share"],
                                              entry.get("png", "")))
            for group in result["duplicates"][:10]:
                print("  повтор ×%d: %s" % (group["count"],
                                            ", ".join(group["addresses"])))
        print("# mcp calls: %d" % session.stats()["total_calls"], file=sys.stderr)
    finally:
        session.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
