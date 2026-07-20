from django.urls import path
from . import views

app_name = 'assets'

urlpatterns = [
    path('', views.list_view, name='list'),
    path('add/', views.create_view, name='create'),
    path('<int:pk>/', views.detail_view, name='detail'),
    path('<int:pk>/edit/', views.edit_view, name='edit'),
    path('<int:pk>/return/', views.return_view, name='return'),
]
