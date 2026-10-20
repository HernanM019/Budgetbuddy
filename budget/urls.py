from django.urls import include, path
from . import views

urlpatterns = [
    # Landing Page & Dashboard
    path('', views.landing_page, name='landing_page'),
    path('dashboard/', views.dashboard, name='dashboard'),

    # Transacciones, Transferencias & ETL CSV
    path('transactions/', views.transaction_list, name='transaction_list'),
    path('transactions/export/csv/', views.export_transactions_csv, name='export_transactions_csv'),
    path('transactions/import/csv/', views.import_transactions_csv, name='import_transactions_csv'),
    path('add/', views.add_transaction, name='add_transaction'),
    path('transfer/', views.transfer_funds, name='transfer_funds'),
    path('delete/<int:pk>/', views.delete_transaction, name='delete_transaction'),
    path('edit/<int:pk>/', views.edit_transaction, name='edit_transaction'),

    # Cuentas Financieras (Accounts)
    path('accounts/', views.account_list, name='account_list'),
    path('accounts/add/', views.add_account, name='add_account'),
    path('accounts/edit/<int:pk>/', views.edit_account, name='edit_account'),
    path('accounts/delete/<int:pk>/', views.delete_account, name='delete_account'),

    # Categorías (Categories)
    path('categories/', views.category_list, name='category_list'),
    path('categories/add/', views.add_category, name='add_category'),
    path('categories/edit/<int:pk>/', views.edit_category, name='edit_category'),
    path('categories/delete/<int:pk>/', views.delete_category, name='delete_category'),

    # Presupuestos Mensuales (Budgets)
    path('budgets/', views.budget_list, name='budget_list'),
    path('budgets/add/', views.add_budget, name='add_budget'),
    path('budgets/edit/<int:pk>/', views.edit_budget, name='edit_budget'),
    path('budgets/delete/<int:pk>/', views.delete_budget, name='delete_budget'),

    # Área Personal (Perfil y Seguridad de Contraseña)
    path('profile/', views.profile_view, name='profile'),

    # Centro de Soporte, Contacto y Buzón de Sugerencias
    path('support/', views.support_center, name='support_center'),
    path('support/manage/', views.admin_support_dashboard, name='admin_support_dashboard'),
    path('support/manage/<int:pk>/', views.admin_update_ticket, name='admin_update_ticket'),

    # REST API v1 (DRF + JWT + Swagger/OpenAPI) & Healthcheck
    path('api/v1/', include('budget.api_urls')),
    path('health/', views.healthcheck, name='healthcheck'),
]
