"""Integration tests for support ticket web workflows."""

from __future__ import annotations

from django.conf import settings
from django.test import TestCase, override_settings
from django.urls import reverse

from project_tests.factories import TestDataFactory
from support.models import SupportTicket, TicketFeedback, TicketMessage

TEST_MIDDLEWARE = [mw for mw in settings.MIDDLEWARE if mw != "whitenoise.middleware.WhiteNoiseMiddleware"]

@override_settings(
    MIDDLEWARE=TEST_MIDDLEWARE,
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
)
class SupportViewTests(TestCase):
    """Validate support ticket creation, messaging, and admin workflows."""

    def setUp(self):
        self.password = "SupportPass123!"
        self.user = TestDataFactory.create_user(
            username="support_user",
            email="support_user@example.com",
            password=self.password,
        )
        self.other_user = TestDataFactory.create_user(
            username="other_user",
            email="other_user@example.com",
            password=self.password,
        )
        self.staff_user = TestDataFactory.create_user(
            username="staff_user",
            email="staff_user@example.com",
            password=self.password,
            is_staff=True,
        )
        self.super_user = TestDataFactory.create_user(
            username="super_user",
            email="super_user@example.com",
            password=self.password,
            is_staff=True,
            is_superuser=True,
        )
        self.ticket = SupportTicket.objects.create(
            user=self.user,
            subject="Unable to submit test",
            category="technical",
            description="Submit button not working.",
            status="sent",
        )

    def _login(self, username):
        self.assertTrue(self.client.login(username=username, password=self.password))

    def test_user_support_post_creates_ticket(self):
        """Posting valid ticket form should create a new support ticket."""
        self._login(self.user.username)
        response = self.client.post(
            reverse("user_support"),
            {
                "subject": "Payment failed",
                "category": "billing",
                "description": "Balance was deducted but plan not activated.",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("user_support"))
        self.assertTrue(
            SupportTicket.objects.filter(user=self.user, subject="Payment failed").exists()
        )

    def test_user_ticket_detail_ajax_message_creates_reply(self):
        """AJAX message post on user ticket detail should create a chat message."""
        self._login(self.user.username)
        response = self.client.post(
            reverse("user_ticket_detail", args=[self.ticket.ticket_id]),
            {"message": "Any update on this issue?"},
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "success")
        self.assertEqual(TicketMessage.objects.filter(ticket=self.ticket).count(), 1)
        self.assertFalse(TicketMessage.objects.get(ticket=self.ticket).is_admin_reply)

    def test_update_typing_status_rejects_unrelated_non_staff_user(self):
        """Only ticket owner or staff should update typing status."""
        self._login(self.other_user.username)
        response = self.client.post(reverse("update_typing_status", args=[self.ticket.ticket_id]))
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["status"], "error")

    def test_admin_support_detail_marks_sent_ticket_as_seen(self):
        """Opening admin ticket detail should move `sent` ticket to `seen`."""
        self._login(self.staff_user.username)
        response = self.client.get(reverse("admin_support_detail", args=[self.ticket.ticket_id]))
        self.assertEqual(response.status_code, 200)
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.status, "seen")
        self.assertTrue(self.ticket.is_read_by_admin)

    def test_submit_feedback_requires_resolved_ticket(self):
        """Feedback submission should be blocked until ticket is resolved."""
        self._login(self.user.username)
        response = self.client.post(
            reverse("submit_feedback", args=[self.ticket.ticket_id]),
            {"rating": "4", "feedback_text": "Good support"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("user_ticket_detail", args=[self.ticket.ticket_id]))
        self.assertFalse(TicketFeedback.objects.filter(ticket_id=str(self.ticket.ticket_id)).exists())

    def test_submit_feedback_creates_entry_for_resolved_ticket(self):
        """Resolved tickets should accept one feedback submission."""
        self.ticket.status = "resolved"
        self.ticket.save(update_fields=["status"])

        self._login(self.user.username)
        response = self.client.post(
            reverse("submit_feedback", args=[self.ticket.ticket_id]),
            {"rating": "5", "feedback_text": "Great turnaround time"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse("user_ticket_detail", args=[self.ticket.ticket_id]))
        self.assertTrue(TicketFeedback.objects.filter(ticket_id=str(self.ticket.ticket_id)).exists())

    def test_super_admin_reviews_access_control(self):
        """Non-superusers should be blocked; superusers should be allowed."""
        self._login(self.staff_user.username)
        blocked = self.client.get(reverse("super_admin_reviews"))
        self.assertEqual(blocked.status_code, 302)
        self.assertEqual(blocked.url, reverse("admin_dashboard_overview"))

        self.client.logout()
        self._login(self.super_user.username)
        allowed = self.client.get(reverse("super_admin_reviews"))
        self.assertEqual(allowed.status_code, 200)

    def test_export_tickets_returns_csv_for_staff(self):
        """Staff export endpoint should return CSV response."""
        self._login(self.staff_user.username)
        response = self.client.get(reverse("export_tickets"))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response["Content-Type"].startswith("text/csv"))
        self.assertIn("support_tickets.csv", response["Content-Disposition"])

    def test_delete_tickets_deletes_only_resolved_records(self):
        """Bulk delete endpoint should skip non-resolved tickets."""
        resolved_ticket = SupportTicket.objects.create(
            user=self.user,
            subject="Resolved issue",
            category="other",
            description="Can be deleted",
            status="resolved",
        )

        self._login(self.staff_user.username)
        response = self.client.post(
            reverse("delete_tickets"),
            {"ticket_ids[]": [str(self.ticket.ticket_id), str(resolved_ticket.ticket_id)]},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "success")
        self.assertTrue(SupportTicket.objects.filter(ticket_id=self.ticket.ticket_id).exists())
        self.assertFalse(SupportTicket.objects.filter(ticket_id=resolved_ticket.ticket_id).exists())
