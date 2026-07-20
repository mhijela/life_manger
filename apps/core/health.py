from django.http import HttpResponse


def healthz(request):
    """Liveness probe for Coolify / Docker — always 200, no DB required."""
    return HttpResponse('ok', content_type='text/plain', status=200)
