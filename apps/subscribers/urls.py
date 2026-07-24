from django.urls import path
from . import views

app_name = 'subscribers'

urlpatterns = [
    path('', views.list_view, name='list'),
    path('add/', views.create_view, name='create'),
    path('packages/search/', views.package_search, name='package_search'),
    path('<int:pk>/', views.detail_view, name='detail'),
    path('<int:pk>/pay/', views.hub_pay, name='hub_pay'),
    path('<int:pk>/renew/', views.hub_renew, name='hub_renew'),
    path('<int:pk>/settle-debt/', views.hub_settle_debt, name='hub_settle_debt'),
    path('<int:pk>/edit/', views.edit_view, name='edit'),
    path('<int:pk>/delete/', views.delete_view, name='delete'),
    path('<int:pk>/send-reminder-sms/', views.send_reminder_sms, name='send_reminder_sms'),
    path('<int:pk>/suspend/', views.suspend_view, name='suspend'),
    path('<int:pk>/activate/', views.activate_view, name='activate'),
]
