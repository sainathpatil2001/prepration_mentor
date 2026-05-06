"""URL wiring smoke tests for critical named routes."""

from __future__ import annotations

import uuid

from django.test import SimpleTestCase
from django.urls import reverse


class URLWiringSmokeTests(SimpleTestCase):
    """Ensure key named URL patterns are reversible."""

    def test_core_named_urls_reverse(self):
        """Core web route names should reverse without errors."""
        names = [
            "home",
            "custom_login",
            "dashboard",
            "test_list",
            "user_support",
            "admin_support_list",
            "contact_us",
            "privacy_policy",
            "terms_of_service",
            "api_login",
            "api_register",
        ]
        for name in names:
            self.assertTrue(reverse(name).startswith("/"), msg=f"URL reverse failed for {name}")

    def test_parameterized_web_urls_reverse(self):
        """Parameterized web route names should reverse with sample identifiers."""
        ticket_uuid = uuid.UUID("11111111-1111-1111-1111-111111111111")
        urls = [
            reverse("test_detail", args=[1]),
            reverse("exam_interface", args=[1]),
            reverse("exam_submit", args=[1]),
            reverse("exam_results", args=[1]),
            reverse("read_notification", args=[1]),
            reverse("user_ticket_detail", args=[ticket_uuid]),
            reverse("admin_support_detail", args=[ticket_uuid]),
            reverse("submit_feedback", args=[ticket_uuid]),
        ]
        for url in urls:
            self.assertTrue(url.startswith("/"))

    def test_parameterized_api_urls_reverse(self):
        """DRF router endpoints and custom actions should reverse."""
        urls = [
            reverse("user-list"),
            reverse("user-me"),
            reverse("test-list"),
            reverse("test-start", args=[1]),
            reverse("test-attempt-list"),
            reverse("test-attempt-questions", args=[1]),
            reverse("test-attempt-submit-answer", args=[1]),
            reverse("test-attempt-complete", args=[1]),
            reverse("support-ticket-list"),
            reverse("support-ticket-add-message", args=[1]),
            reverse("notification-list"),
            reverse("notification-mark-read", args=[1]),
        ]
        for url in urls:
            self.assertTrue(url.startswith("/"))

