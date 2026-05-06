"""API integration tests for DRF endpoints under `/api/`."""

from __future__ import annotations

from django.conf import settings
from django.urls import reverse
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from accounts.models import Notification
from project_tests.factories import TestDataFactory
from support.models import SupportTicket

TEST_MIDDLEWARE = [mw for mw in settings.MIDDLEWARE if mw != "whitenoise.middleware.WhiteNoiseMiddleware"]

from django.test import override_settings


@override_settings(MIDDLEWARE=TEST_MIDDLEWARE)
class APIEndpointTests(APITestCase):
    """Validate authentication, user, exam, support, and notification API behavior."""

    def setUp(self):
        self.password = "ApiPass123!"
        self.user = TestDataFactory.create_user(
            username="api_user",
            email="api_user@example.com",
            password=self.password,
        )
        self.other_user = TestDataFactory.create_user(
            username="api_other",
            email="api_other@example.com",
            password=self.password,
        )

        self.category = TestDataFactory.create_category(name="API Category")
        self.test = TestDataFactory.create_test(category=self.category, passing_score=50)
        self.question = TestDataFactory.create_question(self.test, "What is 2+2?", marks=5, order=1)
        self.correct_answer = TestDataFactory.create_answer(
            self.question,
            "4",
            is_correct=True,
            order=1,
        )
        TestDataFactory.create_answer(self.question, "5", is_correct=False, order=2)

    def authenticate(self):
        """Attach token auth for `self.user`."""
        token, _ = Token.objects.get_or_create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

    def test_register_endpoint_creates_user(self):
        """Public register endpoint should create a new user."""
        payload = {
            "username": "new_api_user",
            "email": "new_api_user@example.com",
            "password": "NewPass123!",
            "first_name": "New",
            "last_name": "User",
        }
        response = self.client.post(reverse("api_register"), payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_login_endpoint_returns_token_payload(self):
        """Login endpoint should return token and identity fields."""
        payload = {"username": self.user.username, "password": self.password}
        response = self.client.post(reverse("api_login"), payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("token", response.data)
        self.assertEqual(response.data["username"], self.user.username)

    def test_tests_list_requires_authentication(self):
        """Default permissions should block unauthenticated test listing."""
        response = self.client.get(reverse("test-list"))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_user_me_get_and_patch(self):
        """`/api/users/me/` should return and update current user."""
        self.authenticate()

        get_response = self.client.get(reverse("user-me"))
        self.assertEqual(get_response.status_code, status.HTTP_200_OK)
        self.assertEqual(get_response.data["username"], self.user.username)

        patch_response = self.client.patch(
            reverse("user-me"),
            {"first_name": "Updated"},
            format="json",
        )
        self.assertEqual(patch_response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, "Updated")

    def test_user_list_is_scoped_for_non_staff_user(self):
        """Non-staff users should only see themselves in user listing."""
        self.authenticate()
        response = self.client.get(reverse("user-list"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], self.user.id)

    def test_exam_attempt_flow_start_submit_complete(self):
        """User should be able to start, answer, and complete a test attempt."""
        self.authenticate()

        start_response = self.client.post(
            reverse("test-start", args=[self.test.id]),
            {"is_timed": True},
            format="json",
        )
        self.assertEqual(start_response.status_code, status.HTTP_200_OK)
        attempt_id = start_response.data["id"]

        questions_response = self.client.get(reverse("test-attempt-questions", args=[attempt_id]))
        self.assertEqual(questions_response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(questions_response.data), 1)

        submit_response = self.client.post(
            reverse("test-attempt-submit-answer", args=[attempt_id]),
            {
                "question_id": self.question.id,
                "answer_id": self.correct_answer.id,
                "is_marked_for_review": False,
            },
            format="json",
        )
        self.assertEqual(submit_response.status_code, status.HTTP_200_OK)

        complete_response = self.client.post(reverse("test-attempt-complete", args=[attempt_id]), format="json")
        self.assertEqual(complete_response.status_code, status.HTTP_200_OK)
        self.assertEqual(complete_response.data["status"], "completed")
        self.assertEqual(float(complete_response.data["score"]), 5.0)
        self.assertTrue(complete_response.data["is_passed"])

    def test_support_ticket_create_and_add_message(self):
        """Authenticated user should create ticket and append message."""
        self.authenticate()
        create_response = self.client.post(
            reverse("support-ticket-list"),
            {"category": "technical", "description": "Need API support"},
            format="json",
        )
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        ticket_id = create_response.data["id"]

        message_response = self.client.post(
            reverse("support-ticket-add-message", args=[ticket_id]),
            {"message": "Any update?"},
            format="multipart",
        )
        self.assertEqual(message_response.status_code, status.HTTP_200_OK)
        self.assertEqual(message_response.data["message"], "Any update?")
        self.assertEqual(SupportTicket.objects.filter(user=self.user).count(), 1)

    def test_notification_mark_read_updates_record(self):
        """Custom `mark_read` action should flip notification state."""
        self.authenticate()
        notification = Notification.objects.create(
            user=self.user,
            title="API Alert",
            message="New test available",
            is_read=False,
        )

        response = self.client.post(reverse("notification-mark-read", args=[notification.id]), format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "marked read")

        notification.refresh_from_db()
        self.assertTrue(notification.is_read)
