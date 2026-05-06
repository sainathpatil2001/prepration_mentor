from rest_framework import viewsets, permissions, status, generics, filters
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Prefetch, Avg, Q
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.authtoken.models import Token
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.core.cache import cache
from django.contrib.auth.hashers import check_password, make_password
import random
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.urls import reverse
from .serializers import *
from accounts.models import *
from support.models import *

PASSWORD_RESET_OTP_TTL_SECONDS = 600
PASSWORD_RESET_OTP_COOLDOWN_SECONDS = 60
PASSWORD_RESET_OTP_DAILY_LIMIT = 5
PASSWORD_RESET_OTP_MAX_VERIFY_ATTEMPTS = 5


def _password_reset_cache_key(user_id: int) -> str:
    return f"api_pwd_reset_otp_{user_id}"


def _password_reset_attempts_key(user_id: int) -> str:
    return f"api_pwd_reset_otp_attempts_{user_id}"


def _password_reset_daily_limit_key(user_id: int) -> str:
    return f"api_pwd_reset_otp_daily_{user_id}"


def _password_reset_cooldown_key(user_id: int) -> str:
    return f"api_pwd_reset_otp_cooldown_{user_id}"


def _generate_otp() -> str:
    return f"{random.randint(0, 999999):06d}"


class CustomAuthToken(ObtainAuthToken):
    """
    Custom authentication token view.
    
    Returns the user's token, ID, email, username, and name upon successful login.
    """
    serializer_class = CustomAuthTokenSerializer

    def post(self, request, *args, **kwargs):
        """
        Handle POST request for token generation.
        """
        serializer = self.serializer_class(data=request.data,
                                           context={'request': request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        token, created = Token.objects.get_or_create(user=user)
        return Response({
            'token': token.key,
            'user_id': user.pk,
            'email': user.email,
            'username': user.username,
            'first_name': user.first_name,
            'last_name': user.last_name
        })

class RegisterView(generics.CreateAPIView):
    """
    API endpoint for user registration.
    
    Allows any user to register. Returns the created user data.
    """
    queryset = User.objects.all()
    permission_classes = (permissions.AllowAny,)
    serializer_class = RegisterSerializer

class RequestPasswordResetView(APIView):
    """
    Public endpoint to request a password reset email link.
    Returns a generic success response to avoid user enumeration.
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = RequestPasswordResetSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data['email'].strip().lower()
        rate_limit_key = f"api_pwd_reset_link_{email}"
        request_count = cache.get(rate_limit_key, 0)

        if request_count >= 3:
            return Response(
                {'status': 'If an account exists, a password reset link will be sent shortly.'},
                status=status.HTTP_200_OK,
            )

        users = User.objects.filter(email__iexact=email, is_active=True)
        if users.exists():
            for user in users:
                try:
                    token = default_token_generator.make_token(user)
                    uid = urlsafe_base64_encode(force_bytes(user.pk))
                    domain = request.build_absolute_uri('/')[:-1]
                    reset_link = f"{domain}{reverse('account_reset_password_confirm', kwargs={'uidb64': uid, 'token': token})}"

                    from accounts.email_utils import send_custom_email

                    send_custom_email(
                        subject='Password Reset Request',
                        message=(
                            f'Hello {user.get_full_name() or user.username},\n\n'
                            f'Use the link below to reset your password:\n\n{reset_link}\n\n'
                            'If you did not request this, you can ignore this email.'
                        ),
                        from_email=None,
                        recipient_list=[user.email],
                    )
                except Exception:
                    pass

            cache.set(rate_limit_key, request_count + 1, 86400)

        return Response(
            {'status': 'If an account exists, a password reset link will be sent shortly.'},
            status=status.HTTP_200_OK,
        )

class UserViewSet(viewsets.ModelViewSet):
    """
    API endpoint for viewing and editing user details.
    
    Restricted to authenticated users. Users can only see/edit their own data
    unless they are staff.
    """
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ['get', 'patch', 'head', 'options']

    @action(detail=False, methods=['get', 'patch'])
    def me(self, request):
        """
        Retrieve or update the authenticated user's profile.
        Supports both nested 'profile' object and flat fields.
        """
        if request.method == 'GET':
            serializer = self.get_serializer(request.user)
            return Response(serializer.data)
        elif request.method == 'PATCH':
            user = request.user
            
            # 1. Update User model fields
            user_data = {}
            for field in ['first_name', 'last_name', 'email']:
                if field in request.data:
                    user_data[field] = request.data[field]
            
            if user_data:
                user_serializer = self.get_serializer(user, data=user_data, partial=True)
                if user_serializer.is_valid():
                    user_serializer.save()
                else:
                    return Response(user_serializer.errors, status=400)
            
            # 2. Update Profile model fields
            profile_fields = ['phone', 'address', 'city', 'state', 'country', 'pincode', 'profile_picture']
            profile_data = {}
            
            # Helper to extract from nested 'profile' or root
            if 'profile' in request.data and isinstance(request.data['profile'], dict):
                 # Nested JSON
                 for k, v in request.data['profile'].items():
                     if k in profile_fields:
                         profile_data[k] = v
            
            # Also check root level (for multipart/form-data convenience)
            for k, v in request.data.items():
                if k in profile_fields:
                    profile_data[k] = v
            
            if profile_data:
                # user.profile is created via signal, so it should exist
                profile_serializer = UserProfileSerializer(user.profile, data=profile_data, partial=True)
                if profile_serializer.is_valid():
                    profile_serializer.save()
                else:
                    return Response(profile_serializer.errors, status=400)
            
            # Return updated data
            return Response(self.get_serializer(user).data)
            
    def get_queryset(self):
        """
        Limit queryset to the authenticated user unless staff.
        """
        queryset = User.objects.select_related('profile')
        if self.request.user.is_staff:
             return queryset
        return queryset.filter(id=self.request.user.id)

class DashboardView(APIView):
    """
    API endpoint for User Dashboard.
    Returns statistics, active subscription, and daily quote.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        
        # Stats
        total_attempts = TestAttempt.objects.filter(user=user, status='completed').count()
        passed_tests = TestAttempt.objects.filter(user=user, status='completed', is_passed=True).count()
        avg_score = TestAttempt.objects.filter(user=user, status='completed').aggregate(
            avg=models.Avg('percentage')
        )['avg'] or 0
        
        # Active Subscription
        active_sub = Subscription.objects.filter(
            user=user,
            status='active',
            is_active=True,
            expires_at__gt=timezone.now()
        ).select_related('plan').order_by('-expires_at').first()
        
        # Quote
        today = timezone.now().date()
        quote = MotivationQuote.objects.filter(display_date=today, is_active=True).first()
        if not quote:
            quote = MotivationQuote.objects.filter(is_active=True).order_by('?').first()
            
        data = {
            'total_attempts': total_attempts,
            'passed_tests': passed_tests,
            'avg_score': round(avg_score, 2),
            'active_subscription': active_sub,
            'quote': quote
        }
        
        serializer = DashboardStatsSerializer(data)
        return Response(serializer.data)

class ChangePasswordView(APIView):
    """
    API endpoint to change user password.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        if serializer.is_valid():
            user = request.user
            if user.check_password(serializer.validated_data['old_password']):
                user.set_password(serializer.validated_data['new_password'])
                user.save()
                return Response({'status': 'Password updated successfully'})
            return Response({'old_password': ['Wrong password.']}, status=status.HTTP_400_BAD_REQUEST)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class SendPasswordResetOTPView(APIView):
    """
    Send password-reset OTP to the authenticated user's email.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        user = request.user
        if not user.email:
            return Response({'error': 'No email is configured for this account.'}, status=status.HTTP_400_BAD_REQUEST)

        cooldown_key = _password_reset_cooldown_key(user.id)
        if cache.get(cooldown_key):
            return Response(
                {'error': 'Please wait 60 seconds before requesting a new OTP.'},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        daily_key = _password_reset_daily_limit_key(user.id)
        daily_count = cache.get(daily_key, 0)
        if daily_count >= PASSWORD_RESET_OTP_DAILY_LIMIT:
            return Response(
                {'error': 'Daily OTP request limit reached. Try again after 24 hours.'},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        otp_code = _generate_otp()
        otp_key = _password_reset_cache_key(user.id)
        attempts_key = _password_reset_attempts_key(user.id)

        cache.set(
            otp_key,
            {
                'otp_hash': make_password(otp_code),
                'created_at': timezone.now().isoformat(),
            },
            PASSWORD_RESET_OTP_TTL_SECONDS,
        )
        cache.set(attempts_key, 0, PASSWORD_RESET_OTP_TTL_SECONDS)
        cache.set(cooldown_key, 1, PASSWORD_RESET_OTP_COOLDOWN_SECONDS)
        cache.set(daily_key, daily_count + 1, 86400)

        try:
            from accounts.email_utils import send_custom_email

            send_custom_email(
                subject='Password reset code',
                message=(
                    f'Your password reset code is: {otp_code}\n'
                    f'This code will expire in {PASSWORD_RESET_OTP_TTL_SECONDS // 60} minutes.'
                ),
                from_email=None,
                recipient_list=[user.email],
            )
        except Exception as exc:
            cache.delete(otp_key)
            cache.delete(attempts_key)
            cache.delete(cooldown_key)
            return Response(
                {'error': f'Unable to send OTP email right now: {exc}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response({'status': 'Password reset OTP sent to your email.'})


class ResetPasswordWithOTPView(APIView):
    """
    Reset password using OTP sent to authenticated user's email.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = PasswordResetWithOTPSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        user = request.user
        otp_key = _password_reset_cache_key(user.id)
        attempts_key = _password_reset_attempts_key(user.id)

        otp_data = cache.get(otp_key)
        if not otp_data:
            return Response(
                {'otp': ['OTP expired or not requested. Please request a new OTP.']},
                status=status.HTTP_400_BAD_REQUEST,
            )

        attempts = cache.get(attempts_key, 0)
        if attempts >= PASSWORD_RESET_OTP_MAX_VERIFY_ATTEMPTS:
            cache.delete(otp_key)
            cache.delete(attempts_key)
            return Response(
                {'otp': ['Too many invalid attempts. Please request a new OTP.']},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )

        otp_code = serializer.validated_data['otp']
        if not check_password(otp_code, otp_data.get('otp_hash', '')):
            cache.set(attempts_key, attempts + 1, PASSWORD_RESET_OTP_TTL_SECONDS)
            return Response({'otp': ['Invalid OTP.']}, status=status.HTTP_400_BAD_REQUEST)

        user.set_password(serializer.validated_data['new_password'])
        user.save()

        cache.delete(otp_key)
        cache.delete(attempts_key)

        try:
            from accounts.email_utils import send_custom_email

            send_custom_email(
                subject='Password changed successfully',
                message=(
                    'Your account password was changed using OTP verification. '
                    'If this was not you, contact support immediately.'
                ),
                from_email=None,
                recipient_list=[user.email],
            )
        except Exception:
            pass

        return Response({'status': 'Password reset successfully.'})

class VerifyEmailView(APIView):
    """
    API endpoint to verify user's email address using OTP.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = VerifyEmailSerializer(data=request.data)
        if serializer.is_valid():
            code = serializer.validated_data['otp']
            user = request.user
            
            # Find valid OTP
            otp = EmailOTP.objects.filter(
                user=user,
                code=code,
                is_used=False,
                expires_at__gt=timezone.now()
            ).order_by('-created_at').first()
            
            if not otp:
                return Response({'otp': ['Invalid or expired code.']}, status=status.HTTP_400_BAD_REQUEST)
            
            otp.is_used = True
            otp.save()
            
            user.profile.email_verified = True
            user.profile.save()
            
            return Response({'status': 'Email verified successfully'})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class ResendVerificationView(APIView):
    """
    API endpoint to resend verification OTP.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        try:
            from accounts.views import _ensure_fresh_otp

            _ensure_fresh_otp(request.user, force_new=True)
            return Response({'status': 'Verification code sent'})
        except Exception as e:
            return Response({'error': str(e)}, status=500)

class ContactView(generics.CreateAPIView):
    """
    API endpoint for Contact Us form.
    """
    permission_classes = [permissions.AllowAny] # Or IsAuthenticated depending on requirement, usually AllowAny
    serializer_class = ContactQuerySerializer

class TestCategoryViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for viewing test categories.
    """
    queryset = TestCategory.objects.filter(is_active=True)
    serializer_class = TestCategorySerializer
    permission_classes = [permissions.IsAuthenticated]

class TestViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for viewing published tests.
    """
    queryset = Test.objects.filter(status='published', is_active=True).select_related('category')
    serializer_class = TestSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [filters.SearchFilter, DjangoFilterBackend]
    search_fields = ['title', 'description']
    filterset_fields = ['category']

    def get_queryset(self):
        qs = super().get_queryset()
        # Month filter
        month = self.request.query_params.get('month')
        if month:
            try:
                year, m = map(int, month.split('-'))
                qs = qs.filter(published_at__year=year, published_at__month=m)
            except ValueError:
                pass
        
        # Saved filter
        saved = self.request.query_params.get('saved')
        if saved == 'true':
            qs = qs.filter(users_saved__user=self.request.user)
            
        return qs.order_by('-published_at')

    @action(detail=True, methods=['post'])
    def toggle_save(self, request, pk=None):
        """
        Toggle 'Save for Later' status for a test.
        """
        test = self.get_object()
        saved_test, created = SavedTest.objects.get_or_create(user=request.user, test=test)
        
        if not created:
            saved_test.delete()
            return Response({'status': 'removed'})
        return Response({'status': 'saved'})

    @action(detail=True, methods=['post'])
    def start(self, request, pk=None):
        """
        Start a new test attempt.
        
        Payload:
            is_timed (bool): Optional. Whether the test attempts should be timed. Default: True.
            
        Returns:
            JSON: The created TestAttempt object.
        """
        test = self.get_object()
        # basic logic to start test
        attempt = TestAttempt.objects.create(
            user=request.user,
            test=test,
            status='in_progress',
            is_timed=request.data.get('is_timed', True)
        )
        return Response(TestAttemptSerializer(attempt).data)

class TestAttemptViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing test attempts.
    """
    serializer_class = TestAttemptSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """
        Only return attempts belonging to the authenticated user.
        """
        return TestAttempt.objects.filter(user=self.request.user).select_related('test')

    @action(detail=True, methods=['get'])
    def questions(self, request, pk=None):
        """
        Retrieve questions for the test attempt.
        Includes current answer state if any.
        """
        attempt = self.get_object()
        questions = attempt.test.questions.prefetch_related('answers').all().order_by('order')
        
        # Pre-fetch user answers
        user_answers = UserAnswer.objects.filter(attempt=attempt)
        user_answers_map = {ua.question_id: ua for ua in user_answers}
        
        serializer = QuestionStateSerializer(
            questions, 
            many=True, 
            context={'request': request, 'user_answers_map': user_answers_map}
        )
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def submit_answer(self, request, pk=None):
        """
        Submit an answer for a specific question in the attempt.
        
        Payload:
            question_id (int): ID of the question being answered.
            answer_id (int): ID of the selected answer option (can be null if deselecting).
            is_marked_for_review (bool): Whether to mark the question for review.
            
        Returns:
            JSON: Status of operation or validation errors.
        """
        attempt = self.get_object()
        if attempt.status != 'in_progress':
             return Response({"error": "Test is not in progress"}, status=400)
             
        serializer = SubmitAnswerSerializer(data=request.data)
        if serializer.is_valid():
            q_id = serializer.validated_data['question_id']
            a_id = serializer.validated_data.get('answer_id')
            is_marked = serializer.validated_data['is_marked_for_review']
            
            question = get_object_or_404(Question, id=q_id, test=attempt.test)
            
            # Save UserAnswer
            user_answer, created = UserAnswer.objects.get_or_create(
                attempt=attempt,
                question=question
            )
            
            if a_id:
                answer = get_object_or_404(Answer, id=a_id, question=question)
                user_answer.selected_answer = answer
                user_answer.is_correct = answer.is_correct
            else:
                 user_answer.selected_answer = None
                 user_answer.is_correct = False
                 
            user_answer.is_marked_for_review = is_marked
            user_answer.save()
            
            return Response({"status": "saved"})
        return Response(serializer.errors, status=400)

    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        """
        Complete and submit the test attempt. 
        
        Calculates the final score, percentage, and pass/fail status immediately.
        
        Returns:
            JSON: The completed TestAttempt object with results.
        """
        attempt = self.get_object()
        if attempt.status != 'in_progress':
             return Response({"status": "already completed"})
        
        # Calculate score
        attempt.submitted_at = timezone.now()
        attempt.status = 'completed'
        
        total_marks = 0
        score = 0
        
        # Fetch current answers
        user_answers = UserAnswer.objects.filter(attempt=attempt)
        
        for ua in user_answers:
             if ua.is_correct:
                 score += ua.question.marks
        
        # Total marks possible
        for q in attempt.test.questions.all():
            total_marks += q.marks
            
        attempt.score = score
        attempt.total_marks = total_marks
        if total_marks > 0:
            attempt.percentage = (score / total_marks) * 100
        else:
            attempt.percentage = 0
            
        attempt.is_passed = attempt.percentage >= attempt.test.passing_score
        
        # Calculate time taken
        if attempt.started_at:
            diff = attempt.submitted_at - attempt.started_at
            attempt.time_taken_minutes = diff.seconds // 60
        else:
            attempt.time_taken_minutes = 0
            
        attempt.save()
        
        return Response(TestAttemptSerializer(attempt).data)

    @action(detail=True, methods=['get'])
    def review(self, request, pk=None):
        """
        Retrieve detailed review of the attempts (questions, selected answers, correct answers).
        Only available for completed or timed-out tests.
        """
        attempt = self.get_object()
        if attempt.status == 'in_progress':
             return Response({"error": "Test is not completed yet"}, status=400)
             
        questions = attempt.test.questions.prefetch_related('answers').all().order_by('order')
        
        # Create a map of question_id -> selected_answer_id
        user_answers = UserAnswer.objects.filter(attempt=attempt)
        user_answers_map = {ua.question_id: ua.selected_answer_id for ua in user_answers}
        
        serializer = QuestionReviewSerializer(
            questions, 
            many=True, 
            context={'request': request, 'user_answers_map': user_answers_map}
        )
        

        return Response({
            'attempt': TestAttemptSerializer(attempt).data,
            'review': serializer.data
        })

    @action(detail=True, methods=['post'])
    def report_question(self, request, pk=None):
        """
        Report an issue with a question in this attempt.
        Payload: {question_id, report_type, description}
        """
        attempt = self.get_object()
        serializer = QuestionReportSerializer(data=request.data)
        
        # We need validation logic similar to views.py submit_report but using serializer
        # However, serializer expects 'question' as PK.
        
        if not request.data.get('question'):
             return Response({'question': ['This field is required.']}, status=400)
             
        # Verify question belongs to test
        q_id = request.data.get('question')
        if not attempt.test.questions.filter(id=q_id).exists():
            return Response({'error': 'Question does not belong to this test.'}, status=400)
            
        if serializer.is_valid():
            serializer.save(user=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class SubscriptionPlanViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for viewing subscription plans.
    """
    queryset = SubscriptionPlan.objects.filter(is_active=True)
    serializer_class = SubscriptionPlanSerializer
    permission_classes = [permissions.IsAuthenticated]

class SubscriptionViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for viewing user subscriptions.
    """
    serializer_class = SubscriptionSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """
        Only return subscriptions for the authenticated user.
        """
        return Subscription.objects.filter(user=self.request.user).select_related('plan')

class SupportTicketViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing support tickets.
    """
    serializer_class = SupportTicketSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """
        Only return tickets for the authenticated user.
        """
        return SupportTicket.objects.filter(user=self.request.user).prefetch_related('messages', 'messages__sender')
    
    def perform_create(self, serializer):
        """
        Automatically associate the ticket with the current user.
        """
        serializer.save(user=self.request.user)
        
    @action(detail=False, methods=['get'])
    def categories(self, request):
        """
        Return available ticket categories.
        """
        from support.models import SupportTicket
        choices = [{'id': k, 'name': v} for k, v in SupportTicket.CATEGORY_CHOICES]
        return Response(choices)

    @action(detail=True, methods=['post'])
    def add_message(self, request, pk=None):
        """
        Add a message (reply) to the ticket.
        
        Payload:
            message (str): The message content.
            attachment (file): Optional file attachment.
            
        Returns:
            JSON: The created TicketMessage object.
        """
        ticket = self.get_object()
        # Create message
        # Use Message Serializer, expect 'message' field
        
        message_text = request.data.get('message')
        if not message_text:
            return Response({"error": "Message is required"}, status=400)
            
        # Optional attachment
        attachment = request.FILES.get('attachment')

        msg = TicketMessage.objects.create(
            ticket=ticket,
            sender=request.user,
            message=message_text,
            attachment=attachment,
            is_admin_reply=False
        )
        return Response(TicketMessageSerializer(msg).data)

class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for viewing notifications.
    """
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """
        Only return notifications for the authenticated user.
        """
        return Notification.objects.filter(user=self.request.user)
    
    @action(detail=True, methods=['post'])
    def mark_read(self, request, pk=None):
        """
        Mark a notification as read.
        """
        note = self.get_object()
        note.is_read = True
        note.save()
        return Response({"status": "marked read"})
