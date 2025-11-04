"""
───────────────────────────────────────────────────────────────
BudgetBuddy - forms.py
───────────────────────────────────────────────────────────────

Los formularios (forms) son los encargados de:
  • Renderizar inputs HTML con labels y clases CSS.
  • Recibir datos del usuario (request.POST).
  • Validarlos (clean_* y reglas del modelo).
  • Convertirlos a tipos Python y, si es ModelForm, guardar en DB.

Acá definimos:
  - TransactionForm  → crear/editar transacciones
  - CustomUserCreationForm → registro de usuarios (envoltura del de Django)
  - CategoryForm     → crear/editar categorías
───────────────────────────────────────────────────────────────
"""

from django import forms
from .models import Transaction, Category
from datetime import date
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User


# ───────────────────────────────────────────────────────────────
# FORM: TransactionForm (ModelForm)
# ───────────────────────────────────────────────────────────────
class TransactionForm(forms.ModelForm):
    """
    Formulario basado en el modelo Transaction.

    Qué hace:
      - Renderiza campos para tipo, categoría, monto, fecha y descripción.
      - Aplica widgets (clases CSS, tipos de input).
      - En __init__, filtra el queryset de 'category' por el usuario actual,
        para que cada usuario solo vea sus propias categorías.
      - Valida que la fecha no sea futura (clean_date).

    Importante:
      - Como es un ModelForm, al llamar form.save() crea/actualiza una instancia
        de Transaction (según se pase o no 'instance=' en la vista).
    """

    class Meta:
        # Relación directa con el modelo:
        model = Transaction
        # Campos del modelo que el formulario expondrá:
        fields = ['type', 'category', 'amount', 'date', 'description']

        # Etiquetas visibles (útil para i18n y UX)
        labels = {
            'type': 'Tipo',
            'category': 'Categoría',
            'amount': 'Monto',
            'date': 'Fecha',
            'description': 'Descripción',
        }

        # Widgets HTML para personalizar cómo se ve cada campo:
        # - attrs permite agregar clases CSS, placeholders, etc.
        widgets = {
            # input tipo fecha nativo del navegador
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            # textarea compacto
            'description': forms.Textarea(attrs={'rows': 2, 'class': 'form-control'}),
            # number con paso de 0.01 para decimales financieros
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            # select bootstrap-like
            'type': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        """
        Personalización del form al crearse.

        Patrón común en Django:
          - Pop 'user' de kwargs para saber quién está usando el form.
          - Filtrar el queryset del campo 'category' por ese usuario.
        Esto evita que un usuario vea/seleccione categorías de otros.
        """
        user = kwargs.pop('user', None)  # extra no estándar que pasa la vista
        super().__init__(*args, **kwargs)

        # Si recibimos el usuario, limitamos las categorías a las suyas
        if user:
            self.fields['category'].queryset = Category.objects.filter(user=user)

        # Aseguramos la clase CSS del select (aunque podría venir de Meta)
        self.fields['category'].widget.attrs.update({'class': 'form-select'})

    def clean_date(self):
        """
        Validación específica del campo 'date'.

        Rechaza fechas futuras para mantener coherencia contable:
        no se registran transacciones de mañana/mes próximo, etc.
        """
        input_date = self.cleaned_data['date']
        if input_date > date.today():
            raise forms.ValidationError("No se pueden registrar transacciones con fecha futura.")
        return input_date


# ───────────────────────────────────────────────────────────────
# FORM: CustomUserCreationForm
# ───────────────────────────────────────────────────────────────
class CustomUserCreationForm(UserCreationForm):
    """
    Formulario de registro de usuario basado en el de Django,
    pero con labels y clases CSS personalizadas para Bootstrap.

    Nota:
      - UserCreationForm ya valida que password1 y password2 coincidan,
        longitud mínima, etc. Nosotros solo ajustamos presentación.
    """
    username = forms.CharField(
        label='Nombre de usuario',
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    password1 = forms.CharField(
        label='Contraseña',
        widget=forms.PasswordInput(attrs={'class': 'form-control'})
    )
    password2 = forms.CharField(
        label='Repetir contraseña',
        widget=forms.PasswordInput(attrs={'class': 'form-control'})
    )

    class Meta:
        model = User
        # Campos que el form expondrá; el modelo User tiene muchos más
        fields = ['username', 'password1', 'password2']


# ───────────────────────────────────────────────────────────────
# FORM: CategoryForm (ModelForm)
# ───────────────────────────────────────────────────────────────
class CategoryForm(forms.ModelForm):
    """
    Formulario simple para crear/editar categorías del usuario.

    Renderiza nombre y descripción con widgets amigables.
    """
    class Meta:
        model = Category
        fields = ['name', 'description']
        widgets = {
            'name': forms.TextInput(
                attrs={'class': 'form-control', 'placeholder': 'Nombre de la categoría'}
            ),
            'description': forms.Textarea(
                attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Descripción opcional'}
            ),
        }
