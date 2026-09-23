#!/usr/bin/env bash
# Запуск конвейера анализа riseout с профильным pipeline.json (рядом с этим
# скриптом). Тонкая обёртка: всю работу делает utils/analyze/run_pipeline.sh
# (профиль riseout сам подключает pipeline.json); сюда лишь прокидываются
# флаги pipeline (--dry-run / --resume / --clean …).
#
#   ./pipeline.sh              # полный прогон (apply по умолчанию)
#   ./pipeline.sh --dry-run    # строго read-only
#   ./pipeline.sh --clean      # стереть чекпоинт и начать заново
#   ./pipeline.sh --resume     # продолжить с чекпоинта
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(dirname "$(dirname "$(dirname "$SCRIPT_DIR")")")"   # roms/redesign/riseout → корень

exec "$REPO/utils/analyze/run_pipeline.sh" riseout "$@"
