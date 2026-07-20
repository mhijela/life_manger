"""Run Jawwal web login and print sanitized result."""
import json
import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django

django.setup()

from apps.finance.jawwal_pay_service import JawwalPayService

USERNAME = sys.argv[1] if len(sys.argv) > 1 else ''
PASSWORD = sys.argv[2] if len(sys.argv) > 2 else ''

service = JawwalPayService()
result = service.login(USERNAME, PASSWORD, force=True)

def redact(obj):
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            if k in ('password',):
                out[k] = '********'
            else:
                out[k] = redact(v)
        return out
    if isinstance(obj, list):
        return [redact(x) for x in obj]
    return obj

print(json.dumps(redact(result), ensure_ascii=False, indent=2))
