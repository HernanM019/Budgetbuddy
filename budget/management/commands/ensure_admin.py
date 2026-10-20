import os
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from budget.services import OnboardingService


class Command(BaseCommand):
    help = (
        "Crea o actualiza automáticamente un superusuario de administración a partir de las "
        "variables de entorno DJANGO_SUPERUSER_USERNAME, DJANGO_SUPERUSER_EMAIL y DJANGO_SUPERUSER_PASSWORD. "
        "Ideal para despliegues gratuitos en Render/Koyeb sin acceso a consola interactiva."
    )

    def handle(self, *args, **options):
        username = os.environ.get('DJANGO_SUPERUSER_USERNAME', '').strip()
        email = os.environ.get('DJANGO_SUPERUSER_EMAIL', '').strip()
        password = os.environ.get('DJANGO_SUPERUSER_PASSWORD', '').strip()

        if not username or not password:
            self.stdout.write(
                self.style.NOTICE(
                    "Variables DJANGO_SUPERUSER_USERNAME / DJANGO_SUPERUSER_PASSWORD no definidas; omitiendo creación de superusuario."
                )
            )
            return

        user, created = User.objects.get_or_create(
            username=username,
            defaults={
                'email': email,
                'is_staff': True,
                'is_superuser': True,
            },
        )
        needs_save = False
        if not user.is_staff or not user.is_superuser:
            user.is_staff = True
            user.is_superuser = True
            needs_save = True
        if email and user.email != email:
            user.email = email
            needs_save = True
        if created or not user.check_password(password):
            user.set_password(password)
            needs_save = True
        if needs_save:
            user.save()
        OnboardingService.setup_new_user(user)

        if created:
            self.stdout.write(self.style.SUCCESS(f"Superusuario '@{username}' creado y aprovisionado correctamente."))
        else:
            self.stdout.write(self.style.SUCCESS(f"Superusuario '@{username}' actualizado correctamente."))
