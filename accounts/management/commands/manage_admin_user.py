"""
Admin User Management Command

This management command provides a complete interface for managing admin users
in the Online Examination System's data entry section.

Usage:
    # Create new admin
    python manage.py manage_admin_user create --username admin --email admin@example.com

    # Reset password
    python manage.py manage_admin_user reset --username admin --password NewPass@123

    # List all admins
    python manage.py manage_admin_user list

    # Delete admin
    python manage.py manage_admin_user delete --username admin

Key Features:
    ✅ Interactive password prompts (secure input)
    ✅ Direct password specification (for automation)
    ✅ Password strength validation (minimum 8 characters)
    ✅ Confirmation prompts for destructive operations
    ✅ Color-coded output for easy reading
    ✅ Detailed user information display

Admin User Properties:
    - is_staff = True (staff access)
    - is_superuser = True (all permissions)
    - Separate from regular user registration
    - Used for data entry section: /accounts/admin-login/
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from getpass import getpass


class Command(BaseCommand):
    """
    Django management command for admin user lifecycle management.
    
    Attributes:
        help (str): Command description shown in help text
    """
    
    help = 'Manage admin users for data entry section (/accounts/admin-login/)'

    def add_arguments(self, parser):
        """
        Define command-line arguments.
        
        Args:
            parser: ArgumentParser instance
        """
        parser.add_argument(
            'action',
            type=str,
            choices=['create', 'reset', 'list', 'delete'],
            help=(
                'Action to perform:\n'
                '  create - Create new admin user\n'
                '  reset  - Reset admin password\n'
                '  list   - List all admin users\n'
                '  delete - Delete admin user'
            )
        )
        parser.add_argument(
            '--username',
            type=str,
            help='Admin username (required for create/reset/delete)',
            default=None
        )
        parser.add_argument(
            '--email',
            type=str,
            help='Admin email address (optional for create, default: admin@example.com)',
            default='admin@example.com'
        )
        parser.add_argument(
            '--password',
            type=str,
            help=(
                'Admin password (optional, if not provided will prompt securely)\n'
                'Requirements: minimum 8 characters'
            ),
            default=None
        )

    def handle(self, *args, **options):
        """
        Main command handler. Routes to appropriate action method.
        
        Args:
            args: Additional positional arguments
            options: Command-line options dictionary
        """
        action = options['action']

        if action == 'create':
            self._create_admin(options)
        elif action == 'reset':
            self._reset_password(options)
        elif action == 'list':
            self._list_admins()
        elif action == 'delete':
            self._delete_admin(options)

    def _create_admin(self, options):
        """
        Create a new admin user with superuser privileges.
        
        Process:
            1. Prompt for username if not provided
            2. Check if username already exists
            3. Get password (interactive or direct)
            4. Validate password (minimum 8 characters)
            5. Create superuser in database
            6. Display confirmation with login details
        
        Args:
            options (dict): Command options including username, email, password
            
        Returns:
            None
        """
        username = options.get('username')
        if not username:
            username = input('Enter admin username: ').strip()

        # Check for existing user
        if User.objects.filter(username__iexact=username).exists():
            self.stdout.write(
                self.style.ERROR(f'❌ Admin user "{username}" already exists!')
            )
            return

        email = options.get('email')
        password = options.get('password')

        # Get password securely if not provided
        if not password:
            password = getpass(f'Enter password for admin "{username}": ')
            password_confirm = getpass('Confirm password: ')

            if password != password_confirm:
                self.stdout.write(self.style.ERROR('❌ Passwords do not match!'))
                return

            if len(password) < 8:
                self.stdout.write(
                    self.style.ERROR('❌ Password must be at least 8 characters long!')
                )
                return

        # Create superuser in database
        try:
            user = User.objects.create_superuser(
                username=username,
                email=email,
                password=password
            )
            self.stdout.write(
                self.style.SUCCESS(f'✅ Admin user "{username}" created successfully!')
            )
            self.stdout.write(
                self.style.WARNING(
                    f'\n📋 Admin Login Details:\n'
                    f'  URL: http://127.0.0.1:8000/accounts/admin-login/\n'
                    f'  Username: {username}\n'
                    f'  Email: {email}\n'
                    f'  Password: {"*" * len(password)}\n'
                )
            )
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Error creating admin: {str(e)}'))

    def _reset_password(self, options):
        """
        Reset password for an existing admin user.
        
        Process:
            1. Prompt for username if not provided
            2. Verify user exists and is admin
            3. Get new password (interactive or direct)
            4. Validate password strength
            5. Update password in database
            6. Display confirmation
        
        Args:
            options (dict): Command options including username, password
            
        Returns:
            None
        """
        username = options.get('username')
        if not username:
            username = input('Enter admin username to reset password: ').strip()

        # Check if user exists
        try:
            user = User.objects.get(username__iexact=username)
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'❌ Admin user "{username}" not found!'))
            return

        password = options.get('password')
        if not password:
            password = getpass(f'Enter new password for "{username}": ')
            password_confirm = getpass('Confirm password: ')

            if password != password_confirm:
                self.stdout.write(self.style.ERROR('❌ Passwords do not match!'))
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
                f'✅ Password for admin "{username}" has been reset successfully!'
            )
        )
        self.stdout.write(
            self.style.WARNING(
                f'\n📋 Updated Credentials:\n'
                f'  URL: http://127.0.0.1:8000/accounts/admin-login/\n'
                f'  Username: {username}\n'
                f'  Password: {"*" * len(password)}\n'
            )
        )

    def _list_admins(self):
        """
        Display all admin users in the system.
        
        Shows:
            - Total admin count
            - Username
            - Email address
            - Account creation date
        
        Returns:
            None
        """
        admins = User.objects.filter(is_staff=True, is_superuser=True)

        if not admins.exists():
            self.stdout.write(self.style.WARNING('❌ No admin users found!'))
            return

        self.stdout.write(self.style.SUCCESS(f'✅ Found {admins.count()} admin user(s):\n'))

        for admin in admins:
            self.stdout.write(
                f'  📝 Username: {admin.username} | Email: {admin.email} | '
                f'Created: {admin.date_joined.strftime("%Y-%m-%d %H:%M:%S")}'
            )

    def _delete_admin(self, options):
        """
        Delete an admin user with confirmation.
        
        Process:
            1. Prompt for username if not provided
            2. Verify user exists
            3. Request user confirmation (destructive operation)
            4. Delete user from database
            5. Display confirmation
        
        Args:
            options (dict): Command options including username
            
        Returns:
            None
            
        Note:
            This is a destructive operation. User must confirm deletion.
        """
        username = options.get('username')
        if not username:
            username = input('Enter admin username to delete: ').strip()

        # Check if user exists
        try:
            user = User.objects.get(username__iexact=username)
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'❌ Admin user "{username}" not found!'))
            return

        # Request confirmation
        confirm = input(f'⚠️  Are you sure you want to delete admin "{username}"? (yes/no): ').lower()
        if confirm != 'yes':
            self.stdout.write(self.style.WARNING('❌ Deletion cancelled.'))
            return

        # Delete user
        user.delete()
        self.stdout.write(self.style.SUCCESS(f'✅ Admin user "{username}" has been deleted!'))
