# Polyglot Academy — сайт-визитка

Одностраничный сайт академии на Flask: лендинг, политика конфиденциальности, условия использования.
Переключение языков (EN/RU/UK/DE) — на стороне браузера, без запросов к серверу.

Ни базы данных, ни авторизации, ни загрузки файлов, ни секретов. Весь контент лежит в репозитории.

```
main.py                      маршруты: /  /privacy  /terms  /health
templates/                   страницы (Jinja2)
static/polyglot_academy_style.css
static/images/               логотип и фон
tests/test_site.py           тесты: страницы, статика, health, 404, файлы деплоя
Dockerfile, .dockerignore    production-образ (gunicorn, non-root, healthcheck)
DEPLOYMENT.md                как это разворачивается на VPS
```

## Запуск локально

```powershell
python -m venv venv
venv\Scripts\pip install -r requirements.txt
venv\Scripts\python main.py
```

http://127.0.0.1:5000 — лендинг. Настройки `HOST`, `PORT`, `FLASK_DEBUG` (см. `.env.example`)
нужны только здесь: в production gunicorn импортирует `app`, и debug выключен всегда.

## Тесты

```powershell
venv\Scripts\python -m unittest discover -s tests -v
```

## Production

Контейнер в общем стеке на VPS (сервис `website`), порт 8080 только на `127.0.0.1`, снаружи —
позже через Caddy. Подробности: [DEPLOYMENT.md](DEPLOYMENT.md).
