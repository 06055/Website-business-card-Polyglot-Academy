# Деплой сайта-визитки Polyglot Academy

Flask + gunicorn в контейнере. Ни базы, ни авторизации, ни загрузки файлов, ни секретов: контейнер
одноразовый, состояния он не хранит и может работать с файловой системой только на чтение.

Часть общего стека на VPS (Debian 13, Docker Compose): сервис `website` в
`/opt/polyglot/compose.production.yml`. Общая инструкция — `academy/DEPLOYMENT.md`.

## Локально

```powershell
python -m venv venv
venv\Scripts\pip install -r requirements.txt
venv\Scripts\python main.py          # http://127.0.0.1:5000
venv\Scripts\python -m unittest discover -s tests
```

`HOST`, `PORT`, `FLASK_DEBUG` — только для этого режима (см. `.env.example`). В production их
задаёт compose, а debug выключен всегда: gunicorn импортирует `app`, и ветка `if __name__ ==
"__main__"` не выполняется.

## В составе стека

```bash
cd /opt/polyglot
docker compose build website
docker compose up -d website
curl -s localhost:8080/health        # {"status":"ok"}
docker compose logs -f --tail=100 website
docker compose restart website
```

Порт 8080 слушает только `127.0.0.1` сервера. Наружу сайт попадёт позже через Caddy
(`docker compose --profile proxy up -d caddy`, домен в `WEBSITE_DOMAIN`).

## Отдельно, без остального стека

```bash
docker build -t polyglot-website .
docker run -d --name polyglot-website -p 127.0.0.1:8080:8080 --restart unless-stopped polyglot-website
docker logs -f polyglot-website
docker stop polyglot-website && docker rm polyglot-website
```

## Обновление и откат

```bash
cd /opt/polyglot/website && git pull
cd /opt/polyglot && docker compose build website && docker compose up -d website
```

Откат: `git checkout <коммит>` и та же пара команд. Бэкапить нечего — весь сайт лежит в git.

## Страницы и проверки

| Адрес | Что это |
|---|---|
| `/` | лендинг (`templates/polyglot_academy.html`) |
| `/privacy` | политика конфиденциальности |
| `/terms` | условия использования |
| `/health` | `{"status":"ok"}` для Docker healthcheck и reverse proxy |
| `/static/...` | CSS и картинки; позже их может раздавать Caddy напрямую |

`python -m unittest discover -s tests` проверяет все страницы, health, статику, 404, отключённый
debug и сами файлы деплоя. Healthcheck зашит в образ (`HEALTHCHECK` в Dockerfile) и ходит на
`/health` раз в 30 секунд.

## Что проверено, а что нет

Проверено: все страницы и статика отдаются (тесты Flask), debug выключен при импорте gunicorn'ом,
в образ не попадают `.env` и `.git`, зависимости зафиксированы, контейнер не root.
**Не проверено:** `docker build` и запуск контейнера — на машине разработки Docker не установлен.
