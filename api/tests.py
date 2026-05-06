from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from django.contrib.auth.models import User
from rest_framework.authtoken.models import Token
from django.core.cache import cache
from accounts.models import (
    TestCategory, Test, Question, Answer, TestAttempt, UserAnswer,
    SubscriptionPlan, Subscription, Notification, UserProfile
)
from support.models import SupportTicket
from django.utils import timezone
import datetime
from unittest.mock import patch
import io
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image

class APIEndpointTests(APITestCase):
    def setUp(self):
        # 1. User Setup
        self.password = 'password123'
        self.user = User.objects.create_user(
            username='testuser', 
            email='test@example.com', 
            password=self.password,
            first_name='Test',
            last_name='User'
        )
        self.token = Token.objects.create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.token.key)

        # 2. Test/Exam Setup
        self.category = TestCategory.objects.create(name='General Knowledge')
        self.test = Test.objects.create(
            title='GK Quiz 2024',
            category=self.category,
            duration_minutes=10,
            total_questions=2,
            passing_score=50,
            status='published',
            is_active=True,
            instructions='Answer all questions.'
        )
        
        # Question 1 (5 marks)
        self.q1 = Question.objects.create(test=self.test, question_text="Capital of France?", marks=5, order=1)
        self.a1_correct = Answer.objects.create(question=self.q1, answer_text="Paris", is_correct=True, order=1)
        self.a1_wrong = Answer.objects.create(question=self.q1, answer_text="London", is_correct=False, order=2)
        
        # Question 2 (5 marks)
        self.q2 = Question.objects.create(test=self.test, question_text="2 + 2 = ?", marks=5, order=2)
        self.a2_correct = Answer.objects.create(question=self.q2, answer_text="4", is_correct=True, order=1)
        self.a2_wrong = Answer.objects.create(question=self.q2, answer_text="5", is_correct=False, order=2)

        # 3. Subscription Setup
        self.plan = SubscriptionPlan.objects.create(
            name='Premium',
            plan_type='monthly',
            duration_months=1,
            price=199.00
        )
        self.subscription = Subscription.objects.create(
            user=self.user,
            plan=self.plan,
            expires_at=timezone.now() + datetime.timedelta(days=30),
            status='active'
        )

        # 4. Notification Setup
        self.notification = Notification.objects.create(
            user=self.user,
            title='Welcome',
            message='Welcome to the platform',
            is_read=False
        )

    # --- Authentication Tests ---

    def test_register(self):
        url = reverse('api_register')
        data = {
            'username': 'newuniqueuser',
            'email': 'new@example.com',
            'password': 'newpassword',
            'first_name': 'New',
            'last_name': 'Member'
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(User.objects.count(), 2)

    def test_login(self):
        url = reverse('api_login')
        data = {'username': 'testuser', 'password': self.password}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('token', response.data)

    # --- Profile Tests ---

    def test_get_profile(self):
        url = reverse('user-me')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['email'], 'test@example.com')
        # Check profile field existence
        self.assertIn('profile', response.data)

    def test_update_profile(self):
        url = reverse('user-me')
        # Update flat fields and profile fields
        data = {
            'first_name': 'UpdatedName',
            'phone': '9998887776',  # Flat profile field supported by our custom logic
            'city': 'New York'
        }
        response = self.client.patch(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, 'UpdatedName')
        self.assertEqual(self.user.profile.phone, '9998887776')
        self.assertEqual(self.user.profile.city, 'New York')

    def test_update_profile_with_image(self):
        url = reverse('user-me')
        img = Image.new('RGB', (2, 2), color='blue')
        stream = io.BytesIO()
        img.save(stream, format='PNG')
        stream.seek(0)
        image = SimpleUploadedFile('avatar.png', stream.read(), content_type='image/png')

        response = self.client.patch(url, {'profile_picture': image}, format='multipart')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.user.refresh_from_db()
        self.assertTrue(bool(self.user.profile.profile_picture))

    # --- Exam Flow Tests ---

    def test_list_tests(self):
        url = reverse('test-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['title'], 'GK Quiz 2024')

    def test_full_exam_lifecycle(self):
        # 1. Start Test
        start_url = reverse('test-start', kwargs={'pk': self.test.id})
        start_response = self.client.post(start_url, {'is_timed': True})
        self.assertEqual(start_response.status_code, status.HTTP_200_OK)
        attempt_id = start_response.data['id']
        
        # 2. Fetch Questions (Initial)
        questions_url = reverse('test-attempt-questions', kwargs={'pk': attempt_id})
        q_response = self.client.get(questions_url)
        self.assertEqual(q_response.status_code, status.HTTP_200_OK)
        questions = q_response.data
        self.assertEqual(len(questions), 2)
        # Verify is_correct is NOT leaked
        self.assertNotIn('is_correct', questions[0]['answers'][0])
        self.assertIsNone(questions[0]['selected_answer_id'])

        # 3. Submit Answer for Q1 (Correct)
        submit_url = reverse('test-attempt-submit-answer', kwargs={'pk': attempt_id})
        response = self.client.post(submit_url, {
            'question_id': self.q1.id,
            'answer_id': self.a1_correct.id,
            'is_marked_for_review': True
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # 4. Resume Test (Check State)
        # Fetch questions again to see if state is preserved
        q_response_resume = self.client.get(questions_url)
        self.assertEqual(q_response_resume.data[0]['selected_answer_id'], self.a1_correct.id)
        self.assertTrue(q_response_resume.data[0]['is_marked_for_review'])
        
        # 5. Submit Answer for Q2 (Wrong)
        self.client.post(submit_url, {
            'question_id': self.q2.id,
            'answer_id': self.a2_wrong.id,
            'is_marked_for_review': False
        })
        
        # 6. Complete Test
        complete_url = reverse('test-attempt-complete', kwargs={'pk': attempt_id})
        complete_response = self.client.post(complete_url)
        self.assertEqual(complete_response.status_code, status.HTTP_200_OK)
        
        # Check Score
        # Total: 10. Q1 correct (5). Q2 wrong (0). Score: 5.
        self.assertEqual(float(complete_response.data['score']), 5.0)
        self.assertEqual(float(complete_response.data['percentage']), 50.0)
        self.assertTrue(complete_response.data['is_passed']) # 50% passing
        
        # 7. Review Results (New Endpoint)
        review_url = reverse('test-attempt-review', kwargs={'pk': attempt_id})
        review_response = self.client.get(review_url)
        self.assertEqual(review_response.status_code, status.HTTP_200_OK)
        
        review_data = review_response.data['review']
        # Verify correctness flags ARE visible now
        self.assertIn('is_correct', review_data[0]['answers'][0])
        # Verify user selection is visible
        self.assertEqual(review_data[0]['user_selected_answer_id'], self.a1_correct.id)

    def test_exam_not_completed_review_fails(self):
        # Start test but don't finish
        start_url = reverse('test-start', kwargs={'pk': self.test.id})
        response = self.client.post(start_url)
        attempt_id = response.data['id']
        
        # Try to review
        review_url = reverse('test-attempt-review', kwargs={'pk': attempt_id})
        response = self.client.get(review_url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # --- Subscription Tests ---

    def test_list_plans(self):
        url = reverse('subscriptionplan-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_list_my_subscriptions(self):
        url = reverse('subscription-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['status'], 'active')

    # --- Support Tests ---

    def test_create_ticket(self):
        url = reverse('support-ticket-list')
        data = {'category': 'other', 'description': 'Help me'}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(SupportTicket.objects.count(), 1)

    def test_add_ticket_message(self):
        ticket = SupportTicket.objects.create(user=self.user, category='other', description='Original')
        url = reverse('support-ticket-add-message', kwargs={'pk': ticket.id})
        response = self.client.post(url, {'message': 'Reply'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(ticket.messages.count(), 1)

    # --- Notification Tests ---

    def test_list_notifications(self):
        url = reverse('notification-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_mark_notification_read(self):
        url = reverse('notification-mark-read', kwargs={'pk': self.notification.id})
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        self.notification.refresh_from_db()
        self.assertTrue(self.notification.is_read)

    # --- New Features Tests ---

    def test_dashboard_stats(self):
        url = reverse('api_dashboard')
        response = self.client.get(url) 
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # We haven't taken any tests in setUp, so stats should be 0 unless we create one
        self.assertEqual(response.data['total_attempts'], 0)
        self.assertIn('total_attempts', response.data)

    def test_contact(self):
        url = reverse('api_contact')
        data = {
            'name': 'Test Visitor',
            'email': 'visitor@example.com',
            'message': 'Hello there'
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_bookmarks(self):
        # 1. Toggle Save (Add)
        url = reverse('test-toggle-save', kwargs={'pk': self.test.id})
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'saved')
        
        # 2. List Saved Tests
        list_url = reverse('test-list') + '?saved=true'
        response = self.client.get(list_url)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['id'], self.test.id)
        
        # 3. Toggle Save (Remove)
        response = self.client.post(url)
        self.assertEqual(response.data['status'], 'removed')
        
        # 4. List Saved (Empty)
        response = self.client.get(list_url)
        self.assertEqual(len(response.data), 0)

    def test_search_filters(self):
        # Search by title
        url = reverse('test-list') + '?search=GK'
        response = self.client.get(url)
        self.assertEqual(len(response.data), 1)
        
        url = reverse('test-list') + '?search=Physics'
        response = self.client.get(url)
        self.assertEqual(len(response.data), 0)

    def test_report_question(self):
        # Create attempt
        attempt = TestAttempt.objects.create(user=self.user, test=self.test, status='in_progress')
        
        url = reverse('test-attempt-report-question', kwargs={'pk': attempt.id})
        data = {
            'question': self.q1.id,
            'report_type': 'wrong_question',
            'description': 'This is wrong'
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_change_password(self):
        url = reverse('api_change_password')
        # Fail case
        data = {'old_password': 'wrong', 'new_password': 'new'}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
        # Success case
        data = {'old_password': self.password, 'new_password': 'newpassword123'}
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Login with new password
        login_url = reverse('api_login')
        response = self.client.post(login_url, {'username': 'testuser', 'password': 'newpassword123'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_request_password_reset(self):
        self.client.credentials()  # Public endpoint
        url = reverse('api_request_password_reset')

        response = self.client.post(url, {'email': self.user.email})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('status', response.data)

        # Non-existing email should still return generic success
        response = self.client.post(url, {'email': 'noaccount@example.com'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_password_reset_otp_flow(self):
        send_url = reverse('api_send_password_reset_otp')
        confirm_url = reverse('api_reset_password_with_otp')

        cache.delete(f'api_pwd_reset_otp_{self.user.id}')
        cache.delete(f'api_pwd_reset_otp_attempts_{self.user.id}')
        cache.delete(f'api_pwd_reset_otp_daily_{self.user.id}')
        cache.delete(f'api_pwd_reset_otp_cooldown_{self.user.id}')

        with patch('api.views._generate_otp', return_value='123456'):
            send_response = self.client.post(send_url)
        self.assertEqual(send_response.status_code, status.HTTP_200_OK)

        confirm_response = self.client.post(confirm_url, {
            'otp': '123456',
            'new_password': 'ResetPassword@123',
            'confirm_password': 'ResetPassword@123',
        })
        self.assertEqual(confirm_response.status_code, status.HTTP_200_OK)

        # Login with new password should work.
        login_url = reverse('api_login')
        login_response = self.client.post(login_url, {'username': 'testuser', 'password': 'ResetPassword@123'})
        self.assertEqual(login_response.status_code, status.HTTP_200_OK)
