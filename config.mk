# config.mk — общие настройки сборки z88dk для Вектора-06Ц.
# Подключается из подпроектов: include ../../../config.mk
#
# Путь к z88dk можно переопределить:
#   make Z88DK=/other/path

Z88DK ?= /home/alexey/z88dk
ifeq ($(wildcard $(Z88DK)),)
$(error Z88DK not found: $(Z88DK). Set Z88DK=/path/to/z88dk)
endif

ZCC          = $(Z88DK)/bin/zcc
ZCCCFG      := $(Z88DK)/lib/config

# PROJECT_ROOT — корень проекта (для include finally.mk в конце Makefile).
# firstword MAKEFILE_LIST = верхний Makefile (GNU Make guarantee).
# config.mk всегда на глубине 0 или 1 (в корне или в config/), поэтому
# abspath(.../../../..) нормализует путь к корню проекта.
_PROJECT_DIR := $(dir $(abspath $(firstword $(MAKEFILE_LIST))))
PROJECT_ROOT ?= $(abspath $(_PROJECT_DIR)/../../..)/
LIB          = $(PROJECT_ROOT)lib
