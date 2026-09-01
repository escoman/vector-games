# config.mk — общие настройки сборки z88dk для Вектора-06Ц.
# Подключается из подпроектов: include ../../config.mk
#
# Путь к z88dk и каталог деплоя можно переопределить:
#   make Z88DK=/other/path PPSSPP_ROMS=/other/roms

Z88DK       ?= /home/alexey/z88dk
ZCC          = $(Z88DK)/bin/zcc
ZCCCFG      := $(Z88DK)/lib/config
PPSSPP_ROMS ?= /home/alexey/snap/ppsspp-emu/common/.config/ppsspp/PSP/GAME/VECTOR06C/ROMS
