from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from django.views.static import serve
from apps.core.health import healthz

urlpatterns = [
    path('healthz/', healthz, name='healthz'),
    path('admin/', admin.site.urls),
    path('', include('apps.dashboard.urls')),
    path('search/', include('apps.core.urls')),
    path('accounts/', include('apps.accounts.urls')),
    path('subscribers/', include('apps.subscribers.urls')),
    path('subscriptions/', include('apps.subscriptions.urls')),
    path('daily-tasks/', include('apps.daily_tasks.urls')),
    path('finance/', include('apps.finance.urls')),
    path('inventory/', include('apps.inventory.urls')),
    path('assets/', include('apps.assets.urls')),
    path('devices/', include('apps.devices.urls')),
    path('messages/', include('apps.messages.urls')),
    path('reports/', include('apps.reports.urls')),
    path('settings/', include('apps.settings_app.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
else:
    # Serve media from persistent volume behind Coolify / gunicorn
    urlpatterns += [
        re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
    ]

admin.site.site_header = 'نظام إدارة شبكة الإنترنت'
admin.site.site_title = 'INMS'
admin.site.index_title = 'لوحة الإدارة'