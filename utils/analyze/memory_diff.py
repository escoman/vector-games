"""Надёжное сравнение памяти и детектор рантайм-патчей (ТЗ §13, §16, §17).

Три источника байт, которые нельзя путать:

    IMAGE    — файл ROM на диске (то, что попало в ПЗУ)
    RUNTIME  — живой address space эмулятора (после загрузки/работы CPU)
    SNAPSHOT — снимок, который хранит отладчик (debug_create_memory_snapshot)

`reliable_memory_diff()` — единственная функция сравнения, которой можно
верить: она читает оба диапазона целиком и сравнивает побайтно локально.
`debug_diff_memory`/`debug_compare_memory_snapshots` допустимы только как
предварительный результат: если их ответ расходится с полным локальным diff,
авторитетом считается локальный (ответ MCP — нижняя оценка).

Детектор патчей (`find_runtime_patches`) ищет участки, где образ ≠ рантайм:
именно так нашли самопатч `0x03F8: 00 00 00 → CD 58 38` (CALL func_music_tick)
в putup. Найденное НЕ подменяет байты образа при экспорте ASM — патч есть
только в RAM (ТЗ §17).
"""
from __future__ import annotations

import argparse
import json
import os
import sys

from analyze.capabilities import CapabilityProfile
from analyze.mcp_session import (addr_hex, bytes_of, envelope, open_session,
                                to_addr)

CHUNK = 0x2000  # 8 КБ на обращение — заглядывает весь ROM-диапазон за 4 вызова


class MemorySource:
    """Байты из одного места. Дочерние классы обязывают вызывающего назвать
    источник (ТЗ §16) — случайное сравнение «файла с RAM» невозможно."""

    kind = "UNKNOWN"

    def read(self, lo, hi):
        raise NotImplementedError

    def __repr__(self):
        return "<%s>" % self.kind


class ImageSource(MemorySource):
    """ROM-образ с диска: адрес → смещение = address − org."""

    kind = "IMAGE"

    def __init__(self, path, org=0x0100, hi=None):
        self.path = os.path.abspath(path)
        self.org = to_addr(org)
        with open(self.path, "rb") as fh:
            self.data = fh.read()
        # Верхнюю границу можно сузить (например, когда образ отражен в ROM
        # только частью диапазона), шире размера файла она не бывает.
        self.hi = min(to_addr(hi), self.org + self.size - 1) if hi is not None \
            else self.org + self.size - 1

    @property
    def size(self):
        return len(self.data)

    def contains(self, address):
        return self.org <= to_addr(address) <= self.hi

    def read(self, lo, hi):
        lo, hi = max(to_addr(lo), self.org), min(to_addr(hi), self.hi)
        if hi < lo:
            return b""
        return self.data[lo - self.org: hi - self.org + 1]

    def offset_of(self, address):
        return to_addr(address) - self.org


class RuntimeSource(MemorySource):
    """Живая память эмулятора через debug_read_memory_range (кэшируется)."""

    kind = "RUNTIME"

    def __init__(self, session, cache=None):
        self.session = session
        self.cache = cache

    def read(self, lo, hi):
        lo, hi = to_addr(lo), to_addr(hi)
        out = bytearray()
        cursor = lo
        while cursor <= hi:
            end = min(cursor + CHUNK - 1, hi)
            args = {"address": cursor, "length": end - cursor + 1}
            if self.cache is not None:
                payload, _ = self.cache.get_or_call(
                    self.session, "debug_read_memory_range", args,
                    stamp="auto", source="RUNTIME")
            else:
                payload = self.session.call("debug_read_memory_range", args)
            out.extend(bytes_of(payload))
            cursor = end + 1
        return bytes(out)


class SnapshotSource(MemorySource):
    """Снимок из отладчика: id даёт debug_create_memory_snapshot."""

    kind = "SNAPSHOT"

    def __init__(self, session, cache=None, snapshot_id=None, address=0x0000):
        self.session = session
        self.cache = cache
        self.snapshot_id = snapshot_id
        self.address = to_addr(address)

    @classmethod
    def capture(cls, session, name="snap", address=0x0000, size=0x8000):
        payload = session.call("debug_create_memory_snapshot",
                               {"address": to_addr(address), "size": int(size)})
        src = cls(session, snapshot_id=payload.get("snapshot_id"), address=address)
        src.name = name
        return src

    def read(self, lo, hi):
        # Сервер умеет отдавать снимок только через diff/compare; побайтово —
        # читаем живой диапазон и сверяем снимок отдельно (см. diff_snapshots).
        raise NotImplementedError(
            "байты снимка отдаются только через debug_diff_memory/compare; "
            "для локального сравнения используйте ImageSource/RuntimeSource")


def reliable_memory_diff(source_a, source_b, lo, hi, mcp_hint=None):
    """Побайтовое сравнение двух источников.

    Возвращает dict:
        identical, bytes_differing, ranges[{start,end,old,new}], authoritative
    `mcp_hint` — результат MCP-инструмента, если он использовался как
    предварительная оценка; к результату добавляется поле `mcp_agrees`.
    """
    lo, hi = to_addr(lo), to_addr(hi)
    a = source_a.read(lo, hi)
    b = source_b.read(lo, hi)
    length = min(len(a), len(b))
    ranges = []
    differing = 0
    run = None
    for index in range(length):
        if a[index] != b[index]:
            differing += 1
            if run is None:
                run = [lo + index, lo + index, [a[index]], [b[index]]]
            else:
                run[1] = lo + index
                run[2].append(a[index])
                run[3].append(b[index])
        elif run is not None:
            ranges.append(_range_dict(run))
            run = None
    if run is not None:
        ranges.append(_range_dict(run))
    result = {
        "source_a": source_a.kind,
        "source_b": source_b.kind,
        "range": [addr_hex(lo), addr_hex(hi)],
        "compared_bytes": length,
        "truncated": len(a) != len(b),
        "bytes_differing": differing,
        "identical": differing == 0 and len(a) == len(b),
        "ranges": ranges,
        "authoritative": "local byte-for-byte compare",
    }
    if mcp_hint is not None:
        hint_bytes = _hint_bytes(mcp_hint)
        result["mcp_hint"] = {
            "tool": mcp_hint.get("_tool"),
            "bytes_differing": hint_bytes,
            "ranges": len(mcp_hint.get("ranges") or mcp_hint.get("differences") or []),
        }
        result["mcp_agrees"] = hint_bytes == differing
        if hint_bytes is not None and hint_bytes < differing:
            result["note"] = ("MCP-сравнение недооценило разницу: локальный "
                              "полный diff авторитетен (ТЗ §13)")
    return result


def _range_dict(run):
    return {
        "start": addr_hex(run[0]),
        "end": addr_hex(run[1]),
        "length": run[1] - run[0] + 1,
        "old": " ".join("%02X" % b for b in run[2][:32]),
        "new": " ".join("%02X" % b for b in run[3][:32]),
        "old_bytes": run[2],
        "new_bytes": run[3],
    }


def _hint_bytes(hint):
    if not isinstance(hint, dict):
        return None
    for key in ("bytes_differing", "differing_bytes", "total_differences",
                "difference_count"):
        if key in hint:
            return int(hint[key])
    ranges = hint.get("ranges") or hint.get("differences") or []
    if ranges:
        return sum(int(r.get("length") or (to_addr(r.get("end")) - to_addr(r.get("start")) + 1))
                   for r in ranges)
    return None


def mcp_snapshot_diff(session, cache, snapshot_a, snapshot_b, address=None,
                      length=None):
    """Предварительная оценка через MCP (только как ускорение, ТЗ §13)."""
    args = {"snapshot_a": int(snapshot_a), "snapshot_b": int(snapshot_b)}
    if address is not None:
        args["address"] = to_addr(address)
    if length is not None:
        args["length"] = int(length)
    if CapabilityProfile.from_session(session).has("debug_diff_memory"):
        payload = session.call("debug_diff_memory", args)
        payload["_tool"] = "debug_diff_memory"
        return payload
    payload = session.call("debug_compare_memory_snapshots", args)
    payload["_tool"] = "debug_compare_memory_snapshots"
    return payload


def find_runtime_patches(session, cache, rom_path, org=0x0100, lo=None, hi=None,
                         limit=200):
    """IMAGE vs RUNTIME: список мест, где ROM был изменён на лету (ТЗ §17)."""
    image = ImageSource(rom_path, org)
    runtime = RuntimeSource(session, cache)
    lo = to_addr(lo) if lo is not None else image.org
    hi = to_addr(hi) if hi is not None else image.hi
    diff = reliable_memory_diff(image, runtime, lo, hi)
    patches = []
    for item in diff["ranges"][:limit]:
        patches.append({
            "address": item["start"],
            "length": item["length"],
            "image": item["old"],
            "runtime": item["new"],
            "evidence": "image=%s runtime=%s" % (os.path.basename(rom_path),
                                                 "debug_read_memory_range"),
        })
    return {
        "image": {"path": rom_path, "org": addr_hex(image.org), "size": image.size},
        "compared": [addr_hex(lo), addr_hex(hi)],
        "bytes_differing": diff["bytes_differing"],
        "patch_count": len(diff["ranges"]),
        "patches": patches,
        "authoritative": diff["authoritative"],
        "warning": ("рантайм-патчи не переносить в экспорт ASM (ТЗ §17)"
                    if patches else None),
    }


def main(argv=None):
    parser = argparse.ArgumentParser(prog="analyze.memory_diff",
                                     description="IMAGE vs RUNTIME и надёжный diff")
    parser.add_argument("--rom", required=True)
    parser.add_argument("--org", type=lambda s: int(s, 0), default=0x0100)
    parser.add_argument("--run-seconds", type=float, default=0.0,
                        help="сколько секунд крутить ROM перед сравнением")
    parser.add_argument("--lo", type=lambda s: int(s, 0), default=None)
    parser.add_argument("--hi", type=lambda s: int(s, 0), default=None)
    parser.add_argument("--cache", default=None)
    parser.add_argument("--server", default=None)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    session, cache = open_session(rom=args.rom, org=args.org, server=args.server,
                                  cache_dir=args.cache)
    try:
        if args.run_seconds:
            session.call("debug_run")
            import time

            time.sleep(args.run_seconds)
            session.call("debug_pause")
        out = find_runtime_patches(session, cache, args.rom, org=args.org,
                                   lo=args.lo, hi=args.hi)
        patches = out.get("patch_count") or 0
        out = envelope(
            out, module="memory_diff", session=session, cache=cache,
            status="OK",
            verdict=("рантайм-патчей нет: образ и RAM совпали на %s" % out["compared"]
                     if not patches else
                     "%.0f байт(а) RAM отличается от образа — %d патч(а)"
                     % (out["bytes_differing"], patches)),
            note="сравнение побайтовое, надёжнее MCP-diff (ТЗ §13); патчи — "
                 "наблюдение рантайма, в экспорт ASM они не переносятся (ТЗ §17)")
        print(json.dumps(out, ensure_ascii=False,
                         indent=2 if args.json else None))
    finally:
        session.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
