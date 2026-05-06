
# Android API Documentation for Exam System
(Optimized for Speed)

Base URL: `http://<your-server-ip>:8000/api/`

## Authentication

### 1. Register
*   **Endpoint:** `/api/auth/register/`
*   **Method:** `POST`
*   **Body:**
    ```json
    {
        "username": "user123",
        "email": "user@example.com",
        "password": "securepassword",
        "first_name": "John",
        "last_name": "Doe"
    }
    ```
*   **Response:** `201 Created`

### 2. Login
*   **Endpoint:** `/api/auth/login/`
*   **Method:** `POST`
*   **Body:**
    ```json
    {
        "username": "user123",
        "password": "securepassword"
    }
    ```
*   **Response:**
    ```json
    {
        "token": "9944b09199c62b...",
        "user_id": 1,
        "email": "user@example.com",
        "username": "user123",
        "first_name": "John",
        "last_name": "Doe"
    }
    ```
    *Note: Save the `token`. You must send it in the header for all subsequent requests: `Authorization: Token <token>`.*

### 3. Change Password
*   **Endpoint:** `/api/change-password/`
*   **Method:** `POST`
*   **Headers:** `Authorization: Token <token>`
*   **Body:**
    ```json
    {
        "old_password": "securepassword",
        "new_password": "newpassword123"
    }
    ```

---

## User Profile

### 1. Get My Profile
*   **Endpoint:** `/api/users/me/`
*   **Method:** `GET`
*   **Headers:** `Authorization: Token <token>`
*   **Response:** Returns user details and profile info.

### 2. Update Profile
*   **Endpoint:** `/api/users/me/`
*   **Method:** `PATCH`
*   **Body:** (Send only fields you want to update)
    ```json
    {
        "first_name": "Johnny",
        "profile": {
             "phone": "1122334455"
        }
    }
    ```

### 3. Dashboard (Home Screen)
*   **Endpoint:** `/api/dashboard/`
*   **Method:** `GET`
*   **Response:**
    ```json
    {
        "total_attempts": 10,
        "passed_tests": 8,
        "avg_score": 85.5,
        "active_subscription": null,
        "quote": {
            "text": "Believe in yourself.",
            "author": "Unknown"
        }
    }
    ```

---

## Exams & Tests

### 1. List Categories
*   **Endpoint:** `/api/categories/`
*   **Method:** `GET`

### 2. List Tests
*   **Endpoint:** `/api/tests/`
*   **Method:** `GET`
*   **Query Params:**
    *   `?category=<id>` (Filter by category)
    *   `?search=Title` (Search by title/description)
    *   `?month=2023-10` (Filter by month)
    *   `?saved=true` (Show only bookmarked tests)

### 3. Toggle Bookmark (Save Test)
*   **Endpoint:** `/api/tests/{id}/toggle-save/`
*   **Method:** `POST`
*   **Response:** `{"status": "saved"}` or `{"status": "removed"}`

### 4. Start Test
*   **Endpoint:** `/api/tests/{id}/start/`
*   **Method:** `POST`
*   **Body:** `{"is_timed": true}`
*   **Response:** Returns Test Attempt object (id, status, etc.)

### 5. Get Questions (for an attempt)
*   **Endpoint:** `/api/attempts/{id}/questions/`
*   **Method:** `GET`
*   **Response:** List of questions with answers. (Preserves state for resuming)

### 6. Submit Answer
*   **Endpoint:** `/api/attempts/{id}/submit_answer/`
*   **Method:** `POST`
*   **Body:**
    ```json
    {
        "question_id": 5,
        "answer_id": 20,
        "is_marked_for_review": false
    }
    ```

### 7. Report Question
*   **Endpoint:** `/api/attempts/{id}/report_question/`
*   **Method:** `POST`
*   **Body:**
    ```json
    {
        "question": 5,
        "report_type": "wrong_question",
        "description": "The options are incorrect."
    }
    ```

### 8. Finish Test
*   **Endpoint:** `/api/attempts/{id}/complete/`
*   **Method:** `POST`

### 9. Review Results
*   **Endpoint:** `/api/attempts/{id}/review/`
*   **Method:** `GET`
*   **Note:** Only available if test is completed.

---

## Subscription & Payments

### 1. List Plans
*   **Endpoint:** `/api/plans/`
*   **Method:** `GET`

### 2. My Subscriptions
*   **Endpoint:** `/api/subscriptions/`
*   **Method:** `GET`

### 3. Create Payment Order (Razorpay)
*   **Endpoint:** `/api/payments/create_order/`
*   **Method:** `POST`
*   **Body:** `{"plan_id": 1}`
*   **Response:** Returns `order_id` and key for Razorpay SDK.

### 4. Verify Payment
*   **Endpoint:** `/api/payments/verify_payment/`
*   **Method:** `POST`
*   **Body:**
    ```json
    {
        "razorpay_order_id": "order_...",
        "razorpay_payment_id": "pay_...",
        "razorpay_signature": "sig_..."
    }
    ```

---

## Support & Contact

### 1. Contact Us (Public)
*   **Endpoint:** `/api/contact/`
*   **Method:** `POST`
*   **Body:**
    ```json
    {
        "name": "Guest",
        "email": "guest@example.com",
        "message": "Hello"
    }
    ```

### 2. List Tickets (Authenticated)
*   **Endpoint:** `/api/tickets/`
*   **Method:** `GET`

### 3. Create Ticket
*   **Endpoint:** `/api/tickets/`
*   **Method:** `POST`
*   **Body:** `{"category": "technical", "description": "Help"}`

### 4. Send Message / Reply
*   **Endpoint:** `/api/tickets/{id}/add_message/`
*   **Method:** `POST`
*   **Body:** `{"message": "Reply text"}`

---

## Notifications

### 1. List
*   **Endpoint:** `/api/notifications/`
*   **Method:** `GET`

### 2. Mark Read
*   **Endpoint:** `/api/notifications/{id}/mark_read/`
*   **Method:** `POST`
