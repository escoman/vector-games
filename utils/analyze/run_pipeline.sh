#!/usr/bin/env bash
# Стандартный launcher ROM-анализа (ТЗ Standard Pipeline Launcher, 37 §).
#
#   ./utils/analyze/run_pipeline.sh <profile|путь.к.rom> [флаги pipeline…]
#
# Профили (§5, §29): riseout / putup / testay — короткое имя ROM, пути
# к ROM/RDB/config определяются таблицей ниже (§30: добавить новую ROM =
# одна запись в таблице + строка в PROFILES, pipeline.py не трогается).
# Обратная совместимость: если первый аргумент — путь к файлу *.rom/*.ROM/
# *.bin, launcher работает в режиме пути (config не подключается).
#
# Launcher — тонкая обёртка (§6, §34): только выбор профиля, разрешение
# путей, передача аргументов и подготовка PYTHONPATH (§23). Никаких stage
# зависимостей, MCP, RDB-операций и JSON-разбора в shell.
#
# Коды выхода (§26): 0 = код pipeline; ошибки launcher: 1 = usage/python3,
# 2 = неизвестный профиль, 3 = отсутствующий обязательный файл.
#
# §22: запуск через `python3 -m`; пакет analyze лежит в utils/, поэтому
# эквивалент `python3 -m utils.analyze.pipeline` здесь — диспетчер
# `python3 -m analyze.cli pipeline` с PYTHONPATH=utils (прямые imports
# `analyze.*` иначе не работают).
#
# §27: exec заменяет оболочку процессом python — Ctrl-C (SIGINT) уходит
# прямо в pipeline, его controlled shutdown/checkpoint не перехватывается.
set -euo pipefail

# §7—§8: все пути — от корня репозитория, найденного от РАСПОЛОЖЕНИЯ
# скрипта, а не от pwd пользователя.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(dirname "$(dirname "$SCRIPT_DIR")")"

# §5/§29: таблица профилей. Единственное место launcher'а, где живёт
# ROM-специфика (пути), — политика прогона остаётся в pipeline/config.
PROFILES="riseout putup testay"

available_roms() {
    local p
    for p in $PROFILES; do
        echo "  $p"
    done
}

usage() {
    echo "использование: $0 <profile|путь-к-rom> [флаги pipeline…]" >&2
    echo >&2
    echo "Available ROMs:" >&2
    available_roms >&2
}

if [ "$#" -lt 1 ]; then
    usage
    exit 1                                        # §26: usage — 1
fi

# §9: python3 обязан быть.
if ! command -v python3 >/dev/null 2>&1; then
    echo "ERROR: python3 not found" >&2
    exit 1
fi

# §10: pipeline.py обязан быть (launcher его не содержит — только проверяет).
if [ ! -f "$REPO/utils/analyze/pipeline.py" ]; then
    echo "ERROR: pipeline.py not found" >&2
    exit 3
fi

NAME="$1"; shift

ROM=""; CONFIG=""; PROFILE=0
case "$NAME" in
    riseout|putup|testay)
        PROFILE=1
        case "$NAME" in
            riseout) ROM="$REPO/roms/redesign/riseout/src/riseout.rom"
                     CONFIG="$REPO/roms/redesign/riseout/pipeline.json" ;;
            putup)   ROM="$REPO/roms/redesign/putup/src/putup.rom"
                     CONFIG="$REPO/roms/redesign/putup/pipeline.json" ;;
            testay)  ROM="$REPO/roms/redesign/testay/src/TESTAY.ROM"
                     CONFIG="$REPO/roms/redesign/testay/pipeline.json" ;;
        esac
        ;;
    *.rom|*.ROM|*.bin)
        # Режим пути (обратная совместимость): аргумент — явный файл ROM.
        ROM="$NAME"
        NAME="$(basename "${ROM%.*}")"
        case "$NAME" in *[[:upper:]*) NAME="$(echo "$NAME" | tr '[:upper:]' '[:lower:]')" ;; esac
        ;;
    *)
        if [ -f "$NAME" ]; then
            ROM="$NAME"
            NAME="$(basename "${ROM%.*}")"
            case "$NAME" in *[[:upper:]*) NAME="$(echo "$NAME" | tr '[:upper:]' '[:lower:]')" ;; esac
        else
            # §11: неизвестный профиль.
            echo "Unknown ROM profile: $NAME" >&2
            echo >&2
            echo "Available ROMs:" >&2
            available_roms >&2
            exit 2
        fi
        ;;
esac

# §5: RDB — сосед ROM по умолчанию (для TESTAY.ROM → TESTAY.rdb).
RDB="${ROM%.*}.rdb"

# §12: ROM обязателен, regularen и читаем — иначе pipeline не стартует.
if [ ! -f "$ROM" ]; then
    echo "ERROR: ROM not found: $ROM" >&2
    exit 3
fi
if [ ! -r "$ROM" ]; then
    echo "ERROR: ROM is not readable: $ROM" >&2
    exit 3
fi
# §13: отсутствие RDB — НЕ ошибка: свежий образ родит его первым
# debug_save_rdb внутри seed_rdb (riseout-сценарий). Политикой RDB владеет
# pipeline, launcher её не дублирует.
# §14: конфиг профиля обязателен (в режиме пути не подключается).
if [ "$PROFILE" = 1 ] && [ ! -f "$CONFIG" ]; then
    echo "ERROR: pipeline configuration not found: $CONFIG" >&2
    exit 3
fi

# §25: краткая сводка перед запуском — в stderr, чтобы stdout остался
# чистым под JSON-сводку pipeline (--json).
{
    echo "ROM:    $NAME"
    echo "ROM:    $ROM"
    if [ -f "$RDB" ]; then
        echo "RDB:    $RDB"
    else
        echo "RDB:    $RDB (ещё не создан — родится seed_rdb)"
    fi
    if [ "$PROFILE" = 1 ]; then
        echo "CONFIG: $CONFIG"
    fi
    echo "ARGS:   $*"
    echo "Starting pipeline..."
} >&2

ARGS=(--rom "$ROM" --results ".scratch/pipeline/$NAME")
if [ -f "$RDB" ]; then
    ARGS+=(--rdb "$RDB")
fi
if [ "$PROFILE" = 1 ]; then
    ARGS+=(--config "$CONFIG")
fi

# §23: окружение пользователя передаётся как есть; PYTHONPATH добавляется
# потому, что так устроена инфраструктура пакета analyze (§22).
cd "$REPO"
PYTHONPATH="$REPO/utils" exec python3 -m analyze.cli pipeline \
    "${ARGS[@]}" "$@"
