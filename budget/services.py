"""
Capa de Servicios / Lógica de Negocio (Service Layer).
Orquesta reglas de dominio, validaciones de pertenencia multi-tenant, operaciones
atómicas de base de datos, cálculo de presupuestos, exportación/importación CSV,
tareas asíncronas con Celery y auditoría de seguridad.
"""
import csv
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
import io
import logging
import uuid
from typing import Optional
from django.conf import settings
from django.contrib.auth.models import User
from django.core.cache import cache
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction as db_transaction

from .models import Account, Category, Transaction, Budget, SupportTicket
from .repositories import (
    AccountRepository,
    CategoryRepository,
    TransactionRepository,
    BudgetRepository,
    SupportTicketRepository,
)
from .tasks import (
    check_and_send_budget_alert_task,
    dispatch_task_safely,
    send_admin_ticket_notification_task,
)

security_logger = logging.getLogger('budget.security')
audit_logger = logging.getLogger('budget.audit')


DEFAULT_CATEGORIES = [
    {'name': 'Salario', 'category_type': 'INCOME', 'color': '#16a34a', 'icon': 'bi-cash-stack', 'description': 'Ingresos laborales y honorarios'},
    {'name': 'Inversiones', 'category_type': 'INCOME', 'color': '#0d9488', 'icon': 'bi-graph-up-arrow', 'description': 'Dividendos, intereses y rendimientos'},
    {'name': 'Alimentación', 'category_type': 'EXPENSE', 'color': '#ea580c', 'icon': 'bi-basket', 'description': 'Supermercado, restaurantes y comidas'},
    {'name': 'Vivienda y Servicios', 'category_type': 'EXPENSE', 'color': '#2563eb', 'icon': 'bi-house-door', 'description': 'Alquiler, expensas, luz, agua e internet'},
    {'name': 'Transporte', 'category_type': 'EXPENSE', 'color': '#7c3aed', 'icon': 'bi-bus-front', 'description': 'Combustible, transporte público y movilidad'},
    {'name': 'Salud y Bienestar', 'category_type': 'EXPENSE', 'color': '#dc2626', 'icon': 'bi-heart-pulse', 'description': 'Farmacia, consultas médicas y gimnasio'},
    {'name': 'Ocio y Entretenimiento', 'category_type': 'EXPENSE', 'color': '#d97706', 'icon': 'bi-controller', 'description': 'Salidas, suscripciones y recreación'},
]


class OnboardingService:
    """Inicializa recursos base para usuarios nuevos o migra datos heredados."""

    @staticmethod
    @db_transaction.atomic
    def setup_new_user(user: User) -> Account:
        default_account, _ = Account.objects.get_or_create(
            user=user,
            name='Cuenta Principal',
            defaults={
                'account_type': 'BANK',
                'currency': 'USD',
                'initial_balance': Decimal('0.00'),
                'is_active': True,
            },
        )
        for cat_data in DEFAULT_CATEGORIES:
            Category.objects.get_or_create(
                user=user,
                name=cat_data['name'],
                defaults={
                    'category_type': cat_data['category_type'],
                    'color': cat_data['color'],
                    'icon': cat_data['icon'],
                    'description': cat_data['description'],
                },
            )
        audit_logger.info(f"Onboarding completado para nuevo usuario @{user.username} (ID: {user.id}).")
        return default_account

    @staticmethod
    def ensure_default_account(user: User) -> Account:
        account = AccountRepository.get_default_for_user(user)
        if not account:
            account, _ = Account.objects.get_or_create(
                user=user,
                name='Cuenta Principal',
                defaults={
                    'account_type': 'BANK',
                    'currency': 'USD',
                    'initial_balance': Decimal('0.00'),
                    'is_active': True,
                },
            )
        Transaction.objects.filter(user=user, account__isnull=True).update(account=account)
        return account


class TransactionService:
    """Servicio de dominio para creación, edición, eliminación y transferencias financieras."""

    @staticmethod
    def validate_ownership(
        user: User,
        category: Optional[Category] = None,
        account: Optional[Account] = None,
        destination_account: Optional[Account] = None,
    ) -> None:
        if category and category.user_id != user.id:
            security_logger.warning(
                f"Intento Cross-Tenant bloqueado: Usuario @{user.username} intentó usar categoría ID={category.id} de otro usuario."
            )
            raise PermissionDenied("Violación de aislamiento: La categoría pertenece a otro usuario.")
        if account and account.user_id != user.id:
            security_logger.warning(
                f"Intento Cross-Tenant bloqueado: Usuario @{user.username} intentó usar cuenta ID={account.id} de otro usuario."
            )
            raise PermissionDenied("Violación de aislamiento: La cuenta pertenece a otro usuario.")
        if destination_account and destination_account.user_id != user.id:
            security_logger.warning(
                f"Intento Cross-Tenant bloqueado: Usuario @{user.username} intentó usar cuenta destino ID={destination_account.id} de otro usuario."
            )
            raise PermissionDenied("Violación de aislamiento: La cuenta destino pertenece a otro usuario.")

    @staticmethod
    @db_transaction.atomic
    def save_transaction(user: User, tx: Transaction) -> Transaction:
        tx.user = user
        if not tx.account_id:
            tx.account = OnboardingService.ensure_default_account(user)
        TransactionService.validate_ownership(
            user=user,
            category=tx.category,
            account=tx.account,
            destination_account=tx.destination_account,
        )
        tx.full_clean()
        tx.save()

        if tx.type == 'EXPENSE' and tx.category_id:
            dispatch_task_safely(
                check_and_send_budget_alert_task,
                user.id,
                tx.category_id,
                tx.date.month,
                tx.date.year,
            )
        return tx

    @staticmethod
    @db_transaction.atomic
    def create_transfer(
        user: User,
        source_account: Account,
        destination_account: Account,
        amount: Decimal,
        tx_date: date,
        description: str = "",
    ) -> Transaction:
        TransactionService.validate_ownership(
            user=user,
            account=source_account,
            destination_account=destination_account,
        )
        if source_account.id == destination_account.id:
            raise ValidationError("La cuenta de origen y la cuenta de destino deben ser diferentes.")
        if amount <= Decimal('0.00'):
            raise ValidationError("El monto a transferir debe ser mayor a cero.")
        if tx_date > date.today():
            raise ValidationError("No se pueden registrar transferencias con fecha futura.")

        transfer_tx = Transaction(
            user=user,
            account=source_account,
            destination_account=destination_account,
            type='TRANSFER',
            category=None,
            amount=amount,
            date=tx_date,
            description=description or f"Transferencia de {source_account.name} a {destination_account.name}",
            transfer_group_id=uuid.uuid4(),
        )
        transfer_tx.full_clean()
        transfer_tx.save()
        return transfer_tx

    @staticmethod
    @db_transaction.atomic
    def delete_transaction(user: User, pk: int) -> None:
        tx = TransactionRepository.get_for_user(user, pk)
        tx.delete()


class CSVDataService:
    """
    Servicio ETL ligero para exportación e importación masiva de movimientos en formato CSV.
    """

    @staticmethod
    def export_transactions_to_csv(transactions) -> str:
        output = io.StringIO()
        # BOM UTF-8 para compatibilidad directa con Microsoft Excel
        output.write('\ufeff')
        writer = csv.writer(output)
        writer.writerow(['Fecha', 'Tipo', 'Cuenta', 'Cuenta Destino', 'Categoría', 'Monto', 'Descripción'])

        for tx in transactions:
            writer.writerow([
                tx.date.isoformat(),
                tx.type,
                tx.account.name if tx.account else 'Cuenta Principal',
                tx.destination_account.name if tx.destination_account else '',
                tx.category.name if tx.category else '',
                f"{tx.amount:.2f}",
                tx.description or '',
            ])
        return output.getvalue()

    @staticmethod
    @db_transaction.atomic
    def import_transactions_from_csv(
        user: User,
        csv_text: str,
        target_account: Optional[Account] = None,
    ) -> dict:
        account = target_account or OnboardingService.ensure_default_account(user)
        TransactionService.validate_ownership(user=user, account=account)

        clean_text = csv_text.lstrip('\ufeff')
        reader = csv.DictReader(io.StringIO(clean_text))

        imported_count = 0
        errors = []

        for idx, row in enumerate(reader, start=2):
            try:
                raw_date = (row.get('Fecha') or row.get('date') or '').strip()
                raw_type = (row.get('Tipo') or row.get('type') or 'EXPENSE').strip().upper()
                raw_category = (row.get('Categoría') or row.get('Categoria') or row.get('category') or 'General').strip()
                raw_amount = (row.get('Monto') or row.get('amount') or '').strip().replace('$', '').replace(',', '')
                raw_desc = (row.get('Descripción') or row.get('Descripcion') or row.get('description') or '').strip()

                if raw_type in ('INGRESO', 'INCOME'):
                    tx_type = 'INCOME'
                elif raw_type in ('EGRESO', 'GASTO', 'EXPENSE'):
                    tx_type = 'EXPENSE'
                else:
                    raise ValueError(f"Tipo inválido '{raw_type}' (use INCOME o EXPENSE).")

                tx_date = datetime.strptime(raw_date, '%Y-%m-%d').date()
                if tx_date > date.today():
                    raise ValueError("La fecha no puede ser futura.")

                amount = Decimal(raw_amount)
                if amount <= Decimal('0.00'):
                    raise ValueError("El monto debe ser mayor a cero.")

                category, _ = Category.objects.get_or_create(
                    user=user,
                    name=raw_category[:100] or 'General',
                    defaults={'category_type': tx_type},
                )

                tx = Transaction(
                    user=user,
                    account=account,
                    category=category,
                    type=tx_type,
                    amount=amount,
                    date=tx_date,
                    description=raw_desc,
                )
                tx.full_clean()
                tx.save()
                imported_count += 1
            except (ValueError, InvalidOperation, ValidationError) as exc:
                errors.append(f"Fila {idx}: {exc}")

        audit_logger.info(
            f"Importación CSV por @{user.username}: {imported_count} registros importados, {len(errors)} errores."
        )
        return {'imported': imported_count, 'errors': errors}


class BudgetService:
    """Servicio para evaluar el estado de ejecución de presupuestos mensuales."""

    @staticmethod
    def get_budgets_with_progress(
        user: User,
        month: Optional[int] = None,
        year: Optional[int] = None,
    ) -> list[dict]:
        today = date.today()
        target_month = month or today.month
        target_year = year or today.year

        budgets = BudgetRepository.list_by_user(user, month=target_month, year=target_year)
        spent_by_category = TransactionRepository.get_category_expenses_for_period(
            user=user,
            month=target_month,
            year=target_year,
        )

        results = []
        for b in budgets:
            spent = spent_by_category.get(b.category_id, Decimal('0.00'))
            remaining = b.amount - spent
            pct = float((spent / b.amount) * Decimal('100')) if b.amount > 0 else 0.0
            if pct >= 100.0:
                status = 'danger'
                status_label = 'Excedido'
            elif pct >= 80.0:
                status = 'warning'
                status_label = 'En alerta'
            else:
                status = 'success'
                status_label = 'Saludable'

            results.append({
                'budget': b,
                'spent': spent,
                'remaining': remaining,
                'percentage': round(pct, 1),
                'bar_width': min(round(pct, 1), 100.0),
                'status': status,
                'status_label': status_label,
            })
        return results


class DashboardService:
    """Construye los indicadores consolidados del panel principal del usuario."""

    @staticmethod
    def get_dashboard_data(user: User, month: Optional[int] = None, year: Optional[int] = None) -> dict:
        OnboardingService.ensure_default_account(user)
        today = date.today()
        target_month = month or today.month
        target_year = year or today.year

        accounts = AccountRepository.list_by_user(user, only_active=True)
        accounts_data = []
        total_net_worth = Decimal('0.00')
        for acc in accounts:
            bal = AccountRepository.calculate_account_balance(user, acc)
            total_net_worth += bal
            accounts_data.append({
                'account': acc,
                'balance': bal,
            })

        all_tx_qs = TransactionRepository.list_by_user(user)
        overall_totals = TransactionRepository.get_totals_for_queryset(all_tx_qs)

        month_tx_qs = TransactionRepository.list_by_user(
            user, month=target_month, year=target_year
        )
        monthly_totals = TransactionRepository.get_totals_for_queryset(month_tx_qs)

        budgets_progress = BudgetService.get_budgets_with_progress(
            user, month=target_month, year=target_year
        )
        monthly_history = TransactionRepository.get_monthly_history(user, limit=6)
        recent_transactions = list(all_tx_qs[:8])

        return {
            'accounts_data': accounts_data,
            'total_net_worth': total_net_worth,
            'overall_totals': overall_totals,
            'monthly_totals': monthly_totals,
            'budgets_progress': budgets_progress,
            'monthly_history': monthly_history,
            'recent_transactions': recent_transactions,
            'current_month': target_month,
            'current_year': target_year,
        }


class AuthRateLimitService:
    """
    Protección contra ataques de fuerza bruta en el inicio de sesión.
    Limita los intentos fallidos por dirección IP y nombre de usuario y registra auditoría.
    """
    MAX_ATTEMPTS = 5
    LOCKOUT_SECONDS = 300  # 5 minutos

    @classmethod
    def _get_keys(cls, ip_address: str, username: str) -> tuple[str, str]:
        clean_ip = (ip_address or 'unknown').strip()
        clean_user = (username or 'anonymous').strip().lower()
        return f"auth_rl:ip:{clean_ip}", f"auth_rl:user:{clean_user}"

    @classmethod
    def is_locked(cls, ip_address: str, username: str = "") -> bool:
        ip_key, user_key = cls._get_keys(ip_address, username)
        ip_attempts = cache.get(ip_key, 0)
        user_attempts = cache.get(user_key, 0) if username else 0
        locked = ip_attempts >= cls.MAX_ATTEMPTS or user_attempts >= cls.MAX_ATTEMPTS
        if locked:
            security_logger.warning(
                f"Bloqueo Rate-Limit activo para IP={ip_address}, usuario='{username}'."
            )
        return locked

    @classmethod
    def record_failure(cls, ip_address: str, username: str = "") -> int:
        ip_key, user_key = cls._get_keys(ip_address, username)
        ip_attempts = cache.get(ip_key, 0) + 1
        cache.set(ip_key, ip_attempts, timeout=cls.LOCKOUT_SECONDS)
        if username:
            user_attempts = cache.get(user_key, 0) + 1
            cache.set(user_key, user_attempts, timeout=cls.LOCKOUT_SECONDS)
            count = max(ip_attempts, user_attempts)
        else:
            count = ip_attempts
        security_logger.info(
            f"Fallo de autenticación #{count} desde IP={ip_address} para usuario='{username}'."
        )
        return count

    @classmethod
    def reset(cls, ip_address: str, username: str = "") -> None:
        ip_key, user_key = cls._get_keys(ip_address, username)
        cache.delete(ip_key)
        if username:
            cache.delete(user_key)


class SupportTicketService:
    """Servicio para la creación, notificación asíncrona vía Celery y moderación de tickets."""

    @staticmethod
    def notify_admins_new_ticket(ticket: SupportTicket):
        try:
            return dispatch_task_safely(send_admin_ticket_notification_task, ticket.pk)
        except Exception as exc:
            audit_logger.warning(f"No se pudo enviar notificación de ticket #{ticket.pk}: {exc}")
            return 0

    @staticmethod
    @db_transaction.atomic
    def create_ticket(ticket: SupportTicket, user: Optional[User] = None) -> SupportTicket:
        if user and user.is_authenticated:
            ticket.user = user
            if not ticket.contact_name:
                ticket.contact_name = user.get_full_name() or user.username
            if not ticket.contact_email and user.email:
                ticket.contact_email = user.email
        ticket.full_clean()
        ticket.save()
        SupportTicketService.notify_admins_new_ticket(ticket)
        return ticket
