from django.urls import path

from . import views

app_name = 'daily_tasks'

urlpatterns = [
    path('', views.list_view, name='list'),
    path('add/', views.create_view, name='create'),
    path('<int:pk>/edit/', views.edit_view, name='edit'),
    path('<int:pk>/complete/', views.complete_view, name='complete'),
    path('<int:pk>/delete/', views.delete_view, name='delete'),
]
