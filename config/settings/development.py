from .base import *
from decouple import config
import dj_database_url

DEBUG = config('DEBUG', default=True, cast=bool)

DATABASES = {
    'default': dj_database_url.config(
        default=config('DATABASE_URL', default='sqlite:///db.sqlite3'),
        conn_max_age=600,
    )
}

EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
