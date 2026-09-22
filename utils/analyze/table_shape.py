"""Форма таблицы: только детерминированные признаки (ТЗ §22).

Никаких «это таблица периодов нот» — модуль считает арифметику и выдаёт
признаки, из которых AI (или человек) делает вывод:

    периодичность     equality_ratio(p) = доля i, где data[i] == data[i+p]
    монотонность      доля шагов вверх/вниз для 8/16-битных окон
    диапазон          min/max/количество различных/частоты верхних значений
    плотность указателей   доля 16-битных слов, попадающих в ROM/RAM-окно
    base+index*K      МНК по 16-битным словам: наклон K, база, невязка
    блоками             совпадает ли блок с шагом p с предыдущим

Каждый выход помечен `status: CANDIDATE`.

Ограничение, которое нужно держать в голове: окно ПЗУ у 16-КиБ ROM — это
0x0100..0x41FF, то есть в него случайно попадает ~25 % произвольных
16-битных значений. Поэтому для коротких таблиц (`small_sample`) вывод
всегда слабый, а `address_like_share` сам по себе не доказательство.

Источник байтов указывается явно (IMAGE или RUNTIME, ТЗ §16) — таблица в
ПЗУ и таблица, скопированная в RAM, это разные наблюдения.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

from analyze import naming
from analyze.mcp_session import addr_hex, envelope, open_session, to_addr
from analyze.memory_diff import ImageSource, RuntimeSource
from analyze.rdb import Rdb

MAX_PERIOD = 64
PERIOD_MATCH = 0.9


def equality_ratio(data, period):
    """Доля совпадений байта с байтом через `period`. 0.0 — нет данных."""
    if period <= 0 or period >= len(data):
        return 0.0
    total = len(data) - period
    hits = sum(1 for index in range(total) if data[index] == data[index + period])
    return round(hits / total, 4)


def period_profile(data, max_period=MAX_PERIOD):
    """Профиль периодичности: [(period, equality_ratio)], по убыванию доли."""
    limit = min(max_period, max(1, len(data) // 2))
    profile = [(period, equality_ratio(data, period))
               for period in range(1, limit + 1)]
    return sorted(profile, key=lambda item: (-item[1], item[0]))


def candidate_periods(profile, threshold=PERIOD_MATCH, want=3):
    return [period for period, ratio in profile if ratio >= threshold][:want]


def monotonicity(data, width=16, endian="little"):
    """Доля шагов вверх/вниз и самые длинные монотонные отрезки."""
    values = words(data, width, endian)
    if len(values) < 2:
        return None
    steps = len(values) - 1
    up = sum(1 for a, b in zip(values, values[1:]) if b > a)
    down = sum(1 for a, b in zip(values, values[1:]) if b < a)
    same = steps - up - down
    best_up = best_down = run_up = run_down = 1
    for a, b in zip(values, values[1:]):
        if b > a:
            run_up += 1
            best_up = max(best_up, run_up)
        else:
            run_up = 1
        if b < a:
            run_down += 1
            best_down = max(best_down, run_down)
        else:
            run_down = 1
    return {
        "width": width, "endian": endian, "count": len(values),
        "up_share": round(up / steps, 4), "down_share": round(down / steps, 4),
        "equal_share": round(same / steps, 4),
        "longest_increasing_run": best_up,
        "longest_decreasing_run": best_down,
        "first": values[0], "last": values[-1],
        "min": min(values), "max": max(values),
    }


def words(data, width=16, endian="little", start=0, stride=None):
    """8/16-битные значения. Шаг по умолчанию = размер значения, то есть
    ОКНА НЕ ПЕРЕКРЫВАЮТСЯ (иначе таблица слов превращается в кашу)."""
    step = width // 8
    stride = step if stride is None else int(stride)
    if stride <= 0:
        raise ValueError("stride must be positive")
    out = []
    index = start
    while index + step <= len(data):
        chunk = data[index:index + step]
        out.append(chunk[0] if width == 8 else int.from_bytes(chunk, endian))
        index += stride
    return out


def value_stats(data):
    distinct = sorted(set(data))
    histogram = sorted(((byte, data.count(byte)) for byte in distinct),
                       key=lambda item: -item[1])
    return {
        "min": min(data) if data else None,
        "max": max(data) if data else None,
        "distinct": len(distinct),
        "zeros": data.count(0),
        "ffs": data.count(0xFF),
        "top_values": [{"byte": addr_hex(byte), "count": count}
                       for byte, count in histogram[:8]],
        "high_bit_share": round(sum(1 for b in data if b & 0x80) / len(data), 4)
        if data else None,
    }


def pointer_density(data, rom_lo, rom_hi, ram_lo=0x4000, ram_hi=0x7FFF,
                    stride=2):
    """Доля 16-битных LE-слов, которые выглядят как адрес в осмысленном окне.

    Считать «адресом» любое число ≤ 0xFFFF нельзя — это всё пространство
    8080. Поэтому окна перечислены явно: ПЗУ-образ, ОЗУ, VRAM. Отдельно
    возвращается доля слов, указывающих внутрь кода (rom_share).
    """
    values = words(data, 16, "little", stride=stride)
    if not values:
        return None
    def share_in(lo, hi):
        return round(sum(1 for v in values if lo <= v <= hi) / len(values), 4)
    rom, ram, vram = (share_in(rom_lo, rom_hi), share_in(ram_lo, ram_hi),
                      share_in(0x8000, 0xFFFF))
    return {
        "stride": stride, "count": len(values),
        "rom_share": rom,
        "ram_share": ram,
        "vram_share": vram,
        "address_like_share": round(min(1.0, rom + ram + vram), 4),
        "zero_share": round(sum(1 for v in values if v == 0) / len(values), 4),
        "distinct": len(set(values)),
    }


def linear_fit(data, width=16, endian="little", stride=None):
    """Проверка формы base + index*K по словам (МНК + точные целые шаги)."""
    values = words(data, width, endian, stride=stride)
    n = len(values)
    if n < 3:
        return None
    mean_x = (n - 1) / 2.0
    mean_y = sum(values) / float(n)
    sxx = sum((index - mean_x) ** 2 for index in range(n))
    sxy = sum((index - mean_x) * (values[index] - mean_y) for index in range(n))
    if sxx == 0:
        return None
    slope = sxy / sxx
    intercept = mean_y - slope * mean_x
    residual = max(abs(values[index] - (intercept + slope * index))
                   for index in range(n))
    exact = [k for k in range(0, 0x200)
             if all(values[index] == values[0] + k * index
                    for index in range(min(n, 32)))]
    return {
        "count": n, "slope": round(slope, 4), "intercept": round(intercept, 2),
        "max_residual": round(residual, 4),
        "exact_integer_strides": exact[:6],
        "base_from_first": values[0],
    }


def block_repetition(data, periods):
    """Совпадает ли содержимое блоков фиксированного шага (для графики)."""
    out = []
    for period in periods:
        if period * 2 > len(data):
            continue
        blocks = [data[index:index + period]
                  for index in range(0, len(data) - period + 1, period)]
        if len(blocks) < 2:
            continue
        identical = sum(1 for block in blocks[1:] if block == blocks[0])
        out.append({
            "period": period, "blocks": len(blocks),
            "same_as_first": identical,
            "share": round(identical / (len(blocks) - 1), 4),
        })
    return out


def traits_for(data, rom_lo, rom_hi):
    """Полный набор детерминированных признаков куска байтов."""
    profile = period_profile(data)
    periods = candidate_periods(profile)
    result = {
        "length": len(data),
        "values": value_stats(data),
        "periodicity": {
            "best": [{"period": p, "equality_ratio": r}
                     for p, r in profile[:5]],
            "candidates": periods,
        },
        "monotonic": [m for m in (monotonicity(data, 16, "little"),
                                 monotonicity(data, 16, "big"),
                                 monotonicity(data, 8)) if m],
        "pointers": pointer_density(data, rom_lo, rom_hi),
        "linear_fit": linear_fit(data),
        "blocks": block_repetition(data, periods or [1, 2, 4, 8]),
    }
    result["candidate_kind"] = classify_shape(result)
    return result


def classify_shape(traits):
    """Форма → имя кандидата. Правила открытые, вывод — кандидат, не факт."""
    pointers = traits.get("pointers") or {}
    fit = traits.get("linear_fit") or {}
    periods = traits.get("periodicity", {}).get("candidates") or []
    mono = _strongest_monotonic(traits.get("monotonic") or [])
    trend = max(mono.get("up_share", 0), mono.get("down_share", 0)) if mono else 0
    address_like = pointers.get("address_like_share", 0)
    exact = fit.get("exact_integer_strides") or []
    if address_like >= 0.7 and pointers.get("distinct", 0) >= 4 \
            and pointers.get("count", 0) >= 4:
        kind = "pointer_table"
    elif exact and trend >= 0.9:
        kind = "arithmetic_word_table"
    elif trend >= 0.9:
        kind = "sorted_word_table"
    elif any(block["share"] >= 0.8 for block in traits.get("blocks") or []):
        kind = "repeating_blocks"
    elif periods:
        kind = "periodic_records"
    elif (traits["values"].get("high_bit_share") or 0) > 0.5:
        kind = "bitmap_like"
    else:
        kind = "opaque"
    return {"kind": kind,
            "evidence": {"address_like_share": address_like,
                        "rom_share": pointers.get("rom_share"),
                        "ram_share": pointers.get("ram_share"),
                        "vram_share": pointers.get("vram_share"),
                        "exact_strides": exact[:3],
                        "trend": mono and _trend_of(mono),
                        "periods": periods[:3]},
            "small_sample": pointers.get("count", 0) < 8 or
            traits["length"] < 16,
            "status": "CANDIDATE"}


def _strongest_monotonic(records):
    """Самый выраженный монотонный ряд среди 8/16LE/16BE."""
    best = None
    for record in records:
        score = max(record.get("up_share", 0), record.get("down_share", 0))
        if best is None or score > best[0]:
            best = (score, record)
    return best[1] if best else None


def _trend_of(mono):
    if mono["up_share"] >= mono["down_share"]:
        return "increasing"
    return "decreasing"


def analyse_span(source, lo, hi, rom_lo, rom_hi):
    data = source.read(lo, hi)
    return {
        "address": addr_hex(to_addr(lo)),
        "end": addr_hex(to_addr(hi)),
        "memory_source": source.kind,
        "traits": traits_for(data, rom_lo, rom_hi),
    }


def rdb_spans(rdb, types=("data", "table")):
    out = []
    for obj in rdb.of_type(*types):
        if not obj.size_known:
            continue
        out.append({"name": obj.name, "type": obj.type,
                    "lo": obj.address, "hi": obj.end,
                    "declared_size": obj.size})
    return sorted(out, key=lambda item: item["lo"])


def format_table(results):
    lines = ["%-8s %-6s %-6s %-20s %-8s %s"
             % ("адрес", "разм", "источ", "кандидат", "период", "признак")]
    for item in results:
        traits = item["traits"]
        kind = traits["candidate_kind"]
        name = kind["kind"] + ("?" if kind.get("small_sample") else "")
        lines.append("%-8s %-6s %-6s %-20s %-8s %s" % (
            item["address"], traits["length"], item["memory_source"][:3],
            name,
            ",".join(str(p) for p in traits["periodicity"]["candidates"]) or "—",
            json.dumps(kind["evidence"], ensure_ascii=False)[:70]))
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(prog="analyze.table_shape",
                                     description="Детерминированные признаки формы данных")
    parser.add_argument("--rom", required=True)
    parser.add_argument("--org", type=lambda s: int(s, 0), default=0x0100)
    parser.add_argument("--rdb", default=None)
    parser.add_argument("--address", default=None, help="разобрать один диапазон")
    parser.add_argument("--size", type=lambda s: int(s, 0), default=None)
    parser.add_argument("--types", default="data,table",
                        help="какие RDB-объекты сканировать (через запятую)")
    parser.add_argument("--runtime", action="store_true",
                        help="читать RUNTIME-память вместо ПЗУ-образа")
    parser.add_argument("--limit", type=int, default=60)
    parser.add_argument("--cache", default=None)
    parser.add_argument("--server", default=None)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    size = os.path.getsize(args.rom)
    rom_lo, rom_hi = args.org, args.org + size - 1
    session, cache = open_session(rom=args.rom, org=args.org, server=args.server,
                                  cache_dir=args.cache)
    try:
        source = RuntimeSource(session, cache) if args.runtime \
            else ImageSource(args.rom, args.org)
        rdb = Rdb.load(args.rdb) if args.rdb else Rdb.from_session(session)
        if args.address is not None:
            lo = to_addr(args.address)
            span_hi = lo + (args.size or 0x20) - 1
            spans = [{"name": None, "lo": lo, "hi": span_hi}]
        else:
            spans = rdb_spans(rdb, tuple(t.strip() for t in args.types.split(",")))
        results = []
        for span in spans[:args.limit]:
            item = analyse_span(source, span["lo"], span["hi"], rom_lo, rom_hi)
            item["rdb_object"] = span.get("name")
            item["rdb_type"] = span.get("type")
            results.append(item)
        payload = {"rom": os.path.basename(args.rom),
                   "image": [addr_hex(rom_lo), addr_hex(rom_hi)],
                   "spans": len(results), "results": results}
        kinds = {}
        candidates = []
        for item in results:
            shape = item["traits"].get("candidate_kind") or {}
            kind = shape.get("kind") or "opaque"
            kinds[kind] = kinds.get(kind, 0) + 1
            if kind == "opaque" or len(candidates) >= 10:
                continue
            candidates.append({
                "name": item.get("rdb_object")
                        or naming.propose("table", addr=to_addr(item["address"])),
                "confidence": "low" if shape.get("small_sample") else "medium",
                "object": "%s (%s)" % (item["address"],
                                       item.get("rdb_object") or "—"),
                "detail": "очертание: %s, %s"
                          % (kind, json.dumps(shape.get("evidence"),
                                              ensure_ascii=False)[:120]),
            })
        payload = envelope(
            payload, module="table_shape", session=session, cache=cache,
            status="CANDIDATE", candidates=candidates,
            verdict="разобрано диапазонов: %d, видов: %s"
                    % (len(results),
                       ", ".join("%s=%d" % pair for pair in sorted(kinds.items()))
                       or "нет"),
            note="детерминированные признаки формы (шаг, монотонность, "
                 "период, доли адресов); что это за таблица — решает не он")
        if args.json:
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            print(format_table(results))
        print("# mcp calls: %d" % session.stats()["total_calls"], file=sys.stderr)
    finally:
        session.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
