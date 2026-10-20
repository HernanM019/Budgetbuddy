from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from budget import views as budget_views

urlpatterns = [
    path('supervision-panel/', admin.site.urls),
    path('', include('budget.urls')),
    path('login/', budget_views.login_view, name='login'),
    path('logout/', budget_views.logout_view, name='logout'),
    path('register/', budget_views.register, name='register'),

    # Recuperación de contraseña
    path(
        'password-reset/',
        auth_views.PasswordResetView.as_view(
            template_name='budget/password_reset.html',
            email_template_name='budget/password_reset_email.html',
        ),
        name='password_reset',
    ),
    path(
        'password-reset/done/',
        auth_views.PasswordResetDoneView.as_view(
            template_name='budget/password_reset_done.html',
        ),
        name='password_reset_done',
    ),
    path(
        'reset/<uidb64>/<token>/',
        auth_views.PasswordResetConfirmView.as_view(
            template_name='budget/password_reset_confirm.html',
        ),
        name='password_reset_confirm',
    ),
    path(
        'reset/done/',
        auth_views.PasswordResetCompleteView.as_view(
            template_name='budget/password_reset_complete.html',
        ),
        name='password_reset_complete',
    ),
]
