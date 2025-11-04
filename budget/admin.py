"""
───────────────────────────────────────────────────────────────
BudgetBuddy - admin.py
───────────────────────────────────────────────────────────────

Este archivo le dice a Django cómo mostrar tus modelos en el panel
de administración* (/supervision-panel/ en tu caso).

Todos los modelos que se “registren” acá podrán ser gestionados desde la interfaz
de admin: crear, editar, borrar, buscar y filtrar registros.

En otras palabras, es como un panel de control general.

───────────────────────────────────────────────────────────────
Documentación:
https://docs.djangoproject.com/en/5.2/ref/contrib/admin/
───────────────────────────────────────────────────────────────
"""

from django.contrib import admin
from .models import Transaction
from .models import Category
# Importamos el modelo que queremos mostrar en el panel de administración.



# ───────────────────────────────────────────────────────────────
# REGISTRO DE MODELO EN EL ADMIN
# ───────────────────────────────────────────────────────────────
@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    """
    Define cómo se mostrará el modelo Transaction en el panel de administración.

    El decorador @admin.register(Transaction) equivale a:
        admin.site.register(Transaction, TransactionAdmin)
    """

    # list_display → columnas visibles en la lista de transacciones
    list_display = ('type', 'category', 'amount', 'date')

    # list_filter → panel lateral de filtros rápidos
    list_filter = ('type', 'category', 'date')

    # search_fields → campos en los que se puede buscar desde el cuadro de búsqueda superior
    search_fields = ('category', 'description')

    #Ordenamiento descendiente por fecha
    ordering = ('-date',)

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'created_at')
    list_filter = ('user',)
    search_fields = ('name',)
