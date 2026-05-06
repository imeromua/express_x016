# Epicentr-Express Samar — Корпоративний Бот-Менеджер

Асинхронний Telegram-бот для автоматизації онбордингу, модерації та видачі графіків роботи.

## Технологічний стек

- Python 3.11+
- aiogram 3.x
- PostgreSQL
- Redis
- APScheduler
- Docker / Docker Compose

## Структура проєкту

```
app/
├── handlers/          # Telegram-хендлери (transport layer)
│   ├── admin/
│   ├── group/
│   └── user/
├── services/          # Бізнес-логіка
├── repositories/      # Доступ до БД
├── models/            # ORM-моделі
├── middlewares/       # Cross-cutting concerns
├── integrations/      # VirusTotal, xlsx parser
├── utils/             # Форматери, хелпери
├── keyboards/         # Telegram InlineKeyboard/ReplyKeyboard
├── states/            # FSM States
├── config.py          # Конфіг з .env
└── main.py            # Точка входу
migrations/            # Alembic міграції
tests/
docker-compose.yml
pyproject.toml
.env.example
```

## Запуск

```bash
cp .env.example .env
# Заповни .env своїми значеннями
docker compose up --build
```

## Розробка без Docker

```bash
pip install -e .[dev]
alembic upgrade head
python -m app.main
```
