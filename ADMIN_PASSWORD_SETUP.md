# Admin Password Management Documentation

## Overview

The admin login section at **http://127.0.0.1:8000/accounts/admin-login/** is a **standalone authentication system** separate from the regular user registration and login. This is the data entry section where administrators can manage test questions and content.

## Key Differences

| Feature | Regular Users | Admin Users |
|---------|---------------|------------|
| **Login URL** | `/accounts/login/` | `/accounts/admin-login/` |
| **Access** | Take tests, view results | Create/edit tests, manage content |
| **Subscription Required** | Yes | No |
| **Model** | UserProfile + User | User (with is_staff=True) |
| **Dashboard** | Test results, scores | Content management dashboard |

---

## Admin User Management Commands

### Command: `manage_admin_user`

This is the primary command for managing admin users for the data entry section.

#### Location
```
accounts/management/commands/manage_admin_user.py
```

---

## Quick Start (5 Minutes)

### 1. Create First Admin User

```bash
cd /path/to/online-examination-system
python manage.py manage_admin_user create --username admin --email admin@example.com --password Admin@123456
```

**Output:**
```
✅ Admin user "admin" created successfully!

📋 Admin Login Details:
  URL: http://127.0.0.1:8000/accounts/admin-login/
  Username: admin
  Email: admin@example.com
  Password: ******************
```

### 2. Log In to Admin Dashboard

1. Visit: **http://127.0.0.1:8000/accounts/admin-login/**
2. Enter Username: `admin`
3. Enter Password: `Admin@123456`
4. Click **Login**

You're now in the **Admin Dashboard** where you can:
- ✅ Create new test sets
- ✅ Add questions
- ✅ Manage categories
- ✅ Publish/draft tests

---

## Complete Command Reference

### Create New Admin User

**Interactive Mode** (password prompt):
```bash
python manage.py manage_admin_user create --username newadmin --email newadmin@example.com
```

You'll be prompted:
```
Enter password for admin "newadmin": 
Confirm password: 
```

**Direct Mode** (password in command):
```bash
python manage.py manage_admin_user create --username newadmin --email newadmin@example.com --password NewPass@123456
```

---

### Reset Admin Password

**Interactive Mode**:
```bash
python manage.py manage_admin_user reset --username admin
```

You'll be prompted:
```
Enter new password for "admin": 
Confirm password: 
```

**Direct Mode**:
```bash
python manage.py manage_admin_user reset --username admin --password NewPassword@123456
```

---

### List All Admin Users

View all admin accounts in the system:

```bash
python manage.py manage_admin_user list
```

**Output Example:**
```
✅ Found 2 admin user(s):

  📝 Username: admin | Email: admin@example.com | Created: 2024-01-15 10:30:45
  📝 Username: dataentry | Email: dataentry@example.com | Created: 2024-01-16 14:22:10
```

---

### Delete Admin User

Remove an admin user (with confirmation):

```bash
python manage.py manage_admin_user delete --username oldadmin
```

You'll be prompted:
```
⚠️  Are you sure you want to delete admin "oldadmin"? (yes/no): yes
✅ Admin user "oldadmin" has been deleted!
```

---

## Management Command Details

### Arguments

| Argument | Required | Description |
|----------|----------|-------------|
| `action` | ✅ Yes | `create`, `reset`, `list`, or `delete` |
| `--username` | For most actions | Admin username |
| `--email` | No | Email address (default: `admin@example.com`) |
| `--password` | No | Password (if not provided, prompts securely) |

### Password Requirements

- ✅ **Minimum 8 characters**
- ✅ **Mix of uppercase and lowercase recommended**
- ✅ **Include numbers and special characters for security**
- ✅ **Avoid using username in password**

**Good Examples:**
- `Admin@2024Pass`
- `SecureDataEntry123!`
- `TestManager#2024`

**Poor Examples:**
- `admin` (too short)
- `12345678` (only numbers)
- `adminadmin` (repeating username)

---

## Alternative Methods

### Method 1: Django Shell (Direct Python)

If the management command doesn't work, use Django shell:

```bash
python manage.py shell
```

Then paste this code:

```python
from django.contrib.auth.models import User

# Create new admin
user = User.objects.create_superuser(
    username='admin',
    email='admin@example.com',
    password='Admin@123456'
)
print(f"✅ Admin user created: {user.username}")

# Reset existing admin password
user = User.objects.get(username='admin')
user.set_password('NewPassword@123456')
user.save()
print(f"✅ Password updated for: {user.username}")

# List all admins
admins = User.objects.filter(is_staff=True, is_superuser=True)
for admin in admins:
    print(f"  - {admin.username} ({admin.email})")

# Exit shell
exit()
```

---

### Method 2: Admin Dashboard (Web Interface)

If you have the admin password and are logged in:

1. Navigate to: **http://127.0.0.1:8000/accounts/admin-reset-password/**
2. Enter username of admin to reset
3. Enter new password
4. Confirm password
5. Click **Reset Password**

---

## Troubleshooting

### Error: "User 'admin' does not exist"

**Cause:** You're trying to reset a password for a non-existent admin.

**Solution:**
```bash
# First, list existing admins
python manage.py manage_admin_user list

# Then create if needed
python manage.py manage_admin_user create --username admin
```

---

### Error: "Password must be at least 8 characters long"

**Cause:** Your password is too short.

**Solution:** Use a password with 8+ characters:
```bash
python manage.py manage_admin_user reset --username admin --password MyNewPassword123!
```

---

### Error: "Passwords do not match"

**Cause:** Confirmation password was different from original.

**Solution:** Try again, ensure you type the password correctly both times:
```bash
python manage.py manage_admin_user reset --username admin
# Then carefully type password twice
```

---

### Error: "Admin user 'admin' already exists"

**Cause:** You're trying to create an admin that already exists.

**Solution:** Either reset the existing password or create with a different username:
```bash
# Reset existing password
python manage.py manage_admin_user reset --username admin

# OR create with different username
python manage.py manage_admin_user create --username admin2
```

---

## Security Best Practices

### ✅ DO:

- ✅ Use strong passwords (8+ characters, mix of types)
- ✅ Change password regularly (every 90 days)
- ✅ Keep credentials private and secure
- ✅ Use different passwords for different admins
- ✅ Log out after completing admin tasks
- ✅ Disable unused admin accounts

### ❌ DON'T:

- ❌ Share admin credentials via email or chat
- ❌ Use simple passwords like "123456" or "password"
- ❌ Write passwords in code or config files
- ❌ Reuse the same password across accounts
- ❌ Leave admin session open on shared computers

---

## Multi-Admin Setup

For a team of data entry personnel:

```bash
# Create admin 1
python manage.py manage_admin_user create --username admin_user1 --email user1@company.com --password User1@Pass2024

# Create admin 2
python manage.py manage_admin_user create --username admin_user2 --email user2@company.com --password User2@Pass2024

# Create admin 3
python manage.py manage_admin_user create --username admin_user3 --email user3@company.com --password User3@Pass2024

# View all
python manage.py manage_admin_user list
```

---

## Workflow Example

### Scenario: New Data Entry Person Joins

**Step 1: Create Admin Account**
```bash
python manage.py manage_admin_user create --username john_admin --email john@company.com
```
(Password will be prompted securely)

**Step 2: Share Login Details**
```
Admin Login URL: http://127.0.0.1:8000/accounts/admin-login/
Username: john_admin
Email: john@company.com
Password: [shared securely]
```

**Step 3: First Login**
- User visits the admin login URL
- Enters username and password
- Accesses the data entry dashboard

**Step 4: Password Change (Optional)**
User can change their password in profile settings after first login.

---

## Database Information

### Admin Users Table

- **Model:** Django `User` model
- **Filter:** `is_staff=True` and `is_superuser=True`
- **Table:** `auth_user`

### View Admin Records in Database

```bash
python manage.py shell
```

```python
from django.contrib.auth.models import User

# Get all admins
admins = User.objects.filter(is_staff=True, is_superuser=True)

# Print details
for admin in admins:
    print(f"Username: {admin.username}")
    print(f"Email: {admin.email}")
    print(f"Created: {admin.date_joined}")
    print(f"Last Login: {admin.last_login}")
    print("---")
```

---

## Support & Help

For issues or questions:

1. **Run the management command with help:**
   ```bash
   python manage.py manage_admin_user --help
   ```

2. **Check logs for errors:**
   ```bash
   # View recent Django logs
   tail -f logs/django.log
   ```

3. **Reset everything (emergency):**
   ```bash
   # Delete all admins and recreate
   python manage.py shell
   ```
   ```python
   from django.contrib.auth.models import User
   User.objects.filter(is_staff=True, is_superuser=True).delete()
   exit()
   ```

---

## Summary

| Task | Command |
|------|---------|
| Create Admin | `python manage.py manage_admin_user create --username admin --email admin@example.com --password Pass@123456` |
| Reset Password | `python manage.py manage_admin_user reset --username admin --password NewPass@123456` |
| List Admins | `python manage.py manage_admin_user list` |
| Delete Admin | `python manage.py manage_admin_user delete --username admin` |
| Login URL | `http://127.0.0.1:8000/accounts/admin-login/` |

---

**Last Updated:** 2024
**Version:** 1.0
