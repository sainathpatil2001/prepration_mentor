from rest_framework import serializers
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from accounts.models import (
    UserProfile, TestCategory, Test, Question, Answer, 
    TestAttempt, UserAnswer, SubscriptionPlan, Subscription, 
    Notification, SavedTest, MotivationQuote, QuestionReport
)
from support.models import SupportTicket, TicketMessage
from accounts.models_contact import ContactQuery

# --- Accounts & Profile ---

class UserProfileSerializer(serializers.ModelSerializer):
    """
    Serializer for the UserProfile model.
    exposes profile details like contact info and picture.
    """
    class Meta:
        model = UserProfile
        fields = ['phone', 'address', 'city', 'state', 'country', 'pincode', 'profile_picture', 'balance', 'email_verified']

class UserSerializer(serializers.ModelSerializer):
    """
    Serializer for the User model, including nested profile data.
    """
    profile = UserProfileSerializer(read_only=True)
    active_subscription = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'profile', 'active_subscription']

    def get_active_subscription(self, obj):
        from django.utils import timezone
        sub = Subscription.objects.filter(
            user=obj,
            status='active',
            is_active=True,
            expires_at__gt=timezone.now()
        ).select_related('plan').order_by('-expires_at').first()
        if sub:
            return SubscriptionSerializer(sub).data
        return None

class RegisterSerializer(serializers.ModelSerializer):
    """
    Serializer for user registration.
    
    Handles creating a new User instance with a hashed password.
    """
    password = serializers.CharField(write_only=True)
    
    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'first_name', 'last_name']
        
    def validate_email(self, value):
        """
        Check that the email is unique.
        """
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value

    def create(self, validated_data):
        """
        Create and return a new User instance, given the validated data.
        """
        user = User.objects.create_user(**validated_data)
        return user

class CustomAuthTokenSerializer(serializers.Serializer):
    username = serializers.CharField(label="Username/Email", write_only=True)
    password = serializers.CharField(label="Password", style={'input_type': 'password'}, write_only=True, trim_whitespace=False)
    token = serializers.CharField(label="Token", read_only=True)

    def validate(self, attrs):
        username = attrs.get('username')
        password = attrs.get('password')

        if username and password:
            # Check if login is via email
            if '@' in username:
                user_obj = User.objects.filter(email__iexact=username).first()
                if user_obj:
                    username = user_obj.username
            
            # Authenticate
            from django.contrib.auth import authenticate
            user = authenticate(request=self.context.get('request'),
                                username=username, password=password)

            # The authenticate call simply returns None for is_active=False
            # users. (Assuming the backend doesn't raise errors).
            if not user:
                msg = 'Unable to log in with provided credentials.'
                raise serializers.ValidationError(msg, code='authorization')
        else:
            msg = 'Must include "username" and "password".'
            raise serializers.ValidationError(msg, code='authorization')

        attrs['user'] = user
        return attrs

class ChangePasswordSerializer(serializers.Serializer):
    """
    Serializer to validate password change requests.
    """
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True)

    def validate_new_password(self, value):
        validate_password(value)
        return value

class VerifyEmailSerializer(serializers.Serializer):
    otp = serializers.CharField(required=True, min_length=6, max_length=6)

class RequestPasswordResetSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)

class PasswordResetWithOTPSerializer(serializers.Serializer):
    otp = serializers.CharField(required=True, min_length=6, max_length=6)
    new_password = serializers.CharField(required=True, write_only=True)
    confirm_password = serializers.CharField(required=True, write_only=True)

    def validate(self, attrs):
        if attrs['new_password'] != attrs['confirm_password']:
            raise serializers.ValidationError({'confirm_password': ['Passwords do not match.']})

        validate_password(attrs['new_password'])
        return attrs

class DashboardStatsSerializer(serializers.Serializer):
    """
    Serializer for the User Dashboard statistics.
    """
    total_attempts = serializers.IntegerField()
    passed_tests = serializers.IntegerField()
    avg_score = serializers.FloatField()
    active_subscription = serializers.SerializerMethodField()
    quote = serializers.SerializerMethodField()
    
    def get_active_subscription(self, obj):
        # obj is a dict here
        sub = obj.get('active_subscription')
        if sub:
            return SubscriptionSerializer(sub).data
        return None

    def get_quote(self, obj):
        quote = obj.get('quote')
        if quote:
            return {'text': quote.quote, 'author': quote.author}
        return None

class ContactQuerySerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactQuery
        fields = ['name', 'email', 'message', 'submitted_at']
        read_only_fields = ['submitted_at']

# --- Exams ---



class QuestionReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = QuestionReport
        fields = ['question', 'report_type', 'description', 'is_resolved', 'created_at']
        read_only_fields = ['is_resolved', 'created_at']

class AnswerSerializer(serializers.ModelSerializer):
    """
    Serializer for Answer model.
    """
    class Meta:
        model = Answer
        fields = ['id', 'answer_text', 'answer_image', 'order']

class QuestionSerializer(serializers.ModelSerializer):
    """
    Serializer for Question model, including nested answers.
    """
    answers = AnswerSerializer(many=True, read_only=True)
    
    class Meta:
        model = Question
        fields = ['id', 'question_text', 'question_image', 'marks', 'order', 'answers']

class TestCategorySerializer(serializers.ModelSerializer):
    """
    Serializer for TestCategory model.
    """
    class Meta:
        model = TestCategory
        fields = ['id', 'name', 'slug', 'description', 'display_order']

class TestSerializer(serializers.ModelSerializer):
    """
    Serializer for Test model.
    """
    category_name = serializers.CharField(source='category.name', read_only=True)
    
    is_saved = serializers.SerializerMethodField()
    
    class Meta:
        model = Test
        fields = ['id', 'title', 'category', 'category_name', 'description', 
                  'duration_minutes', 'total_questions', 'passing_score', 
                  'negative_marking_rule', 'instructions', 'published_at', 'is_saved']
                  
    def get_is_saved(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return SavedTest.objects.filter(user=request.user, test=obj).exists()
        return False

class SavedTestSerializer(serializers.ModelSerializer):
    """
    Serializer for SavedTest (bookmarks).
    """
    test = TestSerializer(read_only=True)
    
    class Meta:
        model = SavedTest
        fields = ['id', 'test', 'created_at']

# --- Attempts ---

class UserAnswerSerializer(serializers.ModelSerializer):
    """
    Serializer for UserAnswer model (individual question responses).
    """
    class Meta:
        model = UserAnswer
        fields = ['id', 'question', 'selected_answer', 'is_marked_for_review']

class TestAttemptSerializer(serializers.ModelSerializer):
    """
    Serializer for TestAttempt model.
    Includes status, score, and timing information.
    """
    test_title = serializers.CharField(source='test.title', read_only=True)
    
    class Meta:
        model = TestAttempt
        fields = ['id', 'test', 'test_title', 'status', 'started_at', 'submitted_at', 
                  'score', 'total_marks', 'percentage', 'is_passed', 'time_taken_minutes', 'is_timed']
        read_only_fields = ['score', 'total_marks', 'percentage', 'is_passed', 'time_taken_minutes', 'started_at', 'submitted_at']

class SubmitAnswerSerializer(serializers.Serializer):
    """
    Serializer for submitting an answer to a question.
    """
    question_id = serializers.IntegerField()
    answer_id = serializers.IntegerField(required=False, allow_null=True)
    is_marked_for_review = serializers.BooleanField(default=False)

# --- Subscription ---

class SubscriptionPlanSerializer(serializers.ModelSerializer):
    """
    Serializer for SubscriptionPlan model.
    """
    duration_display = serializers.CharField(source='get_duration_display_text', read_only=True)
    
    class Meta:
        model = SubscriptionPlan
        fields = ['id', 'name', 'plan_type', 'duration_months', 'price', 
                  'description', 'duration_display']

class PaymentOrderSerializer(serializers.Serializer):
    plan_id = serializers.IntegerField(required=True)

class PaymentVerifySerializer(serializers.Serializer):
    razorpay_order_id = serializers.CharField(required=True)
    razorpay_payment_id = serializers.CharField(required=True)
    razorpay_signature = serializers.CharField(required=True)

class SubscriptionSerializer(serializers.ModelSerializer):
    """
    Serializer for Subscription model.
    """
    plan_name = serializers.CharField(source='plan.name', read_only=True)
    
    class Meta:
        model = Subscription
        fields = ['id', 'plan', 'plan_name', 'status', 'started_at', 'expires_at', 'is_active']

# --- Support ---

class TicketMessageSerializer(serializers.ModelSerializer):
    """
    Serializer for individual messages within a support ticket.
    """
    sender_name = serializers.CharField(source='sender.username', read_only=True)
    
    class Meta:
        model = TicketMessage
        fields = ['id', 'sender', 'sender_name', 'message', 'attachment', 'created_at', 'is_admin_reply']
        read_only_fields = ['sender', 'is_admin_reply']

class SupportTicketSerializer(serializers.ModelSerializer):
    """
    Serializer for SupportTicket model, including nested messages.
    """
    messages = TicketMessageSerializer(many=True, read_only=True)
    
    class Meta:
        model = SupportTicket
        fields = ['id', 'ticket_id', 'category', 'description', 'status', 'created_at', 'messages']
        read_only_fields = ['ticket_id', 'status', 'created_at']

# --- Notification ---

class NotificationSerializer(serializers.ModelSerializer):
    """
    Serializer for Notification model.
    """
    class Meta:
        model = Notification
        fields = ['id', 'title', 'message', 'is_read', 'created_at']

class QuestionStateSerializer(QuestionSerializer):
    """
    Serializer for Question during an attempt, including current answer state.
    """
    selected_answer_id = serializers.SerializerMethodField()
    is_marked_for_review = serializers.SerializerMethodField()
    
    class Meta(QuestionSerializer.Meta):
        fields = QuestionSerializer.Meta.fields + ['selected_answer_id', 'is_marked_for_review']
        
    def get_selected_answer_id(self, obj):
        user_answers_map = self.context.get('user_answers_map', {})
        ua = user_answers_map.get(obj.id)
        return ua.selected_answer_id if ua else None

    def get_is_marked_for_review(self, obj):
        user_answers_map = self.context.get('user_answers_map', {})
        ua = user_answers_map.get(obj.id)
        return ua.is_marked_for_review if ua else False


# --- Review/Results ---

class AnswerReviewSerializer(serializers.ModelSerializer):
    """
    Serializer for Answer model including is_correct flag.
    Used for reviewing results after test completion.
    """
    class Meta:
        model = Answer
        fields = ['id', 'answer_text', 'answer_image', 'order', 'is_correct']

class QuestionReviewSerializer(serializers.ModelSerializer):
    """
    Serializer for Question model for review (includes explanation and correct answers).
    """
    answers = AnswerReviewSerializer(many=True, read_only=True)
    user_selected_answer_id = serializers.SerializerMethodField()
    
    class Meta:
        model = Question
        fields = ['id', 'question_text', 'question_image', 'marks', 'order', 'answers', 'explanation', 'explanation_image', 'user_selected_answer_id']

    def get_user_selected_answer_id(self, obj):
        # This expects a dictionary 'user_answers_map' in the context
        user_answers_map = self.context.get('user_answers_map', {})
        return user_answers_map.get(obj.id)

