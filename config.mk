# config.mk — общие настройки сборки z88dk для Вектора-06Ц.
# Подключается из подпроектов: include ../../../config.mk
#
# Путь к z88dk можно переопределить:
#   make Z88DK=/other/path

# Локальный тулчейн: <корень проекта>/z88dk (config.mk лежит в корне).
_Z88DK_LOCAL := $(abspath $(dir $(abspath $(lastword $(MAKEFILE_LIST))))z88dk)
Z88DK ?= $(_Z88DK_LOCAL)
ifeq ($(wildcard $(Z88DK)),)
$(error Z88DK not found: $(Z88DK). Set Z88DK=/path/to/z88dk)
endif

ZCC          = $(Z88DK)/bin/zcc
# чистый ассемблер — проектам, которые собирают без zcc (tests/clrs, redesign)
Z80ASM       = $(Z88DK)/bin/z80asm
ZCCCFG      := $(Z88DK)/lib/config

# Под Windows в z88dk/bin рядом с Linux-бинарями лежат .exe-версии тех же
# инструментов; все виндоус-особенности — в windows.mk
ifeq ($(OS),Windows_NT)
include $(dir $(abspath $(lastword $(MAKEFILE_LIST))))windows.mk
endif

# PROJECT_ROOT — корень проекта (для include finally.mk в конце Makefile).
# firstword MAKEFILE_LIST = верхний Makefile (GNU Make guarantee).
# config.mk всегда на глубине 0 или 1 (в корне или в config/), поэтому
# abspath(.../../../..) нормализует путь к корню проекта.
_PROJECT_DIR := $(dir $(abspath $(firstword $(MAKEFILE_LIST))))
PROJECT_ROOT ?= $(abspath $(_PROJECT_DIR)/../../..)/
LIB          = $(PROJECT_ROOT)lib
