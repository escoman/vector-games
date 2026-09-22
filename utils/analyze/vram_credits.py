"""Титры в VRAM: предсказание адресов и сверка с рантаймом (ТЗ §23, §15, §16).

Цепочка, которую проверяет модуль:

    строка из RDB (IMAGE)  →  где она в текстовом буфере RAM (RUNTIME)
                           →  (row, col) из смещения курсора
                           →  адрес байтов глифа в 4 плоскостях VRAM
                           →  сравнение с debug_get_vram_bytes

Ничего из этого не «распознаёт текст»: это арифметика адресов и побайтовое
сравнение. ROM-специфичная упаковка строки в адрес НЕ зашита в единственно
верную — перебираются несколько правдоподобных отображений, и наружу
отдаётся то, которое совпало с реальными записями в VRAM (`best_map`).
Вывод — кандидата, а не утверждение «это титры на 23-й строке».

Что берётся из отладчика (никогда не вычисляется локально):
    debug_get_screen_info  → vram_base, разрешение, pixels_per_byte
    debug_get_vram_info    → базовые адреса четырёх плоскостей
    debug_get_vram_bytes   → байты плоскостей (содержимое, без трактовок)
    debug_read_memory_range→ текстовый буфер и блок глифов (RUNTIME)
    RDB                    → объект строки, таблица колонок, таблица указателей
"""
from __future__ import annotations

import argparse
import json
import os
import sys

from analyze.mcp_session import (addr_hex, bytes_of, open_session,
                                session_fields, to_addr)
from analyze.memory_diff import ImageSource, RuntimeSource
from analyze.rdb import Rdb

BYTES_PER_PLANE_ROW = 8          # 8 пикселей по горизонтали = 1 байт плоскости
PLANE_STEP = 0x2000              # шаг между плоскостями в адресе
HL_BIAS = 0xB000                 # `LXI B,B000` + `DAD B` в func_render_glyph
GLYPH_LO, GLYPH_HI = 0x6000, 0x7FFF   # блок глифов в RAM (Stage 7, Finding 2)
VRAM_LO, VRAM_HI = 0x8000, 0xFFFF


# -- отображения «адрес символа → (столбец, байт строки)» ----------

def ror(value, count=2):
    """8-битный поворот вправо — ровно то, что делают две 8080 `RRC`."""
    return ((value >> count) | (value << (8 - count))) & 0xFF


def map_rrc(cursor, offset, columns, bias=HL_BIAS):
    r"""Упаковка из func_render_glyph (Stage 7, `debug_disassemble`):

        LXI B,B000 / DAD B          HL = курсор + 0xB000
        MOV A,L / ANI 1F            column = L & 1F
        RRC/RRC/ANI C0  (из H)  \  row = ror2(H)&C0 | ror2(L)&38
        RRC/RRC/ANI 38  (из L)  /
        LDA 08D0 / SUB B            base_low − row  (вычитание, не сложение)
    """
    hl = (cursor + bias) & 0xFFFF
    high, low = hl >> 8, hl & 0xFF
    return {"column": low & 0x1F,
            "row_part": (ror(high) & 0xC0) | (ror(low) & 0x38),
            "sign": -1}


def map_rrc_add(cursor, offset, columns, bias=HL_BIAS):
    """Та же упаковка, но base_low + row — запасной вариант."""
    return dict(map_rrc(cursor, offset, columns, bias), sign=+1)


def map_grid(cursor, offset, columns):
    """Простейшая сетка без ROM-специфичной упаковки."""
    row, column = divmod(offset, columns)
    return {"column": column, "row_part": row, "sign": +1}


ROW_MAPS = {
    "rrc_sub": map_rrc,
    "rrc_add": map_rrc_add,
    "grid": map_grid,
}


def predict_address(col_table, column, row_part, base_low, sign=-1, plane=0):
    """Адрес 8 байтов одного глифа в одной плоскости VRAM.

    Старший байт — col_table[column] (таблица баз столбцов), младший —
    base_low ± row_part по модулю 256, плоскости разнесены шагом 0x2000.
    Это арифметика адресов: варианты формулы перебираются, а не зашиваются
    как единственно верные.
    """
    if not col_table or not (0 <= column < len(col_table)):
        return None
    low = (to_addr(base_low) + sign * to_addr(row_part)) & 0xFF
    return (((col_table[column] << 8) | low) + plane * PLANE_STEP) & 0xFFFF


def find_in_buffer(data, base, needle, max_hits=8):
    """Поиск байтов строки в буфере (RUNTIME). Возвращает адреса попаданий."""
    hits = []
    start = 0
    while True:
        index = data.find(needle, start)
        if index < 0 or len(hits) >= max_hits:
            break
        hits.append(base + index)
        start = index + 1
    return hits


def glyph_for_char(blob, blob_lo, glyph_ptr, planes=4):
    """8 байт каждой плоскости глифа из среза блока глифов (RUNTIME)."""
    if glyph_ptr is None:
        return []
    start = glyph_ptr - blob_lo
    return [bytes(blob[start + plane * BYTES_PER_PLANE_ROW:
                       start + (plane + 1) * BYTES_PER_PLANE_ROW])
            for plane in range(planes)]


class VramCreditsVerifier:
    def __init__(self, session, cache, image, rdb, screen=None, planes=None):
        self.session = session
        self.cache = cache
        self.image = image
        self.runtime = RuntimeSource(session, cache)
        self.rdb = rdb
        self.screen = screen or session.call("debug_get_screen_info")
        self.plane_info = planes or session.call("debug_get_vram_info")
        self._vram = None
        self._blobs = {}

    # -- массовые чтения ---------------------------------------------------
    # Каждое доказательство снимается ОДНИМ вызовом, дальше режется локально:
    # по вызову на 8 байт каждой плоскости каждого символа — это сотни
    # обращений к серверу там, где достаточно трёх.

    def vram(self):
        """Весь VRAM одним `debug_get_vram_bytes` (максимум = 32768 байт)."""
        if self._vram is None:
            self._vram = bytes_of(self.session.call(
                "debug_get_vram_bytes",
                {"address": VRAM_LO, "length": VRAM_HI - VRAM_LO + 1}))
        return self._vram

    def vram_bytes(self, address, length=BYTES_PER_PLANE_ROW):
        data = self.vram()
        offset = address - VRAM_LO
        if offset < 0 or offset + length > len(data):
            return b""
        return data[offset:offset + length]

    def runtime_blob(self, lo, hi):
        key = (lo, hi)
        if key not in self._blobs:
            self._blobs[key] = bytes(self.runtime.read(lo, hi))
        return self._blobs[key]

    # -- вход --------------------------------------------------------------

    def column_table(self, address=None, size=32):
        """Таблица баз столбцов из ПЗУ (IMAGE)."""
        obj = self.rdb.at(address) if address is not None else None
        if obj is None:
            named = self.rdb.matching(r"col.*table|vram.*col")
            obj = named[0] if named else None
        if obj is None and address is None:
            return None, None
        address = to_addr(address) if address is not None else obj.address
        data = self.image.read(address, address + size - 1)
        return list(data), (obj.name if obj else None)

    def glyph_pointer_table(self, address=None, size=512):
        obj = self.rdb.at(address) if address is not None else None
        if obj is None:
            named = self.rdb.matching(r"glyph.*ptr|ptr.*glyph")
            obj = named[0] if named else None
        address = to_addr(address) if address is not None else (
            obj.address if obj else None)
        if address is None:
            return None, None
        data = self.image.read(address, address + size - 1)
        words = [int.from_bytes(data[i:i + 2], "little")
                 for i in range(0, len(data) - 1, 2)]
        return words, (obj.name if obj else None)

    # -- предсказание ------------------------------------------------------

    def predict(self, string_obj, buffer_lo=0x5000, buffer_hi=0x5400,
                columns=32, col_table=None, glyph_words=None,
                base_low_addr=0x08D0, row_maps=tuple(ROW_MAPS)):
        """Предсказание адресов VRAM для строки + сверка с реальностью."""
        payload = self.session.call("debug_get_rdb_object",
                                    {"address": string_obj.address})
        declared = payload.get("object") or payload or {}
        size = string_obj.size if string_obj.size_known else 16
        image_bytes = self.image.read(string_obj.address,
                                      string_obj.address + size - 1)
        needle = bytes(image_bytes[:min(len(image_bytes), 16)])
        buffer_blob = self.runtime_blob(buffer_lo, buffer_hi)
        cursors = find_in_buffer(buffer_blob, buffer_lo, needle)
        table, table_name = (col_table, "cli") if col_table else self.column_table()
        words, words_name = glyph_words or self.glyph_pointer_table()
        glyph_blob = self.runtime_blob(GLYPH_LO, GLYPH_HI)
        base_low = self.runtime.read(base_low_addr, base_low_addr)[0]
        planes = self._plane_bases()
        attempts = []
        for row_map in row_maps:
            for cursor in cursors:
                plan = self._plan(cursor, buffer_lo, table, words, glyph_blob,
                                  row_map, string_obj.address, size, base_low,
                                  columns)
                plan["row_map"] = row_map
                plan["score"] = self._score(plan)
                attempts.append(plan)
        attempts.sort(key=lambda plan: -plan["score"]["matched_bytes"])
        best = attempts[0] if attempts else None
        verdict = self._verdict(best)
        score = (best or {}).get("score") or {}
        # Совпало байт в байт — это уже предсказание, подтверждённое реальностью
        # (ТЗ §23), то есть факт. Частичное совпадение остаётся кандидатом.
        matched = (verdict.startswith("matched") and score.get("compared_bytes")
                   and score["matched_bytes"] == score["compared_bytes"])
        return {
            "string": {"address": addr_hex(string_obj.address),
                       "name": string_obj.name, "size": size,
                       "declared_comment": (declared.get("comment") or "")[:120]},
            "buffer": [addr_hex(buffer_lo), addr_hex(buffer_hi)],
            "needle": needle.hex().upper(),
            "cursors_found": [addr_hex(c) for c in cursors],
            "screen": {"vram_base": self.screen.get("vram_base"),
                       "columns": columns,
                       "base_low": {"address": addr_hex(base_low_addr),
                                    "value": addr_hex(base_low)},
                       "visible": [self.screen.get("visible_width"),
                                   self.screen.get("visible_height")]},
            "tables": {"column_table": [table_name, len(table or [])],
                       "glyph_table": words_name},
            "planes": {addr_hex(base): name for name, base in planes.items()},
            "attempts": [self._compact(plan) for plan in attempts[:8]],
            "best": self._compact(best, detail=True) if best else None,
            "verdict": verdict,
            "status": "MATCHED" if matched else "CANDIDATE",
        }

    def _plane_bases(self):
        """Имя → базовый адрес плоскости из debug_get_vram_info."""
        planes = self.plane_info.get("planes") or []
        out = {}
        for item in planes:
            index = item.get("plane", item.get("index"))
            base = to_addr(item.get("base") or item.get("address")
                           or item.get("base_address"))
            out["plane%s" % index] = base
        if not out:                                  # запасной вариант по docs
            for index, base in enumerate((0xE000, 0xC000, 0xA000, 0x8000)):
                out["plane%d" % index] = base
        return out

    def _plan(self, cursor, buffer_lo, table, words, glyph_blob, row_map,
              string_address, size, base_low, columns):
        """Один кандидат: (row, col) по каждому символу → адреса VRAM → сверка."""
        plane_names = self._plane_bases()
        if not table:
            return {"cursor": addr_hex(cursor), "row": None, "column": None,
                    "steps": [], "error": "нет таблицы баз столбцов"}
        steps = []
        for offset in range(min(size, 40)):
            code = self.image.read(string_address + offset,
                                   string_address + offset)[0]
            # каждый символ рендерится своим курсором: адрес в буфере +1
            parts = ROW_MAPS[row_map](cursor + offset, offset, columns)
            column, row_part, sign = (parts["column"], parts["row_part"],
                                      parts["sign"])
            base_address = predict_address(table, column, row_part, base_low, sign)
            if base_address is None:
                continue
            glyph_ptr = words[code] if words else None
            expected_planes = glyph_for_char(glyph_blob, GLYPH_LO, glyph_ptr)
            record = {"char_index": offset, "code": addr_hex(code),
                      "column": column, "row_part": addr_hex(row_part),
                      "planes": []}
            for plane_index in range(len(plane_names) or 4):
                name = "plane%d" % plane_index
                address = (base_address + plane_index * PLANE_STEP) & 0xFFFF
                actual = self.vram_bytes(address)
                if not actual:
                    continue
                expected = (expected_planes[plane_index]
                            if plane_index < len(expected_planes) else b"")
                matched = sum(1 for a, b in zip(actual, expected) if a == b)
                record["planes"].append({
                    "plane": name, "window": self._plane_of(address, plane_names),
                    "address": addr_hex(address), "matched": matched,
                    "of": len(actual), "actual": actual.hex().upper(),
                    "expected": expected.hex().upper()})
            steps.append(record)
        row, col = divmod(cursor - buffer_lo, columns)
        return {"cursor": addr_hex(cursor), "row": row, "column": col,
                "steps": steps}

    @staticmethod
    def _plane_of(address, plane_names):
        """В каком из объявленных отладчиком окон лежит адрес (0xE000 …)."""
        for name, base in plane_names.items():
            if base is not None and base <= address < base + PLANE_STEP:
                return name
        return None

    def _score(self, plan):
        matched = total = 0
        full_glyphs = 0
        for step in plan["steps"]:
            planes = step.get("planes") or []
            complete = bool(planes)
            for value in planes:
                matched += value["matched"]
                total += value["of"]
                complete = complete and value["matched"] == value["of"]
            full_glyphs += 1 if complete else 0
        return {"matched_bytes": matched, "compared_bytes": total,
                "glyphs_fully_matching": full_glyphs,
                "glyphs": len(plan["steps"])}

    def _compact(self, plan, detail=False):
        """Аттемт в сжатом виде; hex-дампы плоскостей — только у лучшего."""
        steps = plan["steps"]
        out = {"row_map": plan.get("row_map"), "cursor": plan["cursor"],
               "row": plan["row"], "column": plan["column"],
               "score": plan["score"], "per_plane": self._plane_profile(plan),
               "chars": [{"i": step["char_index"], "code": step["code"],
                          "col": step["column"],
                          "vram": (step["planes"] or [{}])[0].get("address"),
                          "matched": [p["matched"] for p in step["planes"]]}
                         for step in steps[:12]]}
        if detail:
            out["steps"] = [dict(
                [item for item in step.items() if item[0] != "planes"],
                planes=[{key: plane[key] for key in
                         ("plane", "window", "address", "matched", "of",
                          "actual", "expected")} for plane in step["planes"]])
                for step in steps[:12]]
        return out

    @staticmethod
    def _plane_profile(plan):
        """Совпадения по номерам плоскостей: видно перепутан ли порядок."""
        profile = {}
        for step in plan["steps"]:
            for plane in step["planes"]:
                cell = profile.setdefault(plane["plane"], {"matched": 0, "of": 0,
                                                           "window": plane["window"]})
                cell["matched"] += plane["matched"]
                cell["of"] += plane["of"]
        return profile

    def _verdict(self, best):
        if not best:
            return "no_prediction: строка не найдена в текстовом буфере RAM"
        score = best["score"]
        if not score["compared_bytes"]:
            return "no_data: ни один предсказанный адрес не лёг в VRAM"
        text = "%s: %d/%d байт совпало, глифов целиком %d/%d"
        if score["matched_bytes"] == score["compared_bytes"]:
            return text % ("matched", score["matched_bytes"], score["compared_bytes"],
                           score["glyphs_fully_matching"], score["glyphs"])
        if score["matched_bytes"]:
            return text % ("partial", score["matched_bytes"], score["compared_bytes"],
                           score["glyphs_fully_matching"], score["glyphs"])
        return "unmatched: предсказание не подтвердилось — формула или вход неверны"


def format_report(result):
    """Человеческий вывод: таблица кандидатов + разбор лучших 12 символов."""
    lines = []
    string = result["string"]
    lines.append("строка    %s  %s  size=%s" % (string["address"], string["name"],
                                                string["size"]))
    lines.append("игла      %s" % result["needle"])
    lines.append("курсоры   %s" % (", ".join(result["cursors_found"]) or "— нет в буфере"))
    screen = result["screen"]
    table_name, table_len = result["tables"]["column_table"]
    lines.append("база      vram_base=%s columns=%s base_low=%s/%s"
                 % (screen.get("vram_base"), screen.get("columns"),
                    screen["base_low"]["value"], screen["base_low"]["address"]))
    lines.append("таблицы   col=%s(%s) glyph_ptr=%s"
                 % (table_name, table_len, result["tables"]["glyph_table"]))
    lines.append("плоскости " + ", ".join("%s@%s" % (name, base) for base, name
                                          in sorted(result["planes"].items())))
    lines.append("")
    lines.append("%-10s %-8s %-4s %-4s %-12s %-9s %s"
                 % ("row_map", "cursor", "row", "col", "matched/total",
                    "glyphs", "по плоскостям"))
    for attempt in result["attempts"]:
        score = attempt["score"]
        per_plane = "/".join("%s:%d" % (name, cell["matched"])
                             for name, cell in sorted(attempt["per_plane"].items()))
        lines.append("%-10s %-8s %-4s %-4s %-12s %d/%-8s %s"
                     % (attempt["row_map"], attempt["cursor"], attempt["row"],
                        attempt["column"],
                        "%d/%d" % (score["matched_bytes"], score["compared_bytes"]),
                        score["glyphs_fully_matching"], score["glyphs"], per_plane))
    best = result.get("best")
    if best and best.get("steps"):
        lines.append("")
        lines.append("разбор лучшего кандидата (%s):" % best["row_map"])
        head = " ".join("%-18s" % plane["plane"] for plane in best["steps"][0]["planes"])
        lines.append("%-4s %-6s %-6s %s" % ("i", "code", "vram", head))
        for step in best["steps"]:
            cells = " ".join("%-9s %-8s %d/%d" % (plane["actual"][:8],
                                                 plane["expected"][:8],
                                                 plane["matched"], plane["of"])
                             for plane in step["planes"])
            lines.append("%-4s %-6s %-6s %s" % (step["char_index"], step["code"],
                                               (step["planes"] or [{}])[0].get("address"),
                                               cells))
    lines.append("")
    lines.append("ВЕРДИКТ   %s  [%s]  mcp_calls=%s"
                 % (result["verdict"], result["status"], result.get("mcp_calls")))
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="analyze.vram_credits",
        description="Предсказание адресов строки в VRAM и сверка с рантаймом")
    parser.add_argument("--rom", required=True)
    parser.add_argument("--org", type=lambda s: int(s, 0), default=0x0100)
    parser.add_argument("--rdb", default=None)
    parser.add_argument("--string", required=True, help="адрес строкового объекта")
    parser.add_argument("--buffer", nargs=2, default=["0x5000", "0x5400"])
    parser.add_argument("--columns", type=int, default=32)
    parser.add_argument("--base-low", default="0x08D0",
                        help="адрес RAM, откуда берётся младший байт базы экрана")
    parser.add_argument("--run", type=float, default=3.0,
                        help="секунд прогона: без него буфер и глифы пусты")
    parser.add_argument("--key", action="append", default=[],
                        help="клавиши для вывода нужного экрана, '0.5:SPACE'")
    parser.add_argument("--cache", default=None)
    parser.add_argument("--server", default=None)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    from analyze.probe import parse_key_specs, run_for

    session, cache = open_session(rom=args.rom, org=args.org, server=args.server,
                                  cache_dir=args.cache)
    try:
        run_for(session, cache, rom=args.rom, org=args.org, seconds=args.run,
                keys=parse_key_specs(args.key))
        rdb = Rdb.load(args.rdb) if args.rdb else Rdb.from_session(session)
        # `--string` принимает и адрес, и имя объекта: адрес удобнее, имя не
        # разъезжается при правке RDB.
        try:
            address = to_addr(args.string)
        except ValueError:
            named = rdb.by_name(args.string)
            obj = named[0] if isinstance(named, list) and named else named
            if obj is None:
                print("в RDB нет объекта с именем %s, а адрес из строки не "
                      "читается" % args.string, file=sys.stderr)
                return 2
            address = obj.address
        else:
            obj = rdb.at(address) or rdb.by_addr(address)
        if obj is None:
            print("в RDB нет объекта по адресу %s" % addr_hex(address),
                  file=sys.stderr)
            return 2
        verifier = VramCreditsVerifier(session, cache,
                                       ImageSource(args.rom, args.org), rdb)
        result = verifier.predict(obj, buffer_lo=to_addr(args.buffer[0]),
                                  buffer_hi=to_addr(args.buffer[1]),
                                  columns=args.columns,
                                  base_low_addr=to_addr(args.base_low))
        result["rom"] = os.path.basename(args.rom)
        result.update(session_fields(session))
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
        else:
            print(format_report(result))
    finally:
        session.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
