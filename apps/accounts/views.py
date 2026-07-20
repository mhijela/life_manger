from django.contrib.auth import login
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from .forms import InitialSetupForm
from .models import User


def needs_initial_setup():
    return not User.objects.filter(is_superuser=True).exists()


@require_http_methods(['GET', 'POST'])
def setup_view(request):
    if not needs_initial_setup():
        return redirect('accounts:login')

    if request.method == 'POST':
        form = InitialSetupForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('dashboard:index')
    else:
        form = InitialSetupForm()

    return render(request, 'accounts/setup.html', {'form': form})
