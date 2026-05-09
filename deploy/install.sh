#!/usr/bin/env bash
# =============================================================
# install.sh — установка express-bot як systemd-сервісу
# Запуск: sudo bash deploy/install.sh
# =============================================================
set -euo pipefail

APP_DIR="/opt/express_x016"
SERVICE_NAME="express-bot"
SERVICE_FILE="deploy/express-bot.service"
SYSTEMD_DIR="/etc/systemd/system"

echo "➤ Перевіряємо Docker..."
if ! command -v docker &>/dev/null; then
  echo "❌ Docker не знайдено. Встановіть: https://docs.docker.com/engine/install/"
  exit 1
fi

echo "➤ Створюємо папку ${APP_DIR}..."
mkdir -p "${APP_DIR}"

echo "➤ Копіюємо файли проекту в ${APP_DIR}..."
# rsync зберігає структуру і не стирає .env
rsync -av --exclude='.git' --exclude='__pycache__' \
      --exclude='*.pyc' --exclude='.env' \
      ./ "${APP_DIR}/"

echo "➤ Встановлюємо systemd-сервіс..."
cp "${APP_DIR}/${SERVICE_FILE}" "${SYSTEMD_DIR}/${SERVICE_NAME}.service"

systemctl daemon-reload
systemctl enable "${SERVICE_NAME}"
systemctl start "${SERVICE_NAME}"

echo ""
echo "✅ Готово! Сервіс '${SERVICE_NAME}' запущено."
echo ""
echo "📋 Корисні команди:"
echo "  systemctl status ${SERVICE_NAME}       # статус"
echo "  journalctl -u ${SERVICE_NAME} -f        # логи в реальному часі"
echo "  systemctl restart ${SERVICE_NAME}       # перезапуск"
echo "  systemctl stop ${SERVICE_NAME}          # зупинка"
