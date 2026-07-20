from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator
from django.db.models import Q


class LoginRequiredView(LoginRequiredMixin):
    login_url = 'accounts:login'


def get_pagination_size():
    from apps.settings_app.models import SystemSettings
    return SystemSettings.load().pagination_size


def paginate_queryset(request, queryset, per_page=None):
    per_page = per_page or get_pagination_size()
    paginator = Paginator(queryset, per_page)
    page = request.GET.get('page', 1)
    return paginator.get_page(page)


def apply_search(queryset, search_fields, query):
    if not query:
        return queryset
    q = Q()
    for field in search_fields:
        q |= Q(**{f'{field}__icontains': query})
    return queryset.filter(q)
