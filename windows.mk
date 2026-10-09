# windows.mk — виндоус-надстройка к сборке (подключается из config.mk).
#
# Идея: Makefile'ы проектов остаются общими для Linux и Windows, а все
# отличия Windows живут здесь:
#   * под Linux recipe зовёт $(Z88DK)/bin/zcc (sh-скрипт), под Windows —
#     $(Z88DK)/bin/zcc.cmd: тонкую обёртку над zcc.exe, которая чинит PATH
#     для дочерних инструментов (те же .exe лежат рядом в z88dk/bin);
#   * recipe написаны в синтаксисе POSIX-шелла (VAR=..., for/do, cp, stat),
#     поэтому гоняем их через sh.exe из Git for Windows; cmd.exe такой
#     синтаксис не понимает;
#   * часть команд make исполняет напрямую (без шелловых мета-символов),
#     поэтому утилиты Git (cp, mkdir, rm, ls, stat) добавляются в PATH,
#     вместе с utils/winshim — каталогом шиммеров вроде python3 (в Windows
#     python3.exe — заглушка Store, а recipe зовут python3 как на Linux).
#
# Если Git установлен в другом месте: make SH="D:\path\Git\bin\sh.exe"
# (лучше без пробелов — make плохо переносит пробелы в SHELL; короткое
# имя PROGRA~1 совпадает с "Program Files").

ZCC := $(Z88DK)/bin/zcc.cmd
# то же для чистого z80asm (redesign/*, tests/clrs зовут его напрямую)
Z80ASM := $(Z88DK)/bin/z88dk-z80asm.exe

# Python-скрипты (utils/*.py) печатают в консоль русские строки и пишут
# комментарии в .inc/.c — по умолчанию encoding в Windows это cp1251,
# из-за чего файлы расходились бы с Linux-версией (UTF-8). UTF-8-режим
# Python делает utf-8 и stdout, и open() без явного encoding.
export PYTHONUTF8 := 1

# Корень проекта (каталог этого windows.mk) — для пути к utils/winshim.
_ROOT_DIR := $(dir $(abspath $(lastword $(MAKEFILE_LIST))))

SH ?= $(firstword $(wildcard C:/PROGRA~1/Git/bin/sh.exe C:/PROGRA~2/Git/bin/sh.exe))
ifneq ($(SH),)
SHELL := $(SH)
export PATH := $(dir $(SH));$(dir $(SH))../usr/bin;$(_ROOT_DIR)utils/winshim;$(PATH)
else
$(warning sh.exe не найден — укажите make SH=C:/.../Git/bin/sh.exe, POSIX-recipe не соберутся)
endif
