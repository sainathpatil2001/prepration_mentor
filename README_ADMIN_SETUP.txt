================================================================================
                    ADMIN PASSWORD SETUP - QUICK GUIDE
================================================================================

LOCATION: Admin Login at http://127.0.0.1:8000/accounts/admin-login/

KEY FACTS:
  • SEPARATE from regular user login
  • Used for data entry / content management
  • Only admins can create/edit test questions
  • Requires is_staff and is_superuser privileges

================================================================================
                         QUICK START (5 MINUTES)
================================================================================

STEP 1: CREATE ADMIN USER
  Command: python manage.py manage_admin_user create --username admin

  Output will show:
    ✅ Admin user "admin" created successfully!
    📋 Admin Login Details:
       URL: http://127.0.0.1:8000/accounts/admin-login/
       Username: admin
       Email: admin@example.com
       Password: [securely stored]

STEP 2: LOGIN TO ADMIN DASHBOARD
  URL: http://127.0.0.1:8000/accounts/admin-login/
  Username: admin
  Password: [use password from Step 1]

STEP 3: START MANAGING CONTENT
  • Create test sets
  • Add questions
  • Manage categories
  • Publish tests

================================================================================
                          COMMON COMMANDS
================================================================================

CREATE ADMIN:
  python manage.py manage_admin_user create --username admin --email admin@example.com

RESET PASSWORD:
  python manage.py manage_admin_user reset --username admin --password NewPass@123456

LIST ALL ADMINS:
  python manage.py manage_admin_user list

DELETE ADMIN:
  python manage.py manage_admin_user delete --username admin

================================================================================
                       PASSWORD REQUIREMENTS
================================================================================

✅ DO:
  • Use 8+ characters minimum
  • Mix uppercase and lowercase
  • Include numbers and special characters
  • Use unique passwords for each admin

❌ DON'T:
  • Use simple passwords (123456, password)
  • Share credentials via email
  • Use username in password
  • Reuse passwords

Good Examples:
  • Admin@2024Pass
  • SecureDataEntry123!
  • TestManager#2024

================================================================================
                      TROUBLESHOOTING
================================================================================

ERROR: "User 'admin' does not exist"
  SOLUTION: python manage.py manage_admin_user create --username admin

ERROR: "Password must be at least 8 characters"
  SOLUTION: Use password with 8+ characters
  python manage.py manage_admin_user reset --username admin --password MyNewPassword123!

ERROR: "Admin user 'admin' already exists"
  SOLUTION: List existing admins first
  python manage.py manage_admin_user list

For detailed documentation, see: ADMIN_PASSWORD_SETUP.md

================================================================================
                           NEED HELP?
================================================================================

COMMAND HELP:
  python manage.py manage_admin_user --help

MANAGEMENT COMMAND FILE:
  accounts/management/commands/manage_admin_user.py

FULL DOCUMENTATION:
  ADMIN_PASSWORD_SETUP.md

ADMIN LOGIN URL:
  http://127.0.0.1:8000/accounts/admin-login/

================================================================================
================================================================================
