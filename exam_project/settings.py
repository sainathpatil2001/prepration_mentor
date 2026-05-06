"""
Code Design and Developed By: Sainath Ravindra Patil, Quick Builds Solutions
Contact: +91 7219585666
Email: patilsainath517@gmail.com
Location: Jamner, Jalgaon, Maharashtra, India
Date : 25 Martch 2026 wensday.
License: All rights reserved. Code modification and commercial use are strictly prohibited.
"""
from pathlib import Path
import os

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/4.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-7a)&c-01*n%+91!yf96k%b!^gb(igqo@b+z*q=g8rk)dibbpy6')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get('DEBUG', 'True') == 'True'

ALLOWED_HOSTS = ['*']


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',
    
    # Third party apps
    'allauth',
    'allauth.account',
    'crispy_forms',
    'crispy_bootstrap5',
    
    # Local apps
    'accounts',
    'support',
    
    # API
    'rest_framework',
    'rest_framework.authtoken',
    'django_filters',
    'api',
]


MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware', # Added WhiteNoise
    'django.middleware.gzip.GZipMiddleware', # Added GZip
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'allauth.account.middleware.AccountMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'accounts.middleware.SingleSessionMiddleware',  # Custom middleware for single session
]


ROOT_URLCONF = 'exam_project.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'django.template.context_processors.static',
                'exam_project.context_processors.installed_apps',
            ],
        },
    },
]

WSGI_APPLICATION = 'exam_project.wsgi.application'


# Database
# https://docs.djangoproject.com/en/4.2/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
        'CONN_MAX_AGE': 600, # Persistent connections for 10 minutes
    }
}

# Social login disabled: remove socialaccount providers


# Password validation
# https://docs.djangoproject.com/en/4.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/4.2/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/4.2/howto/static-files/

STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
# https://docs.djangoproject.com/en/4.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Authentication settings
AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
]

SITE_ID = 1

# Allauth settings (using username/password only)
ACCOUNT_LOGIN_METHODS = {'email', 'username'}
ACCOUNT_SIGNUP_FIELDS = ['email*', 'username*', 'password1*', 'password2*']
ACCOUNT_EMAIL_VERIFICATION = 'none'  # Using custom OTP verification
LOGIN_REDIRECT_URL = '/dashboard/'
LOGOUT_REDIRECT_URL = '/accounts/login/'

# Email settings (Gmail/Google Workspace SMTP - uses Google App credits)
# To set up Gmail SMTP:
# 1. Go to your Google Account: https://myaccount.google.com/
# 2. Enable 2-Step Verification if not already enabled
# 3. Go to App Passwords: https://myaccount.google.com/apppasswords
# 4. Generate an App Password for "Mail" and select "Other (Custom name)" as device
# 5. Enter "Django Exam Portal" and click Generate
# 6. Copy the 16-character password (no spaces) and set it as EMAIL_HOST_PASSWORD
# 7. Set EMAIL_HOST_USER to your Gmail address (e.g., 'yourname@gmail.com')
EMAIL_BACKEND = os.environ.get('EMAIL_BACKEND', 'django.core.mail.backends.smtp.EmailBackend')
EMAIL_HOST = os.environ.get('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', '587'))
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', 'patilsainath517@gmail.com')  # Your Gmail address (e.g., 'yourname@gmail.com')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', 'yfho qsvr gswq vevi')  # Your Gmail App Password (16 characters)
EMAIL_USE_TLS = os.environ.get('EMAIL_USE_TLS', 'True').lower() == 'true'
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', EMAIL_HOST_USER or 'noreply@exam-portal.local')

# Razorpay Settings
# Add your API keys here or set as environment variables
RAZORPAY_KEY_ID = os.environ.get('RAZORPAY_KEY_ID', 'rzp_live_Rb7oRm9361HECE')
RAZORPAY_KEY_SECRET = os.environ.get('RAZORPAY_KEY_SECRET', '6qVrdhH9VX3umJXjI9Pp2OOb')

# Security settings
SESSION_COOKIE_SECURE = False  # Set to True in production with HTTPS
SESSION_COOKIE_HTTPONLY = True
SESSION_EXPIRE_AT_BROWSER_CLOSE = False
SESSION_COOKIE_AGE = 86400  # 24 hours

# Caching Configuration
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.filebased.FileBasedCache',
        'LOCATION': BASE_DIR / 'django_cache',
        'TIMEOUT': 300, # 5 minutes default
        'OPTIONS': {
            'MAX_ENTRIES': 1000
        }
    }
}

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.TokenAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_FILTER_BACKENDS': ['django_filters.rest_framework.DjangoFilterBackend'],
}

ALLOWED_HOSTS = [
    '*'
]

#ng rock setup
# Use the URL shown in your error message
CSRF_TRUSTED_ORIGINS = [
    'https://berniece-unnarrated-arbitrarily.ngrok-free.dev', 'http://10.111.72.249:8000', 'http://127.0.0.1:8000'
]
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# Crispy Forms
CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"
CRISPY_TEMPLATE_PACK = "bootstrap5"

