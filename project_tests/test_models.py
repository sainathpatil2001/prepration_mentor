"""Model-level tests for accounts and support domain behavior."""

from __future__ import annotations

from datetime import timedelta

from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone

from accounts.models import (
    EmailConfiguration,
    Notification,
    QuestionReport,
    ReferralCode,
    SavedTest,
    SubscriptionPlan,
    TestCategory,
    UserProfile,
)
from project_tests.factories import TestDataFactory


class UserProfileSignalModelTests(TestCase):
    """Validate `User` to `UserProfile` signal behavior."""

    def test_profile_created_for_new_user(self):
        """Creating a user should automatically create its profile."""
        user = TestDataFactory.create_user()
        self.assertTrue(UserProfile.objects.filter(user=user).exists())
        self.assertEqual(str(user.profile), f"{user.username}'s Profile")


class TestCategoryModelTests(TestCase):
    """Validate category model defaults and helper behavior."""

    def test_slug_auto_generated_when_missing(self):
        """`save()` should create a slug from the category name."""
        category = TestCategory.objects.create(name="Banking Exams", description="All banking tests")
        self.assertEqual(category.slug, "banking-exams")


class SubscriptionPlanModelTests(TestCase):
    """Validate subscription plan computed properties."""

    def test_duration_display_text(self):
        """Human-readable duration should match known month values."""
        monthly = SubscriptionPlan.objects.create(
            name="Monthly Plan",
            plan_type="monthly",
            duration_months=1,
            price="99.00",
            description="Monthly access",
        )
        yearly = SubscriptionPlan.objects.create(
            name="Yearly Plan",
            plan_type="yearly",
            duration_months=12,
            price="899.00",
            description="Yearly access",
        )

        self.assertEqual(monthly.get_duration_display_text, "1 Month")
        self.assertEqual(yearly.get_duration_display_text, "1 Year")


class ReferralCodeModelTests(TestCase):
    """Validate referral code time-window and usage-limit logic."""

    def test_code_is_valid_within_dates_and_limit(self):
        """Active code in range and below limit should be valid."""
        referral = ReferralCode.objects.create(
            code="SAVE10",
            discount_type="percent",
            discount_value="10.00",
            valid_from=timezone.now() - timedelta(days=1),
            valid_until=timezone.now() + timedelta(days=1),
            is_active=True,
            usage_limit=5,
            usage_count=1,
        )
        self.assertTrue(referral.is_valid())

    def test_code_is_invalid_after_expiry(self):
        """Expired code should be invalid."""
        referral = ReferralCode.objects.create(
            code="EXPIRED10",
            discount_type="percent",
            discount_value="10.00",
            valid_from=timezone.now() - timedelta(days=10),
            valid_until=timezone.now() - timedelta(seconds=1),
            is_active=True,
        )
        self.assertFalse(referral.is_valid())

    def test_code_is_invalid_when_usage_limit_reached(self):
        """Code should be invalid once `usage_count` reaches `usage_limit`."""
        referral = ReferralCode.objects.create(
            code="LIMIT1",
            discount_type="fixed",
            discount_value="50.00",
            valid_from=timezone.now() - timedelta(days=1),
            valid_until=timezone.now() + timedelta(days=1),
            is_active=True,
            usage_limit=1,
            usage_count=1,
        )
        self.assertFalse(referral.is_valid())


class EmailConfigurationModelTests(TestCase):
    """Validate singleton-like active configuration behavior."""

    def test_only_one_configuration_remains_active(self):
        """Saving a new active config should deactivate prior active config."""
        first = EmailConfiguration.objects.create(
            email_host_user="first@example.com",
            email_host_password="first-pass",
            default_from_email="first@example.com",
            is_active=True,
        )
        second = EmailConfiguration.objects.create(
            email_host_user="second@example.com",
            email_host_password="second-pass",
            default_from_email="second@example.com",
            is_active=True,
        )

        first.refresh_from_db()
        second.refresh_from_db()

        self.assertFalse(first.is_active)
        self.assertTrue(second.is_active)


class TestPublishModelTests(TestCase):
    """Validate publishing lifecycle side effects."""

    def test_publish_marks_test_live_and_generates_notifications(self):
        """Publishing should update visibility/status and notify active non-staff users."""
        student_one = TestDataFactory.create_user(username="student_one")
        student_two = TestDataFactory.create_user(username="student_two")
        staff_user = TestDataFactory.create_user(username="staff_user", is_staff=True)

        exam = TestDataFactory.create_test(status="draft", is_hidden=True, published_at=None)
        exam.notifications_generated = False
        exam.save(update_fields=["notifications_generated"])

        exam.publish(save=True)
        exam.refresh_from_db()

        self.assertEqual(exam.status, "published")
        self.assertFalse(exam.is_hidden)
        self.assertIsNotNone(exam.published_at)
        self.assertTrue(exam.notifications_generated)

        notified_user_ids = set(
            Notification.objects.filter(title__icontains=exam.title).values_list("user_id", flat=True)
        )
        self.assertSetEqual(notified_user_ids, {student_one.id, student_two.id})
        self.assertNotIn(staff_user.id, notified_user_ids)


class ConstraintModelTests(TestCase):
    """Validate DB-level uniqueness constraints important for integrity."""

    def test_question_report_unique_per_user_and_question(self):
        """A user should not be able to file duplicate reports for the same question."""
        user = TestDataFactory.create_user()
        test = TestDataFactory.create_test()
        question = TestDataFactory.create_question(test=test)

        QuestionReport.objects.create(
            user=user,
            question=question,
            report_type="other",
            description="Initial report",
        )

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                QuestionReport.objects.create(
                    user=user,
                    question=question,
                    report_type="spelling_mistake",
                    description="Duplicate report",
                )

    def test_saved_test_unique_per_user_and_test(self):
        """The same user should not save the same test multiple times."""
        user = TestDataFactory.create_user()
        test = TestDataFactory.create_test()
        SavedTest.objects.create(user=user, test=test)

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                SavedTest.objects.create(user=user, test=test)

