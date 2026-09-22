"""Универсальный ROM → Standard MIDI File конвертер (ТЗ §21, §8, §17).

Никаких знаний о конкретной ROM здесь нет: формат дорожек, адрес, длина,
шаг, темп, смещение ноты и номера каналов приходят из ROM-специфичного
`music_spec.json` (лежит рядом с ROM, например
`roms/redesign/putup/tools/music_spec.json`).

Что делает Python: читает байты, вычитает константу из спецификации, складывает
события SMF в правильном порядке. Чего не делает: не угадывает, где лежит
музыка, не решает, что такое «рест», и не назначает темп — всё это Fact'ы из
спеки, которую собрал анализатор. Если спецификация подозрительна, здесь она
и проверяется: `expect`-дампы сверяются побайтово, а неизвестный код —
остановка, а не молчаливая нота.

Источники байтов: IMAGE (файл ROM по org) или RUNTIME (живая RAM через MCP) —
для ROM с самомодифицирующимся загрузчиком это разные числа, и ТЗ §17 требует
не подменять одно другим.

    PYTHONPATH=utils python3 utils/analyze/cli.py music2midi \
        --spec roms/redesign/putup/tools/music_spec.json -o out.mid
"""
from __future__ import annotations

import argparse
import json
import os
import struct
import sys

from analyze.mcp_session import addr_hex, bytes_of, open_session, to_addr

SUPPORTED_ENCODINGS = ("note_code",)
# Коды, которые спецификация обязана объяснить явно: старший бит в 8080-ных
# нотно-табличных форматах обычно означает разветвление, а не высоту тона.
DEFAULT_CODE_MASK = 0x7F


def num(value, default=None):
    """Число из спецификации: 192, "0x7F", "0100h", "96" — всё годится."""
    if value is None:
        if default is None:
            raise SystemExit("в спецификации не хватает числа")
        return int(default)
    if isinstance(value, bool):
        raise SystemExit("булево там, где ожидалось число: %r" % (value,))
    if isinstance(value, int):
        return value
    text = str(value).strip()
    try:
        if text.lower().endswith("h"):
            return int(text[:-1], 16)
        return int(text, 0)
    except ValueError:
        raise SystemExit("не число в спецификации: %r" % (value,)) from None


# ---------------------------------------------------------------------------
# SMF-письмо (format 0/1), ровно то, что описано в MIDI 1.0 Specification
# ---------------------------------------------------------------------------

def vlq(value):
    """Variable-length quantity."""
    out = [value & 0x7F]
    value >>= 7
    while value:
        out.append((value & 0x7F) | 0x80)
        value >>= 7
    return bytes(reversed(out))


def chunk(kind, body):
    return kind + struct.pack(">I", len(body)) + body


def meta(delta, dt, payload):
    return vlq(delta) + bytes([0xFF, dt, len(payload)]) + payload


def end_of_track():
    return vlq(0) + bytes([0xFF, 0x2F, 0x00])


def track_name_event(name):
    return meta(0, 0x03, name.encode("ascii", "replace"))


def write_smf(spec, tracks):
    """tracks: список (дорожка_из_спеки, список_событий) → байты SMF."""
    ppq = num(spec.get("ppq"), 192)
    format_id = num(spec.get("format"), 1)
    n_trks = 1 + len(tracks) if format_id == 1 else 1
    body = struct.pack(">HHH", format_id, n_trks, ppq)
    smf = chunk(b"MThd", body)
    if format_id == 1:
        header = track_name_event(spec.get("title", "ROM export"))
        if spec.get("tempo_us_per_quarter"):
            header += meta(0, 0x51,
                           num(spec["tempo_us_per_quarter"]).to_bytes(3, "big"))
        if spec.get("time_signature"):
            header += meta(0, 0x58, bytes(spec["time_signature"]))
        smf += chunk(b"MTrk", header + end_of_track())
    for track, events in tracks:
        name = track_name_event(track.get("name", "track"))
        body = name + _events_to_bytes(events) + end_of_track()
        smf += chunk(b"MTrk", body)
    return smf


def _events_to_bytes(events):
    """events: [(absolute_tick, order, message_bytes)] → трек с дельтами."""
    out = b""
    position = 0
    for tick, _, message in sorted(events, key=lambda item: (item[0], item[1])):
        out += vlq(tick - position) + message
        position = tick
    return out


# ---------------------------------------------------------------------------
# Дорожки: коды из ROM → события SMF
# ---------------------------------------------------------------------------

def codes_of(track, rom_bytes, runtime_bytes=None):
    """Байты дорожки: адрес и длина берутся из спецификации."""
    source = track.get("source", "image")
    address = to_addr(track["address"])
    length = num(track["length"])
    if source == "runtime":
        if runtime_bytes is None:
            raise SystemExit("дорожка %s просит runtime-байты, а RAM не прочитана "
                             "(--runtime выключен?)" % track.get("name"))
        data = runtime_bytes
    elif source == "image":
        if rom_bytes is None:
            raise SystemExit("дорожка %s просит байты ROM-образа" % track.get("name"))
        data = rom_bytes
    else:
        raise SystemExit("неизвестный source %r у дорожки %s"
                         % (source, track.get("name")))
    offset = address - to_addr(track.get("org", 0x0100))
    if offset < 0 or offset + length > len(data):
        raise SystemExit("дорожка %s: %s+%d не помещается в источник (%d байт)"
                         % (track.get("name"), addr_hex(address), length,
                            len(data)))
    return list(data[offset:offset + length])


def validate_codes(track, codes, spec):
    """Сверка с expect-дампом из спецификации и проверка неизвестных кодов."""
    name = track.get("name") or "?"
    expected = track.get("expect")
    if expected is not None and list(expected) != codes:
        for index, (got, want) in enumerate(zip(codes, expected)):
            if got != want:
                raise SystemExit("дорожка %s: шаг %d = %d, спецификация ждёт %d "
                                 "— останов" % (name, index, got, want))
        raise SystemExit("дорожка %s: длина %d, спецификация ждёт %d"
                         % (name, len(codes), len(expected)))
    mask = num(track.get("code_mask", spec.get("code_mask")), DEFAULT_CODE_MASK)
    unknown = track.get("unknown_codes", spec.get("unknown_codes", "abort"))
    rest = num(track.get("rest_code", spec.get("rest_code")), 0)
    bad = [index for index, code in enumerate(codes)
           if code != rest and (code & ~mask)]
    if bad and unknown == "abort":
        raise SystemExit("дорожка %s: коды с неподдерживаемими битами в шагах %s; "
                         "спецификация не описывает такой случай — расширьте "
                         "code_mask или задайте ветку в спецификации"
                         % (name, bad[:8]))
    return bad


def events_for_track(track, codes, spec):
    """Коды → note on/off. Порядок note_off раньше note_on в одном тике."""
    ppq = num(spec.get("ppq"), 192)
    step_ticks = num(track.get("step_ticks", spec.get("step_ticks")), ppq // 4)
    note_offset = num(track.get("note_offset", spec.get("note_offset")), 0)
    rest = num(track.get("rest_code", spec.get("rest_code")), 0)
    velocity = num(track.get("velocity", spec.get("velocity")), 100)
    channel = num(track.get("midi_channel"), 0)
    events = []
    program = track.get("gm_program")
    if program is not None:
        events.append((0, -1, bytes([0xC0 | channel, num(program) & 0x7F])))
    repeats = num(track.get("repeat", spec.get("repeat")), 1)
    pending = None                       # (tick, note) открытой ноты
    for cycle in range(max(1, repeats)):
        base = cycle * len(codes) * step_ticks
        for step, code in enumerate(codes):
            on = base + step * step_ticks
            off = base + (step + 1) * step_ticks
            if pending is not None:
                events.append((pending[0], 0,
                               bytes([0x80 | channel, pending[1], 0])))
                pending = None
            if code == rest:
                continue
            note = code + note_offset
            if not 0 <= note <= 127:
                raise SystemExit("дорожка %s: шаг %d даёт MIDI-ноту %d вне 0..127 "
                                 "— проверьте note_offset в спецификации"
                                 % (track.get("name"), step, note))
            events.append((on, 1, bytes([0x90 | channel, note, velocity])))
            pending = (off, note)
    if pending is not None:              # закрыть хвост, иначе нота «висит»
        events.append((pending[0], 0, bytes([0x80 | channel, pending[1], 0])))
    return events


def summarize(spec, built):
    rows = []
    for track, events in built:
        notes = [item for item in events if item[2][0] & 0xF0 == 0x90]
        offs = [item for item in events if item[2][0] & 0xF0 == 0x80]
        pitches = [item[2][1] for item in notes]
        rows.append({
            "name": track.get("name"),
            "channel": track.get("midi_channel"),
            "program": track.get("gm_program"),
            "steps": num(track["length"]),
            "notes": len(notes),
            "note_offs": len(offs),
            "range": [min(pitches), max(pitches)] if pitches else None,
            "end_tick": max((item[0] for item in events), default=0),
        })
    return rows


def convert(spec_path, out_path=None, allow_runtime=False, server=None,
            cache_dir=None, rom_override=None):
    with open(spec_path, "r", encoding="utf-8") as handle:
        spec = json.load(handle)
    base = os.path.dirname(os.path.abspath(spec_path))
    rom = rom_override or os.path.join(base, spec.get("rom", "rom.bin"))
    if not os.path.isfile(rom):
        raise SystemExit("ROM не найден: %s" % rom)
    with open(rom, "rb") as handle:
        rom_bytes = handle.read()
    org = to_addr(spec.get("org", 0x0100))
    for track in spec["tracks"]:
        track.setdefault("org", org)
    runtime_bytes = None
    need_runtime = any(track.get("source") == "runtime"
                       for track in spec["tracks"])
    if need_runtime:
        if not allow_runtime:
            raise SystemExit("спецификация просит RUNTIME-байты; добавьте "
                             "--runtime, иначе источник истины подменён (ТЗ §17)")
        session, cache = open_session(rom=rom, org=org, server=server,
                                      cache_dir=cache_dir)
        try:
            lo = min(to_addr(track["address"]) for track in spec["tracks"]
                     if track.get("source") == "runtime")
            hi = max(to_addr(track["address"]) + num(track["length"]) - 1
                     for track in spec["tracks"]
                     if track.get("source") == "runtime")
            payload = session.call("debug_read_memory_range",
                                   {"address": lo, "length": hi - lo + 1})
            runtime_bytes = bytes_of(payload)
            runtime_lo = lo
            mcp_calls = session.stats()["total_calls"]
        finally:
            session.close()
    else:
        runtime_lo = 0
        mcp_calls = 0

    built = []
    for track in spec["tracks"]:
        codes = codes_of(track, rom_bytes,
                         _slice_runtime(track, runtime_bytes, runtime_lo))
        validate_codes(track, codes, spec)
        built.append((track, events_for_track(track, codes, spec)))
    smf = write_smf(spec, built)
    rows = summarize(spec, built)
    if out_path:
        resolved = out_path                       # передано руками — от CWD
    else:
        resolved = spec.get("output") or (
            os.path.splitext(os.path.basename(spec_path))[0] + ".mid")
        # путь в спеке относительный — от каталога спеки, а не от CWD
        resolved = resolved if os.path.isabs(resolved) \
            else os.path.join(base, resolved)
    parent = os.path.dirname(os.path.abspath(resolved))
    if parent and not os.path.isdir(parent):
        raise SystemExit("каталога нет: %s" % parent)
    resolved = os.path.normpath(resolved)
    with open(resolved, "wb") as handle:
        handle.write(smf)
    return {
        "spec": os.path.abspath(spec_path),
        "rom": os.path.abspath(rom),
        "output": resolved,
        "bytes": len(smf),
        "format": spec.get("format", 1),
        "ppq": num(spec.get("ppq"), 192),
        "tempo_us_per_quarter": spec.get("tempo_us_per_quarter"),
        "bpm": (round(6e7 / num(spec["tempo_us_per_quarter"]), 1)
                if spec.get("tempo_us_per_quarter") else None),
        "tracks": rows,
        "status": "DERIVED",
        "verdict": "%d дорожки, %d нот, %d байт SMF"
                   % (len(rows), sum(row["notes"] for row in rows), len(smf)),
        "note": "формат дорожек задан спецификацией; скрипт только раскладывает "
                "коды в события SMF",
        "mcp_calls": mcp_calls,
    }


def _slice_runtime(track, runtime_bytes, runtime_lo):
    """Окно RAM под дорожку; None, если runtime не читали."""
    if runtime_bytes is None:
        return None
    address = to_addr(track["address"])
    length = num(track["length"])
    start = address - runtime_lo
    return runtime_bytes[start:start + length]


def format_report(result):
    lines = ["rom      %s" % result["rom"],
             "спека    %s" % result["spec"],
             "выпуск   %s (%d байт, format %s, %s PPQ)"
             % (result["output"], result["bytes"], result["format"],
                result["ppq"]),
             "темп     %s us/четверть%s"
             % (result["tempo_us_per_quarter"],
                "" if not result["bpm"] else " (~%s BPM)" % result["bpm"]), ""]
    for row in result["tracks"]:
        lines.append("  %-16s ch=%s prog=%-3s шагов=%-4s нот=%-4s "
                     "диапазон=%s конец=%s тик"
                     % (row["name"], row["channel"], row["program"],
                        row["steps"], row["notes"],
                        ("%d..%d" % tuple(row["range"])) if row["range"] else "—",
                        row["end_tick"]))
        if row["notes"] != row["note_offs"]:
            lines.append("      ! note on=%d, note off=%d — висящие ноты"
                         % (row["notes"], row["note_offs"]))
    lines.append("")
    lines.append("ВЕРДИКТ  %d дорожек записано  [%s]  mcp_calls=%s"
                 % (len(result["tracks"]), result["status"],
                    result["mcp_calls"]))
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="analyze.music2midi",
        description="ROM-дорожки → Standard MIDI File по ROM-специфичной спеке")
    parser.add_argument("--spec", required=True, help="music_spec.json")
    parser.add_argument("-o", "--output", default=None)
    parser.add_argument("--rom", default=None, help="перекрыть путь к ROM из спеки")
    parser.add_argument("--runtime", action="store_true",
                        help="разрешить чтение RUNTIME-байтов через MCP")
    parser.add_argument("--server", default=None)
    parser.add_argument("--cache", default=None)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    result = convert(args.spec, out_path=args.output, allow_runtime=args.runtime,
                     server=args.server, cache_dir=args.cache,
                     rom_override=args.rom)
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str)
          if args.json else format_report(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
