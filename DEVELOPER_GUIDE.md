# Developer Guide

Welcome to the **Online Examination System** developer documentation. This guide is intended for developers who want to understand the codebase, contribute to the project, or build applications (like Android apps) that interface with the system.

## 1. Project Overview

The Online Examination System is a **Django-based** web application that allows:
*   **Admins/Instructors** to create tests, manage questions, and view results.
*   **Students** to take tests (timed or untimed), view their profiles, and manage subscriptions.
*   **Mobile Apps** to consume these features via a REST API.

### Tech Stack
*   **Backend**: Python 3.x, Django 4.x
*   **API**: Django Rest Framework (DRF)
*   **Database**: SQLite (Development), PostgreSQL (Production recommended)
*   **Authentication**: Django Allauth + Custom Token Auth for API
*   **Payment**: Razorpay Integration

---

## 2. Getting Started

### Prerequisites
*   Python 3.8+
*   pip
*   git

### Installation
1.  **Clone the repository:**
    ```bash
    git clone <repository_url>
    cd online-examination-system
    ```

2.  **Create a virtual environment:**
    ```bash
    python -m venv venv
    # Windows
    venv\Scripts\activate
    # Linux/Mac
    source venv/bin/activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Run Migrations:**
    ```bash
    python manage.py makemigrations
    python manage.py migrate
    ```

5.  **Create a Superuser:**
    ```bash
    python manage.py createsuperuser
    ```

6.  **Run the Server:**
    ```bash
    python manage.py runserver
    ```

    Access the admin panel at `http://127.0.0.1:8000/admin/`.

---

## 3. Project Architecture

The project follows a monolithic Django structure where the `accounts` app contains the majority of the business logic.

### Directory Structure

*   **`exam_project/`**: Project configuration directory (`settings.py`, `urls.py`).
    *   `settings.py`: Contains all configuration including installed apps, database, and email settings.
*   **`accounts/`**: **Core Logic App**. Despite the name, this app handles:
    *   User Profiles (`UserProfile`)
    *   **Examinations**: `Test`, `Question`, `Answer` models.
    *   **Attempts**: `TestAttempt`, `UserAnswer` (logic for taking exams).
    *   **Subscriptions**: `SubscriptionPlan`, `Subscription` logic.
    *   **Payments**: `PaymentTransaction` (Razorpay).
    *   **Notifications**: `Notification`.
*   **`support/`**: Handles user support tickets.
    *   `Ticket`, `TicketMessage` models.
*   **`api/`**: **REST API Layer**.
    *   Contains Serializers and Views for exposing `accounts` and `support` logic to mobile/external clients.
    *   See [API_DOCUMENTATION.md](API_DOCUMENTATION.md) for endpoint details.
*   **`templates/`**: HTML Templates for the web frontend.
*   **`static/` & `media/`**: CSS, JS, and user-uploaded content (profile pics, question images).

### Key Models (Entity-Relationship)

#### User & Profile
*   **`User`** (Django Built-in): Handles authentication.
*   **`UserProfile`** (One-to-One): Stores phone, address, balance.

#### Examination
*   **`TestCategory`**: Categories for exams (e.g., "Banking").
*   **`Test`**: The exam entity. Has `questions` (One-to-Many).
*   **`Question`**: Has text/image, marks. Has `answers` (One-to-Many).
*   **`Answer`**: Possible choices. One is marked `is_correct`.

#### Test Taking
*   **`TestAttempt`**: Represents a single user taking a single test. Tracks `score`, `status` (in_progress/completed), `time_taken`.
*   **`UserAnswer`**: Links `TestAttempt` -> `Question` -> `Answer`. Stores the user's selected choice.

#### Subscriptions & Payments
*   **`SubscriptionPlan`**: Defines duration and price.
*   **`Subscription`**: Links `User` -> `SubscriptionPlan`. Used to control access to premium tests.
*   **`PaymentTransaction`**: Records Razorpay transaction details and status.
*   **`ReferralCode`**: System for validation and tracking of discount codes.

#### Auditing & Logs
*   **`AdminLog`**: Tracks important admin actions (creating/publishing tests) for accountability.
*   **`SubscriptionLog`**: Tracks changes to user subscriptions (extensions, cancellations).

---

## 4. Key Workflows

### Taking an Exam (Data Flow)
1.  **Start**: Client POSTs to `/api/tests/{id}/start/`.
    *   Server creates a `TestAttempt` with status `in_progress`.
2.  **Fetch Questions**: Client GETs `/api/attempts/{id}/questions/`.
3.  **Submit Answers**: Client POSTs to `/api/attempts/{id}/submit_answer/`.
    *   Server creates/updates `UserAnswer`.
4.  **Finish**: Client POSTs to `/api/attempts/{id}/complete/`.
    *   Server calculates score based on `UserAnswer` vs `Answer.is_correct`.
    *   `TestAttempt` is marked `completed`.

### Subscriptions
*   Users must purchase a `SubscriptionPlan`.
*   Payment is handled via Razorpay.
*   Upon successful payment webhook/verification, a `Subscription` record is created.
*   Middleware or Decorators check for active subscription before allowing access to premium tests.

---

## 5. Development Tips

*   **Admin Panel**: Use the Django Admin to populate data (Tests, Questions, Plans) quickly.
*   **API Testing**: Use Postman or the provided `API_DOCUMENTATION.md` to test endpoints.
*   **Environment Variables**: Use a `.env` file for keys (Razorpay, Email) in production.

## 6. References
*   [Setup Instructions](SETUP_INSTRUCTIONS.md)
*   [API Documentation](API_DOCUMENTATION.md)
*   [Architecture (Old)](docs/architecture.md)
