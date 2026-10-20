from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from . import api_views, views

router = DefaultRouter()
router.register(r'accounts', api_views.AccountViewSet, basename='api-accounts')
router.register(r'categories', api_views.CategoryViewSet, basename='api-categories')
router.register(r'transactions', api_views.TransactionViewSet, basename='api-transactions')
router.register(r'budgets', api_views.BudgetViewSet, basename='api-budgets')
router.register(r'support', api_views.SupportTicketViewSet, basename='api-support')

urlpatterns = [
    path('summary/', views.api_financial_summary, name='api_summary'),
    path('auth/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('schema/', SpectacularAPIView.as_view(), name='api_schema'),
    path('docs/', SpectacularSwaggerView.as_view(url_name='api_schema'), name='api_docs'),
    path('', include(router.urls)),
]
