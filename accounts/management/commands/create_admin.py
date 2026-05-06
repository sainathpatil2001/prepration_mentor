from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from getpass import getpass


class Command(BaseCommand):
    help = 'Create a new admin/superuser account'

    def add_arguments(self, parser):
        parser.add_argument(
            'username',
            type=str,
            help='Username for the new admin account'
        )
        parser.add_argument(
            '--email',
            type=str,
            help='Email for the admin account',
            default='admin@example.com'
        )
        parser.add_argument(
            '--password',
            type=str,
            help='Password (if not provided, will prompt securely)',
            default=None
        )

    def handle(self, *args, **options):
        username = options['username'].strip()
        email = options['email'].strip()
        password = options.get('password')

        # Check if user already exists
        if User.objects.filter(username__iexact=username).exists():
            self.stdout.write(
                self.style.ERROR(f'❌ User "{username}" already exists!')
            )
            return

        # Get password securely if not provided
        if not password:
            password = getpass(f'Enter password for "{username}": ')
            password_confirm = getpass('Confirm password: ')

            if password != password_confirm:
                self.stdout.write(
                    self.style.ERROR('❌ Passwords do not match!')
                )
                return

            if len(password) < 8:
                self.stdout.write(
                    self.style.ERROR('❌ Password must be at least 8 characters long!')
                )
                return

        # Create superuser
        try:
            user = User.objects.create_superuser(
                username=username,
                email=email,
                password=password
            )
            self.stdout.write(
                self.style.SUCCESS(
                    f'✅ Superuser "{username}" created successfully!'
                )
            )
            self.stdout.write(
                self.style.WARNING(
                    f'\nAdmin Details:\n'
                    f'  Username: {username}\n'
                    f'  Email: {email}\n'
                    f'  URL: /accounts/admin-login/\n'
                )
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Error creating user: {str(e)}')
            )
