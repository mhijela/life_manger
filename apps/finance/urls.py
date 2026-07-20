from django.urls import path
from . import views
from . import jawwal_views

app_name = 'finance'

urlpatterns = [
    path('', views.index, name='index'),
    path('payments/', views.payment_list, name='payments'),
    path('payments/add/', views.payment_create, name='payment_create'),
    path('payments/jawwal/', jawwal_views.jawwal_payment_request, name='jawwal_payment'),
    path('payments/jawwal/verify/', jawwal_views.jawwal_payment_verify, name='jawwal_payment_verify'),
    path('payments/jawwal/success/', jawwal_views.jawwal_payment_success, name='jawwal_payment_success'),  # receipt page
    path('expenses/', views.expense_list, name='expenses'),
    path('expenses/add/', views.expense_create, name='expense_create'),
    path('debts/', views.debt_list, name='debts'),
    path('debts/add/', views.debt_create, name='debt_create'),
    path('debts/bulk/', views.debt_bulk_action, name='debt_bulk'),
    path('debts/send-all-sms/', views.debt_send_all_sms, name='debt_send_all_sms'),
    path('debts/<int:pk>/pay/', views.debt_pay, name='debt_pay'),
    path('debts/<int:pk>/send-sms/', views.debt_send_sms, name='debt_send_sms'),
]
