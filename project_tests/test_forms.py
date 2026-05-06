"""Form-level validation tests for accounts and support modules."""

from __future__ import annotations

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from accounts.forms import AdminTestSetForm, QuestionForm
from project_tests.factories import TestDataFactory
from support.forms import TicketMessageForm


class AdminTestSetFormTests(TestCase):
    """Validate custom admin test-set form rules."""

    def setUp(self):
        self.category = TestDataFactory.create_category(name="Admin Category")

    def _valid_payload(self):
        return {
            "title": "Mock Test",
            "description": "A sample test form payload",
            "category": str(self.category.id),
            "duration_minutes": 45,
            "total_questions": 25,
            "passing_score": 40,
            "negative_marking_rule": "none",
            "instructions": "Read all instructions before starting.",
            "is_active": "on",
        }

    def test_form_accepts_valid_payload(self):
        """Nominal valid payload should pass validation."""
        form = AdminTestSetForm(data=self._valid_payload())
        self.assertTrue(form.is_valid(), form.errors)

    def test_passing_score_must_be_between_zero_and_hundred(self):
        """Passing score above 100 should fail."""
        data = self._valid_payload()
        data["passing_score"] = 101
        form = AdminTestSetForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn("passing_score", form.errors)

    def test_total_questions_cannot_be_negative(self):
        """Negative total question counts should fail."""
        data = self._valid_payload()
        data["total_questions"] = -1
        form = AdminTestSetForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn("total_questions", form.errors)


class QuestionFormTests(TestCase):
    """Validate question content rules."""

    def test_question_requires_text_or_image(self):
        """Question form should reject payloads missing both text and image."""
        form = QuestionForm(data={"marks": 1, "order": 1})
        self.assertFalse(form.is_valid())
        self.assertIn("__all__", form.errors)

    def test_question_with_text_is_valid(self):
        """Question form with text content should pass."""
        form = QuestionForm(
            data={
                "question_text": "What is the capital of France?",
                "marks": 1,
                "order": 1,
            }
        )
        self.assertTrue(form.is_valid(), form.errors)


class TicketMessageFormTests(TestCase):
    """Validate support ticket chat form rules."""

    def test_message_or_attachment_is_required(self):
        """Empty payload should fail."""
        form = TicketMessageForm(data={"message": ""})
        self.assertFalse(form.is_valid())
        self.assertIn("__all__", form.errors)

    def test_attachment_larger_than_five_mb_is_rejected(self):
        """Attachments greater than 5MB should fail validation."""
        big_file = SimpleUploadedFile(
            "too_large.txt",
            b"a" * (5 * 1024 * 1024 + 1),
            content_type="text/plain",
        )
        form = TicketMessageForm(
            data={"message": "Please see attachment"},
            files={"attachment": big_file},
        )
        self.assertFalse(form.is_valid())
        self.assertIn("attachment", form.errors)

    def test_message_only_payload_is_valid(self):
        """Text-only support messages should pass."""
        form = TicketMessageForm(data={"message": "Need help with payment"})
        self.assertTrue(form.is_valid(), form.errors)

