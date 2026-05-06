from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Create or update a demo staff user for the custom admin dashboard."

    def add_arguments(self, parser):
        parser.add_argument(
            '--username',
            default='demo_admin',
            help='Username for the demo admin user (default: demo_admin)',
        )
        parser.add_argument(
            '--password',
            default='DemoAdmin@123',
            help='Password for the demo admin user (default: DemoAdmin@123)',
        )
        parser.add_argument(
            '--email',
            default='demo-admin@example.com',
            help='Email for the demo admin user (default: demo-admin@example.com)',
        )

    def handle(self, *args, **options):
        User = get_user_model()
        username = options['username']
        password = options['password']
        email = options['email']

        user, created = User.objects.get_or_create(
            username=username,
            defaults={
                'email': email,
            },
        )

        if created:
            self.stdout.write(self.style.SUCCESS(f'Created demo admin user "{username}".'))
        else:
            self.stdout.write(self.style.WARNING(f'User "{username}" already exists; updating credentials.'))

        user.email = email
        user.is_staff = True
        user.is_superuser = False
        user.set_password(password)
        user.save()

        self.stdout.write(self.style.SUCCESS('Demo admin credentials:'))
        self.stdout.write(self.style.SUCCESS(f'  Username: {username}'))
        self.stdout.write(self.style.SUCCESS(f'  Password: {password}'))
        self.stdout.write(self.style.NOTICE('Remember to change these credentials in production.'))

