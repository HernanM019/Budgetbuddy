from datetime import date
from decimal import Decimal
from django import forms
from django.contrib.auth.forms import UserCreationForm, PasswordChangeForm
from django.contrib.auth.models import User

from .models import Account, Category, Transaction, Budget, SupportTicket


class TransactionForm(forms.ModelForm):
    """Formulario de registro y edición de Ingresos y Egresos."""

    TYPE_CHOICES = [
        ('INCOME', 'Ingreso'),
        ('EXPENSE', 'Egreso'),
    ]

    type = forms.ChoiceField(
        choices=TYPE_CHOICES,
        label='Tipo',
        widget=forms.Select(attrs={'class': 'form-select'}),
    )

    class Meta:
        model = Transaction
        fields = ['type', 'account', 'category', 'amount', 'date', 'description']
        labels = {
            'type': 'Tipo',
            'account': 'Cuenta',
            'category': 'Categoría',
            'amount': 'Monto',
            'date': 'Fecha',
            'description': 'Descripción',
        }
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'description': forms.Textarea(attrs={'rows': 2, 'class': 'form-control', 'placeholder': 'Detalle opcional de la operación'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0.01'}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if self.user:
            self.instance.user = self.user
            self.fields['category'].queryset = Category.objects.filter(user=self.user)
            self.fields['account'].queryset = Account.objects.filter(user=self.user, is_active=True)
            if not self.instance.pk and not self.initial.get('account'):
                default_acc = Account.objects.filter(user=self.user, is_active=True).order_by('id').first()
                if default_acc:
                    self.initial['account'] = default_acc.pk
        else:
            self.fields['category'].queryset = Category.objects.none()
            self.fields['account'].queryset = Account.objects.none()

        self.fields['category'].required = True
        self.fields['account'].required = False
        self.fields['category'].widget.attrs.update({'class': 'form-select'})
        self.fields['account'].widget.attrs.update({'class': 'form-select'})
        if not self.instance.pk and not self.initial.get('date'):
            self.initial['date'] = date.today()

    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        if amount is not None and amount <= Decimal('0.00'):
            raise forms.ValidationError("El monto debe ser mayor a cero.")
        return amount

    def clean_date(self):
        input_date = self.cleaned_data['date']
        if input_date > date.today():
            raise forms.ValidationError("No se pueden registrar transacciones con fecha futura.")
        return input_date


class TransferForm(forms.Form):
    """Formulario para transferencias entre cuentas del mismo usuario."""

    source_account = forms.ModelChoiceField(
        queryset=Account.objects.none(),
        label='Cuenta de Origen',
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    destination_account = forms.ModelChoiceField(
        queryset=Account.objects.none(),
        label='Cuenta de Destino',
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    amount = forms.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=Decimal('0.01'),
        label='Monto a Transferir',
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0.01'}),
    )
    date = forms.DateField(
        label='Fecha',
        initial=date.today,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
    )
    description = forms.CharField(
        required=False,
        label='Concepto / Nota',
        widget=forms.Textarea(attrs={'rows': 2, 'class': 'form-control', 'placeholder': 'Ej: Paso a caja de ahorro'}),
    )

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if self.user:
            qs = Account.objects.filter(user=self.user, is_active=True)
            self.fields['source_account'].queryset = qs
            self.fields['destination_account'].queryset = qs

    def clean_date(self):
        input_date = self.cleaned_data['date']
        if input_date > date.today():
            raise forms.ValidationError("No se pueden registrar transferencias con fecha futura.")
        return input_date

    def clean(self):
        cleaned_data = super().clean()
        src = cleaned_data.get('source_account')
        dst = cleaned_data.get('destination_account')
        if src and dst and src.pk == dst.pk:
            raise forms.ValidationError("La cuenta de origen y la cuenta de destino no pueden ser la misma.")
        return cleaned_data


class AccountForm(forms.ModelForm):
    """Formulario para crear y editar cuentas financieras del usuario."""

    class Meta:
        model = Account
        fields = ['name', 'account_type', 'currency', 'initial_balance', 'is_active']
        labels = {
            'name': 'Nombre de la Cuenta',
            'account_type': 'Tipo de Cuenta',
            'currency': 'Moneda',
            'initial_balance': 'Saldo Inicial',
            'is_active': 'Cuenta activa',
        }
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: Banco Nación, Efectivo, MercadoPago'}),
            'account_type': forms.Select(attrs={'class': 'form-select'}),
            'currency': forms.Select(attrs={'class': 'form-select'}),
            'initial_balance': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if self.user:
            self.instance.user = self.user

    def clean_name(self):
        name = self.cleaned_data['name'].strip()
        if self.user:
            qs = Account.objects.filter(user=self.user, name__iexact=name)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError("Ya tienes una cuenta con este nombre.")
        return name


class CategoryForm(forms.ModelForm):
    """Formulario para gestionar categorías personalizadas por usuario."""

    class Meta:
        model = Category
        fields = ['name', 'category_type', 'color', 'description']
        labels = {
            'name': 'Nombre',
            'category_type': 'Aplica para',
            'color': 'Color Identificador',
            'description': 'Descripción',
        }
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre de la categoría'}),
            'category_type': forms.Select(attrs={'class': 'form-select'}),
            'color': forms.TextInput(attrs={'type': 'color', 'class': 'form-control form-control-color'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Descripción opcional'}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if self.user:
            self.instance.user = self.user
        self.fields['category_type'].required = False
        self.fields['color'].required = False

    def clean_category_type(self):
        return self.cleaned_data.get('category_type') or 'BOTH'

    def clean_color(self):
        return self.cleaned_data.get('color') or '#2563eb'

    def clean_name(self):
        name = self.cleaned_data['name'].strip()
        if self.user:
            qs = Category.objects.filter(user=self.user, name__iexact=name)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError("Ya tienes una categoría registrada con este nombre.")
        return name


class BudgetForm(forms.ModelForm):
    """Formulario para definir presupuestos mensuales por categoría."""

    MONTH_CHOICES = [
        (1, 'Enero'), (2, 'Febrero'), (3, 'Marzo'), (4, 'Abril'),
        (5, 'Mayo'), (6, 'Junio'), (7, 'Julio'), (8, 'Agosto'),
        (9, 'Septiembre'), (10, 'Octubre'), (11, 'Noviembre'), (12, 'Diciembre'),
    ]

    month = forms.TypedChoiceField(
        choices=MONTH_CHOICES,
        coerce=int,
        label='Mes',
        widget=forms.Select(attrs={'class': 'form-select'}),
    )

    class Meta:
        model = Budget
        fields = ['category', 'amount', 'month', 'year']
        labels = {
            'category': 'Categoría',
            'amount': 'Monto Límite Mensual',
            'month': 'Mes',
            'year': 'Año',
        }
        widgets = {
            'category': forms.Select(attrs={'class': 'form-select'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0.01'}),
            'year': forms.NumberInput(attrs={'class': 'form-control', 'min': '2020', 'max': '2100'}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        today = date.today()
        if not self.instance.pk:
            self.initial.setdefault('month', today.month)
            self.initial.setdefault('year', today.year)
        if self.user:
            self.instance.user = self.user
            self.fields['category'].queryset = Category.objects.filter(user=self.user)
        else:
            self.fields['category'].queryset = Category.objects.none()

    def clean(self):
        cleaned_data = super().clean()
        category = cleaned_data.get('category')
        month = cleaned_data.get('month')
        year = cleaned_data.get('year')
        if self.user and category and month and year:
            qs = Budget.objects.filter(
                user=self.user,
                category=category,
                month=month,
                year=year,
            )
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError(
                    "Ya existe un presupuesto configurado para esta categoría en el mes y año seleccionados."
                )
        return cleaned_data


class CustomUserCreationForm(UserCreationForm):
    """Formulario de registro de usuario con soporte opcional de correo electrónico."""

    username = forms.CharField(
        label='Nombre de usuario',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: hernan_dev'}),
    )
    email = forms.EmailField(
        label='Correo electrónico (opcional)',
        required=False,
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'tu@email.com'}),
    )
    password1 = forms.CharField(
        label='Contraseña',
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Mínimo 8 caracteres'}),
    )
    password2 = forms.CharField(
        label='Repetir contraseña',
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Confirma tu contraseña'}),
    )

    class Meta:
        model = User
        fields = ['username', 'email']


class UserProfileForm(forms.ModelForm):
    """Formulario para que el usuario edite su información personal en su Área Personal."""

    first_name = forms.CharField(
        label='Nombre',
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Tu nombre'}),
    )
    last_name = forms.CharField(
        label='Apellido',
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Tu apellido'}),
    )
    email = forms.EmailField(
        label='Correo electrónico',
        required=True,
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'tu@email.com'}),
    )

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        if email:
            qs = User.objects.filter(email__iexact=email)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError("Este correo electrónico ya está asociado a otra cuenta.")
        return email


class StyledPasswordChangeForm(PasswordChangeForm):
    """Formulario estilizado para cambio seguro de contraseña manteniendo la sesión activa."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['old_password'].label = 'Contraseña actual'
        self.fields['new_password1'].label = 'Nueva contraseña'
        self.fields['new_password2'].label = 'Confirmar nueva contraseña'
        for field in self.fields.values():
            field.widget.attrs.update({'class': 'form-control'})


class SupportTicketForm(forms.ModelForm):
    """
    Formulario unificado para enviar Sugerencias de producto o Reportes de Soporte Técnico.
    Funciona tanto para visitantes en la Landing Page como para usuarios autenticados.
    """

    class Meta:
        model = SupportTicket
        fields = ['ticket_type', 'contact_name', 'contact_email', 'subject', 'message']
        labels = {
            'ticket_type': 'Motivo de tu mensaje',
            'contact_name': 'Tu nombre o usuario',
            'contact_email': 'Correo electrónico de contacto',
            'subject': 'Asunto breve',
            'message': 'Detalle de tu sugerencia o problema',
        }
        widgets = {
            'ticket_type': forms.Select(attrs={'class': 'form-select'}),
            'contact_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: Hernán'}),
            'contact_email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'tu@email.com'}),
            'subject': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: Idea para exportar a Excel / Problema al iniciar sesión'}),
            'message': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Cuéntanos tu idea para mejorar BudgetBuddy o describe el inconveniente que encontraste...'}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if self.user and self.user.is_authenticated and not self.is_bound:
            self.initial.setdefault('contact_name', self.user.get_full_name() or self.user.username)
            if self.user.email:
                self.initial.setdefault('contact_email', self.user.email)


class AdminTicketReviewForm(forms.ModelForm):
    """Formulario para que el administrador gestione el estado y responda sugerencias/tickets."""

    class Meta:
        model = SupportTicket
        fields = ['status', 'admin_response']
        labels = {
            'status': 'Estado del Ticket / Idea',
            'admin_response': 'Respuesta / Nota del Administrador',
        }
        widgets = {
            'status': forms.Select(attrs={'class': 'form-select form-select-sm'}),
            'admin_response': forms.Textarea(attrs={'class': 'form-control form-control-sm', 'rows': 2, 'placeholder': 'Respuesta visible para el usuario...'}),
        }

