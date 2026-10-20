"""
Serializers de Django REST Framework (budget/serializers.py).
Garantizan validación de datos y aislamiento multi-usuario en cada endpoint REST.
"""
from datetime import date
from decimal import Decimal
from rest_framework import serializers

from .models import Account, Budget, Category, SupportTicket, Transaction
from .repositories import AccountRepository


class AccountSerializer(serializers.ModelSerializer):
    current_balance = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Account
        fields = [
            'id',
            'name',
            'account_type',
            'currency',
            'initial_balance',
            'current_balance',
            'is_active',
            'created_at',
        ]
        read_only_fields = ['id', 'current_balance', 'created_at']

    def get_current_balance(self, obj: Account) -> str:
        request = self.context.get('request')
        user = request.user if request else obj.user
        bal = AccountRepository.calculate_account_balance(user, obj)
        return f"{bal:.2f}"

    def validate_name(self, value: str) -> str:
        clean_name = value.strip()
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            qs = Account.objects.filter(user=request.user, name__iexact=clean_name)
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError("Ya posees una cuenta con este nombre.")
        return clean_name


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = [
            'id',
            'name',
            'category_type',
            'color',
            'icon',
            'description',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at']

    def validate_name(self, value: str) -> str:
        clean_name = value.strip()
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            qs = Category.objects.filter(user=request.user, name__iexact=clean_name)
            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise serializers.ValidationError("Ya posees una categoría con este nombre.")
        return clean_name


class TransactionSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    account_name = serializers.CharField(source='account.name', read_only=True)

    class Meta:
        model = Transaction
        fields = [
            'id',
            'type',
            'account',
            'account_name',
            'destination_account',
            'category',
            'category_name',
            'amount',
            'date',
            'description',
            'created_at',
        ]
        read_only_fields = ['id', 'category_name', 'account_name', 'created_at']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get('request')
        if request and hasattr(request, 'user') and request.user.is_authenticated:
            self.fields['category'].queryset = Category.objects.filter(user=request.user)
            self.fields['account'].queryset = Account.objects.filter(user=request.user)
            self.fields['destination_account'].queryset = Account.objects.filter(user=request.user)

    def validate_amount(self, value: Decimal) -> Decimal:
        if value <= Decimal('0.00'):
            raise serializers.ValidationError("El monto debe ser mayor a cero.")
        return value

    def validate_date(self, value: date) -> date:
        if value > date.today():
            raise serializers.ValidationError("No se permiten transacciones con fecha futura.")
        return value


class BudgetSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)

    class Meta:
        model = Budget
        fields = [
            'id',
            'category',
            'category_name',
            'amount',
            'month',
            'year',
            'created_at',
        ]
        read_only_fields = ['id', 'category_name', 'created_at']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get('request')
        if request and hasattr(request, 'user') and request.user.is_authenticated:
            self.fields['category'].queryset = Category.objects.filter(user=request.user)


class SupportTicketSerializer(serializers.ModelSerializer):
    class Meta:
        model = SupportTicket
        fields = [
            'id',
            'ticket_type',
            'contact_name',
            'contact_email',
            'subject',
            'message',
            'status',
            'admin_response',
            'created_at',
        ]
        read_only_fields = ['id', 'status', 'admin_response', 'created_at']
