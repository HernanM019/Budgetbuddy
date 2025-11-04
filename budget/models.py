# Create your models here.

"""
───────────────────────────────────────────────────────────────
BudgetBuddy - models.py
───────────────────────────────────────────────────────────────

Los *modelos* son las representaciones en Python de las tablas de la base de datos.
Cada clase hereda de django.db.models.Model y Django se encarga de convertirla
en una tabla SQL real.

Este archivo define:
  - Transaction (cada movimiento de dinero)
  - Category (las categorías personalizadas por usuario)
───────────────────────────────────────────────────────────────
"""

from django.db import models
from django.contrib.auth.models import User
# User es el modelo integrado de Django para manejar usuarios.
# Nos permite asociar transacciones y categorías con el usuario logueado.


# ───────────────────────────────────────────────────────────────
# MODELO: Transaction
# ───────────────────────────────────────────────────────────────
class Transaction(models.Model):
    """
    Representa un movimiento financiero (ingreso o egreso)
    asociado a un usuario y a una categoría.

    Campos:
        user -> quién creó el registro.
        type -> tipo de transacción (INCOME o EXPENSE).
        category -> categoría a la que pertenece.
        amount -> monto de dinero.
        date -> fecha de la transacción.
        description -> texto opcional.
    """

    # Opciones predefinidas para el campo 'type'
    TYPE_CHOICES = [
        ('INCOME', 'Ingreso'),
        ('EXPENSE', 'Egreso'),
    ]

    # Usuario propietario de la transacción
    # - ForeignKey crea una relación "muchos a uno"
    # - on_delete=models.CASCADE -> si se borra el usuario, se borran sus transacciones
    # - related_name permite acceder desde el usuario inversamente: user.transactions.all()
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='transactions'
    )

    # Tipo de movimiento: ingreso o egreso
    # CharField = texto corto
    # choices limita el valor posible a las opciones definidas arriba
    type = models.CharField(max_length=10, choices=TYPE_CHOICES)

    # Categoría asociada (por ejemplo, “Comida”, “Salario”, “Transporte”)
    category = models.ForeignKey(
        'Category',                 # Referencia al modelo Category (entre comillas para definirlo más abajo)
        on_delete=models.CASCADE,   # Si se borra la categoría, también se borran sus transacciones
        related_name='transactions' # Permite acceder desde la categoría: category.transactions.all()
    )

    # Monto de la transacción (usa DecimalField por precisión financiera)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    # max_digits = total de dígitos, incluyendo los decimales
    # decimal_places = cuántos dígitos después del punto

    # Fecha del movimiento
    date = models.DateField()

    # Descripción opcional (comentario o detalle)
    description = models.TextField(blank=True)

    # Django automáticamente crea un campo 'id' (primary key) aunque no lo veas.


# ───────────────────────────────────────────────────────────────
# MODELO: Category
# ───────────────────────────────────────────────────────────────
class Category(models.Model):
    """
    Representa una categoría personalizada para agrupar transacciones.

    Campos:
        user -> usuario propietario.
        name -> nombre de la categoría (ej. “Comida”, “Salario”).
        description -> texto opcional.
        created_at -> fecha de creación automática.

    Reglas:
        - Cada usuario puede tener categorías con nombres distintos,
          pero no duplicadas (gracias a unique_together).
        - Las categorías se ordenan alfabéticamente por defecto.
    """

    # Relación con el usuario que creó la categoría
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='categories'
    )

    # Nombre visible de la categoría (obligatorio)
    name = models.CharField(max_length=100)

    # Descripción opcional
    description = models.TextField(blank=True, null=True)

    # Fecha/hora de creación (auto_now_add = se guarda automáticamente al crear)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # unique_together crea una restricción compuesta:
        # impide que un mismo usuario tenga dos categorías con el mismo nombre.
        unique_together = ('user', 'name')

        # ordering define el orden por defecto de los resultados del modelo.
        ordering = ['name']

    def __str__(self):
        """
        Representación legible de la categoría cuando se imprime o aparece en el admin.
        """
        return self.name
