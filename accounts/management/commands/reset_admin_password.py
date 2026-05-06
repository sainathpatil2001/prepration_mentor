from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from getpass import getpass


class Command(BaseCommand):
    help = 'Reset a user password securely'

    def add_arguments(self, parser):
        parser.add_argument(
            'username',
            type=str,
            help='Username of the account to reset password for'
        )
        parser.add_argument(
            '--password',
            type=str,
            help='New password (if not provided, will prompt securely)',
            default=None
        )

    def handle(self, *args, **options):
        username = options['username'].strip()
        password = options.get('password')

        # Check if user exists
        try:
            user = User.objects.get(username__iexact=username)
        except User.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f'❌ User "{username}" does not exist.')
            )
            return

        # Get password securely if not provided via command line
        if not password:
            password = getpass(f'Enter new password for "{username}": ')
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

        # Update password
        user.set_password(password)
        user.save()

        self.stdout.write(
            self.style.SUCCESS(
                f'✅ Password for "{username}" has been reset successfully!'
            )
        )
        self.stdout.write(
            self.style.WARNING(
                'Note: User will need to log in again with the new password.'
            )
        )
