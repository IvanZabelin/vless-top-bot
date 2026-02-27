# Архитектура vless-top-bot

## 1) Цели
- Проверять список `vless://` узлов из подписки.
- Отбирать рабочие узлы.
- Сортировать по минимальному latency.
- Отдавать ТОП через Telegram-бота.

## 2) Поток данных
1. Пользователь отправляет команду боту (`/check` или кнопку).
2. Bot layer передаёт задачу в `services.check_service`.
3. Service:
   - получает subscription URL пользователя,
   - скачивает/декодирует payload,
   - парсит VLESS ссылки,
   - запускает асинхронные TCP-проверки,
   - сортирует/формирует ТОП.
4. Результат сохраняется в storage.
5. Бот отправляет сводку + при необходимости файл с топ-линками.

## 3) Модули

### `core/subscription.py`
- fetch_subscription(url)
- maybe_base64_decode(text)

### `core/vless_parser.py`
- parse_vless_lines(text) -> list[Node]

### `core/latency_checker.py`
- tcp_latency_once(host, port, timeout)
- measure_node(node, attempts, timeout, sem)

### `core/ranking.py`
- rank_nodes(results, top_n)
- render_human_report(...)

### `services/check_service.py`
- run_check(user_id, subscription_url, params)
- объединяет все шаги, возвращает DTO для бота

### `bot/handlers.py`
- `/start`
- `/setsub <url>`
- `/check`
- `/top <N>`
- кнопки: «Быстрая проверка», «Точная проверка», «Скачать TOP как файл»

### `adapters/storage`
- `user_repo.py` — хранение подписки пользователя
- `result_repo.py` — хранение последних проверок

## 4) Конфиг
Через `.env`:
- `TELEGRAM_BOT_TOKEN`
- `DEFAULT_TOP=5`
- `DEFAULT_ATTEMPTS=3`
- `DEFAULT_TIMEOUT=2.0`
- `DEFAULT_CONCURRENCY=50`
- `DATA_DIR=./data`

## 5) Режимы
- **Быстрый**: attempts=1, timeout=1.5
- **Точный**: attempts=3..5, timeout=2.0..3.0

## 6) Следующий этап
Реализовать код в `core/` и `services/` на основе текущего прототипа в `scripts/prototype_latency_check.py`.
