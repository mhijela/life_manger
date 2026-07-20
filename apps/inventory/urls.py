from django.urls import path
from . import views

app_name = 'inventory'

urlpatterns = [
    path('', views.list_view, name='list'),
    path('add/', views.create_view, name='create'),
    path('<int:pk>/edit/', views.edit_view, name='edit'),
    path('<int:pk>/delete/', views.delete_view, name='delete'),
    path('movement/', views.movement_create, name='movement'),
]
