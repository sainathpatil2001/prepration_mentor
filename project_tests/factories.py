"""Reusable test data builders for the external project test suite."""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.utils import timezone
from django.utils.text import slugify

from accounts.models import Answer, Question, Subscription, SubscriptionPlan, Test, TestCategory


class TestDataFactory:
    """Factory helpers that create consistent data for tests."""

    _user_counter = 0
    _category_counter = 0
    _test_counter = 0

    @classmethod
    def create_user(
        cls,
        username: str | None = None,
        email: str | None = None,
        password: str = "TestPass123!",
        is_staff: bool = False,
        is_superuser: bool = False,
    ) -> User:
        """Create and return a Django user with optional staff/superuser flags."""
        cls._user_counter += 1
        suffix = cls._user_counter

        username = username or f"user_{suffix}"
        email = email or f"user_{suffix}@example.com"

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
        )

        if is_staff or is_superuser:
            user.is_staff = is_staff or is_superuser
            user.is_superuser = is_superuser
            user.save(update_fields=["is_staff", "is_superuser"])

        return user

    @classmethod
    def create_category(cls, name: str | None = None, is_active: bool = True) -> TestCategory:
        """Create and return a test category."""
        cls._category_counter += 1
        label = name or f"Category {cls._category_counter}"
        return TestCategory.objects.create(
            name=label,
            slug=slugify(label),
            description=f"{label} description",
            display_order=cls._category_counter,
            is_active=is_active,
        )

    @staticmethod
    def create_plan(plan_type: str = "monthly", **overrides) -> SubscriptionPlan:
        """Create and return a subscription plan."""
        defaults = {
            "monthly": {"name": "Monthly Plan", "duration_months": 1, "price": Decimal("99.00")},
            "half_yearly": {"name": "Half-Yearly Plan", "duration_months": 6, "price": Decimal("499.00")},
            "yearly": {"name": "Yearly Plan", "duration_months": 12, "price": Decimal("899.00")},
        }
        selected = defaults.get(plan_type, defaults["monthly"])
        data = {
            "name": selected["name"],
            "plan_type": plan_type,
            "duration_months": selected["duration_months"],
            "price": selected["price"],
            "description": f"{selected['name']} description",
            "is_active": True,
        }
        data.update(overrides)
        return SubscriptionPlan.objects.create(**data)

    @classmethod
    def create_active_subscription(
        cls,
        user: User,
        plan: SubscriptionPlan | None = None,
        expires_in_days: int = 30,
    ) -> Subscription:
        """Create an active subscription for a user."""
        if plan is None:
            plan = cls.create_plan(plan_type="monthly")
        return Subscription.objects.create(
            user=user,
            plan=plan,
            status="active",
            is_active=True,
            expires_at=timezone.now() + timedelta(days=expires_in_days),
        )

    @classmethod
    def create_test(
        cls,
        category: TestCategory | None = None,
        **overrides,
    ) -> Test:
        """Create a published and visible test by default."""
        cls._test_counter += 1
        category = category or cls.create_category()
        data = {
            "title": f"Sample Test {cls._test_counter}",
            "category": category,
            "description": "Practice test description",
            "duration_minutes": 30,
            "total_questions": 0,
            "passing_score": 50,
            "negative_marking_rule": "none",
            "is_active": True,
            "instructions": "Read all instructions carefully.",
            "status": "published",
            "is_hidden": False,
            "published_at": timezone.now(),
        }
        data.update(overrides)
        return Test.objects.create(**data)

    @staticmethod
    def create_question(test: Test, question_text: str = "Sample question?", marks: int = 1, order: int = 1) -> Question:
        """Create and return a question for the given test."""
        return Question.objects.create(
            test=test,
            question_text=question_text,
            marks=marks,
            order=order,
        )

    @staticmethod
    def create_answer(
        question: Question,
        answer_text: str,
        is_correct: bool = False,
        order: int = 1,
    ) -> Answer:
        """Create and return an answer for the given question."""
        return Answer.objects.create(
            question=question,
            answer_text=answer_text,
            is_correct=is_correct,
            order=order,
        )

