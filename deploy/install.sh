#!/usr/bin/env bash
# =============================================================
# install.sh — реєстрація systemd-сервісу express-bot
# Запуск: sudo bash deploy/install.sh
# =============================================================
set -euo pipefail

SERVICE_NAME="express-bot"
SERVICE_SRC="$(dirname "$0")/express-bot.service"
SYSTEMD_DIR="/etc/systemd/system"

# ---- Перевірки -------------------------------------------------------
if [[ $EUID -ne 0 ]]; then
  echo "❌ Запустіть з правами root: sudo bash deploy/install.sh"
  exit 1
fi

if [[ ! -f "$SERVICE_SRC" ]]; then
  echo "❌ Файл не знайдено: $SERVICE_SRC"
  exit 1
fi

# ---- Налаштування шляху (WorkingDirectory) ---------------------------
echo ""
echo "ℹ️  Відкрийте deploy/express-bot.service і перевірте:"
echo "     - User=        (поточний користувач: $(logname 2>/dev/null || echo ubuntu))"
echo "     - WorkingDirectory= (повний шлях до проекту)"
echo "     - ExecStart=    (шлях до python у venv)"
echo ""
read -r -p "Тисніть Enter коли все налаштовано..."

# ---- Інсталяція ----------------------------------------------------------
echo "➤ Копіюємо $SERVICE_SRC → $SYSTEMD_DIR/${SERVICE_NAME}.service"
cp "$SERVICE_SRC" "${SYSTEMD_DIR}/${SERVICE_NAME}.service"

echo "➤ systemctl daemon-reload"
systemctl daemon-reload

echo "➤ systemctl enable ${SERVICE_NAME}"
systemctl enable "${SERVICE_NAME}"

echo "➤ systemctl start ${SERVICE_NAME}"
systemctl start "${SERVICE_NAME}"

echo ""
echo "✅ Сервіс '${SERVICE_NAME}' запущено і додано до автозапуску."
echo ""
echo "📋 Корисні команди:"
echo "   systemctl status ${SERVICE_NAME}"
echo "   journalctl -u ${SERVICE_NAME} -f"
echo "   systemctl restart ${SERVICE_NAME}"
echo "   systemctl stop ${SERVICE_NAME}"
