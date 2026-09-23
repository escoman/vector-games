"""Пакетное нанесение семантических аннотаций на RDB (ТЗ §28—§29).

Вход — стандартный JSON-файл аннотаций:

    {
      "objects": [
        {
          "address": "0x2706",            // int или hex-строка
          "name": "font_8x8",             // обязателен, проходит naming.validate
          "type": "data",                 // один из naming.TYPE_PREFIX
          "size": 256,                    // необязательно
          "comment": "основной шрифт",
          "properties": {"glyph_width": 8},
          "aliases": ["glyphs"],
          "links": [{"to": "0x274E", "kind": "points_to"}]
        }
      ]
    }

Схема выполнения (ТЗ §3):

    validate_annotations   ← ЧИСТАЯ функция: ни MCP, ни записей; любая
    │                      ошибка в файле — отказ ДО первого изменения
    ▼
    apply (RdbWriter)      ← N отдельных debug_* вызовов; пакетного API в
    │                      сервере нет и имитировать его запрещено (ТЗ §29),
    │                      но при появлении `debug_apply_rdb_batch` в
    │                      CapabilityProfile модуль перейдёт на него сам
    ▼
    каждые <=10 изменений: save → checkpoint (ТЗ §4.2, §7)

Идемпотентность (ТЗ §12): повтор того же файла не создаёт дублей —
`ensure_object` оставляет существующий объект, aliases/link добавляются
аддитивно дедуплицированными средствами `rdb.py`.

    python3 utils/analyze/cli.py apply_annotations \
        --in annotations.json --rom … --rdb … --org 0x0100 --apply --json
"""
from __future__ import annotations

import argparse
import json
import os
import sys

from analyze import naming, pipeline_state
from analyze.mcp_session import addr_hex, envelope, open_session, to_addr
from analyze.rdb import RdbWriter
from analyze.seed_rdb import BatchSaver

# Инструмент, который появится в сервере позже (ТЗ §29): при его наличии
# модуль обязан перейти на него без правки вызывающего кода.
BATCH_TOOL = "debug_apply_rdb_batch"


def validate_annotations(data, image_lo=None, image_hi=None):
    """Проверить файл аннотаций, не трогая MCP. → (objects, errors).

    `objects` — нормализованные записи (адреса int, links [(to, kind)]),
    отсортированные по адресу (детерминизм, ТЗ §32). `errors` — список
    строк; непустой список означает «не применять ничего» (ТЗ §30: semantic
    ошибки файла — не повод мутировать RDB наполовину).
    """
    errors = []
    if not isinstance(data, dict) or not isinstance(data.get("objects"), list):
        return [], ['ожидался {"objects": [...]}']
    objects = []
    seen_addresses = set()
    for index, raw in enumerate(data["objects"]):
        where = "объект #%d" % index
        if not isinstance(raw, dict):
            errors.append("%s: не объект, а %s" % (where, type(raw).__name__))
            continue
        address = to_addr(raw.get("address"))
        if address is None:
            errors.append("%s: нет/битый address" % where)
            continue
        where = "объект @%s" % addr_hex(address)
        if image_lo is not None and image_hi is not None and \
                not (to_addr(image_lo) <= address <= to_addr(image_hi)):
            errors.append("%s: вне образа ROM [%s..%s]"
                          % (where, addr_hex(image_lo), addr_hex(image_hi)))
        if address in seen_addresses:
            errors.append("%s: дубликат адреса внутри файла" % where)
            continue
        seen_addresses.add(address)

        name = raw.get("name")
        rtype = (raw.get("type") or "").strip().lower()
        if rtype not in naming.TYPE_PREFIX:
            errors.append("%s: неизвестный тип %r (ожидан один из %s)"
                          % (where, raw.get("type"),
                             ", ".join(sorted(naming.TYPE_PREFIX))))
            continue
        if not name:
            errors.append("%s: пустое name" % where)
            continue
        problems = [p for p in naming.validate(name, rtype) if p[0] == "error"]
        if problems:
            errors.append("%s: имя %r — %s" % (where, name, problems[0][1]))
            continue

        aliases = raw.get("aliases") or []
        if not isinstance(aliases, list):
            errors.append("%s: aliases должен быть списком" % where)
            continue
        for alias in aliases:
            if not naming.is_valid_alias(alias, rtype):
                errors.append("%s: невалидный alias %r" % (where, alias))

        links = []
        for link in raw.get("links") or []:
            if not isinstance(link, dict) or to_addr(link.get("to")) is None:
                errors.append('%s: link без "to"' % where)
                continue
            if to_addr(link["to"]) == address:
                errors.append("%s: self-link на себя" % where)
                continue
            links.append((to_addr(link["to"]), link.get("kind") or ""))

        properties = raw.get("properties") or {}
        if not isinstance(properties, dict):
            errors.append("%s: properties должен быть объектом" % where)
            continue

        size = raw.get("size")
        if size is not None and (not isinstance(size, int) or size < 0):
            errors.append("%s: некорректный size %r" % (where, size))
            continue
        objects.append({
            "address": address,
            "name": name,
            "type": rtype,
            "size": size,
            "comment": raw.get("comment"),
            "properties": properties,
            "aliases": sorted(set(aliases)),
            "links": sorted(set(links)),
        })
    if errors:
        return [], sorted(set(errors))
    objects.sort(key=lambda o: o["address"])
    return objects, []


def apply_annotations(writer, objects, saver=None):
    """Нанести проверенные аннотации через `RdbWriter` (идемпотентно)."""
    counts = {"objects_added": 0, "objects_updated": 0, "links_added": 0,
              "aliases_added": 0}
    left = {"pending": sum(1 + len(o["links"]) + len(o["aliases"])
                           for o in objects)}

    def note():
        left["pending"] -= 1
        if saver is not None:
            saver.note(1, left["pending"])

    for obj in objects:
        result = writer.ensure_object(
            obj["address"], obj["name"], obj["type"], size=obj.get("size"),
            comment=obj.get("comment"), properties=obj.get("properties") or None)
        counts["objects_added" if result.get("created") else "objects_updated"] += 1
        note()
        for alias in obj["aliases"]:
            added = writer.add_alias(obj["address"], alias)
            if added.get("added"):
                counts["aliases_added"] += 1
            note()
        # Существующие ссылки (ТЗ §12: повтор файла не плодит дублей):
        # debug_get_rdb_object отдаёт объект с полем `links`.
        current = writer.exists(obj["address"]) or {}
        known = {to_addr(a) for a in (current.get("links") or [])}
        for target, kind in obj["links"]:
            writer.add_link(obj["address"], target)
            if target not in known:
                counts["links_added"] += 1
            note()
    return counts


def _apply_via_batch(session, objects, batch_size):
    """Путь, когда сервер однажды отдаст debug_apply_rdb_batch (ТЗ §29).

    Один вызов на пачку <= batch_size объектов; payload повторяет формат
    входного файла — это сознательная точка перехода, пока инструмента нет,
    в основной код он не вызывается.
    """
    applied = 0
    for start in range(0, len(objects), batch_size):
        chunk = objects[start:start + batch_size]
        session.call(BATCH_TOOL, {"objects": [
            {"address": o["address"], "name": o["name"], "type": o["type"],
             "size": o.get("size"), "comment": o.get("comment"),
             "properties": o.get("properties"), "aliases": o["aliases"],
             "links": [{"to": t, "kind": k} for t, k in o["links"]]}
            for o in chunk]})
        applied += len(chunk)
    return applied


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="analyze.apply_annotations",
        description="Нанести JSON-аннотации на RDB через MCP (save+checkpoint "
                    "пачками)")
    parser.add_argument("--in", dest="source", required=True,
                        help="файл аннотаций ({objects:[…]})")
    parser.add_argument("--rom", required=True)
    parser.add_argument("--rdb", default=None)
    parser.add_argument("--org", type=lambda s: int(s, 0), default=0x0100)
    parser.add_argument("--hi", type=lambda s: int(s, 0), default=None)
    parser.add_argument("--apply", action="store_true",
                        help="записать изменения (по умолчанию — план)")
    parser.add_argument("--dry-run", action="store_true",
                        help="только план (режим по умолчанию)")
    parser.add_argument("--save-every", type=int, default=10,
                        help="при записи: save+checkpoint каждые N изменений "
                             "(предел max_unsaved_objects, ТЗ §4.2)")
    parser.add_argument("--cache", default=None)
    parser.add_argument("--server", default=None)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    dry_run = not args.apply
    try:
        with open(args.source, encoding="utf-8") as handle:
            data = json.load(handle)
    except (IOError, OSError, ValueError) as exc:
        print("apply_annotations: файл аннотаций не читается: %s" % exc,
              file=sys.stderr)
        return 2

    size = os.path.getsize(args.rom) if os.path.exists(args.rom) else 0
    lo = args.org
    hi = args.hi if args.hi is not None else lo + size - 1
    objects, errors = validate_annotations(data, lo, hi)
    if errors:
        # Ошибки валидации — до первого MCP-mutating вызова (ТЗ §30).
        print(json.dumps(envelope(
            {"module": "apply_annotations", "source": args.source,
             "errors": errors, "validated": 0},
            module="apply_annotations", status="FAILED",
            verdict="файл аннотаций невалиден: %d ошибок, мутаций 0"
                    % len(errors)), ensure_ascii=False,
            indent=2 if args.json else None))
        return 1

    session, cache = open_session(rom=args.rom, org=args.org,
                                  server=args.server, cache_dir=args.cache)
    try:
        writer = RdbWriter(session, dry_run=dry_run)
        saver = None if dry_run else BatchSaver(
            writer, args.save_every,
            log=lambda m: print("# " + m, file=sys.stderr))
        result = {"source": args.source, "objects": len(objects)}
        if not dry_run and BATCH_TOOL in session.tools:
            # Штатный переход, когда сервер получит пакетный API (ТЗ §29).
            applied = _apply_via_batch(session, objects,
                                       max(1, min(args.save_every, 10)))
            result["objects_added"] = applied
            result["batch_tool"] = BATCH_TOOL
            session.call("debug_save_rdb")
            pipeline_state.checkpoint_active(current_stage="apply_annotations",
                                             status="checkpoint")
        else:
            counts = apply_annotations(writer, objects, saver=saver)
            result.update(counts)
            if not dry_run:
                writer.save()
                if saver is not None:
                    saver.flush(0)
                    pipeline_state.checkpoint_active(
                        current_stage="apply_annotations",
                        current_batch=saver.batches,
                        processed_objects=saver.applied, pending_objects=0,
                        status="checkpoint")
                result["batches"] = saver.batches if saver else 0
                result["saves"] = (saver.saves if saver else 0) + 1
        status = "CANDIDATE" if dry_run else "PASS"
        verdict = ("%s: объектов %d, +%d, ~%d, links %d, aliases %d"
                   % ("план" if dry_run else "нанесено", len(objects),
                      result.get("objects_added", 0),
                      result.get("objects_updated", 0),
                      result.get("links_added", 0),
                      result.get("aliases_added", 0)))
        data = envelope(result, module="apply_annotations", session=session,
                        cache=cache, status=status, verdict=verdict,
                        note="аннотации применяются строго через MCP; при "
                             "появлении %s модуль использует его автоматически"
                             % BATCH_TOOL)
        print(json.dumps(data, ensure_ascii=False,
                         indent=2 if args.json else None))
    except Exception as error:                       # noqa: BLE001 — отказ не роняет прогон
        data = envelope({"module": "apply_annotations",
                         "error": "%s: %s" % (type(error).__name__, error)},
                        module="apply_annotations", session=session,
                        status="FAILED",
                        verdict="нанесение завершилось ошибкой: %s" % error)
        print(json.dumps(data, ensure_ascii=False,
                         indent=2 if args.json else None))
        return 1
    finally:
        session.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
