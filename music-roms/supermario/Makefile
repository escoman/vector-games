# Makefile — сборка supermario.rom для Вектора-06Ц.
#
# Данные треков и конфигурация меню — в rom.json.
# Общие правила сборки — в ../soundtracks/soundtrack.mk.
#
# make          — собрать supermario.rom;
# make clean    — убрать все артефакты (включая сгенерированный main.c);
# make deploy   — собрать и положить ROM в папку ROMS эмулятора PPSSPP;
# make full     — clean + deploy.

TARGET = supermario.rom
SONGS  = track_0 track_1 track_2 track_3 track_5 track_6 track_7 \
         track_8 track_9 track_10 track_11 track_13 track_17

include ../soundtracks/soundtrack.mk
