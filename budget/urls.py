from django.urls import path
from . import views

urlpatterns = [
    path('', views.transaction_list, name='transaction_list'),
    path('add/', views.add_transaction, name='add_transaction'),
    path('delete/<int:pk>/', views.delete_transaction, name='delete_transaction'),
    path('edit/<int:pk>/', views.edit_transaction, name='edit_transaction'),
    path('logout/', views.logout_view, name='logout'),
    path('categories/', views.category_list, name='category_list'),
    path('categories/add/', views.add_category, name='add_category'),
    path('categories/edit/<int:pk>/', views.edit_category, name='edit_category'),
    path('categories/delete/<int:pk>/', views.delete_category, name='delete_category'),
]
