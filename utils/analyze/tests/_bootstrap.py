#!/usr/bin/env python3
"""Служебный бутстрап тестов: кладёт корень `utils/` в sys.path.

Модули пакета импортируются как `analyze.*`, поэтому тесты обязаны видеть
каталог `utils/`. Этот модуль подключается первым в каждом файле тестов.
"""
from __future__ import annotations

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.dirname(HERE)                 # utils/analyze
UTILS = os.path.dirname(PKG)                # utils
REPO = os.path.dirname(UTILS)               # корень проекта (над utils/)
for path in (UTILS,):
    if path not in sys.path:
        sys.path.insert(0, path)

# Удобные пути к ROM/RDB для интеграционных тестов.
PUTUP_ROM = os.path.join(REPO, "roms/redesign/putup/src/putup.rom")
PUTUP_RDB = os.path.join(REPO, "roms/redesign/putup/src/putup.rdb")
PUTUP_SPEC = os.path.join(REPO, "roms/redesign/putup/tools/music_spec.json")
TESTAY_ROM = os.path.join(REPO, "roms/redesign/testay/src/TESTAY.ROM")
TESTAY_RDB = os.path.join(REPO, "roms/redesign/testay/src/TESTAY.rdb")
MCP_SERVER = "/home/alexey/Projects/vector-debugger/debugger/build/v06c-mcp"
