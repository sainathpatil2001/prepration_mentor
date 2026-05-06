"""Integration-style tests for key accounts app web views."""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from accounts.models import EmailOTP, SavedTest, TestAttempt, UserAnswer
from accounts.models_contact import ContactQuery
from project_tests.factories import TestDataFactory

TEST_MIDDLEWARE = [mw for mw in settings.MIDDLEWARE if mw != "whitenoise.middleware.WhiteNoiseMiddleware"]

@override_settings(
    MIDDLEWARE=TEST_MIDDLEWARE,
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
)
class AccountsViewTests(TestCase):
    """Validate auth, exam, and utility endpoints in accounts views."""

    def setUp(self):
        cache.clear()
        self.password = "SecurePass123!"
        self.user = TestDataFactory.create_user(
            username="student_user",
            email="student@example.com",
            password=self.password,
        )
        self.category = TestDataFactory.create_category(name="General Exams")
        self.test = TestDataFactory.create_test(category=self.category)

    def _login(self):
        logged_in = self.client.login(username=self.user.username, password=self.password)
        self.assertTrue(logged_in, "Client login failed in test setup")

    def test_check_username_reports_existing_username(self):
        """Username checker should report an existing username as unavailable."""
        response = self.client.get(reverse("check_username"), {"username": self.user.username})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["valid"])

    def test_check_email_reports_existing_email(self):
        """Email checker should report an existing email as unavailable."""
        response = self.client.get(reverse("check_email"), {"email": self.user.email})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["valid"])

    def test_check_username_rate_limit_after_thirty_requests(self):
        """Username checker should return 429 after the configured request threshold."""
        for _ in range(30):
            self.client.get(reverse("check_username"), {"username": "candidate_name"})
        response = self.client.get(reverse("check_username"), {"username": "candidate_name"})
        self.assertEqual(response.status_code, 429)

    def test_custom_login_accepts_email_credentials(self):
        """Custom login should authenticate when email is posted in username field."""
        response = self.client.post(
            reverse("custom_login"),
            {"username": self.user.email, "password": self.password},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("dashboard"))

    def test_verify_email_marks_profile_verified_for_valid_otp(self):
        """Posting a valid OTP should verify user email and consume OTP code."""
        self._login()
        otp = EmailOTP.objects.create(
            user=self.user,
            code="123456",
            expires_at=timezone.now() + timedelta(minutes=10),
            is_used=False,
        )

        response = self.client.post(reverse("verify_email"), {"otp": "123456"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("dashboard"))

        self.user.profile.refresh_from_db()
        otp.refresh_from_db()
        self.assertTrue(self.user.profile.email_verified)
        self.assertTrue(otp.is_used)

    def test_toggle_save_test_creates_then_deletes_saved_test(self):
        """Save toggle endpoint should create and then remove saved-test row."""
        self._login()
        toggle_url = reverse("toggle_save_test", args=[self.test.id])

        first = self.client.post(toggle_url)
        self.assertEqual(first.status_code, 200)
        self.assertTrue(first.json()["success"])
        self.assertTrue(first.json()["is_saved"])
        self.assertEqual(SavedTest.objects.filter(user=self.user, test=self.test).count(), 1)

        second = self.client.post(toggle_url)
        self.assertEqual(second.status_code, 200)
        self.assertTrue(second.json()["success"])
        self.assertFalse(second.json()["is_saved"])
        self.assertEqual(SavedTest.objects.filter(user=self.user, test=self.test).count(), 0)

    def test_test_detail_redirects_to_add_funds_without_subscription(self):
        """Users without active subscription should be redirected from test detail."""
        self._login()
        response = self.client.get(reverse("test_detail", args=[self.test.id]))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("add_funds"))

    def test_exam_start_creates_attempt_and_user_answers_for_subscriber(self):
        """Subscribed users should get in-progress attempt and pre-created answer rows."""
        TestDataFactory.create_active_subscription(self.user)

        question_one = TestDataFactory.create_question(self.test, "Q1", marks=2, order=1)
        question_two = TestDataFactory.create_question(self.test, "Q2", marks=3, order=2)
        TestDataFactory.create_answer(question_one, "A", is_correct=True)
        TestDataFactory.create_answer(question_two, "B", is_correct=True)

        self._login()
        response = self.client.post(
            reverse("exam_start", args=[self.test.id]),
            {"exam_mode": "timed"},
        )
        self.assertEqual(response.status_code, 302)

        attempt = TestAttempt.objects.get(user=self.user, test=self.test, status="in_progress")
        self.assertTrue(attempt.is_timed)
        self.assertEqual(UserAnswer.objects.filter(attempt=attempt).count(), 2)
        self.assertEqual(response.url, reverse("exam_interface", args=[attempt.id]))

    def test_exam_submit_applies_negative_marking_rule(self):
        """Exam submission should deduct marks for wrong answers under 1/4 rule."""
        exam = TestDataFactory.create_test(
            category=self.category,
            negative_marking_rule="1/4",
            passing_score=50,
        )
        q1 = TestDataFactory.create_question(exam, "First question", marks=4, order=1)
        q2 = TestDataFactory.create_question(exam, "Second question", marks=4, order=2)
        correct_q1 = TestDataFactory.create_answer(q1, "Correct", is_correct=True, order=1)
        wrong_q2 = TestDataFactory.create_answer(q2, "Wrong", is_correct=False, order=1)

        attempt = TestAttempt.objects.create(
            user=self.user,
            test=exam,
            status="in_progress",
            is_timed=True,
        )
        TestAttempt.objects.filter(pk=attempt.pk).update(started_at=timezone.now() - timedelta(minutes=20))
        attempt.refresh_from_db()

        UserAnswer.objects.create(
            attempt=attempt,
            question=q1,
            selected_answer=correct_q1,
            is_correct=True,
            is_visited=True,
        )
        UserAnswer.objects.create(
            attempt=attempt,
            question=q2,
            selected_answer=wrong_q2,
            is_correct=False,
            is_visited=True,
        )

        self._login()
        response = self.client.get(reverse("exam_submit", args=[attempt.id]))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("exam_results", args=[attempt.id]))

        attempt.refresh_from_db()
        self.assertEqual(attempt.status, "completed")
        self.assertEqual(attempt.score, Decimal("3.00"))
        self.assertEqual(attempt.total_marks, 8)
        self.assertEqual(attempt.percentage, Decimal("37.50"))
        self.assertFalse(attempt.is_passed)

    def test_contact_us_creates_query_when_payload_valid(self):
        """Public contact endpoint should persist valid contact submissions."""
        response = self.client.post(
            reverse("contact_us"),
            {
                "name": "Test User",
                "email": "contact@example.com",
                "message": "Need details about plans.",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("contact_us"))
        self.assertTrue(ContactQuery.objects.filter(email="contact@example.com").exists())

    def test_account_reset_password_redirects_even_when_email_not_found(self):
        """Password-reset request should always redirect to avoid account enumeration."""
        response = self.client.post(
            reverse("account_reset_password"),
            {"email": "unknown@example.com"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("custom_login"))
