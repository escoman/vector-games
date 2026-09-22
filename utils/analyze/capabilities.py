"""CapabilityProfile — реальный состав инструментов MCP (ТЗ §5).

Анализатор не имеет права сравнивать строки или «надеяться», что инструмент
есть: он спрашивает профиль.

    caps = CapabilityProfile.from_session(session)
    caps.require("debug_coverage_report")            # без него — падаем
    if caps.has("debug_diff_memory"):                # опциональное ускорение
        ...
    caps.accepts("debug_analyze_code", "addresses")  # состав параметров

Профиль строится из ответа `tools/list`, поэтому не зависит от порядка
инструментов (ТЗ §32) и от версий описаний.

`MissingCapability` формулирует понятное сообщение: чего нет и чем заменить.
"""
from __future__ import annotations

import re


class MissingCapability(RuntimeError):
    def __init__(self, names, hint=None):
        message = "v06c-mcp не предоставляет инструмент(ы): " + ", ".join(
            names if isinstance(names, (list, tuple, set)) else [names]
        )
        if hint:
            message += " — " + hint
        super().__init__(message)
        self.names = list(names) if isinstance(names, (list, tuple, set)) else [names]


# Группы, без которых пакет в принципе неработоспособен.
CORE_REQUIRED = (
    "debug_load_rom",
    "debug_get_state",
    "debug_analyze_code",
    "debug_disassemble_range",
    "debug_read_memory_range",
    "debug_list_rdb_objects",
    "debug_get_rdb_info",
    "debug_save_rdb",
)

# Пакетные инструменты Stage 6.26: экономия round-trip. Их отсутствие —
# повод для деградации, а не для отказа работать.
BATCH_TOOLS = (
    "debug_disassemble_image",
    "debug_coverage_report",
    "debug_diff_memory",
    "debug_find_bytecode_sequence",
    "debug_find_immediate_in_range",
    "debug_get_vram_bytes",
)


class CapabilityProfile:
    """Множество реальных инструментов + их схемы параметров."""

    def __init__(self, tools):
        # tools: {name: {"schema": {...}, "description": str}} | {name: schema}
        self._tools = {}
        for name, entry in dict(tools).items():
            if isinstance(entry, dict) and "schema" in entry:
                self._tools[name] = entry["schema"] or {}
            else:
                self._tools[name] = entry or {}

    @classmethod
    def from_session(cls, session):
        return cls(session.tools)

    # -- базовые вопросы ---------------------------------------------------

    def names(self):
        return set(self._tools)

    def __len__(self):
        return len(self._tools)

    def __contains__(self, name):
        return name in self._tools

    def has(self, *names):
        """True, если EVERY перечисленный инструмент зарегистрирован."""
        return all(name in self._tools for name in names)

    def require(self, *names, hint=None):
        for name in names:
            if name not in self._tools:
                raise MissingCapability(list(names), hint)
        return True

    def optional(self, name, default=None):
        """Имя инструмента, если он есть, иначе default."""
        return name if name in self._tools else default

    def missing_core(self):
        return [name for name in CORE_REQUIRED if name not in self._tools]

    def batch_available(self):
        return [name for name in BATCH_TOOLS if name in self._tools]

    # -- параметры ---------------------------------------------------------

    def accepts(self, tool, param):
        schema = self._tools.get(tool) or {}
        return param in (schema.get("properties") or {})

    def required_params(self, tool):
        schema = self._tools.get(tool) or {}
        return list(schema.get("required") or [])

    def param_type(self, tool, param):
        schema = self._tools.get(tool) or {}
        spec = (schema.get("properties") or {}).get(param) or {}
        if spec.get("type") == "array":
            return "array<%s>" % (spec.get("items") or {}).get("type", "?")
        return spec.get("type")

    def param_bounds(self, tool, param):
        schema = self._tools.get(tool) or {}
        spec = (schema.get("properties") or {}).get(param) or {}
        return {k: spec[k] for k in ("minimum", "maximum", "minItems", "maxItems")
                if k in spec}

    def description(self, tool):
        schema = self._tools.get(tool)
        return (schema or {}).get("description", "") if schema else ""

    # -- удобства для «спрятать ограничения MCP» (ТЗ §9) -------------------

    def analyze_code_form(self):
        """Как передавать точки входа в debug_analyze_code.

        Возвращает "both" (start_address и addresses можно вместе),
        "addresses" / "start_address" (только одна форма) или "none".
        """
        props = ((self._tools.get("debug_analyze_code") or {}).get("properties") or {})
        has_start = "start_address" in props
        has_multi = "addresses" in props
        if has_start and has_multi:
            text = (self._tools["debug_analyze_code"].get("description") or "")
            if re.search(r"may be combined|combine", text, re.I):
                return "both"
            return "either"
        if has_multi:
            return "addresses"
        if has_start:
            return "start_address"
        return "none"

    def summary(self):
        return {
            "tools": len(self._tools),
            "core_missing": self.missing_core(),
            "batch": self.batch_available(),
            "analyze_code_form": self.analyze_code_form(),
        }

    def __repr__(self):
        return "CapabilityProfile(%d инструментов, batch=%d)" % (
            len(self._tools), len(self.batch_available()))
