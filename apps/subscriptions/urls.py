from django.urls import path
from . import views

app_name = 'subscriptions'

urlpatterns = [
    path('', views.list_view, name='list'),
    path('add/', views.create_view, name='create'),
    path('<int:pk>/renew/', views.renew_view, name='renew'),
    path('<int:pk>/expire/', views.expire_view, name='expire'),
    path('<int:pk>/suspend/', views.suspend_view, name='suspend'),
    path('packages/', views.package_list, name='packages'),
    path('packages/add/', views.package_create, name='package_create'),
    path('packages/<int:pk>/edit/', views.package_edit, name='package_edit'),
]
