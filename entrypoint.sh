#!/bin/sh
set -e

echo "Waiting for database..."
python <<'PY'
import os
import sys
import time
from urllib.parse import urlparse

url = os.environ.get("DATABASE_URL", "")
if not url or url.startswith("sqlite"):
    print("Skipping DB wait.")
    sys.exit(0)

import psycopg2

parsed = urlparse(url)
dbname = (parsed.path or "/").lstrip("/") or "postgres"

for attempt in range(30):
    try:
        conn = psycopg2.connect(
            dbname=dbname,
            user=parsed.username,
            password=parsed.password,
            host=parsed.hostname or "localhost",
            port=parsed.port or 5432,
            connect_timeout=3,
        )
        conn.close()
        print("Database is ready.")
        sys.exit(0)
    except Exception as exc:
        print(f"Database not ready ({attempt + 1}/30): {exc}")
        time.sleep(2)

print("Database connection failed.", file=sys.stderr)
sys.exit(1)
PY

# Migrations + static files only for the web process
case " $* " in
  *" gunicorn "*|*" manage.py runserver "*)
    echo "Running migrations..."
    python manage.py migrate --noinput
    echo "Collecting static files..."
    python manage.py collectstatic --noinput
    ;;
esac

echo "Starting: $*"
exec "$@"
