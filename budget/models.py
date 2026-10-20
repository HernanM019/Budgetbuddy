from decimal import Decimal
import uuid
from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError


class Account(models.Model):
    """
    Representa una cuenta financiera perteneciente a un usuario (Efectivo, Banco, Billetera Virtual, etc.).
    """
    ACCOUNT_TYPES = [
        ('CASH', 'Efectivo'),
        ('BANK', 'Cuenta Bancaria'),
        ('WALLET', 'Billetera Virtual'),
        ('SAVINGS', 'Caja de Ahorro / Inversión'),
        ('CREDIT', 'Tarjeta de Crédito'),
    ]

    CURRENCY_CHOICES = [
        ('USD', 'USD ($)'),
        ('ARS', 'ARS ($)'),
        ('EUR', 'EUR (€)'),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='accounts',
        db_index=True,
    )
    name = models.CharField(max_length=100)
    account_type = models.CharField(max_length=15, choices=ACCOUNT_TYPES, default='BANK')
    currency = models.CharField(max_length=3, choices=CURRENCY_CHOICES, default='USD')
    initial_balance = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'name')
        ordering = ['name']
        indexes = [
            models.Index(fields=['user', 'is_active']),
        ]

    def __str__(self):
        return f"{self.name} ({self.get_account_type_display()})"


class Category(models.Model):
    """
    Categoría de clasificación para ingresos y egresos, aislada por usuario.
    """
    CATEGORY_TYPES = [
        ('EXPENSE', 'Gasto'),
        ('INCOME', 'Ingreso'),
        ('BOTH', 'Ambos'),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='categories',
        db_index=True,
    )
    name = models.CharField(max_length=100)
    category_type = models.CharField(max_length=10, choices=CATEGORY_TYPES, default='BOTH')
    color = models.CharField(max_length=7, default='#2563eb')
    icon = models.CharField(max_length=50, default='bi-tag')
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'name')
        ordering = ['name']
        indexes = [
            models.Index(fields=['user', 'category_type']),
        ]

    def __str__(self):
        return self.name


class Transaction(models.Model):
    """
    Registro financiero individual (Ingreso, Egreso o Transferencia entre cuentas).
    """
    TYPE_CHOICES = [
        ('INCOME', 'Ingreso'),
        ('EXPENSE', 'Egreso'),
        ('TRANSFER', 'Transferencia'),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='transactions',
        db_index=True,
    )
    account = models.ForeignKey(
        Account,
        on_delete=models.CASCADE,
        related_name='transactions',
        null=True,
        blank=True,
    )
    destination_account = models.ForeignKey(
        Account,
        on_delete=models.SET_NULL,
        related_name='incoming_transfers',
        null=True,
        blank=True,
    )
    type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        related_name='transactions',
        null=True,
        blank=True,
    )
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
    )
    date = models.DateField(db_index=True)
    description = models.TextField(blank=True)
    transfer_group_id = models.UUIDField(null=True, blank=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)

    class Meta:
        ordering = ['-date', '-id']
        indexes = [
            models.Index(fields=['user', '-date']),
            models.Index(fields=['user', 'type']),
            models.Index(fields=['user', 'category']),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(amount__gt=0),
                name='transaction_amount_positive',
            ),
        ]

    def clean(self):
        super().clean()
        if self.user_id:
            if self.category_id and self.category.user_id != self.user_id:
                raise ValidationError("La categoría seleccionada no pertenece al usuario.")
            if self.account_id and self.account.user_id != self.user_id:
                raise ValidationError("La cuenta seleccionada no pertenece al usuario.")
            if self.destination_account_id and self.destination_account.user_id != self.user_id:
                raise ValidationError("La cuenta de destino no pertenece al usuario.")
        if self.type == 'TRANSFER':
            if not self.account_id or not self.destination_account_id:
                raise ValidationError("Las transferencias requieren cuenta de origen y cuenta de destino.")
            if self.account_id == self.destination_account_id:
                raise ValidationError("La cuenta de origen y destino no pueden ser la misma.")

    def __str__(self):
        return f"{self.get_type_display()} - ${self.amount} ({self.date})"


class Budget(models.Model):
    """
    Presupuesto mensual asignado por un usuario a una categoría específica.
    """
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='budgets',
        db_index=True,
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name='budgets',
    )
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
    )
    month = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(12)],
    )
    year = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(2000), MaxValueValidator(2100)],
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'category', 'month', 'year')
        ordering = ['-year', '-month', 'category__name']
        indexes = [
            models.Index(fields=['user', 'year', 'month']),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(amount__gt=0),
                name='budget_amount_positive',
            ),
        ]

    def clean(self):
        super().clean()
        if self.user_id and self.category_id and self.category.user_id != self.user_id:
            raise ValidationError("No puedes asignar un presupuesto a una categoría de otro usuario.")

    def __str__(self):
        return f"Presupuesto {self.category.name} ({self.month:02d}/{self.year}): ${self.amount}"


class SupportTicket(models.Model):
    """
    Ticket unificado de Sugerencias (Ideas de producto) y Soporte Técnico / Contacto.
    Puede ser enviado tanto por usuarios autenticados como por visitantes desde la Landing Page.
    """
    TICKET_TYPES = [
        ('SUGGESTION', '💡 Sugerencia / Nueva Idea'),
        ('BUG', '🐛 Falla o Error Técnico'),
        ('LOGIN_ISSUE', '🔐 Problema de Acceso / Contraseña'),
        ('OTHER', '💬 Consulta General'),
    ]

    STATUS_CHOICES = [
        ('OPEN', 'Abierto'),
        ('IN_REVIEW', 'En Revisión'),
        ('PLANNED', 'Planificado para Futura Versión'),
        ('RESOLVED', 'Resuelto / Cerrado'),
    ]

    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='support_tickets',
        db_index=True,
    )
    contact_name = models.CharField(max_length=100)
    contact_email = models.EmailField()
    ticket_type = models.CharField(max_length=20, choices=TICKET_TYPES, default='SUGGESTION')
    subject = models.CharField(max_length=150)
    message = models.TextField()
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='OPEN')
    admin_response = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['ticket_type', 'status']),
            models.Index(fields=['user', '-created_at']),
        ]

    def __str__(self):
        return f"[{self.get_ticket_type_display()}] {self.subject} ({self.contact_name})"

