#!/usr/bin/env python3
"""Служебный бутстрап тестов: кладёт корень `utils/` в sys.path.

Модули пакета импортируются как `analyze.*`, поэтому тесты обязаны видеть
каталог `utils/`. Этот модуль подключается первым в каждом файле тестов.

Плюс два обязательных для E2E помощника (решение пользователя по ТЗ §25:
интеграционные прогоны никогда не трогают tracked-файлы): `copy_fixture`
копирует rom/rdb во временный каталог, `git_clean` проверяет, что дерево
репозитория после прогонов не изменилось.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile

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
RISEOUT_ROM = os.path.join(REPO, "roms/redesign/riseout/src/riseout.rom")


def make_tmp(prefix="v06c-e2e-"):
    """Временный каталог прогона (удаляет сам процесс tests через rmtree)."""
    return tempfile.mkdtemp(prefix=prefix)


def copy_fixture(rom, rdb=None, dest_dir=None):
    """Скопировать фикстуру во временный каталог → (rom, rdb|None, tmp).

    E2E-прогоны с мутациями (apply) обязаны работать только по копиям:
    tracked `putup.rdb`/`TESTAY.rdb`/`clrs.rdb` менять нельзя. `rdb` — путь
    исходного .rdb (может отсутствовать: свежий образ вроде riseout, где
    RDB родится первым debug_save_rdb).
    """
    tmp = dest_dir or make_tmp()
    dst_rom = os.path.join(tmp, os.path.basename(rom))
    shutil.copyfile(rom, dst_rom)
    dst_rdb = None
    if rdb:
        dst_rdb = os.path.join(tmp, os.path.basename(rdb))
        shutil.copyfile(rdb, dst_rdb)
    return dst_rom, dst_rdb, tmp


def git_clean(*paths):
    """True, если в git нет ИЗМЕНЕНИЙ по указанным путям (acceptance §56).

    Только diff по tracked-файлам: untracked-артефакты (вроде riseout.rom,
    которого сознательно нет в git) сюда не попадают.
    """
    result = subprocess.Popen(
        ["git", "diff", "--name-only", "--"] + list(paths),
        cwd=REPO, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out = result.communicate()[0].decode("utf-8", "replace").strip()
    return not out
