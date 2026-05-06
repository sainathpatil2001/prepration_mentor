# 📝 Preparation Mentor — Online Examination System

A full-featured, web-based online examination platform built with **Django** for creating, delivering, and grading competitive exams. Designed for coaching institutes, educators, and self-study students preparing for Banking, State Services, and other competitive examinations.

---

## ✨ Features

### 🎓 Student Features
- **User Registration & Login** — Secure signup/login with email and username via Django Allauth
- **Email Verification (OTP)** — Custom OTP-based email verification system
- **Password Reset** — Forgot password flow with secure email-based reset link and OTP
- **Dashboard** — Personalized student dashboard with exam stats and activity summary
- **Profile Management** — Edit personal details, upload profile picture (auto-compressed & resized)
- **Browse & Search Tests** — Filter exams by category (Banking, State Services, etc.)
- **Bookmark Tests** — Save/bookmark tests for later access
- **Timed Exam Interface** — Real-time countdown timer with auto-submit on time-up
- **Practice Mode** — Untimed practice mode for self-study
- **Question Navigation Panel** — Mark questions for review, skip, and navigate freely
- **Negative Marking Support** — Configurable rules (1/4th, 1/3rd deduction)
- **Instant Results & Analytics** — Score, percentage, pass/fail status, correct/wrong breakdown
- **Detailed Answer Review** — View correct answers with explanations and images after submission
- **Question Reporting** — Report wrong questions, options, or spelling mistakes
- **Test History** — Complete history of all past attempts with scores
- **Notifications** — Real-time notifications when new tests are published
- **Subscription Plans** — Monthly, Half-Yearly, and Yearly subscription options
- **Razorpay Payment Integration** — Secure online payments for subscriptions and balance top-up
- **Referral/Discount Codes** — Apply coupon codes for discounts on plans
- **Payment History** — Track all past transactions
- **Account Deletion** — Self-service account deletion option
- **Privacy Policy & Terms** — Dynamic, admin-editable legal pages

### 🛠️ Admin Features
- **Custom Admin Dashboard** — Separate admin panel (not Django's default admin)
- **Test Management** — Create, edit, publish, hide, and delete test sets
- **Question Builder** — Add questions with text/image, multiple-choice options with images, and explanations
- **Category Management** — Organize tests into categories with custom ordering
- **Draft & Publish Workflow** — Save tests as drafts, publish when ready (auto-notifies students)
- **Student Report Management** — View and resolve question reports from students
- **Subscription Management** — Add, edit, extend, and cancel student subscriptions
- **Referral Code Management** — Create/manage discount codes (fixed amount or percentage)
- **Email Configuration** — Configure SMTP settings (Gmail) directly from admin panel
- **Email Marketing** — Send bulk emails to all registered users
- **Backup & Restore** — Database backup and restore functionality
- **Admin Audit Logs** — Full activity log of all admin actions (create, update, publish, delete)
- **Subscription Logs** — Track all subscription lifecycle events
- **User Search** — Search and manage registered users

### 🔒 Security Features
- **Single Session Enforcement** — Only one active session per user at a time
- **CSRF Protection** — Built-in Django CSRF middleware
- **Password Validation** — Enforced strong passwords
- **Secure Session Handling** — HTTP-only cookies, configurable session expiry
- **Input Sanitization** — Prepared statements via Django ORM

### 🌐 REST API
- **Token-Based Authentication** — Login, register, and manage sessions via API
- **Full CRUD Endpoints** — Users, tests, categories, attempts, subscriptions, notifications
- **Payment API** — Razorpay payment creation and verification
- **Support Ticket API** — Create and manage support tickets via API
- **Dashboard API** — Fetch user dashboard data
- **Password Reset API** — OTP-based password reset flow
- **Contact API** — Submit contact form inquiries

### 💬 Support System
- **Ticket-Based Support** — Users can submit support tickets with categories
- **Live Chat Thread** — Threaded message system between user and admin
- **File Attachments** — Support for file uploads in messages
- **Typing Indicators** — Real-time typing indicators for both user and admin
- **Ticket Feedback** — Star rating and feedback after ticket resolution
- **Status Tracking** — Ticket statuses: Sent → Seen → Resolved

---

## 🛠️ Tech Stack

| Layer          | Technology                                          |
|----------------|-----------------------------------------------------|
| **Backend**    | Python 3.x, Django 4.x                              |
| **Frontend**   | HTML5, CSS3, JavaScript, Bootstrap 5                 |
| **Database**   | SQLite (default) / PostgreSQL (recommended)          |
| **Auth**       | Django Allauth, Custom OTP Verification              |
| **Payments**   | Razorpay Payment Gateway                             |
| **API**        | Django REST Framework, Token Authentication          |
| **Forms**      | Django Crispy Forms + Bootstrap 5                    |
| **Static**     | WhiteNoise (compressed static file serving)          |
| **Email**      | Gmail SMTP with App Password                         |
| **Deployment** | Gunicorn, Docker (optional)                          |

---

## 📁 Project Structure

```
Online-Examination-System/
├── accounts/              # Core app — Users, Tests, Exams, Payments, Admin
│   ├── models.py          # All database models
│   ├── views.py           # Student-facing views
│   ├── admin_views.py     # Custom admin dashboard views
│   ├── forms.py           # Django forms
│   ├── urls.py            # URL routing
│   ├── middleware.py       # Single session enforcement
│   ├── signals.py         # Auto profile creation signals
│   └── templatetags/      # Custom template filters
├── api/                   # REST API app
│   ├── views.py           # API viewsets and views
│   ├── serializers.py     # DRF serializers
│   ├── views_payments.py  # Payment API endpoints
│   └── urls.py            # API URL routing
├── support/               # Support ticket system
│   ├── models.py          # Ticket, Message, Feedback models
│   ├── views.py           # Support views
│   └── forms.py           # Support forms
├── templates/             # HTML templates
│   ├── base.html          # Base layout template
│   ├── landing_page.html  # Home/landing page
│   ├── accounts/          # Student-facing pages
│   ├── admin_panel/       # Admin dashboard pages
│   └── support/           # Support ticket pages
├── static/                # Static files (CSS, JS, Images)
├── docs/                  # Project documentation
├── project_tests/         # Automated test suite
├── exam_project/          # Django project settings
│   ├── settings.py        # Main settings
│   └── urls.py            # Root URL config
├── manage.py              # Django management script
├── requirements.txt       # Python dependencies
├── gunicorn_config.py     # Production server config
└── README.md              # This file
```

---

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- pip (Python package manager)
- Git

### 1. Clone the Repository
```bash
git clone https://github.com/sainathpatil2001/prepration_mentor.git
cd prepration_mentor
```

### 2. Create Virtual Environment
```bash
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Linux/Mac
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables (Optional)
Create a `.env` file in the project root:
```env
SECRET_KEY=your-secret-key-here
DEBUG=True
RAZORPAY_KEY_ID=your_razorpay_key_id
RAZORPAY_KEY_SECRET=your_razorpay_key_secret
EMAIL_HOST_USER=your_email@gmail.com
EMAIL_HOST_PASSWORD=your_app_password
```

### 5. Run Database Migrations
```bash
python manage.py makemigrations
python manage.py migrate
```

### 6. Create Admin User
```bash
python manage.py createsuperuser
```

### 7. Run Development Server
```bash
python manage.py runserver
```

### 8. Access the Application
| Page              | URL                                      |
|-------------------|------------------------------------------|
| Landing Page      | http://localhost:8000/                    |
| Student Login     | http://localhost:8000/accounts/login/     |
| Student Dashboard | http://localhost:8000/accounts/dashboard/ |
| Admin Dashboard   | http://localhost:8000/accounts/admin-dashboard/ |
| REST API          | http://localhost:8000/api/                |
| Django Admin      | http://localhost:8000/admin/              |

---

## 📖 Documentation

- [Setup Instructions](SETUP_INSTRUCTIONS.md) — Detailed setup with Razorpay & Google OAuth config
- [Admin Password Setup](ADMIN_PASSWORD_SETUP.md) — How to configure admin credentials
- [API Documentation](API_DOCUMENTATION.md) — REST API endpoints reference
- [Developer Guide](DEVELOPER_GUIDE.md) — Architecture and contribution guide
- [Razorpay Setup](RAZORPAY_SETUP.md) — Payment gateway integration guide
- [Database Schema](docs/database_schema.md) — Complete database ERD and model details
- [Architecture](docs/architecture.md) — System architecture overview

---

## 🧪 Running Tests
```bash
python manage.py test project_tests
```

---

## 👤 Author

**Sainath Ravindra Patil**
- 📧 Email: patilsainath517@gmail.com
- 📱 Phone: +91 7219585666
- 📍 Location: Jamner, Jalgaon, Maharashtra, India

---

## 📄 License

All rights reserved. Code modification and commercial use are strictly prohibited.
