from django.core.management.base import BaseCommand
from django.contrib.auth.models import User


class Command(BaseCommand):
    help = 'List all users in the system'

    def handle(self, *args, **options):
        users = User.objects.all().values('id', 'username', 'email', 'is_staff', 'is_superuser', 'date_joined')
        
        if not users.exists():
            self.stdout.write(self.style.WARNING('❌ No users found in the system.'))
            return
        
        self.stdout.write(self.style.SUCCESS(f'\n✅ Found {users.count()} user(s):\n'))
        
        for user in users:
            role = []
            if user['is_superuser']:
                role.append('SUPERUSER')
            if user['is_staff']:
                role.append('STAFF')
            if not role:
                role.append('USER')
            
            role_str = ' | '.join(role)
            self.stdout.write(
                f"  ID: {user['id']} | Username: {user['username']} | Email: {user['email']} | Role: {role_str} | Joined: {user['date_joined']}"
            )
        
        self.stdout.write(self.style.SUCCESS('\n✅ Command completed.\n'))
