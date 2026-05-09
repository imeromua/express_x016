#!/usr/bin/env bash
# =============================================================
# update.sh — оновлення бота (з git pull)
# Запуск: sudo bash deploy/update.sh
# =============================================================
set -euo pipefail

APP_DIR="/opt/express_x016"
SERVICE_NAME="express-bot"

cd "${APP_DIR}"

echo "➤ git pull..."
git pull origin main

echo "➤ Перезапуск сервісу (ребілд Docker)..."
systemctl reload-or-restart "${SERVICE_NAME}"

echo "✅ Оновлення завершено."
echo ""
docker compose ps
