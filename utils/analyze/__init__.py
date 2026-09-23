"""Общий Python-фреймворк детерминированного анализа ROM Vector-06C.

Пакет живёт в `utils/analyze/` и не зависит от конкретного ROM. Единственный
канал к эмулятору/отладчику — MCP-сервер `v06c-mcp` (ТЗ §3, §33); официальный
CLI `v06c-asm-export` разрешён как внешний инструмент (ТЗ §24, §33).

Слои:

    mcp_session / capabilities / evidence_cache   доступ и кэш доказательств
    rdb / naming                                  модель RDB и шаблоны имён
    disassembly / coverage / probe                статика и рантайм-доказательства
    rdb_lint / memory_diff / io_signature / ...   детерминированные анализаторы
    seed_rdb / apply_annotations                  детерминированное наполнение RDB
    pipeline / pipeline_state                     стандартный исполнитель и checkpoint
    report_gen                                    сборка отчёта

Python собирает кандидатов и доказательства; семантику назначает AI (ТЗ §2,
§8, §34).
"""
from __future__ import annotations

from analyze.mcp_session import (
    McpError,
    McpSession,
    McpTimeout,
    addr_hex,
    to_addr,
)
from analyze.capabilities import CapabilityProfile, MissingCapability
from analyze.evidence_cache import EvidenceCache
from analyze.rdb import Rdb, RdbObject, RdbWriter

__version__ = "1.0"

__all__ = [
    "McpSession", "McpError", "McpTimeout", "to_addr", "addr_hex",
    "CapabilityProfile", "MissingCapability",
    "EvidenceCache", "Rdb", "RdbObject", "RdbWriter", "__version__",
]

# ROM для тестов и примеров (можно переопределить окружением).
import os

PUTUP_ROM = os.environ.get(
    "V06C_PUTUP_ROM",
    os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                 "roms/redesign/putup/src/putup.rom"),
)
TESTAY_ROM = os.environ.get(
    "V06C_TESTAY_ROM",
    os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                 "roms/redesign/testay/src/TESTAY.ROM"),
)
