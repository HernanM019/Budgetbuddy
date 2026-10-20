from datetime import date, timedelta
from decimal import Decimal
from django.contrib.auth.models import User
from django.core import mail
from django.core.cache import cache
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import Account, Budget, Category, SupportTicket, Transaction
from .repositories import AccountRepository
from .services import OnboardingService, TransactionService


class LandingAndAuthTests(TestCase):
    """Pruebas de Landing Page, Registro, Hashing Argon2, Redirecciones y Rate Limiting."""

    def setUp(self):
        cache.clear()

    def test_landing_page_renders_for_anonymous_user(self):
        response = self.client.get(reverse('landing_page'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'BudgetBuddy')
        self.assertContains(response, reverse('register'))

    def test_landing_page_redirects_authenticated_user_to_dashboard(self):
        user = User.objects.create_user(username='alice', password='StrongPassword123!')
        self.client.force_login(user)
        response = self.client.get(reverse('landing_page'))
        self.assertRedirects(response, reverse('dashboard'))

    def test_registration_uses_argon2_and_provisions_defaults(self):
        response = self.client.post(reverse('register'), {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password1': 'Sup3rS3cur3P@ss!',
            'password2': 'Sup3rS3cur3P@ss!',
        })
        self.assertRedirects(response, reverse('dashboard'))
        user = User.objects.get(username='newuser')
        self.assertTrue(user.password.startswith('argon2$'))
        self.assertTrue(Account.objects.filter(user=user, name='Cuenta Principal').exists())
        self.assertGreaterEqual(Category.objects.filter(user=user).count(), 5)

    def test_login_rate_limiting_blocks_brute_force(self):
        User.objects.create_user(username='victim', password='CorrectPassword123!')
        login_url = reverse('login')

        for _ in range(5):
            resp = self.client.post(login_url, {'username': 'victim', 'password': 'WrongPassword!'})
            self.assertEqual(resp.status_code, 200)

        # El 6to intento debe ser bloqueado con HTTP 429 Too Many Requests
        blocked_resp = self.client.post(login_url, {'username': 'victim', 'password': 'CorrectPassword123!'})
        self.assertEqual(blocked_resp.status_code, 429)


class MultiUserIsolationTests(TestCase):
    """
    Pruebas críticas de Aislamiento Multi-Usuario (Data Segregation & IDOR Prevention).
    Garantiza que ningún usuario pueda ver, editar, eliminar o inyectar recursos de otro usuario.
    """

    def setUp(self):
        cache.clear()
        self.user_a = User.objects.create_user(username='user_a', password='PasswordA123!')
        self.user_b = User.objects.create_user(username='user_b', password='PasswordB123!')

        self.acc_a = OnboardingService.setup_new_user(self.user_a)
        self.acc_b = OnboardingService.setup_new_user(self.user_b)

        self.cat_a = Category.objects.filter(user=self.user_a).first()
        self.cat_b = Category.objects.filter(user=self.user_b).first()

        self.tx_a = Transaction.objects.create(
            user=self.user_a,
            account=self.acc_a,
            category=self.cat_a,
            type='EXPENSE',
            amount=Decimal('150.00'),
            date=date.today(),
            description='Secreto de User A',
        )
        self.budget_a = Budget.objects.create(
            user=self.user_a,
            category=self.cat_a,
            amount=Decimal('500.00'),
            month=date.today().month,
            year=date.today().year,
        )

    def test_unauthenticated_access_to_all_protected_routes_redirects_to_login(self):
        protected_urls = [
            reverse('dashboard'),
            reverse('transaction_list'),
            reverse('add_transaction'),
            reverse('transfer_funds'),
            reverse('edit_transaction', args=[self.tx_a.pk]),
            reverse('delete_transaction', args=[self.tx_a.pk]),
            reverse('account_list'),
            reverse('category_list'),
            reverse('budget_list'),
            reverse('api_summary'),
        ]
        for url in protected_urls:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 302, f"La ruta {url} no redirigió a login")
            self.assertIn(reverse('login'), response.url)

    def test_user_b_cannot_see_user_a_transactions_in_list_or_dashboard(self):
        self.client.force_login(self.user_b)
        resp_list = self.client.get(reverse('transaction_list'))
        self.assertNotContains(resp_list, 'Secreto de User A')

        resp_dash = self.client.get(reverse('dashboard'))
        self.assertNotContains(resp_dash, 'Secreto de User A')

    def test_user_b_cannot_delete_user_a_transaction_idor_protection(self):
        self.client.force_login(self.user_b)
        response = self.client.post(reverse('delete_transaction', args=[self.tx_a.pk]))
        self.assertEqual(response.status_code, 404)
        self.assertTrue(Transaction.objects.filter(pk=self.tx_a.pk).exists())

    def test_user_b_cannot_edit_user_a_transaction_idor_protection(self):
        self.client.force_login(self.user_b)
        response = self.client.post(reverse('edit_transaction', args=[self.tx_a.pk]), {
            'type': 'INCOME',
            'account': self.acc_b.pk,
            'category': self.cat_b.pk,
            'amount': '9999.00',
            'date': date.today().isoformat(),
            'description': 'Hackeado',
        })
        self.assertEqual(response.status_code, 404)
        self.tx_a.refresh_from_db()
        self.assertEqual(self.tx_a.amount, Decimal('150.00'))

    def test_user_b_cannot_edit_or_delete_user_a_category_account_or_budget(self):
        self.client.force_login(self.user_b)
        self.assertEqual(self.client.post(reverse('delete_category', args=[self.cat_a.pk])).status_code, 404)
        self.assertEqual(self.client.post(reverse('edit_category', args=[self.cat_a.pk]), {'name': 'X'}).status_code, 404)
        self.assertEqual(self.client.post(reverse('delete_account', args=[self.acc_a.pk])).status_code, 404)
        self.assertEqual(self.client.post(reverse('delete_budget', args=[self.budget_a.pk])).status_code, 404)

    def test_user_b_cannot_create_transaction_using_user_a_category_or_account(self):
        self.client.force_login(self.user_b)
        response = self.client.post(reverse('add_transaction'), {
            'type': 'EXPENSE',
            'account': self.acc_a.pk,
            'category': self.cat_a.pk,
            'amount': '50.00',
            'date': date.today().isoformat(),
            'description': 'Intento Cross-Tenant',
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Transaction.objects.filter(description='Intento Cross-Tenant').exists())

        # Y en capa de servicios lanza PermissionDenied
        with self.assertRaises(PermissionDenied):
            bad_tx = Transaction(
                user=self.user_b,
                account=self.acc_a,
                category=self.cat_a,
                type='EXPENSE',
                amount=Decimal('50.00'),
                date=date.today(),
            )
            TransactionService.save_transaction(self.user_b, bad_tx)


class FinancialDomainTests(TestCase):
    """Pruebas del módulo financiero central: balances, transferencias, presupuestos y validaciones."""

    def setUp(self):
        self.user = User.objects.create_user(username='fin_user', password='Password123!')
        self.main_account = OnboardingService.setup_new_user(self.user)
        self.savings_account = Account.objects.create(
            user=self.user,
            name='Caja de Ahorros',
            account_type='SAVINGS',
            currency='USD',
            initial_balance=Decimal('100.00'),
        )
        self.income_cat = Category.objects.filter(user=self.user, category_type='INCOME').first()
        self.expense_cat = Category.objects.filter(user=self.user, category_type='EXPENSE').first()
        self.client.force_login(self.user)

    def test_income_expense_and_inter_account_transfer_balances(self):
        # 1. Registrar ingreso de $1000 en Cuenta Principal
        self.client.post(reverse('add_transaction'), {
            'type': 'INCOME',
            'account': self.main_account.pk,
            'category': self.income_cat.pk,
            'amount': '1000.00',
            'date': date.today().isoformat(),
            'description': 'Sueldo mensual',
        })
        # 2. Registrar gasto de $200 en Cuenta Principal
        self.client.post(reverse('add_transaction'), {
            'type': 'EXPENSE',
            'account': self.main_account.pk,
            'category': self.expense_cat.pk,
            'amount': '200.00',
            'date': date.today().isoformat(),
            'description': 'Compra supermercado',
        })
        # 3. Transferir $300 desde Cuenta Principal hacia Caja de Ahorros
        self.client.post(reverse('transfer_funds'), {
            'source_account': self.main_account.pk,
            'destination_account': self.savings_account.pk,
            'amount': '300.00',
            'date': date.today().isoformat(),
            'description': 'Ahorro del mes',
        })

        main_bal = AccountRepository.calculate_account_balance(self.user, self.main_account)
        savings_bal = AccountRepository.calculate_account_balance(self.user, self.savings_account)

        # Cuenta Principal: 0 + 1000 - 200 - 300 = 500
        self.assertEqual(main_bal, Decimal('500.00'))
        # Caja de Ahorros: 100 (inicial) + 300 (transferencia) = 400
        self.assertEqual(savings_bal, Decimal('400.00'))

    def test_budget_progress_and_alert_thresholds(self):
        today = date.today()
        self.client.post(reverse('add_budget'), {
            'category': self.expense_cat.pk,
            'amount': '500.00',
            'month': today.month,
            'year': today.year,
        })
        # Gastamos $450 (90% del presupuesto -> estado 'warning')
        Transaction.objects.create(
            user=self.user,
            account=self.main_account,
            category=self.expense_cat,
            type='EXPENSE',
            amount=Decimal('450.00'),
            date=today,
        )

        api_resp = self.client.get(reverse('api_summary'))
        self.assertEqual(api_resp.status_code, 200)
        payload = api_resp.json()
        self.assertEqual(len(payload['budgets']), 1)
        self.assertEqual(payload['budgets'][0]['percentage'], 90.0)
        self.assertEqual(payload['budgets'][0]['status'], 'warning')

    def test_rejects_future_date_and_duplicate_category_cleanly(self):
        future_date = (date.today() + timedelta(days=5)).isoformat()
        resp = self.client.post(reverse('add_transaction'), {
            'type': 'EXPENSE',
            'account': self.main_account.pk,
            'category': self.expense_cat.pk,
            'amount': '100.00',
            'date': future_date,
        })
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(Transaction.objects.filter(user=self.user).count(), 0)

        # Intentar crear una categoría con nombre duplicado debe devolver error de formulario (200), nunca 500
        dup_resp = self.client.post(reverse('add_category'), {
            'name': self.expense_cat.name,
            'category_type': 'EXPENSE',
            'color': '#000000',
        })
        self.assertEqual(dup_resp.status_code, 200)
        self.assertContains(dup_resp, 'Ya tienes una categoría registrada con este nombre')

    def test_healthcheck_endpoint(self):
        resp = self.client.get(reverse('healthcheck'))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()['status'], 'ok')


class ProfileAndSupportTests(TestCase):
    """Pruebas del Área Personal (/profile/) y del Centro de Soporte y Sugerencias (/support/)."""

    def setUp(self):
        self.user_a = User.objects.create_user(
            username='carlos',
            email='carlos@old.com',
            password='OldPassword123!',
        )
        self.user_b = User.objects.create_user(
            username='maria',
            email='maria@example.com',
            password='MariaPassword123!',
        )
        self.admin_user = User.objects.create_superuser(
            username='admin_boss',
            email='admin@budgetbuddy.com',
            password='AdminPassword123!',
        )

    def test_user_can_update_personal_info_and_email(self):
        self.client.force_login(self.user_a)
        resp = self.client.post(reverse('profile'), {
            'action': 'update_profile',
            'first_name': 'Carlos',
            'last_name': 'Gómez',
            'email': 'carlos.nuevo@example.com',
        })
        self.assertRedirects(resp, reverse('profile'))
        self.user_a.refresh_from_db()
        self.assertEqual(self.user_a.first_name, 'Carlos')
        self.assertEqual(self.user_a.email, 'carlos.nuevo@example.com')

    def test_user_can_change_password_and_stays_logged_in(self):
        self.client.force_login(self.user_a)
        resp = self.client.post(reverse('profile'), {
            'action': 'change_password',
            'old_password': 'OldPassword123!',
            'new_password1': 'NewSuperSecure456!',
            'new_password2': 'NewSuperSecure456!',
        })
        self.assertRedirects(resp, reverse('profile'))
        self.user_a.refresh_from_db()
        self.assertTrue(self.user_a.check_password('NewSuperSecure456!'))
        self.assertTrue(self.user_a.password.startswith('argon2$'))
        # Verificar que la sesión sigue activa tras cambiar la contraseña
        dash_resp = self.client.get(reverse('dashboard'))
        self.assertEqual(dash_resp.status_code, 200)

    def test_anonymous_visitor_can_submit_support_ticket_from_landing(self):
        resp = self.client.post(reverse('support_center'), {
            'ticket_type': 'LOGIN_ISSUE',
            'contact_name': 'Visitante',
            'contact_email': 'visitante@test.com',
            'subject': 'No puedo entrar a mi cuenta',
            'message': 'Olvidé mi usuario y necesito ayuda.',
        })
        self.assertRedirects(resp, reverse('support_center'))
        self.assertTrue(SupportTicket.objects.filter(contact_email='visitante@test.com', ticket_type='LOGIN_ISSUE').exists())

    def test_authenticated_suggestions_are_isolated_and_admin_can_moderate(self):
        self.client.force_login(self.user_a)
        self.client.post(reverse('support_center'), {
            'ticket_type': 'SUGGESTION',
            'contact_name': 'Carlos',
            'contact_email': 'carlos@old.com',
            'subject': 'Modo oscuro automático',
            'message': 'Sería genial agregar un botón de modo oscuro en el dashboard.',
        })
        ticket = SupportTicket.objects.get(subject='Modo oscuro automático')
        self.assertEqual(ticket.user, self.user_a)

        # Usuario B no puede ver las sugerencias enviadas por Usuario A ni entrar al panel admin
        self.client.force_login(self.user_b)
        resp_b = self.client.get(reverse('support_center'))
        self.assertNotContains(resp_b, 'Modo oscuro automático')
        self.assertEqual(self.client.get(reverse('admin_support_dashboard')).status_code, 403)

        # El administrador sí puede verla y planificarla en el roadmap con respuesta
        self.client.force_login(self.admin_user)
        admin_resp = self.client.get(reverse('admin_support_dashboard'))
        self.assertEqual(admin_resp.status_code, 200)
        self.assertContains(admin_resp, 'Modo oscuro automático')

        self.client.post(reverse('admin_update_ticket', args=[ticket.pk]), {
            'status': 'PLANNED',
            'admin_response': '¡Excelente idea! La incluiremos en la versión 1.1.',
        })
        ticket.refresh_from_db()
        self.assertEqual(ticket.status, 'PLANNED')
        self.assertIn('versión 1.1', ticket.admin_response)

    def test_new_ticket_sends_automatic_email_only_to_staff_with_email(self):
        # Staff con email registrado (debe recibir)
        staff_with_email = User.objects.create_user(
            username='staff_alert',
            email='staff@budgetbuddy.com',
            password='StaffPassword123!',
            is_staff=True,
        )
        # Staff SIN email registrado (no debe generar destinatario vacío)
        User.objects.create_user(
            username='staff_no_email',
            email='',
            password='StaffPassword123!',
            is_staff=True,
        )
        mail.outbox.clear()

        self.client.post(reverse('support_center'), {
            'ticket_type': 'BUG',
            'contact_name': 'Laura',
            'contact_email': 'laura@cliente.com',
            'subject': 'Error al exportar reporte',
            'message': 'Cuando presiono exportar aparece un error en pantalla.',
        })

        self.assertEqual(len(mail.outbox), 1)
        sent_email = mail.outbox[0]

        # Verificar que el Subject contiene el motivo seleccionado para filtrado por carpetas
        self.assertIn('[BudgetBuddy | 🐛 Falla o Error Técnico]', sent_email.subject)
        self.assertIn('Error al exportar reporte', sent_email.subject)

        # Verificar que el cuerpo contiene todo el detalle del ticket
        self.assertIn('Cuando presiono exportar aparece un error en pantalla.', sent_email.body)
        self.assertIn('Laura <laura@cliente.com>', sent_email.body)
        self.assertIn('🐛 Falla o Error Técnico (BUG)', sent_email.body)

        # Verificar destinatarios: solo admin_boss y staff_with_email (nunca usuarios comunes ni staff sin email)
        self.assertCountEqual(
            sent_email.to,
            [self.admin_user.email, staff_with_email.email],
        )
        self.assertNotIn(self.user_a.email, sent_email.to)
        self.assertNotIn(self.user_b.email, sent_email.to)


@override_settings(CELERY_TASK_ALWAYS_EAGER=True)
class AdvancedFeaturesAndDRFTests(TestCase):
    """
    Pruebas de:
    1. Exportación e Importación de Movimientos en CSV (ETL).
    2. Alertas automáticas de Presupuesto por Email vía Celery (80%+ / 100%+).
    3. API REST con Django REST Framework, Autenticación JWT, Aislamiento y Swagger Docs.
    """

    def setUp(self):
        self.user_a = User.objects.create_user(
            username='api_user_a',
            email='user_a@budgetbuddy.com',
            password='ApiPassword123!',
        )
        self.user_b = User.objects.create_user(
            username='api_user_b',
            email='user_b@budgetbuddy.com',
            password='ApiPassword123!',
        )
        self.acc_a = OnboardingService.setup_new_user(self.user_a)
        self.acc_b = OnboardingService.setup_new_user(self.user_b)
        self.cat_a = Category.objects.filter(user=self.user_a, category_type='EXPENSE').first()

    def test_csv_export_and_import_workflow(self):
        self.client.force_login(self.user_a)
        csv_data = (
            "Fecha,Tipo,Categoría,Monto,Descripción\n"
            f"{date.today().isoformat()},INCOME,Salario,2500.00,Sueldo Octubre\n"
            f"{date.today().isoformat()},EXPENSE,Supermercado Nuevo,320.50,Compra mensual\n"
        )
        uploaded = SimpleUploadedFile(
            "movimientos.csv",
            csv_data.encode('utf-8'),
            content_type="text/csv",
        )
        resp_import = self.client.post(reverse('import_transactions_csv'), {
            'account_id': self.acc_a.pk,
            'csv_file': uploaded,
        })
        self.assertRedirects(resp_import, reverse('transaction_list'))
        self.assertEqual(Transaction.objects.filter(user=self.user_a).count(), 2)
        self.assertTrue(Category.objects.filter(user=self.user_a, name='Supermercado Nuevo').exists())

        # Exportar a CSV y verificar que contiene los registros importados
        resp_export = self.client.get(reverse('export_transactions_csv'))
        self.assertEqual(resp_export.status_code, 200)
        content = resp_export.content.decode('utf-8-sig')
        self.assertIn('Sueldo Octubre', content)
        self.assertIn('320.50', content)

    def test_celery_budget_alert_email_triggered_when_spending_reaches_80_percent(self):
        today = date.today()
        Budget.objects.create(
            user=self.user_a,
            category=self.cat_a,
            amount=Decimal('1000.00'),
            month=today.month,
            year=today.year,
        )
        mail.outbox.clear()

        # Registrar gasto de $850 (85% del presupuesto) a través de TransactionService
        tx = Transaction(
            user=self.user_a,
            account=self.acc_a,
            category=self.cat_a,
            type='EXPENSE',
            amount=Decimal('850.00'),
            date=today,
            description='Gasto que activa umbral de alerta',
        )
        TransactionService.save_transaction(self.user_a, tx)

        self.assertEqual(len(mail.outbox), 1)
        alert_email = mail.outbox[0]
        self.assertIn('ALERTA DE PRESUPUESTO', alert_email.subject)
        self.assertIn('85.0%', alert_email.body)
        self.assertEqual(alert_email.to, [self.user_a.email])

    def test_drf_jwt_authentication_and_multi_tenant_api_isolation(self):
        # Crear transacción de User A
        tx_a = Transaction.objects.create(
            user=self.user_a,
            account=self.acc_a,
            category=self.cat_a,
            type='EXPENSE',
            amount=Decimal('99.00'),
            date=date.today(),
            description='Transacción privada API User A',
        )

        # Obtener token JWT para User B
        token_resp = self.client.post(reverse('token_obtain_pair'), {
            'username': 'api_user_b',
            'password': 'ApiPassword123!',
        })
        self.assertEqual(token_resp.status_code, 200)
        access_token = token_resp.json()['access']
        auth_headers = {'HTTP_AUTHORIZATION': f'Bearer {access_token}'}

        # User B consulta /api/v1/transactions/ -> no debe ver la transacción de User A
        list_resp = self.client.get('/api/v1/transactions/', **auth_headers)
        self.assertEqual(list_resp.status_code, 200)
        self.assertEqual(list_resp.json()['count'], 0)

        # User B intenta acceder o borrar el detalle de la transacción de User A por ID -> 404
        detail_resp = self.client.get(f'/api/v1/transactions/{tx_a.pk}/', **auth_headers)
        self.assertEqual(detail_resp.status_code, 404)

        # Documentación Swagger UI accesible para usuario autenticado
        docs_resp = self.client.get(reverse('api_docs'), **auth_headers)
        self.assertEqual(docs_resp.status_code, 200)



