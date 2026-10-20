from django.contrib import admin
from .models import Account, Category, Transaction, Budget, SupportTicket


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'account_type', 'currency', 'initial_balance', 'is_active')
    list_filter = ('account_type', 'currency', 'is_active')
    search_fields = ('name', 'user__username')


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'category_type', 'color', 'created_at')
    list_filter = ('category_type',)
    search_fields = ('name', 'user__username', 'description')


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ('type', 'user', 'account', 'category', 'amount', 'date')
    list_filter = ('type', 'date')
    search_fields = ('user__username', 'category__name', 'description')


@admin.register(Budget)
class BudgetAdmin(admin.ModelAdmin):
    list_display = ('user', 'category', 'amount', 'month', 'year')
    list_filter = ('year', 'month')
    search_fields = ('user__username', 'category__name')


@admin.register(SupportTicket)
class SupportTicketAdmin(admin.ModelAdmin):
    list_display = ('id', 'ticket_type', 'subject', 'contact_name', 'contact_email', 'user', 'status', 'created_at')
    list_filter = ('ticket_type', 'status', 'created_at')
    search_fields = ('subject', 'message', 'contact_name', 'contact_email', 'user__username')
    list_editable = ('status',)

