from django.shortcuts import redirect
from django.urls import reverse
from django.db.utils import OperationalError, ProgrammingError

from .models import User


class InitialSetupMiddleware:
    """Redirect all traffic to first-time admin setup until a superuser exists."""

    EXEMPT_PREFIXES = (
        '/static/',
        '/media/',
        '/healthz/',
        '/accounts/setup/',
    )

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path
        if any(path.startswith(prefix) for prefix in self.EXEMPT_PREFIXES):
            return self.get_response(request)

        try:
            needs_setup = not User.objects.filter(is_superuser=True).exists()
        except (OperationalError, ProgrammingError):
            return self.get_response(request)

        if needs_setup:
            return redirect(reverse('accounts:setup'))

        return self.get_response(request)
