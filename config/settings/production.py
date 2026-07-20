from .base import *
from decouple import config
import dj_database_url

DEBUG = config('DEBUG', default=False, cast=bool)

ALLOWED_HOSTS = [
    h.strip() for h in config('ALLOWED_HOSTS', default='localhost').split(',') if h.strip()
]

# Coolify / reverse-proxy HTTPS
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
USE_X_FORWARDED_HOST = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

_csrf_origins = config('CSRF_TRUSTED_ORIGINS', default='').strip()
if _csrf_origins:
    CSRF_TRUSTED_ORIGINS = [o.strip() for o in _csrf_origins.split(',') if o.strip()]
else:
    CSRF_TRUSTED_ORIGINS = [
        f'https://{h}' for h in ALLOWED_HOSTS
        if h not in ('*', 'localhost', '127.0.0.1') and not h.startswith('.')
    ]

_database_url = config('DATABASE_URL')
DATABASES = {
    'default': dj_database_url.parse(
        _database_url,
        conn_max_age=600,
        ssl_require=config('DB_SSL', default=False, cast=bool),
    )
}

# Persist uploaded files (logos, backups) on Coolify volume
STORAGES = {
    'default': {
        'BACKEND': 'django.core.files.storage.FileSystemStorage',
    },
    'staticfiles': {
        'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage',
    },
}
