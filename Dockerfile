FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=8000

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc curl postgresql-client \
    libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf-2.0-0 \
    libffi-dev shared-mime-info \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN chmod +x /app/entrypoint.sh /app/healthcheck.sh \
    && mkdir -p /app/media /app/staticfiles

EXPOSE 8000

# Do not put ${VAR} inline here — Coolify injects ARGs and breaks Dockerfile parsing.
HEALTHCHECK --interval=15s --timeout=5s --start-period=20s --retries=5 \
    CMD ["/app/healthcheck.sh"]

ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["sh", "-c", "exec gunicorn config.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers 3 --timeout 120"]
