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
node --test tests\test_site_js.cjs   # переключатель языка; нужен только Node, без npm-зависимостей
```

Файл теста указывать обязательно: `node --test tests` попытается выполнить и `.py`-файлы.

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
debug, выбор языка, тексты и сами файлы деплоя. Healthcheck зашит в образ (`HEALTHCHECK` в
Dockerfile) и ходит на `/health` раз в 30 секунд.

## Языки

Все тексты сайта — только в `translations/en.json`, `uk.json`, `ru.json` (разделы `common`, `home`,
`privacy`, `terms`; у трёх файлов одинаковые ключи — это проверяет тест). Первый язык страницы
выбирает сервер, поэтому ничего не «перескакивает» после загрузки:

1. язык, выбранный вручную, — cookie `polyglot_lang` (год, `SameSite=Lax`);
2. иначе страна публичного IP из локальной GeoIP-базы: Украина → UA, Россия → RU, другие страны → EN;
3. если страна неизвестна, первый язык браузера из `Accept-Language`: `uk*` → UA, `ru*` → RU,
   всё остальное → EN.

Переключатель меняет текст сразу, без перезагрузки, из тех же JSON и записывает cookie. Ответы
несут `Vary: Accept-Language, Cookie`, `Cache-Control: private` и `Content-Language`. Внешних
GeoIP-сервисов и HTTP-запросов нет.

Для GeoIP перед production нужно отдельно получить актуальную базу `GeoLite2-Country.mmdb`,
смонтировать её в контейнер и задать `GEOIP_COUNTRY_DB`. База лицензируется и обновляется MaxMind,
поэтому в репозиторий не входит. `TRUSTED_PROXY_CIDRS` должен содержать фактический адрес или сеть
Caddy. Только от такого peer приложение читает `X-Forwarded-For`; произвольный посетитель не может
подменить клиентский IP. Если база отсутствует, повреждена, IP локальный/private или адреса в ней
нет, сайт безопасно переходит к `Accept-Language`.

### Точная настройка GeoIP перед production

Схема: Internet → Caddy container → Website container. GeoIP необязателен для запуска:
без переменной, без файла и с повреждённой MMDB приложение импортируется, страницы и `/health`
работают. При этом страна не определяется и используется описанный выше языковой fallback.

- Файл: актуальная **GeoLite2-Country.mmdb**, формат MMDB, не CSV и не архив.
- Env в контейнере website: `GEOIP_COUNTRY_DB=/app/data/GeoLite2-Country.mmdb`.
  Путь не зашит в код: он целиком задаётся этой переменной.
- Dependency: `maxminddb==3.2.0` уже включена в `requirements.txt`; Pillow для production не нужен.
- Dockerfile менять не требуется: он уже устанавливает `requirements.txt`. При будущем deploy
  потребуется пересобрать image website, чтобы установить новый reader.
- Файл подключается read-only; пользователь контейнера UID 10001 должен иметь право чтения.
  `.mmdb` исключена из Git и Docker build context. База не скачивается приложением автоматически.
- После обновления/добавления базы перезапустить website workers: reader и результаты lookup
  кешируются на время жизни процесса. Организовать регулярное обновление базы отдельно.

Фрагмент для включения в **существующий** `compose.production.yml` (не отдельный compose-файл):

```yaml
services:
  website:
    environment:
      GEOIP_COUNTRY_DB: /app/data/GeoLite2-Country.mmdb
      TRUSTED_PROXY_CIDRS: "${WEBSITE_CADDY_PROXY_CIDR:?Set the exact Caddy address as /32 or /128}"
    volumes:
      - type: bind
        source: ./geoip/GeoLite2-Country.mmdb
        target: /app/data/GeoLite2-Country.mmdb
        read_only: true
        bind:
          create_host_path: false
```

Если compose находится в `/opt/polyglot/compose.production.yml`, source выше означает
`/opt/polyglot/geoip/GeoLite2-Country.mmdb`. `create_host_path: false` предотвращает создание
каталога вместо отсутствующего файла. Для запуска **без** GeoIP убрать этот mount и оставить
`GEOIP_COUNTRY_DB` пустой: сам Docker с обязательным отсутствующим bind mount контейнер не запустит,
хотя приложение без базы работает.

### TRUSTED_PROXY_CIDRS и Caddy

Переменная содержит IP/CIDR **непосредственных доверенных прокси**, а не стран и не посетителей.
По умолчанию список пуст. Для Caddy в отдельном контейнере `127.0.0.1` не подходит.
Предпочтителен стабильный адрес Caddy в общей сети, например `172.30.0.2/32`, **только если именно
этот адрес закреплён за Caddy и виден website как REMOTE_ADDR**. Это пример, не обнаруженный адрес
текущего VPS. Для IPv6 использовать фактический `/128`. Не задавать `0.0.0.0/0` или все private-сети.
Широкая Docker subnet доверяет всем контейнерам в ней; для этой схемы нужен точный адрес Caddy.

Алгоритм приложения:

1. Прочитать socket peer из `REMOTE_ADDR`; обычный HTTP-заголовок не меняет его.
2. Если peer не входит в список доверия, полностью игнорировать `X-Forwarded-For`.
3. Если входит, пройти цепочку `X-Forwarded-For` справа налево, пропустить доверенные proxy hops
   и взять первый недоверенный адрес. Не доверять самому левому адресу без проверки цепочки.
4. При повреждённой цепочке использовать direct peer и языковой fallback для private IP.

Для Internet → Caddy без CDN стандартный `reverse_proxy website:8080` формирует forwarded headers
и игнорирует присланные клиентом значения этих заголовков. Не включать доверие ко всему Internet
в самом Caddy. Website должен быть доступен Caddy по общей Docker-сети; не публиковать его порт
на публичном интерфейсе. При будущем изменении сети обновить allow-list и перезапустить website.

Фактические compose/Caddyfile и IP Caddy на VPS в этом review не проверялись: SSH/deploy не выполнялись.
Перед deploy подтвердить сеть и peer IP, доступность MMDB для UID 10001 и отсутствие подмены IP
при отправке внешним клиентом собственного `X-Forwarded-For`.

Официальные источники: [Caddy forwarded headers](https://caddyserver.com/docs/caddyfile/directives/reverse_proxy#headers),
[Docker bind volumes](https://docs.docker.com/reference/compose-file/services/#volumes),
[GeoLite database access](https://dev.maxmind.com/geoip/geolite2-free-geolocation-data/).

## Логотип и иконки

Два исходника владельца, оба лежат нетронутыми:

- `brand/own_book.png` — герб (сова, книга, звезда, колосья на щите) → логотип в шапке;
- `brand/icon_own.png` — голова совы на тёмно-синей плитке → favicon и иконки приложений.

Всё остальное собирается из них скриптом, который ничего не дорисовывает:

```powershell
uv run --no-project --with pillow python brand/make_icons.py
```

Скрипт обрезает пустой фон вокруг рисунка, масштабирует, скругляет
углы и пишет `static/icons/`: `polyglot-owl-logo.png` (шапка),
`favicon.ico` (16/32/48), `favicon-16x16.png`, `favicon-32x32.png`, `apple-touch-icon.png`,
`android-chrome-192x192.png`, `android-chrome-512x512.png`. Pillow нужен только для сборки иконок;
в `requirements.txt` его нет, в production он не ставится. Папка `brand/` не попадает в образ
(`.dockerignore`).

После замены иконок поднять `FAVICON_VERSION` в `main.py` и тот же `?v=` в `site.webmanifest`:
браузеры держат favicon в кеше дольше всего остального. Контрольные суммы обоих исходников
зафиксированы в тесте — при замене артворка их нужно обновить тем же коммитом.

## Что проверено, а что нет

Проверено: все страницы и статика отдаются (тесты Flask), debug выключен при импорте gunicorn'ом,
в образ не попадают `.env` и `.git`, зависимости зафиксированы, контейнер не root.
**Не проверено:** `docker build` и запуск контейнера — на машине разработки Docker не установлен.
