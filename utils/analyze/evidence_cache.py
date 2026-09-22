"""Кэш доказательств MCP + provenance (ТЗ §6, §7, §16, §30).

Каждый ответ сервера оборачивается в конверт (envelope), который сам
отвечает на вопросы «какой инструмент, какие параметры, какой ROM, какой
момент рантайма, какой результат». Конверт — это и есть evidence-артефакт:
в отчёте на него ссылаются по `evidence_id`.

Ключ кэша:

    sha1( tool + нормализованные параметры + ROM identity + runtime stamp )

поэтому одно и то же обращение к тому же ROM в том же состоянии не уходит в
сервер повторно, а смена рантайма (после mutating-вызова — run/pause/load_rom —
сессия сбрасывает отпечаток) сама инвалидирует записи.

Повторная сборка отчёта возможна без MCP: `index.jsonl` + конверты дают
перенести весь прогон (`EvidenceCache.iter_envelopes()`).

Режимы источника (`source` в конверте, ТЗ §16):
    IMAGE    — байты ROM-образа
    RUNTIME  — байты/состояние живого эмулятора
    DERIVED  — производные от доказательств данные (наши таблицы, графики)
"""
from __future__ import annotations

import hashlib
import json
import os
import time

ENVELOPE_VERSION = 1
DEFAULT_CACHE_ENV = "V06C_ANALYZE_CACHE"


def normalize_args(args):
    """Канонический вид параметров для ключа: sorted keys, адреса — числами."""
    if not isinstance(args, dict):
        return args
    out = {}
    for key in sorted(args):
        value = args[key]
        if value is None:
            continue
        if isinstance(value, (list, tuple)):
            out[key] = [_norm_scalar(v) for v in value]
        else:
            out[key] = _norm_scalar(value)
    return out


def _norm_scalar(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        text = value.strip()
        if text.lower().startswith("0x"):
            try:
                return int(text, 16)
            except ValueError:
                return text
        return text
    if isinstance(value, dict):
        return normalize_args(value)
    return value


class EvidenceCache:
    """Слой кэширования над сессией MCP.

    root=None → $V06C_ANALYZE_CACHE, иначе `<rom_dir>/.analyze/cache`.
    enabled=False ⇒ прозрачный промах к серверу (для отладки одного шага).
    """

    def __init__(self, root=None, identity=None, enabled=True, verbose=False):
        self.root = os.path.abspath(root) if root else None
        self.identity = dict(identity or {})
        self.enabled = bool(enabled)
        self.verbose = verbose
        self.hits = 0
        self.misses = 0
        self.stores = 0
        self.bypasses = 0
        self.per_tool = {}
        self._by_id = {}

    # -- расположение ------------------------------------------------------

    @classmethod
    def for_rom(cls, rom_path, root=None, identity=None, **kw):
        """Кэш рядом с ROM: <каталог ROM>/.analyze/cache/<stem>-<sha[:8]>."""
        if root is None:
            root = os.environ.get(DEFAULT_CACHE_ENV)
        if root is None:
            root = os.path.join(os.path.dirname(os.path.abspath(rom_path)), ".analyze")
        stem = os.path.splitext(os.path.basename(rom_path))[0]
        digest = (identity or {}).get("sha256") or ""
        tag = "%s-%s" % (stem, digest[:8]) if digest else stem
        return cls(os.path.join(os.path.abspath(root), "cache", tag), identity, **kw)

    def subdir(self, kind):
        path = os.path.join(self.root, kind)
        os.makedirs(path, exist_ok=True)
        return path

    # -- ключ --------------------------------------------------------------

    def key_for(self, tool, args, stamp=None, identity=None):
        ident = self._identity_part(identity)
        payload = {
            "tool": tool,
            "args": normalize_args(args or {}),
            "rom": ident,
            "runtime": _stamp_part(stamp) if stamp is not None else None,
        }
        blob = json.dumps(payload, sort_keys=True, separators=(",", ":"),
                          ensure_ascii=False)
        return hashlib.sha1(blob.encode("utf-8")).hexdigest(), payload

    def _identity_part(self, override=None):
        ident = dict(self.identity)
        ident.update(override or {})
        return {
            "filename": ident.get("filename"),
            "size": ident.get("size"),
            "sha256": (ident.get("sha256") or "")[:16] or None,
            "org": ident.get("org"),
        }

    def path_for(self, tool, key):
        return os.path.join(self.subdir("evidence"), "%s.%s.json" % (tool[6:] if tool.startswith("debug_") else tool, key[:12]))

    # -- основной доступ -----------------------------------------------------

    def get_or_call(self, session, tool, args=None, stamp="auto", source="RUNTIME",
                    refresh=False, timeout=None, note=None):
        """Закэшированный tools/call.

        stamp="auto" — берём отпечаток рантайма у сессии; stamp=None — ключ
        от рантайма не зависит (например для чтения самого файла ROM).
        Возвращает (result, envelope).
        """
        args = dict(args or {})
        if stamp == "auto":
            stamp = session.runtime_stamp()
        key, payload = self.key_for(tool, args, stamp)
        env_path = self.path_for(tool, key)
        ev_id = "ev:%s:%s" % (tool.replace("debug_", ""), key[:12])

        if self.enabled and not refresh and os.path.exists(env_path):
            envelope = _read_json(env_path)
            if envelope:
                envelope["source"] = "CACHE"
                envelope["cached"] = True     # на диске лежал свежий store (cached=False)
                self._count_hit(tool)
                self._by_id[ev_id] = env_path
                return envelope.get("result"), envelope

        started = time.time()
        result = session.call(tool, args, timeout=timeout) if session is not None else None
        elapsed_ms = (time.time() - started) * 1000.0
        if not self.enabled:
            self.bypasses += 1
            self._count_miss(tool)
            return result, {"evidence_id": ev_id, "tool": tool, "arguments": args,
                            "result": result, "source": "MCP", "cached": False}

        envelope = {
            "envelope": ENVELOPE_VERSION,
            "evidence_id": ev_id,
            "tool": tool,
            "arguments": normalize_args(args),
            "rom": payload["rom"],
            "runtime": payload["runtime"],
            "memory_source": source,
            "collected_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "elapsed_ms": round(elapsed_ms, 1),
            "cached": False,
            "result": result,
        }
        if note:
            envelope["note"] = note
        _write_json(env_path, envelope)
        self._index(envelope)
        self._by_id[ev_id] = env_path
        self.stores += 1
        self._count_miss(tool)
        if self.verbose:
            print("[cache] miss %s → %s" % (ev_id, os.path.relpath(env_path, self.root)))
        return result, envelope

    def _count_hit(self, tool):
        self.hits += 1
        slot = self.per_tool.setdefault(tool, {"hits": 0, "misses": 0})
        slot["hits"] += 1

    def _count_miss(self, tool):
        self.misses += 1
        slot = self.per_tool.setdefault(tool, {"hits": 0, "misses": 0})
        slot["misses"] += 1

    # -- производные артефакты (ТЗ §16 DERIVED) ----------------------------

    def save_derived(self, name, obj, derived_from=None, note=None):
        """Сохранить результат локальной обработки со ссылкой на доказательства."""
        path = os.path.join(self.subdir("derived"), "%s.json" % name)
        envelope = {
            "envelope": ENVELOPE_VERSION,
            "evidence_id": "ev:derived:%s" % name,
            "artifact": name,
            "source": "DERIVED",
            "memory_source": "DERIVED",
            "derived_from": list(derived_from or []),
            "rom": self._identity_part(),
            "collected_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "result": obj,
        }
        if note:
            envelope["note"] = note
        _write_json(path, envelope)
        self._index(envelope)
        return path, envelope["evidence_id"]

    def load(self, evidence_id):
        path = self._by_id.get(evidence_id)
        if path is None and evidence_id.startswith("ev:"):
            tool, _, tail = evidence_id[3:].partition(":")
            for candidate in os.listdir(os.path.join(self.root, "evidence")) \
                    if os.path.isdir(os.path.join(self.root, "evidence")) else []:
                if candidate.endswith(".%s.json" % tail):
                    path = os.path.join(self.root, "evidence", candidate)
                    break
        return _read_json(path) if path else None

    def iter_envelopes(self):
        """Все конверты прогона (для пересборки отчёта без MCP)."""
        evidence = os.path.join(self.root, "evidence")
        derived = os.path.join(self.root, "derived")
        for folder in (evidence, derived):
            if not os.path.isdir(folder):
                continue
            for name in sorted(os.listdir(folder)):
                if name.endswith(".json"):
                    envelope = _read_json(os.path.join(folder, name))
                    if envelope:
                        yield envelope

    def _index(self, envelope):
        os.makedirs(self.root, exist_ok=True)
        entry = {
            "evidence_id": envelope.get("evidence_id"),
            "tool": envelope.get("tool"),
            "artifact": envelope.get("artifact"),
            "source": envelope.get("source"),
            "collected_at": envelope.get("collected_at"),
            "rom": envelope.get("rom"),
            "runtime": envelope.get("runtime"),
        }
        with open(os.path.join(self.root, "index.jsonl"), "a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, ensure_ascii=False, sort_keys=True) + "\n")

    def stats(self):
        total = self.hits + self.misses
        return {
            "root": self.root,
            "enabled": self.enabled,
            "hits": self.hits,
            "misses": self.misses,
            "stores": self.stores,
            "bypasses": self.bypasses,
            "hit_rate": round(100.0 * self.hits / total, 1) if total else 0.0,
            "by_tool": self.per_tool,
        }

    def __repr__(self):
        return "EvidenceCache(%s, hits=%d, misses=%d)" % (self.root, self.hits, self.misses)


def _stamp_part(stamp):
    if not isinstance(stamp, dict):
        return stamp
    return {k: stamp[k] for k in ("pc", "running", "cycles", "frames", "sp")
            if k in stamp and stamp[k] is not None}


def _read_json(path):
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, json.JSONDecodeError):
        return None


def _write_json(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, ensure_ascii=False, indent=1, sort_keys=True)
    os.replace(tmp, path)
