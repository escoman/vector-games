"""Модель RDB: лёгкий читатель JSON + писатель через MCP (ТЗ §11, §12, §28).

Формат на диске (проверено на putup.rdb / TESTAY.rdb):

    {"format": "rdb", "version": int, "platform": str, "rom": {...},
     "objects": [{"address": "0x0100", "name": "func_entry",
                  "type": "function", "size": 4, "comment": "...",
                  "links": ["0x0B57"], "properties": {"params": "..."}}]}

Чтение — локальное и бесплатное (lint, отчёты, покрытие). ЗАПИСЬ штатно
ведётся только через MCP (`RdbWriter`), чтобы не разъезжаться с отладчиком:
он хранит RDB в состоянии процесса, и правка JSON «под ногами» будет
проигнорирована или перезаписана. Прямая запись JSON доступна лишь осознанно
(`Rdb.dump()` с `force=True`) — для тестов и исправления повреждённых файлов.

Важное ограничение отладчика: на один адрес приходится один объект. Поэтому
логические подэлементы (строка внутри блока, глиф внутри шрифта) — это
свойства/комментарии/ссылки родительского объекта, а не отдельные записи
(ТЗ §12).
"""
from __future__ import annotations

import json
import os
import re

from analyze.mcp_session import addr_hex, to_addr
from analyze import naming


class RdbObject:
    __slots__ = ("address", "name", "type", "size", "comment", "links", "properties")

    def __init__(self, address, name, type, size=0, comment="", links=None,
                 properties=None):
        self.address = to_addr(address)
        self.name = name
        self.type = (type or "").strip().lower()
        self.size = int(size or 0)
        self.comment = comment or ""
        self.links = [to_addr(a) for a in (links or [])]
        self.properties = dict(properties or {})

    @property
    def size_known(self):
        """Размер пригоден как длина интервала.

        Отладчик пишет 0xFFFFFFFF (и иногда 0), когда длина области не
        определена: это не размер, а «неизвестно».
        """
        return 0 < self.size <= 0x10000

    @property
    def span(self):
        return self.size if self.size_known else 1

    @property
    def end(self):
        """Адрес последнего байта объекта (при неизвестном размере — сам адрес)."""
        return self.address + self.span - 1

    def contains(self, address):
        address = to_addr(address)
        return self.address <= address <= self.end

    def overlaps(self, other):
        return self.address <= other.end and other.address <= self.end

    @property
    def is_unknown(self):
        return naming.is_unknown(self.name)

    @property
    def is_code(self):
        return self.type in ("function", "code", "label")

    def get(self, prop, default=None):
        return self.properties.get(prop, default)

    def to_dict(self, hex_addrs=True):
        fmt = addr_hex if hex_addrs else (lambda a: int(a))
        out = {
            "address": fmt(self.address),
            "type": self.type,
            "name": self.name,
            "size": self.size,
        }
        if self.comment:
            out["comment"] = self.comment
        if self.links:
            out["links"] = [fmt(a) for a in self.links]
        if self.properties:
            out["properties"] = dict(self.properties)
        return out

    def __repr__(self):
        return "RdbObject(%s %s %s size=%d)" % (
            addr_hex(self.address), self.type, self.name, self.size)


class Rdb:
    """Иммутная модель для анализа."""

    def __init__(self, objects=None, meta=None, path=None):
        self.objects = sorted(objects or [], key=lambda o: (o.address, o.name))
        self.meta = dict(meta or {})
        self.path = path

    # -- источники ---------------------------------------------------------

    @classmethod
    def load(cls, path):
        with open(path, encoding="utf-8") as fh:
            return cls.from_dict(json.load(fh), path=path)

    @classmethod
    def from_dict(cls, data, path=None):
        if not isinstance(data, dict) or "objects" not in data:
            raise ValueError("не RDB: ожидался {'format':'rdb','objects':[...]}")
        objects = [RdbObject(**{k: v for k, v in item.items()
                               if k in RdbObject.__slots__})
                   for item in data["objects"]]
        meta = {k: v for k, v in data.items() if k != "objects"}
        return cls(objects, meta, path)

    @classmethod
    def from_session(cls, session, limit=2000):
        """Снять текущее состояние RDB из отладчика."""
        listed = session.call("debug_list_rdb_objects", {"limit": limit})
        objects = [RdbObject(**item) for item in listed.get("objects", [])]
        info = session.call("debug_get_rdb_info")
        return cls(objects, meta={"info": info})

    # -- поиск -------------------------------------------------------------

    def by_addr(self, address):
        address = to_addr(address)
        for obj in self.objects:
            if obj.address == address:
                return obj
        return None

    def at(self, address):
        """Объект, накрывающий адрес (в том числе началом или серединой)."""
        address = to_addr(address)
        best = None
        for obj in self.objects:
            if obj.contains(address):
                if best is None or obj.address > best.address:
                    best = obj
        return best

    def by_name(self, name):
        return [o for o in self.objects if o.name == name]

    def of_type(self, *types):
        wanted = {t.lower() for t in types}
        return [o for o in self.objects if o.type in wanted]

    def matching(self, pattern):
        rx = re.compile(pattern)
        return [o for o in self.objects if rx.search(o.name)]

    def unknowns(self):
        return [o for o in self.objects if o.is_unknown]

    # -- геометрия ---------------------------------------------------------

    def extents(self):
        """Объединение всех объектов: [(start, end)] без пересечений."""
        merged = []
        for obj in sorted(self.objects, key=lambda o: o.address):
            start, end = obj.address, obj.end
            if merged and start <= merged[-1][1] + 1:
                merged[-1] = (merged[-1][0], max(merged[-1][1], end))
            else:
                merged.append((start, end))
        return merged

    def gaps(self, lo, hi):
        """Свободные интервалы [lo, hi] без объектов."""
        lo, hi = to_addr(lo), to_addr(hi)
        out, cursor = [], lo
        for start, end in self.extents():
            if end < lo or start > hi:
                continue
            start = max(start, lo)
            if start > cursor:
                out.append((cursor, start - 1))
            cursor = max(cursor, min(end, hi) + 1)
            if cursor > hi:
                break
        if cursor <= hi:
            out.append((cursor, hi))
        return out

    def covered_count(self, lo, hi):
        lo, hi = to_addr(lo), to_addr(hi)
        total = 0
        for start, end in self.extents():
            total += max(0, min(end, hi) - max(start, lo) + 1)
        return total

    # -- отчёты -----------------------------------------------------------

    def stats(self, image_lo=None, image_hi=None):
        types = {}
        for obj in self.objects:
            types[obj.type] = types.get(obj.type, 0) + 1
        out = {
            "path": self.path,
            "objects": len(self.objects),
            "by_type": dict(sorted(types.items())),
            "links": sum(len(o.links) for o in self.objects),
            "comments": sum(1 for o in self.objects if o.comment),
            "properties": sum(1 for o in self.objects if o.properties),
            "unknowns": len(self.unknowns()),
            "bad_names": sum(1 for o in self.objects
                             if [p for p in naming.validate(o.name, o.type)
                                 if p[0] == "error"]),
        }
        if image_lo is not None and image_hi is not None:
            total = to_addr(image_hi) - to_addr(image_lo) + 1
            covered = self.covered_count(image_lo, image_hi)
            out["image"] = {"lo": addr_hex(image_lo), "hi": addr_hex(image_hi),
                            "bytes": total, "covered": covered,
                            "coverage_percent": round(100.0 * covered / total, 2)}
        return out

    def dump(self, path=None, force=False):
        """Прямая запись JSON — ТОЛЬКО для тестов/восстановления (ТЗ §11)."""
        if not force:
            raise RuntimeError(
                "Rdb.dump() без force запрещён: штатная запись RDB идёт через "
                "MCP (RdbWriter + debug_save_rdb), иначе отладчик перезапишет файл")
        path = path or self.path
        if not path:
            raise ValueError("не указан путь для записи")
        data = {"format": "rdb", "objects": [o.to_dict() for o in self.objects]}
        for key, value in self.meta.items():
            if key != "objects":
                data[key] = value
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=False, indent=2)
            fh.write("\n")
        return path

    def __len__(self):
        return len(self.objects)

    def __iter__(self):
        return iter(self.objects)


# ---------------------------------------------------------------------------
# Запись — через официальный API отладчика.
# ---------------------------------------------------------------------------

class RdbWriter:
    """Идемпотентная запись RDB через debug_*-инструменты.

    Все методы возвращают короткое описание действия, чтобы вызывающий мог
    собрать протокол изменений; `save()` в конце обязателен.
    """

    def __init__(self, session, dry_run=False):
        self.session = session
        self.dry_run = dry_run
        self.actions = []
        self.conflicts = []

    def _do(self, kind, tool, args, apply_fn=True):
        self.actions.append({"kind": kind, "tool": tool, "arguments": args})
        if self.dry_run or not apply_fn:
            return {"dry_run": True}
        return self.session.call(tool, args)

    def exists(self, address):
        return self.session.call("debug_get_rdb_object", {"address": to_addr(address)})

    def ensure_object(self, address, name, type, size=None, comment=None,
                      properties=None, links=None, rename=False):
        """Создать объект или привести существующий к указанным полям.

        Один адрес — один объект: если по адресу уже есть запись, она
        обновляется (или остаётся как есть при rename=False).
        """
        address = to_addr(address)
        current = self.exists(address)
        problems = [p for p in naming.validate(name, type) if p[0] == "error"]
        if problems:
            raise ValueError("нелигитимное имя %r: %s" % (name, problems[0][1]))
        if not current or not current.get("address"):
            self._do("add", "debug_add_rdb_object",
                     _clean({"address": address, "name": name, "type": type,
                             "size": size}))
            created = True
        else:
            created = False
            if rename and current.get("name") != name:
                self._do("rename", "debug_update_rdb_object",
                         _clean({"address": address, "name": name,
                                 "type": current.get("type") or type,
                                 "size": current.get("size") if size is None else size}))
            elif size is not None and int(current.get("size") or 0) != int(size):
                self._do("resize", "debug_update_rdb_object",
                         _clean({"address": address,
                                 "name": current.get("name") or name,
                                 "type": current.get("type") or type,
                                 "size": size}))
        if comment is not None:
            self.set_comment(address, comment)
        for key, value in (properties or {}).items():
            self.set_property(address, key, value)
        for target in (links or []):
            self.add_link(address, target)
        return {"address": addr_hex(address), "created": created, "name": name}

    def set_comment(self, address, comment):
        return self._do("comment", "debug_set_rdb_comment",
                        {"address": to_addr(address), "comment": comment})

    def set_property(self, address, prop, value):
        return self._do("property", "debug_set_rdb_property",
                        {"address": to_addr(address), "property": prop,
                         "value": value if isinstance(value, str)
                         else json.dumps(value, ensure_ascii=False)})

    def add_link(self, source, target):
        return self._do("link", "debug_add_rdb_link",
                        {"source": to_addr(source), "target": to_addr(target)})

    def remove_link(self, source, target):
        return self._do("unlink", "debug_remove_rdb_link",
                        {"source": to_addr(source), "target": to_addr(target)})

    def remove_object(self, address):
        return self._do("remove", "debug_remove_rdb_object",
                        {"address": to_addr(address)})

    def add_label(self, address, name):
        """Метка-затравка для control flow (ТЗ §10)."""
        return self.ensure_object(address, name, "label")

    def save(self):
        out = None if self.dry_run else self.session.call("debug_save_rdb")
        self.actions.append({"kind": "save", "tool": "debug_save_rdb",
                             "arguments": {}, "result": out})
        return out

    def reload(self):
        """Перечитать RDB с диска (после внешней правки файла)."""
        return self.session.call("debug_reload_rdb")

    def summary(self):
        return {"actions": len(self.actions), "dry_run": self.dry_run,
                "kinds": _histogram(a["kind"] for a in self.actions)}


def _clean(args):
    return {k: v for k, v in args.items() if v is not None}


def _histogram(items):
    out = {}
    for item in items:
        out[item] = out.get(item, 0) + 1
    return dict(sorted(out.items()))
