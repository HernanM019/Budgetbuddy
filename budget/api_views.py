"""
ViewSets de Django REST Framework (budget/api_views.py).
Reutilizan la capa de Repositorios (`repositories.py`) y Servicios (`services.py`)
para mantener el aislamiento estricto por usuario (`request.user`).
"""
from rest_framework import permissions, viewsets

from .repositories import (
    AccountRepository,
    BudgetRepository,
    CategoryRepository,
    SupportTicketRepository,
    TransactionRepository,
)
from .serializers import (
    AccountSerializer,
    BudgetSerializer,
    CategorySerializer,
    SupportTicketSerializer,
    TransactionSerializer,
)
from .services import SupportTicketService, TransactionService


class AccountViewSet(viewsets.ModelViewSet):
    """CRUD REST para las cuentas financieras del usuario autenticado."""
    serializer_class = AccountSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return AccountRepository.list_by_user(self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class CategoryViewSet(viewsets.ModelViewSet):
    """CRUD REST para las categorías personalizadas del usuario autenticado."""
    serializer_class = CategorySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return CategoryRepository.list_by_user(self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class TransactionViewSet(viewsets.ModelViewSet):
    """CRUD REST para transacciones del usuario autenticado, disparando alertas de presupuesto vía Celery."""
    serializer_class = TransactionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        tx_type = self.request.query_params.get('type')
        return TransactionRepository.list_by_user(self.request.user, tx_type=tx_type)

    def perform_create(self, serializer):
        tx = serializer.save(user=self.request.user)
        TransactionService.save_transaction(self.request.user, tx)

    def perform_update(self, serializer):
        tx = serializer.save(user=self.request.user)
        TransactionService.save_transaction(self.request.user, tx)


class BudgetViewSet(viewsets.ModelViewSet):
    """CRUD REST para presupuestos mensuales del usuario autenticado."""
    serializer_class = BudgetSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return BudgetRepository.list_by_user(self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class SupportTicketViewSet(viewsets.ModelViewSet):
    """API REST para envío y consulta de tickets de soporte y sugerencias del usuario."""
    serializer_class = SupportTicketSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ['get', 'post', 'head', 'options']

    def get_queryset(self):
        return SupportTicketRepository.list_by_user(self.request.user)

    def perform_create(self, serializer):
        ticket = serializer.save(user=self.request.user)
        SupportTicketService.notify_admins_new_ticket(ticket)
