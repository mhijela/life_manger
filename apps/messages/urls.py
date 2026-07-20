from django.urls import path
from . import views

app_name = 'messages'

urlpatterns = [
    path('', views.index, name='index'),
    path('send/', views.send_view, name='send'),
    path('bulk/', views.bulk_send, name='bulk'),
    path('templates/', views.template_list, name='templates'),
    path('templates/add/', views.template_create, name='template_create'),
    path('templates/<int:pk>/edit/', views.template_edit, name='template_edit'),
    path('templates/<int:pk>/delete/', views.template_delete, name='template_delete'),
]
