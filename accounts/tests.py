from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone
from .models import UserProfile, Test, TestCategory, Subscription, SubscriptionPlan, Question, Answer, TestAttempt
from dateutil.relativedelta import relativedelta

class AccountsTestFactory:
    @staticmethod
    def create_user(username='testuser', email='test@example.com', password='password'):
        return User.objects.create_user(username=username, email=email, password=password)

    @staticmethod
    def create_category(name='General Knowledge'):
        return TestCategory.objects.create(name=name, slug=name.lower().replace(' ', '-'))

    @staticmethod
    def create_test(category, title='Sample Test'):
        return Test.objects.create(
            category=category,
            title=title,
            duration_minutes=60,
            total_questions=10,
            status='published',
            published_at=timezone.now()
        )

    @staticmethod
    def create_plan(name='Monthly', duration=1, price=100):
        return SubscriptionPlan.objects.create(
            name=name,
            plan_type='monthly',
            duration_months=duration,
            price=price
        )

class AccountsModelTest(TestCase):
    def setUp(self):
        self.user = AccountsTestFactory.create_user()

    def test_profile_created_signal(self):
        self.assertTrue(hasattr(self.user, 'profile'))
        self.assertEqual(self.user.profile.balance, 0.00)

    def test_subscription_creation(self):
        plan = AccountsTestFactory.create_plan()
        sub = Subscription.objects.create(
            user=self.user,
            plan=plan,
            expires_at=timezone.now() + relativedelta(months=plan.duration_months)
        )
        self.assertEqual(sub.status, 'active')
        self.assertTrue(sub.is_active)

class AccountsViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = AccountsTestFactory.create_user()
        self.category = AccountsTestFactory.create_category()
        self.test = AccountsTestFactory.create_test(self.category)

    def test_login_view(self):
        response = self.client.get(reverse('account_login'))
        self.assertEqual(response.status_code, 200)

    def test_dashboard_requires_login(self):
        response = self.client.get(reverse('dashboard'))
        self.assertNotEqual(response.status_code, 200)
        self.assertTrue(response.status_code in [302, 301]) # Redirects

    def test_dashboard_access(self):
        self.client.login(username='testuser', password='password')
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 200)

    def test_test_list_view(self):
        self.client.login(username='testuser', password='password')
        response = self.client.get(reverse('test_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.test.title)

    def test_profile_update(self):
        self.client.login(username='testuser', password='password')
        response = self.client.post(reverse('profile'), {
            'first_name': 'John',
            'last_name': 'Doe',
            'phone': '1234567890'
        })
        self.assertEqual(response.status_code, 302)
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, 'John')
        self.assertEqual(self.user.profile.phone, '1234567890')

class ExamLogicTest(TestCase):
    def setUp(self):
        self.user = AccountsTestFactory.create_user()
        self.category = AccountsTestFactory.create_category()
        self.test = AccountsTestFactory.create_test(self.category)
        
        # Create questions
        self.q1 = Question.objects.create(test=self.test, question_text="Q1", marks=1)
        self.a1 = Answer.objects.create(question=self.q1, answer_text="A1", is_correct=True)
        self.a2 = Answer.objects.create(question=self.q1, answer_text="A2", is_correct=False)

    def test_attempt_creation(self):
        attempt = TestAttempt.objects.create(
            user=self.user,
            test=self.test,
            status='in_progress'
        )
        self.assertEqual(attempt.status, 'in_progress')
        self.assertEqual(attempt.score, 0)

