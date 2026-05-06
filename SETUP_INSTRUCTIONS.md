# Quick Setup Instructions

## Step-by-Step Setup

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure Razorpay API Keys

**Option A: Using Environment Variables (Recommended)**
Create a `.env` file:
```
RAZORPAY_KEY_ID=your_key_id_here
RAZORPAY_KEY_SECRET=your_secret_key_here
```

**Option B: Edit settings.py directly**
Edit `exam_project/settings.py`:
```python
RAZORPAY_KEY_ID = 'your_razorpay_key_id'
RAZORPAY_KEY_SECRET = 'your_razorpay_key_secret'
```

Get your keys from: https://dashboard.razorpay.com/app/keys

### 3. Database Setup

**Option A: SQLite (Quick Start - Basic Login Only, No Google OAuth)**

1. Comment out socialaccount apps temporarily in `settings.py`:
   ```python
   # 'allauth.socialaccount',
   # 'allauth.socialaccount.providers.google',
   ```

2. Run migrations:
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

3. After migrations, uncomment the socialaccount lines if you want Google login later (will require PostgreSQL)

**Option B: PostgreSQL (Recommended - Full Features)**

**For PostgreSQL (Recommended - Full Features)**
1. Install PostgreSQL and psycopg2:
   ```bash
   pip install psycopg2-binary
   ```

2. Update `exam_project/settings.py`:
   ```python
   DATABASES = {
       'default': {
           'ENGINE': 'django.db.backends.postgresql',
           'NAME': 'exam_db',
           'USER': 'your_user',
           'PASSWORD': 'your_password',
           'HOST': 'localhost',
           'PORT': '5432',
       }
   }
   ```

3. Run migrations:
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

### 4. Create Superuser
```bash
python manage.py createsuperuser
```

### 5. Setup Site (For Google OAuth)
```bash
python manage.py shell
```

```python
from django.contrib.sites.models import Site
site = Site.objects.get(id=1)
site.domain = 'localhost:8000'
site.name = 'Exam Portal'
site.save()
exit()
```

### 6. Configure Google OAuth (Optional)

1. Go to https://console.cloud.google.com/
2. Create a new project
3. Enable Google+ API
4. Create OAuth 2.0 credentials
5. Add authorized redirect URI: `http://localhost:8000/accounts/google/login/callback/`
6. Go to Django admin: http://localhost:8000/admin/socialaccount/socialapp/
7. Add new Social Application:
   - Provider: Google
   - Name: Google
   - Client ID: (from Google Console)
   - Secret key: (from Google Console)
   - Sites: Select "Example.com"

### 7. Run Server
```bash
python manage.py runserver
```

### 8. Access the Application
- Login: http://localhost:8000/accounts/login/
- Admin: http://localhost:8000/admin/

## Important Notes

1. **Razorpay Keys**: Replace placeholder keys with your actual Razorpay API keys
2. **Google OAuth**: Optional but requires PostgreSQL for JSONField support
3. **Production**: 
   - Use PostgreSQL
   - Set DEBUG = False
   - Use environment variables for secrets
   - Enable HTTPS
   - Set SESSION_COOKIE_SECURE = True

## Troubleshooting

**Issue: JSONField error with SQLite**
- Solution: Use PostgreSQL for full features, or use SQLite only for basic login

**Issue: Google login not working**
- Check if Social Application is configured in admin
- Verify redirect URI matches Google Console settings
- Ensure Site domain is correct

**Issue: Payment not working**
- Verify Razorpay keys are correct
- Check Razorpay dashboard for transaction logs
- Ensure you're using test keys for testing

