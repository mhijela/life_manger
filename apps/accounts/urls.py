from django.contrib.auth import views as auth_views
from django.urls import path
from .forms import EmailAuthenticationForm
from . import views

app_name = 'accounts'

urlpatterns = [
    path('setup/', views.setup_view, name='setup'),
    path('login/', auth_views.LoginView.as_view(
        template_name='accounts/login.html',
        authentication_form=EmailAuthenticationForm,
    ), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
]
