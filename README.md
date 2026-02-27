# vless-top-bot

Телеграм-бот + локальный сервис, который:
- принимает VLESS-подписку,
- проверяет рабочие узлы,
- ранжирует по latency,
- отдаёт пользователю ТОП серверов в удобном виде.

## Для кого
Пользователь разворачивает сервис у себя (ПК/домашний сервер), указывает `TELEGRAM_BOT_TOKEN` и пользуется через Telegram.

## Архитектура (кратко)
- `src/vless_top_bot/bot` — Telegram handlers / команды
- `src/vless_top_bot/core` — доменная логика (парсинг VLESS, проверка узлов, ранжирование)
- `src/vless_top_bot/services` — orchestration/use-cases (запуск проверки по запросу пользователя)
- `src/vless_top_bot/adapters/storage` — хранение настроек/результатов (JSON/SQLite)
- `src/vless_top_bot/config` — загрузка конфигурации из env
- `scripts/` — утилиты и прототипы
- `docs/` — архитектура и сценарии

Подробно: `docs/ARCHITECTURE.md`

## Быстрый старт
```bash
cd /home/theza/dev/vless-top-bot
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
cp .env.example .env
# впиши TELEGRAM_BOT_TOKEN в .env
set -a; source .env; set +a
python -m vless_top_bot
```

Команды в боте:
- `/setsub <url>`
- `/check`

## План разработки
1. Добавить `/top N` и профили проверки (быстрый/точный).
2. Добавить экспорт результатов файлом.
3. Добавить SQLite и историю проверок.
4. Упаковать systemd unit без ручной настройки.
