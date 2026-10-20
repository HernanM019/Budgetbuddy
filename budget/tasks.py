"""
Tareas Asíncronas con Celery + Redis (budget/tasks.py).
Incluye:
1. Envío asíncrono de correos a administradores ante nuevos tickets de soporte o sugerencias.
2. Evaluación y alerta automática por email cuando el gasto mensual de una categoría
   supera el 80% (En alerta) o el 100% (Excedido) del presupuesto configurado.
"""
from decimal import Decimal
import logging
import threading
from celery import shared_task
from django.conf import settings
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.db import close_old_connections

from .models import Budget, SupportTicket
from .repositories import SupportTicketRepository, TransactionRepository

audit_logger = logging.getLogger('budget.audit')


@shared_task(name='budget.send_admin_ticket_notification')
def send_admin_ticket_notification_task(ticket_id: int) -> int:
    """
    Tarea Celery para notificar a los usuarios staff/admin con correo registrado
    cuando se crea un nuevo ticket de soporte o sugerencia.
    """
    ticket = SupportTicket.objects.select_related('user').filter(pk=ticket_id).first()
    if not ticket:
        return 0

    recipient_list = SupportTicketRepository.get_admin_recipient_emails()
    if not recipient_list:
        return 0

    motivo_display = ticket.get_ticket_type_display()
    subject = f"[BudgetBuddy | {motivo_display}] Ticket #{ticket.pk}: {ticket.subject}"

    user_info = (
        f"@{ticket.user.username} (ID: {ticket.user.id})"
        if ticket.user
        else "Visitante no autenticado (Landing Page / Login)"
    )

    body = (
        f"Hola equipo de administración de BudgetBuddy,\n\n"
        f"Se ha registrado un nuevo ingreso en el Centro de Sugerencias y Soporte.\n"
        f"================================================================\n"
        f"• Ticket ID: #{ticket.pk}\n"
        f"• Motivo seleccionado: {motivo_display} ({ticket.ticket_type})\n"
        f"• Asunto: {ticket.subject}\n"
        f"• Remitente: {ticket.contact_name} <{ticket.contact_email}>\n"
        f"• Cuenta asociada: {user_info}\n"
        f"• Estado inicial: {ticket.get_status_display()}\n"
        f"================================================================\n\n"
        f"CONTENIDO DEL MENSAJE / TICKET:\n"
        f"----------------------------------------------------------------\n"
        f"{ticket.message}\n"
        f"----------------------------------------------------------------\n\n"
        f"Puedes gestionar y responder este ticket desde el Buzón de Administración:\n"
        f"http://127.0.0.1:8000/support/manage/\n"
    )

    from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'alertas@budgetbuddy.local')
    sent = send_mail(
        subject=subject,
        message=body,
        from_email=from_email,
        recipient_list=recipient_list,
        fail_silently=True,
    )
    audit_logger.info(
        f"Notificación de ticket #{ticket.pk} ({ticket.ticket_type}) enviada a {len(recipient_list)} admin(s)."
    )
    return sent


@shared_task(name='budget.check_and_send_budget_alert')
def check_and_send_budget_alert_task(user_id: int, category_id: int, month: int, year: int) -> int:
    """
    Tarea Celery que verifica si el gasto acumulado del mes en una categoría superó el
    80% o el 100% del presupuesto del usuario y le envía una alerta por correo.
    """
    user = User.objects.filter(pk=user_id, is_active=True).first()
    if not user or not user.email:
        return 0

    budget = (
        Budget.objects.select_related('category')
        .filter(user=user, category_id=category_id, month=month, year=year)
        .first()
    )
    if not budget or budget.amount <= Decimal('0.00'):
        return 0

    spent_map = TransactionRepository.get_category_expenses_for_period(user, month=month, year=year)
    spent = spent_map.get(category_id, Decimal('0.00'))
    pct = float((spent / budget.amount) * Decimal('100'))

    if pct < 80.0:
        return 0

    estado = "🚨 PRESUPUESTO EXCEDIDO" if pct >= 100.0 else "⚠️ ALERTA DE PRESUPUESTO (80%+)"
    subject = f"[BudgetBuddy | {estado}] Categoría {budget.category.name} ({month:02d}/{year})"
    body = (
        f"Hola {user.get_full_name() or user.username},\n\n"
        f"Te informamos que tu presupuesto mensual para la categoría '{budget.category.name}' "
        f"en el período {month:02d}/{year} ha alcanzado el {pct:.1f}% de utilización.\n\n"
        f"• Límite configurado: ${budget.amount}\n"
        f"• Gasto acumulado del mes: ${spent}\n"
        f"• Saldo disponible: ${budget.amount - spent}\n\n"
        f"Ingresa a tu Dashboard en BudgetBuddy para revisar el detalle de tus movimientos.\n"
    )
    from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'alertas@budgetbuddy.local')
    sent = send_mail(
        subject=subject,
        message=body,
        from_email=from_email,
        recipient_list=[user.email],
        fail_silently=True,
    )
    audit_logger.info(
        f"Alerta de presupuesto ({pct:.1f}%) enviada a usuario @{user.username} para categoría '{budget.category.name}'."
    )
    return sent


def _run_task_in_background(task_func, *args):
    """Ejecuta la tarea en un hilo en segundo plano cerrando conexiones de DB al finalizar."""
    try:
        close_old_connections()
        task_func(*args)
    except Exception as exc:
        audit_logger.warning(f"Error ejecutando tarea en background '{getattr(task_func, 'name', task_func)}': {exc}")
    finally:
        close_old_connections()


def dispatch_task_safely(task_func, *args):
    """
    Despacha una tarea Celery:
    - En tests (`settings.TESTING`): ejecución síncrona inmediata para validar `mail.outbox`.
    - En producción sin Redis (`CELERY_TASK_ALWAYS_EAGER=True`): ejecución asíncrona en un
      hilo `daemon` para no bloquear jamás el worker HTTP de Gunicorn (evitando timeouts SMTP).
    - Con broker Redis configurado: `.delay(*args)` con fallback a hilo en segundo plano.
    """
    if getattr(settings, 'TESTING', False):
        return task_func(*args)

    if getattr(settings, 'CELERY_TASK_ALWAYS_EAGER', False):
        thread = threading.Thread(target=_run_task_in_background, args=(task_func, *args), daemon=True)
        thread.start()
        return None

    try:
        return task_func.delay(*args)
    except Exception as exc:
        audit_logger.warning(f"Broker Redis no disponible ({exc}); ejecutando tarea '{task_func.name}' en background thread.")
        thread = threading.Thread(target=_run_task_in_background, args=(task_func, *args), daemon=True)
        thread.start()
        return None
