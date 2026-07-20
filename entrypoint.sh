#!/bin/sh
set -e

export DJANGO_SETTINGS_MODULE="${DJANGO_SETTINGS_MODULE:-config.settings.production}"

echo "Waiting for database..."
python <<'PY'
import os
import sys
import time

url = os.environ.get("DATABASE_URL", "")
if not url or url.startswith("sqlite"):
    print("Skipping DB wait.")
    sys.exit(0)

import dj_database_url
import psycopg2

cfg = dj_database_url.parse(url)
connect_kwargs = {
    "dbname": cfg.get("NAME") or "postgres",
    "user": cfg.get("USER"),
    "password": cfg.get("PASSWORD"),
    "host": cfg.get("HOST") or "localhost",
    "port": int(cfg.get("PORT") or 5432),
    "connect_timeout": 3,
}
options = cfg.get("OPTIONS") or {}
if options.get("sslmode"):
    connect_kwargs["sslmode"] = options["sslmode"]
elif os.environ.get("DB_SSL", "").lower() in ("1", "true", "yes"):
    connect_kwargs["sslmode"] = "require"

for attempt in range(40):
    try:
        conn = psycopg2.connect(**connect_kwargs)
        conn.close()
        print("Database is ready.")
        sys.exit(0)
    except Exception as exc:
        print(f"Database not ready ({attempt + 1}/40): {exc}")
        time.sleep(2)

print("Database connection failed.", file=sys.stderr)
sys.exit(1)
PY

# Migrations + static files only for the web (gunicorn) process
case " $* " in
  *" gunicorn "*)
    echo "Running migrations..."
    python manage.py migrate --noinput
    echo "Collecting static files..."
    python manage.py collectstatic --noinput
    ;;
esac

echo "Starting: $*"
exec "$@"
