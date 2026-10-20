"""
Capa de Presentación / Vistas y Controladores HTTP (Presentation Layer).
Gestiona peticiones, autenticación, control de acceso (`@login_required`),
rate limiting y delega toda la lógica de negocio a `services.py` y `repositories.py`.
"""
from django.contrib import messages
from django.contrib.auth import login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.utils.http import url_has_allowed_host_and_scheme

from .forms import (
    AccountForm,
    AdminTicketReviewForm,
    BudgetForm,
    CategoryForm,
    CustomUserCreationForm,
    StyledPasswordChangeForm,
    SupportTicketForm,
    TransactionForm,
    TransferForm,
    UserProfileForm,
)
from .repositories import (
    AccountRepository,
    BudgetRepository,
    CategoryRepository,
    SupportTicketRepository,
    TransactionRepository,
)
from .services import (
    AuthRateLimitService,
    BudgetService,
    CSVDataService,
    DashboardService,
    OnboardingService,
    SupportTicketService,
    TransactionService,
)


def _get_client_ip(request: HttpRequest) -> str:
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '127.0.0.1')


#################################### LANDING PAGE & AUTH ##############################

def landing_page(request: HttpRequest) -> HttpResponse:
    """
    Landing Page pública para conversión de visitantes.
    Si el usuario ya tiene una sesión activa, redirige automáticamente al Dashboard.
    """
    if request.user.is_authenticated:
        return redirect('dashboard')
    support_form = SupportTicketForm(initial={'ticket_type': 'LOGIN_ISSUE'})
    return render(request, 'budget/landing.html', {'support_form': support_form})


def login_view(request: HttpRequest) -> HttpResponse:
    """
    Inicio de sesión con protección Rate Limiting contra fuerza bruta y
    redirección automática para usuarios ya autenticados.
    """
    if request.user.is_authenticated:
        return redirect('dashboard')

    client_ip = _get_client_ip(request)
    username_attempt = request.POST.get('username', '').strip() if request.method == 'POST' else ''

    if request.method == 'POST':
        if AuthRateLimitService.is_locked(client_ip, username_attempt):
            messages.error(
                request,
                "Demasiados intentos de inicio de sesión fallidos. Por seguridad, espera 5 minutos.",
            )
            form = AuthenticationForm(request)
            return render(request, 'budget/login.html', {'form': form, 'rate_limited': True}, status=429)

        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            AuthRateLimitService.reset(client_ip, user.username)
            login(request, user)
            OnboardingService.ensure_default_account(user)
            next_url = request.POST.get('next') or request.GET.get('next')
            if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
                return redirect(next_url)
            return redirect('dashboard')
        else:
            AuthRateLimitService.record_failure(client_ip, username_attempt)
    else:
        form = AuthenticationForm(request)

    return render(request, 'budget/login.html', {'form': form})


def register(request: HttpRequest) -> HttpResponse:
    """
    Registro de nuevos usuarios con aprovisionamiento inicial de cuenta y categorías.
    """
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            OnboardingService.setup_new_user(user)
            login(request, user)
            messages.success(
                request,
                f"¡Bienvenido, {user.username}! Tu cuenta y tus categorías iniciales están listas.",
            )
            return redirect('dashboard')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field.capitalize()}: {error}")
    else:
        form = CustomUserCreationForm()

    return render(request, 'budget/register.html', {'form': form})


def logout_view(request: HttpRequest) -> HttpResponse:
    """Cierre de sesión seguro."""
    if request.user.is_authenticated:
        logout(request)
        messages.success(request, "👋 Sesión cerrada correctamente.")
    return redirect('login')


#################################### DASHBOARD ##############################

@login_required(login_url='login')
def dashboard(request: HttpRequest) -> HttpResponse:
    """Panel financiero principal del usuario autenticado."""
    month = request.GET.get('month')
    year = request.GET.get('year')
    parsed_month = int(month) if month and month.isdigit() and 1 <= int(month) <= 12 else None
    parsed_year = int(year) if year and year.isdigit() and 2000 <= int(year) <= 2100 else None

    context = DashboardService.get_dashboard_data(
        request.user,
        month=parsed_month,
        year=parsed_year,
    )
    return render(request, 'budget/dashboard.html', context)


#################################### TRANSACCIONES & TRANSFERENCIAS ##############################

@login_required(login_url='login')
def transaction_list(request: HttpRequest) -> HttpResponse:
    """Listado filtrable de transacciones del usuario autenticado."""
    OnboardingService.ensure_default_account(request.user)

    tx_type = request.GET.get('type') or None
    category_id = int(request.GET['category']) if request.GET.get('category', '').isdigit() else None
    account_id = int(request.GET['account']) if request.GET.get('account', '').isdigit() else None
    month = int(request.GET['month']) if request.GET.get('month', '').isdigit() else None
    year = int(request.GET['year']) if request.GET.get('year', '').isdigit() else None
    search = request.GET.get('q', '').strip() or None

    transactions = TransactionRepository.list_by_user(
        user=request.user,
        tx_type=tx_type,
        category_id=category_id,
        account_id=account_id,
        month=month,
        year=year,
        search=search,
    )
    totals = TransactionRepository.get_totals_for_queryset(transactions)

    categories = CategoryRepository.list_by_user(request.user)
    accounts = AccountRepository.list_by_user(request.user, only_active=True)

    return render(request, 'budget/transaction_list.html', {
        'transactions': transactions,
        'total_income': totals['total_income'],
        'total_expense': totals['total_expense'],
        'total_transfer': totals['total_transfer'],
        'balance': totals['balance'],
        'categories': categories,
        'accounts': accounts,
        'selected_type': tx_type or '',
        'selected_category': category_id or '',
        'selected_account': account_id or '',
        'search_query': search or '',
    })


@login_required(login_url='login')
def add_transaction(request: HttpRequest) -> HttpResponse:
    OnboardingService.ensure_default_account(request.user)
    if request.method == 'POST':
        form = TransactionForm(request.POST, user=request.user)
        if form.is_valid():
            tx = form.save(commit=False)
            TransactionService.save_transaction(request.user, tx)
            messages.success(request, "Registro financiero agregado correctamente.")
            return redirect('transaction_list')
    else:
        form = TransactionForm(user=request.user)
    return render(request, 'budget/add_transaction.html', {'form': form})


@login_required(login_url='login')
def edit_transaction(request: HttpRequest, pk: int) -> HttpResponse:
    transaction = TransactionRepository.get_for_user(request.user, pk)
    if request.method == 'POST':
        form = TransactionForm(request.POST, instance=transaction, user=request.user)
        if form.is_valid():
            tx = form.save(commit=False)
            TransactionService.save_transaction(request.user, tx)
            messages.success(request, "Registro actualizado correctamente.")
            return redirect('transaction_list')
    else:
        form = TransactionForm(instance=transaction, user=request.user)
    return render(request, 'budget/edit_transaction.html', {'form': form, 'transaction': transaction})


@login_required(login_url='login')
def delete_transaction(request: HttpRequest, pk: int) -> HttpResponse:
    transaction = TransactionRepository.get_for_user(request.user, pk)
    if request.method == 'POST':
        TransactionService.delete_transaction(request.user, pk)

        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': True})

        messages.success(request, "Registro eliminado correctamente.")
        return redirect('transaction_list')

    return render(request, 'budget/confirm_delete.html', {
        'object_type': 'transacción',
        'object_name': f"{transaction.get_type_display()} de ${transaction.amount} ({transaction.date})",
        'transaction': transaction,
        'cancel_url': 'transaction_list',
    })


@login_required(login_url='login')
def transfer_funds(request: HttpRequest) -> HttpResponse:
    """Transferencia atómica de saldo entre dos cuentas del mismo usuario."""
    OnboardingService.ensure_default_account(request.user)
    if request.method == 'POST':
        form = TransferForm(request.POST, user=request.user)
        if form.is_valid():
            try:
                TransactionService.create_transfer(
                    user=request.user,
                    source_account=form.cleaned_data['source_account'],
                    destination_account=form.cleaned_data['destination_account'],
                    amount=form.cleaned_data['amount'],
                    tx_date=form.cleaned_data['date'],
                    description=form.cleaned_data.get('description', ''),
                )
                messages.success(request, "Transferencia entre cuentas realizada con éxito.")
                return redirect('transaction_list')
            except ValidationError as exc:
                form.add_error(None, exc.message if hasattr(exc, 'message') else str(exc))
    else:
        form = TransferForm(user=request.user)

    return render(request, 'budget/transfer_form.html', {'form': form})


@login_required(login_url='login')
def export_transactions_csv(request: HttpRequest) -> HttpResponse:
    """Exporta las transacciones del usuario autenticado (respetando filtros activos) a un archivo CSV compatible con Excel."""
    tx_type = request.GET.get('type') or None
    category_id = int(request.GET['category']) if request.GET.get('category', '').isdigit() else None
    account_id = int(request.GET['account']) if request.GET.get('account', '').isdigit() else None
    month = int(request.GET['month']) if request.GET.get('month', '').isdigit() else None
    year = int(request.GET['year']) if request.GET.get('year', '').isdigit() else None
    search = request.GET.get('q', '').strip() or None

    transactions = TransactionRepository.list_by_user(
        user=request.user,
        tx_type=tx_type,
        category_id=category_id,
        account_id=account_id,
        month=month,
        year=year,
        search=search,
    )
    csv_content = CSVDataService.export_transactions_to_csv(transactions)
    response = HttpResponse(csv_content, content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="budgetbuddy_movimientos_{request.user.username}.csv"'
    return response


@login_required(login_url='login')
def import_transactions_csv(request: HttpRequest) -> HttpResponse:
    """Importa movimientos masivos desde un archivo CSV a una cuenta del usuario."""
    if request.method == 'POST':
        csv_file = request.FILES.get('csv_file')
        account_id = request.POST.get('account_id')
        if not csv_file:
            messages.error(request, "Debes seleccionar un archivo CSV válido para importar.")
            return redirect('transaction_list')

        target_account = None
        if account_id and str(account_id).isdigit():
            target_account = AccountRepository.get_for_user(request.user, int(account_id))

        try:
            decoded_text = csv_file.read().decode('utf-8-sig', errors='replace')
            result = CSVDataService.import_transactions_from_csv(
                user=request.user,
                csv_text=decoded_text,
                target_account=target_account,
            )
            if result['imported'] > 0:
                messages.success(request, f"✅ Se importaron {result['imported']} movimientos correctamente.")
            if result['errors']:
                messages.warning(request, f"⚠️ Algunas filas tuvieron observaciones: {'; '.join(result['errors'][:3])}")
        except Exception as exc:
            messages.error(request, f"No se pudo procesar el archivo CSV: {exc}")

    return redirect('transaction_list')


#################################### CUENTAS (ACCOUNTS) ##############################

@login_required(login_url='login')
def account_list(request: HttpRequest) -> HttpResponse:
    OnboardingService.ensure_default_account(request.user)
    accounts = AccountRepository.list_by_user(request.user)
    accounts_with_balance = [
        {
            'account': acc,
            'balance': AccountRepository.calculate_account_balance(request.user, acc),
        }
        for acc in accounts
    ]
    return render(request, 'budget/account_list.html', {'accounts_data': accounts_with_balance})


@login_required(login_url='login')
def add_account(request: HttpRequest) -> HttpResponse:
    if request.method == 'POST':
        form = AccountForm(request.POST, user=request.user)
        if form.is_valid():
            account = form.save(commit=False)
            account.user = request.user
            account.save()
            messages.success(request, f"Cuenta '{account.name}' creada correctamente.")
            return redirect('account_list')
    else:
        form = AccountForm(user=request.user)
    return render(request, 'budget/account_form.html', {'form': form, 'is_edit': False})


@login_required(login_url='login')
def edit_account(request: HttpRequest, pk: int) -> HttpResponse:
    account = AccountRepository.get_for_user(request.user, pk)
    if request.method == 'POST':
        form = AccountForm(request.POST, instance=account, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, f"Cuenta '{account.name}' actualizada correctamente.")
            return redirect('account_list')
    else:
        form = AccountForm(instance=account, user=request.user)
    return render(request, 'budget/account_form.html', {'form': form, 'account': account, 'is_edit': True})


@login_required(login_url='login')
def delete_account(request: HttpRequest, pk: int) -> HttpResponse:
    account = AccountRepository.get_for_user(request.user, pk)
    if request.method == 'POST':
        account_name = account.name
        account.delete()
        messages.success(request, f"Cuenta '{account_name}' eliminada.")
        return redirect('account_list')
    return render(request, 'budget/confirm_delete.html', {
        'object_type': 'cuenta',
        'object_name': account.name,
        'cancel_url': 'account_list',
    })


#################################### CATEGORÍAS (CATEGORIES) ##############################

@login_required(login_url='login')
def category_list(request: HttpRequest) -> HttpResponse:
    categories = CategoryRepository.list_by_user(request.user)
    return render(request, 'budget/category_list.html', {'categories': categories})


@login_required(login_url='login')
def add_category(request: HttpRequest) -> HttpResponse:
    if request.method == 'POST':
        form = CategoryForm(request.POST, user=request.user)
        if form.is_valid():
            category = form.save(commit=False)
            category.user = request.user
            category.save()
            messages.success(request, f"Categoría '{category.name}' creada correctamente.")
            return redirect('category_list')
    else:
        form = CategoryForm(user=request.user)
    return render(request, 'budget/add_category.html', {'form': form})


@login_required(login_url='login')
def edit_category(request: HttpRequest, pk: int) -> HttpResponse:
    category = CategoryRepository.get_for_user(request.user, pk)
    if request.method == 'POST':
        form = CategoryForm(request.POST, instance=category, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, f"Categoría '{category.name}' actualizada correctamente.")
            return redirect('category_list')
    else:
        form = CategoryForm(instance=category, user=request.user)
    return render(request, 'budget/edit_category.html', {'form': form, 'category': category})


@login_required(login_url='login')
def delete_category(request: HttpRequest, pk: int) -> HttpResponse:
    category = CategoryRepository.get_for_user(request.user, pk)
    if request.method == 'POST':
        name = category.name
        category.delete()
        messages.success(request, f"Categoría '{name}' eliminada.")
        return redirect('category_list')
    return render(request, 'budget/confirm_delete.html', {
        'object_type': 'categoría',
        'object_name': category.name,
        'object': category,
        'cancel_url': 'category_list',
    })


#################################### PRESUPUESTOS (BUDGETS) ##############################

@login_required(login_url='login')
def budget_list(request: HttpRequest) -> HttpResponse:
    month = request.GET.get('month')
    year = request.GET.get('year')
    parsed_month = int(month) if month and month.isdigit() and 1 <= int(month) <= 12 else None
    parsed_year = int(year) if year and year.isdigit() and 2000 <= int(year) <= 2100 else None

    budgets_progress = BudgetService.get_budgets_with_progress(
        request.user,
        month=parsed_month,
        year=parsed_year,
    )
    return render(request, 'budget/budget_list.html', {
        'budgets_progress': budgets_progress,
    })


@login_required(login_url='login')
def add_budget(request: HttpRequest) -> HttpResponse:
    if request.method == 'POST':
        form = BudgetForm(request.POST, user=request.user)
        if form.is_valid():
            budget = form.save(commit=False)
            budget.user = request.user
            budget.save()
            messages.success(request, "Presupuesto mensual guardado correctamente.")
            return redirect('budget_list')
    else:
        form = BudgetForm(user=request.user)
    return render(request, 'budget/budget_form.html', {'form': form, 'is_edit': False})


@login_required(login_url='login')
def edit_budget(request: HttpRequest, pk: int) -> HttpResponse:
    budget = BudgetRepository.get_for_user(request.user, pk)
    if request.method == 'POST':
        form = BudgetForm(request.POST, instance=budget, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Presupuesto actualizado correctamente.")
            return redirect('budget_list')
    else:
        form = BudgetForm(instance=budget, user=request.user)
    return render(request, 'budget/budget_form.html', {'form': form, 'budget': budget, 'is_edit': True})


@login_required(login_url='login')
def delete_budget(request: HttpRequest, pk: int) -> HttpResponse:
    budget = BudgetRepository.get_for_user(request.user, pk)
    if request.method == 'POST':
        budget.delete()
        messages.success(request, "Presupuesto eliminado correctamente.")
        return redirect('budget_list')
    return render(request, 'budget/confirm_delete.html', {
        'object_type': 'presupuesto',
        'object_name': str(budget),
        'cancel_url': 'budget_list',
    })


#################################### API & HEALTHCHECK ##############################

@login_required(login_url='login')
def api_financial_summary(request: HttpRequest) -> JsonResponse:
    """Endpoint JSON con el resumen financiero aislado para el usuario autenticado."""
    data = DashboardService.get_dashboard_data(request.user)
    return JsonResponse({
        'user': request.user.username,
        'total_net_worth': str(data['total_net_worth']),
        'monthly_income': str(data['monthly_totals']['total_income']),
        'monthly_expense': str(data['monthly_totals']['total_expense']),
        'monthly_balance': str(data['monthly_totals']['balance']),
        'accounts': [
            {
                'id': item['account'].id,
                'name': item['account'].name,
                'type': item['account'].account_type,
                'currency': item['account'].currency,
                'balance': str(item['balance']),
            }
            for item in data['accounts_data']
        ],
        'budgets': [
            {
                'id': item['budget'].id,
                'category': item['budget'].category.name,
                'limit': str(item['budget'].amount),
                'spent': str(item['spent']),
                'percentage': item['percentage'],
                'status': item['status'],
            }
            for item in data['budgets_progress']
        ],
    })


def healthcheck(request: HttpRequest) -> JsonResponse:
    """Endpoint de salud para contenedores Docker y balanceadores."""
    return JsonResponse({'status': 'ok', 'service': 'budgetbuddy'})


#################################### ÁREA PERSONAL / PERFIL DE USUARIO ##############################

@login_required(login_url='login')
def profile_view(request: HttpRequest) -> HttpResponse:
    """
    Área Personal del usuario autenticado:
    - Permite actualizar nombre, apellido y correo electrónico.
    - Permite cambiar la contraseña de acceso (con re-hash Argon2id y manteniendo la sesión activa).
    """
    profile_form = UserProfileForm(instance=request.user)
    password_form = StyledPasswordChangeForm(user=request.user)

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'update_profile':
            profile_form = UserProfileForm(request.POST, instance=request.user)
            if profile_form.is_valid():
                profile_form.save()
                messages.success(request, "✅ Tu información personal fue actualizada correctamente.")
                return redirect('profile')
            else:
                messages.error(request, "Por favor revisa los errores en tu información personal.")
        elif action == 'change_password':
            password_form = StyledPasswordChangeForm(user=request.user, data=request.POST)
            if password_form.is_valid():
                user = password_form.save()
                update_session_auth_hash(request, user)
                messages.success(request, "🔒 Tu contraseña ha sido actualizada de forma segura.")
                return redirect('profile')
            else:
                messages.error(request, "No se pudo cambiar la contraseña. Verifica los datos ingresados.")

    user_tickets = SupportTicketRepository.list_by_user(request.user)[:5]
    hash_algorithm = request.user.password.split('$', 1)[0].upper() if '$' in request.user.password else 'ARGON2'

    return render(request, 'budget/profile.html', {
        'profile_form': profile_form,
        'password_form': password_form,
        'user_tickets': user_tickets,
        'hash_algorithm': hash_algorithm,
        'accounts_count': AccountRepository.list_by_user(request.user).count(),
        'categories_count': CategoryRepository.list_by_user(request.user).count(),
        'transactions_count': TransactionRepository.list_by_user(request.user).count(),
    })


#################################### SOPORTE Y SUGERENCIAS ##############################

def support_center(request: HttpRequest) -> HttpResponse:
    """
    Centro de Soporte y Buzón de Sugerencias.
    Accesible tanto por usuarios autenticados como por visitantes no autenticados
    (por ejemplo, desde la Landing Page o si tienen problemas para iniciar sesión).
    """
    initial_type = request.GET.get('type', 'SUGGESTION')
    if initial_type not in ('SUGGESTION', 'BUG', 'LOGIN_ISSUE', 'OTHER'):
        initial_type = 'SUGGESTION'

    if request.method == 'POST':
        form = SupportTicketForm(request.POST, user=request.user)
        if form.is_valid():
            ticket = form.save(commit=False)
            SupportTicketService.create_ticket(ticket, user=request.user)
            if ticket.ticket_type == 'SUGGESTION':
                messages.success(
                    request,
                    "💡 ¡Gracias por tu sugerencia! Nuestro equipo la revisará para futuras iteraciones de BudgetBuddy.",
                )
            else:
                messages.success(
                    request,
                    "🛠️ Hemos recibido tu reporte de soporte. Te contactaremos a la brevedad al correo indicado.",
                )
            return redirect('support_center')
    else:
        form = SupportTicketForm(user=request.user, initial={'ticket_type': initial_type})

    my_tickets = (
        SupportTicketRepository.list_by_user(request.user)
        if request.user.is_authenticated
        else []
    )

    return render(request, 'budget/support.html', {
        'form': form,
        'my_tickets': my_tickets,
    })


@login_required(login_url='login')
def admin_support_dashboard(request: HttpRequest) -> HttpResponse:
    """
    Panel exclusivo para administradores (staff/superuser) donde pueden revisar
    todas las sugerencias de producto y los tickets de soporte de los usuarios.
    """
    if not (request.user.is_staff or request.user.is_superuser):
        raise PermissionDenied("Acceso restringido a administradores del sitio.")

    ticket_type = request.GET.get('type') or None
    status = request.GET.get('status') or None

    tickets = SupportTicketRepository.list_all_for_admin(ticket_type=ticket_type, status=status)
    all_tickets = SupportTicketRepository.list_all_for_admin()

    return render(request, 'budget/admin_support.html', {
        'tickets': tickets,
        'selected_type': ticket_type or '',
        'selected_status': status or '',
        'total_suggestions': all_tickets.filter(ticket_type='SUGGESTION').count(),
        'total_bugs': all_tickets.filter(ticket_type__in=['BUG', 'LOGIN_ISSUE', 'OTHER']).count(),
        'open_count': all_tickets.filter(status='OPEN').count(),
        'planned_count': all_tickets.filter(status='PLANNED').count(),
    })


@login_required(login_url='login')
def admin_update_ticket(request: HttpRequest, pk: int) -> HttpResponse:
    """Permite al administrador cambiar el estado y dejar una respuesta en un ticket o sugerencia."""
    if not (request.user.is_staff or request.user.is_superuser):
        raise PermissionDenied("Acceso restringido a administradores del sitio.")

    ticket = SupportTicketRepository.get_by_id(pk)
    if request.method == 'POST':
        form = AdminTicketReviewForm(request.POST, instance=ticket)
        if form.is_valid():
            form.save()
            messages.success(request, f"Ticket #{ticket.pk} ('{ticket.subject}') actualizado a {ticket.get_status_display()}.")
    return redirect('admin_support_dashboard')

