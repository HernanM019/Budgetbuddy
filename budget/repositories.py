"""
Capa de Persistencia / Repositorio (Repository Layer).
Garantiza el aislamiento multi-usuario (Data Segregation) obligando a que toda consulta
reciba explícitamente la instancia de `User` autenticada y optimiza consultas ORM.
"""
from decimal import Decimal
from typing import Optional
from django.contrib.auth.models import User
from django.db.models import Sum, Q, QuerySet, Value, DecimalField
from django.db.models.functions import Coalesce, TruncMonth
from django.shortcuts import get_object_or_404

from .models import Account, Category, Transaction, Budget, SupportTicket


class AccountRepository:
    """Repositorio para acceso a datos de cuentas bancarias/billeteras de un usuario."""

    @staticmethod
    def list_by_user(user: User, only_active: bool = False) -> QuerySet[Account]:
        qs = Account.objects.filter(user=user)
        if only_active:
            qs = qs.filter(is_active=True)
        return qs.order_by('name')

    @staticmethod
    def get_for_user(user: User, pk: int) -> Account:
        return get_object_or_404(Account, pk=pk, user=user)

    @staticmethod
    def get_default_for_user(user: User) -> Optional[Account]:
        return Account.objects.filter(user=user, is_active=True).order_by('id').first()

    @staticmethod
    def calculate_account_balance(user: User, account: Account) -> Decimal:
        """
        Calcula el saldo actual de una cuenta:
        saldo_inicial + ingresos - egresos - transferencias_enviadas + transferencias_recibidas
        """
        agg = Transaction.objects.filter(user=user).aggregate(
            incomes=Coalesce(
                Sum('amount', filter=Q(account=account, type='INCOME')),
                Value(Decimal('0.00')),
                output_field=DecimalField(),
            ),
            expenses=Coalesce(
                Sum('amount', filter=Q(account=account, type='EXPENSE')),
                Value(Decimal('0.00')),
                output_field=DecimalField(),
            ),
            transfers_out=Coalesce(
                Sum('amount', filter=Q(account=account, type='TRANSFER')),
                Value(Decimal('0.00')),
                output_field=DecimalField(),
            ),
            transfers_in=Coalesce(
                Sum('amount', filter=Q(destination_account=account, type='TRANSFER')),
                Value(Decimal('0.00')),
                output_field=DecimalField(),
            ),
        )
        return (
            account.initial_balance
            + agg['incomes']
            - agg['expenses']
            - agg['transfers_out']
            + agg['transfers_in']
        )


class CategoryRepository:
    """Repositorio para acceso a categorías aisladas por usuario."""

    @staticmethod
    def list_by_user(user: User, category_type: Optional[str] = None) -> QuerySet[Category]:
        qs = Category.objects.filter(user=user)
        if category_type in ('INCOME', 'EXPENSE'):
            qs = qs.filter(Q(category_type=category_type) | Q(category_type='BOTH'))
        return qs.order_by('name')

    @staticmethod
    def get_for_user(user: User, pk: int) -> Category:
        return get_object_or_404(Category, pk=pk, user=user)

    @staticmethod
    def exists_by_name(user: User, name: str, exclude_pk: Optional[int] = None) -> bool:
        qs = Category.objects.filter(user=user, name__iexact=name.strip())
        if exclude_pk:
            qs = qs.exclude(pk=exclude_pk)
        return qs.exists()


class TransactionRepository:
    """Repositorio para transacciones con optimización `select_related` y agregaciones SQL."""

    @staticmethod
    def list_by_user(
        user: User,
        tx_type: Optional[str] = None,
        category_id: Optional[int] = None,
        account_id: Optional[int] = None,
        month: Optional[int] = None,
        year: Optional[int] = None,
        search: Optional[str] = None,
    ) -> QuerySet[Transaction]:
        qs = (
            Transaction.objects.filter(user=user)
            .select_related('category', 'account', 'destination_account')
            .order_by('-date', '-id')
        )
        if tx_type in ('INCOME', 'EXPENSE', 'TRANSFER'):
            qs = qs.filter(type=tx_type)
        if category_id:
            qs = qs.filter(category_id=category_id)
        if account_id:
            qs = qs.filter(Q(account_id=account_id) | Q(destination_account_id=account_id))
        if month:
            qs = qs.filter(date__month=month)
        if year:
            qs = qs.filter(date__year=year)
        if search:
            qs = qs.filter(
                Q(description__icontains=search) | Q(category__name__icontains=search)
            )
        return qs

    @staticmethod
    def get_for_user(user: User, pk: int) -> Transaction:
        return get_object_or_404(
            Transaction.objects.select_related('category', 'account', 'destination_account'),
            pk=pk,
            user=user,
        )

    @staticmethod
    def get_totals_for_queryset(qs: QuerySet[Transaction]) -> dict:
        agg = qs.aggregate(
            total_income=Coalesce(
                Sum('amount', filter=Q(type='INCOME')),
                Value(Decimal('0.00')),
                output_field=DecimalField(),
            ),
            total_expense=Coalesce(
                Sum('amount', filter=Q(type='EXPENSE')),
                Value(Decimal('0.00')),
                output_field=DecimalField(),
            ),
            total_transfer=Coalesce(
                Sum('amount', filter=Q(type='TRANSFER')),
                Value(Decimal('0.00')),
                output_field=DecimalField(),
            ),
        )
        agg['balance'] = agg['total_income'] - agg['total_expense']
        return agg

    @staticmethod
    def get_monthly_history(user: User, limit: int = 6) -> list[dict]:
        """
        Retorna el balance histórico agrupado por mes (Ingresos, Egresos y Neto).
        """
        rows = (
            Transaction.objects.filter(user=user)
            .annotate(month_date=TruncMonth('date'))
            .values('month_date')
            .annotate(
                income=Coalesce(
                    Sum('amount', filter=Q(type='INCOME')),
                    Value(Decimal('0.00')),
                    output_field=DecimalField(),
                ),
                expense=Coalesce(
                    Sum('amount', filter=Q(type='EXPENSE')),
                    Value(Decimal('0.00')),
                    output_field=DecimalField(),
                ),
            )
            .order_by('-month_date')[:limit]
        )
        history = []
        for row in rows:
            net = row['income'] - row['expense']
            history.append({
                'month_date': row['month_date'],
                'income': row['income'],
                'expense': row['expense'],
                'net': net,
            })
        return history

    @staticmethod
    def get_category_expenses_for_period(user: User, month: int, year: int) -> dict[int, Decimal]:
        """Retorna un diccionario {category_id: monto_gastado} para un mes y año dados."""
        rows = (
            Transaction.objects.filter(
                user=user,
                type='EXPENSE',
                date__month=month,
                date__year=year,
                category__isnull=False,
            )
            .values('category_id')
            .annotate(
                spent=Coalesce(
                    Sum('amount'),
                    Value(Decimal('0.00')),
                    output_field=DecimalField(),
                )
            )
        )
        return {row['category_id']: row['spent'] for row in rows}


class BudgetRepository:
    """Repositorio para presupuestos mensuales por categoría."""

    @staticmethod
    def list_by_user(
        user: User,
        month: Optional[int] = None,
        year: Optional[int] = None,
    ) -> QuerySet[Budget]:
        qs = Budget.objects.filter(user=user).select_related('category')
        if month:
            qs = qs.filter(month=month)
        if year:
            qs = qs.filter(year=year)
        return qs.order_by('-year', '-month', 'category__name')

    @staticmethod
    def get_for_user(user: User, pk: int) -> Budget:
        return get_object_or_404(
            Budget.objects.select_related('category'),
            pk=pk,
            user=user,
        )


class SupportTicketRepository:
    """Repositorio para tickets de soporte técnico y buzón de sugerencias."""

    @staticmethod
    def list_by_user(user: User) -> QuerySet[SupportTicket]:
        return SupportTicket.objects.filter(user=user).order_by('-created_at')

    @staticmethod
    def list_all_for_admin(
        ticket_type: Optional[str] = None,
        status: Optional[str] = None,
    ) -> QuerySet[SupportTicket]:
        qs = SupportTicket.objects.select_related('user').order_by('-created_at')
        if ticket_type:
            qs = qs.filter(ticket_type=ticket_type)
        if status:
            qs = qs.filter(status=status)
        return qs

    @staticmethod
    def get_by_id(pk: int) -> SupportTicket:
        return get_object_or_404(SupportTicket.objects.select_related('user'), pk=pk)

    @staticmethod
    def get_admin_recipient_emails() -> list[str]:
        """
        Retorna la lista única de correos electrónicos de usuarios activos que son
        staff o superuser y tienen un correo electrónico válido registrado.
        """
        emails = (
            User.objects.filter(is_active=True)
            .filter(Q(is_staff=True) | Q(is_superuser=True))
            .exclude(email__isnull=True)
            .exclude(email__exact='')
            .values_list('email', flat=True)
        )
        # Normalizar y eliminar duplicados preservando el orden
        seen = set()
        unique_emails = []
        for email in emails:
            clean = email.strip()
            if clean and clean.lower() not in seen:
                seen.add(clean.lower())
                unique_emails.append(clean)
        return unique_emails


