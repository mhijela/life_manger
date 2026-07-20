from django.urls import path
from . import views
from . import jawwal_views

app_name = 'settings_app'

urlpatterns = [
    path('', views.index, name='index'),
    path('payment-methods/', views.payment_methods, name='payment_methods'),
    path('payment-methods/<int:pk>/edit/', views.payment_methods, name='payment_method_edit'),
    path('payment-methods/<int:pk>/toggle/', views.payment_method_toggle, name='payment_method_toggle'),
    path('payment-methods/<int:pk>/delete/', views.payment_method_delete, name='payment_method_delete'),
    path('jawwal/wizard/', jawwal_views.jawwal_wizard, name='jawwal_wizard'),
]
