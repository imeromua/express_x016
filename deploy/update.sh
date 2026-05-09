#!/usr/bin/env bash
# =============================================================
# update.sh — оновлення бота на сервері
# Запуск: sudo bash deploy/update.sh
# =============================================================
set -euo pipefail

SERVICE_NAME="express-bot"
# Щлях до проекту (визначається автоматично відносно цього скрипту)
APP_DIR="$(cd "$(dirname "$0")/.." && pwd)"

cd "${APP_DIR}"

echo "➤ git pull..."
git pull origin main

echo "➤ Оновлення залежностей..."
.venv/bin/pip install -q -r requirements.txt

echo "➤ Перезапуск сервісу..."
systemctl restart "${SERVICE_NAME}"

echo "✅ Оновлення завершено."
echo ""
systemctl status "${SERVICE_NAME}" --no-pager -l
