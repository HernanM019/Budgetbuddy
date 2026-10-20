"""
Tareas Asíncronas con Celery + Redis (budget/tasks.py).
Incluye:
1. Envío asíncrono de correos a administradores ante nuevos tickets de soporte o sugerencias.
2. Evaluación y alerta automática por email cuando el gasto mensual de una categoría
   supera el 80% (En alerta) o el 100% (Excedido) del presupuesto configurado.
"""
from decimal import Decimal
import json
import logging
import os
import threading
import urllib.request
from celery import shared_task
from django.conf import settings
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.db import close_old_connections

from .models import Budget, SupportTicket
from .repositories import SupportTicketRepository, TransactionRepository

audit_logger = logging.getLogger('budget.audit')


def _deliver_email(subject: str, body: str, recipient_list: list[str]) -> int:
    """
    Envía un correo electrónico soportando:
    1. HTTPS vía Resend API (`RESEND_API_KEY`) — ideal para Render Free Tier (puerto 443).
    2. HTTPS vía Google Apps Script Webhook (`GMAIL_WEBHOOK_URL`) — usa tu propio Gmail por puerto 443.
    3. SMTP / EmailBackend estándar de Django (`send_mail`).
    """
    if not recipient_list:
        return 0

    resend_api_key = os.environ.get('RESEND_API_KEY', '').strip()
    if resend_api_key:
        try:
            from_addr = os.environ.get('RESEND_FROM_EMAIL', 'BudgetBuddy <onboarding@resend.dev>').strip()
            payload = json.dumps({
                'from': from_addr,
                'to': recipient_list,
                'subject': subject,
                'text': body,
            }).encode('utf-8')
            req = urllib.request.Request(
                'https://api.resend.com/emails',
                data=payload,
                headers={
                    'Authorization': f'Bearer {resend_api_key}',
                    'Content-Type': 'application/json',
                    'User-Agent': 'BudgetBuddy/1.1',
                },
                method='POST',
            )
            with urllib.request.urlopen(req, timeout=8) as resp:
                if 200 <= resp.status < 300:
                    audit_logger.info(f"Email enviado exitosamente vía Resend API (HTTPS) a {recipient_list}.")
                    return len(recipient_list)
        except Exception as exc:
            audit_logger.warning(f"Fallo al enviar vía Resend API ({exc}); intentando siguiente método.")

    gmail_webhook_url = os.environ.get('GMAIL_WEBHOOK_URL', '').strip()
    if gmail_webhook_url:
        try:
            payload = json.dumps({
                'to': ','.join(recipient_list),
                'subject': subject,
                'body': body,
            }).encode('utf-8')
            req = urllib.request.Request(
                gmail_webhook_url,
                data=payload,
                headers={'Content-Type': 'application/json'},
                method='POST',
            )
            with urllib.request.urlopen(req, timeout=8) as resp:
                if 200 <= resp.status < 400:
                    audit_logger.info(f"Email enviado exitosamente vía Gmail HTTPS Webhook a {recipient_list}.")
                    return len(recipient_list)
        except Exception as exc:
            audit_logger.warning(f"Fallo al enviar vía Gmail Webhook ({exc}); intentando siguiente método.")

    from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'alertas@budgetbuddy.local')
    return send_mail(
        subject=subject,
        message=body,
        from_email=from_email,
        recipient_list=recipient_list,
        fail_silently=True,
    )


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

    render_host = os.environ.get('RENDER_EXTERNAL_HOSTNAME', '').strip()
    base_url = f"https://{render_host}" if render_host else "http://127.0.0.1:8000"

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
        f"{base_url}/support/manage/\n"
    )

    sent = _deliver_email(
        subject=subject,
        body=body,
        recipient_list=recipient_list,
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
    sent = _deliver_email(
        subject=subject,
        body=body,
        recipient_list=[user.email],
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
