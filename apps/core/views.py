from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render
from django.urls import reverse

from .search import global_search


@login_required
def global_search_view(request):
    query = request.GET.get('q', '').strip()
    limit = 8 if request.GET.get('format') == 'json' else 10
    results = global_search(query, limit_per_group=limit)

    if request.GET.get('format') == 'json':
        flat = []
        for group in results['groups']:
            for item in group['items']:
                flat.append(item)
        return JsonResponse({
            'query': results['query'],
            'total': results['total'],
            'results': flat[:15],
            'more_url': reverse('core:search') + f'?q={query}' if query else '',
        })

    return render(request, 'search/results.html', {
        'query': query,
        'groups': results['groups'],
        'total': results['total'],
    })
