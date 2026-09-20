# Polyglot Academy - business-card website (Flask + gunicorn).
# Built on the server: docker compose build website. Nothing here is Windows- or host-specific.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8080 \
    WEB_CONCURRENCY=2

WORKDIR /app

# Dependencies first: this layer is rebuilt only when requirements.txt changes.
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# No secrets, no writable state: the container may run read-only.
RUN useradd --create-home --uid 10001 polyglot
USER polyglot

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import os,urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:'+os.environ.get('PORT','8080')+'/health', timeout=4).status==200 else 1)"

# gunicorn is PID 1 and handles SIGTERM itself: `docker compose stop` is graceful.
CMD ["sh", "-c", "exec gunicorn --bind 0.0.0.0:${PORT} --workers ${WEB_CONCURRENCY} --access-logfile - --error-logfile - --graceful-timeout 20 main:app"]
