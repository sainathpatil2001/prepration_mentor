"""
Models for the Accounts app.

This module defines the database models for user profiles, examinations,
subscriptions, payments, and other core system components.
"""
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils.text import slugify
import json
from PIL import Image
from io import BytesIO
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import InMemoryUploadedFile, TemporaryUploadedFile

class UserProfile(models.Model):
    """
    Extends the default User model to store additional user information.
    
    Attributes:
        user (User): One-to-one relationship with the User model.
        phone (str): User's phone number.
        address (str): User's address.
        city (str): User's city.
        state (str): User's state.
        country (str): User's country.
        pincode (str): User's postal code.
        profile_picture (ImageField): User's profile image.
        balance (Decimal): User's account balance.
        email_verified (bool): Whether the user's email is verified.
        created_at (datetime): Timestamp when the profile was created.
        updated_at (datetime): Timestamp when the profile was last updated.
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    phone = models.CharField(max_length=15, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    state = models.CharField(max_length=100, blank=True, null=True)
    country = models.CharField(max_length=100, blank=True, null=True)
    pincode = models.CharField(max_length=10, blank=True, null=True)
    profile_picture = models.ImageField(upload_to='profile_pics/', blank=True, null=True)
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    email_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username}'s Profile"

    def save(self, *args, **kwargs):
        """
        Overrides the save method to handle image compression and resizing.
        
        If a new profile picture is uploaded, it is resized to a maximum of 300x300
        and compressed to JPEG format to save storage space.
        """
        if self.profile_picture:
            # Check if this is a new upload (or if field has changed)
            try:
                # Get the existing object from DB to check if image is new?
                # Actually, self.profile_picture will be a temporary UploadedFile object if new
                # Or we can just process it if it's open/unsaved
                
                # We want to process only if it's a new file or if we force it. 
                # A simple heuristic is check if image has close() method which implies it's open file
                
                img = Image.open(self.profile_picture)
                
                # Convert to RGB (in case of PNG with alpha)
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                # Resize if too large
                max_size = (300, 300)
                if img.height > 300 or img.width > 300:
                    img.thumbnail(max_size, Image.Resampling.LANCZOS)
                
                # Save to BytesIO buffer
                buffer = BytesIO()
                img.save(buffer, format='JPEG', quality=60, optimize=True)
                buffer.seek(0)
                
                # Replace the file content with compressed version
                # We need to assign it back. But we need to avoid infinite recursion if we were to just save()
                # Instead, we modify the FileField content before saving.
                
                # To avoid re-compressing already saved (and closed) files, we can check 
                # if the file name was changed or if it's an UploadedFile instance
                
                if isinstance(self.profile_picture.file, (InMemoryUploadedFile, TemporaryUploadedFile)):
                     # Generate a unique filename using timestamp to avoid cache issues
                     import time
                     filename = f"{self.user.username}_{int(time.time())}.jpg"
                     
                     self.profile_picture.save(
                         filename,
                         ContentFile(buffer.getvalue()),
                         save=False
                     )
            except Exception as e:
                # Log error but don't stop save
                # print(f"Error compressing image: {e}")
                pass

        super().save(*args, **kwargs)

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.profile.save()

class UserSession(models.Model):
    """
    Tracks user login sessions to enforce single-session policy or monitor activity.
    
    Attributes:
        user (User): The user who owns the session.
        session_key (str): Unique identifier for the Django session.
        created_at (datetime): When the session was created.
        last_activity (datetime): When the session was last active.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sessions')
    session_key = models.CharField(max_length=40, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_activity = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} - {self.session_key}"

class EmailOTP(models.Model):
    """
    Stores One-Time Passwords (OTPs) for email verification.
    
    Attributes:
        user (User): The user requesting verification.
        code (str): The 6-digit OTP code.
        created_at (datetime): When the OTP was generated.
        expires_at (datetime): When the OTP expires.
        is_used (bool): Whether the OTP has been used.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='email_otps')
    code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)

    class Meta:
        indexes = [
            models.Index(fields=['user', 'code', 'is_used']),
        ]

    def __str__(self):
        return f"OTP for {self.user.username}"

class TestCategory(models.Model):
    """
    Categorizes tests (e.g., Banking, State Services).
    
    Attributes:
        name (str): Category name.
        slug (str): URL-friendly slug for the category.
        description (str): Description of the category.
        display_order (int): Order for display purposes.
        is_active (bool): Whether the category is active.
    """
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True, help_text='URL friendly identifier')
    description = models.TextField(blank=True)
    display_order = models.PositiveIntegerField(default=0, help_text='Lower numbers appear first')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['display_order', 'name']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

class Test(models.Model):
    """
    Represents an examination or test.
    
    Attributes:
        title (str): Title of the test.
        category (TestCategory): The category this test belongs to.
        description (str): Detailed description of the test.
        duration_minutes (int): Time limit for the test in minutes.
        total_questions (int): Total number of questions in the test.
        passing_score (int): Percentage required to pass.
        negative_marking_rule (str): Rule for negative marking (e.g., '1/4').
        is_active (bool): Whether the test is active.
        instructions (str): Instructions for the test takers.
        status (str): Publication status ('draft', 'published').
        is_hidden (bool): Whether the test is hidden from students.
        published_at (datetime): When the test was published.
        notifications_generated (bool): Whether notifications have been sent.
    """
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('published', 'Published'),
    ]

    title = models.CharField(max_length=200)
    category = models.ForeignKey(TestCategory, on_delete=models.SET_NULL, null=True, blank=True, related_name='tests', help_text='Exam category such as Banking, State Services, etc.')
    description = models.TextField(blank=True)
    duration_minutes = models.IntegerField(help_text='Duration in minutes')
    total_questions = models.IntegerField(default=0)
    passing_score = models.IntegerField(default=50, help_text='Passing percentage')
    NEGATIVE_MARKING_CHOICES = [
        ('none', 'No Negative Marking'),
        ('1/4', '1/4th (0.25) Deduction'),
        ('1/3', '1/3rd (0.33) Deduction'),
    ]
    negative_marking_rule = models.CharField(max_length=10, choices=NEGATIVE_MARKING_CHOICES, default='none', help_text="Penalty for wrong answers")
    is_active = models.BooleanField(default=True)
    instructions = models.TextField(help_text='Test instructions and rules')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    is_hidden = models.BooleanField(default=False, help_text='Hidden tests are not visible to students')
    published_at = models.DateTimeField(null=True, blank=True)
    notifications_generated = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-published_at', '-created_at']
        indexes = [
            models.Index(fields=['status', 'is_active', '-published_at']),
        ]

    def __str__(self):
        return self.title

    def publish(self, save=True):
        """
        Publishes the test and generates notifications for users.
        
        Args:
            save (bool): Whether to save the model after updating status.
        """
        self.status = 'published'
        self.is_hidden = False
        self.published_at = timezone.now()
        
        if not self.notifications_generated:
            try:
                from django.apps import apps
                from django.urls import reverse
                Notification = apps.get_model('accounts', 'Notification')
                User = apps.get_model('auth', 'User')
                
                users = User.objects.filter(is_active=True).exclude(is_staff=True)
                test_url = reverse('test_detail', args=[self.id])
                
                notes = [
                    Notification(
                        user=u,
                        title=f"New Test Added: {self.title}",
                        message=f"A new test '{self.title}' is now live. Check the Tests section to start practicing.",
                        action_url=test_url,
                        is_read=False
                    ) for u in users
                ]
                Notification.objects.bulk_create(notes)
                self.notifications_generated = True
            except Exception as e:
                print(f"Error generating notifications: {e}")

        if save:
            self.save()

    def mark_draft(self, save=True):
        self.status = 'draft'
        self.published_at = None
        if save:
            self.save()

class Question(models.Model):
    """
    Represents a single question in a test.
    
    Attributes:
        test (Test): The test this question belongs to.
        question_text (str): The text of the question.
        question_image (ImageField): Optional image for the question.
        marks (int): Marks awarded for a correct answer.
        explanation (str): Explanation for the correct answer.
        explanation_image (ImageField): Optional image for the explanation.
        order (int): Order of the question within the test.
    """
    test = models.ForeignKey(Test, on_delete=models.CASCADE, related_name='questions')
    question_text = models.TextField(blank=True, null=True)
    question_image = models.ImageField(upload_to='question_images/', blank=True, null=True, help_text='Upload an image if text is not provided')
    marks = models.IntegerField(default=1)
    explanation = models.TextField(blank=True, null=True, help_text='Explanation for the correct answer')
    explanation_image = models.ImageField(upload_to='explanation_images/', blank=True, null=True, help_text='Image explaining the solution')
    order = models.IntegerField(default=0, help_text='Question order in test')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order', 'id']
        indexes = [
            models.Index(fields=['test', 'order']),
        ]

    def __str__(self):
        return f"{self.test.title} - Q{self.order}"

class QuestionReport(models.Model):
    """
    Stores user reports about issues with questions (e.g., wrong options).
    
    Attributes:
        user (User): The user reporting the issue.
        question (Question): The question being reported.
        report_type (str): Type of issue (e.g., 'wrong_question').
        description (str): Details about the issue.
        is_resolved (bool): Whether the report has been resolved by admin.
    """
    REPORT_TYPES = [
        ('wrong_question', 'Wrong Question'),
        ('wrong_options', 'Wrong Options'),
        ('spelling_mistake', 'Spelling Mistake'),
        ('other', 'Other'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='question_reports')
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='reports')
    report_type = models.CharField(max_length=20, choices=REPORT_TYPES)
    description = models.TextField(blank=True, null=True)
    is_resolved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']
        unique_together = ['user', 'question']

    def __str__(self):
        return f"{self.user.username} - {self.question} ({self.get_report_type_display()})"

class Answer(models.Model):
    """
    Represents an option/answer for a question.
    
    Attributes:
        question (Question): The question this answer belongs to.
        answer_text (str): Text of the answer option.
        answer_image (ImageField): Optional image for the answer.
        is_correct (bool): Whether this is the correct answer.
        order (int): Order of the answer option.
    """
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='answers')
    answer_text = models.CharField(max_length=500, blank=True, null=True)
    answer_image = models.ImageField(upload_to='answer_images/', blank=True, null=True)
    is_correct = models.BooleanField(default=False)
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ['order', 'id']
        indexes = [
            models.Index(fields=['question', 'order']),
        ]

    def __str__(self):
        return self.answer_text

class TestAttempt(models.Model):
    """
    Tracks a user's attempt at taking a test.
    
    Attributes:
        user (User): The user taking the test.
        test (Test): The test being attempted.
        status (str): Status of the attempt ('in_progress', 'completed', etc.).
        started_at (datetime): When the attempt started.
        submitted_at (datetime): When the attempt was submitted.
        time_taken_minutes (int): Time taken to complete.
        score (Decimal): Score obtained.
        total_marks (int): Total marks available.
        percentage (Decimal): Percentage score.
        is_passed (bool): Whether the user passed.
        is_timed (bool): Whether the attempt was timed (exam mode vs practice).
    """
    STATUS_CHOICES = [
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('time_up', 'Time Up'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='test_attempts')
    test = models.ForeignKey(Test, on_delete=models.CASCADE, related_name='attempts')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='in_progress')
    started_at = models.DateTimeField(auto_now_add=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    time_taken_minutes = models.IntegerField(null=True, blank=True)
    score = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    total_marks = models.IntegerField(default=0)
    percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    is_passed = models.BooleanField(default=False)
    is_timed = models.BooleanField(default=True, help_text="Whether this attempt is timed or untimed practice")

    class Meta:
        ordering = ['-started_at']
        indexes = [
            models.Index(fields=['user', 'test']),
            models.Index(fields=['user', '-started_at']),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.test.title}"

class UserAnswer(models.Model):
    """
    Stores the user's selected answer for a specific question in an attempt.
    
    Attributes:
        attempt (TestAttempt): The test attempt.
        question (Question): The question answered.
        selected_answer (Answer): The answer selected by the user.
        is_correct (bool): Whether the selection was correct.
        is_marked_for_review (bool): Whether marked for review.
        is_visited (bool): Whether the user visited this question.
    """
    attempt = models.ForeignKey(TestAttempt, on_delete=models.CASCADE, related_name='user_answers')
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    selected_answer = models.ForeignKey(Answer, on_delete=models.CASCADE, null=True, blank=True)
    is_correct = models.BooleanField(default=False)
    is_marked_for_review = models.BooleanField(default=False)
    is_visited = models.BooleanField(default=False)
    answered_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['attempt', 'question']

    def __str__(self):
        return f"{self.attempt} - {self.question}"

class SubscriptionPlan(models.Model):
    """
    Defines available subscription plans (e.g., Monthly, Yearly).
    
    Attributes:
        name (str): Display name of the plan.
        plan_type (str): Identifier for logic ('monthly', 'yearly').
        duration_months (int): Duration of the plan in months.
        price (Decimal): Cost of the plan.
        is_active (bool): Whether the plan is available for purchase.
        description (str): Description of plan features.
    """
    PLAN_TYPES = [
        ('monthly', 'Monthly'),
        ('half_yearly', 'Half-Yearly'),
        ('yearly', 'Yearly'),
    ]

    name = models.CharField(max_length=100)
    plan_type = models.CharField(max_length=20, choices=PLAN_TYPES, unique=True)
    duration_months = models.IntegerField(help_text='Duration in months')
    price = models.DecimalField(max_digits=10, decimal_places=2, help_text='Price in INR')
    is_active = models.BooleanField(default=True)
    description = models.TextField(blank=True, help_text='Plan description and features')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['price']

    def __str__(self):
        return self.name

    @property
    def get_duration_display_text(self):
        if self.duration_months == 1:
            return "1 Month"
        elif self.duration_months == 6:
            return "6 Months"
        elif self.duration_months == 12:
            return "1 Year"
        return f"{self.duration_months} Months"

class Subscription(models.Model):
    """
    Records a user's subscription to the platform.
    
    Attributes:
        user (User): The subscriber.
        plan (SubscriptionPlan): The plan subscribed to.
        status (str): Status ('active', 'expired', 'cancelled').
        started_at (datetime): Start date.
        expires_at (datetime): Expiration date.
        is_active (bool): Boolean flag for quick active check.
    """
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('expired', 'Expired'),
        ('cancelled', 'Cancelled'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='subscriptions')
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.CASCADE, related_name='subscriptions')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    started_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_active = models.BooleanField(default=True, help_text='Whether subscription is currently active')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'status', 'expires_at']),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.plan.name}"

class PaymentTransaction(models.Model):
    """
    Logs payment transactions.
    
    Attributes:
        user (User): User who made the payment.
        transaction_type (str): Type of transaction ('balance', 'subscription').
        subscription_plan (SubscriptionPlan): Plan purchased (if applicable).
        subscription (Subscription): Resulting subscription (if applicable).
        razorpay_order_id (str): Order ID from Razorpay.
        razorpay_payment_id (str): Payment ID from Razorpay.
        amount (Decimal): Transaction amount.
        status (str): Payment status ('success', 'pending', etc.).
    """
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('success', 'Success'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ]
    TRANSACTION_TYPES = [
        ('balance', 'Balance Top-up'),
        ('subscription', 'Subscription'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='transactions')
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES, default='balance')
    subscription_plan = models.ForeignKey(SubscriptionPlan, on_delete=models.SET_NULL, null=True, blank=True, related_name='transactions')
    subscription = models.ForeignKey(Subscription, on_delete=models.SET_NULL, null=True, blank=True, related_name='payment_transactions')
    razorpay_order_id = models.CharField(max_length=255)
    razorpay_payment_id = models.CharField(max_length=255, blank=True, null=True)
    razorpay_signature = models.CharField(max_length=255, blank=True, null=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} - {self.amount}"

class AdminLog(models.Model):
    """
    Audit log for administrative actions.
    
    Attributes:
        admin_user (User): Admin who performed the action.
        action (str): Type of action performed.
        test (Test): The test affected (if applicable).
        message (str): Description of the action.
        metadata (str): JSON string with additional details.
    """
    ACTION_CHOICES = [
        ('create', 'Create'),
        ('update', 'Update'),
        ('publish', 'Publish'),
        ('draft', 'Save Draft'),
        ('hide', 'Hide'),
        ('unhide', 'Unhide'),
        ('delete', 'Delete'),
    ]

    admin_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='admin_logs')
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    test = models.ForeignKey(Test, on_delete=models.SET_NULL, null=True, blank=True, related_name='admin_logs')
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    metadata = models.TextField(blank=True, null=True, help_text='Additional context stored as JSON string')

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['action', 'created_at']),
        ]

    def __str__(self):
        return f"{self.admin_user.username} - {self.action}"

class SubscriptionLog(models.Model):
    """
    Audit log specific to subscription management.
    
    Attributes:
        admin_user (User): Admin involved (if any).
        user (User): User whose subscription was affected.
        plan (SubscriptionPlan): Plan details.
        action (str): Action type ('create', 'expire', etc.).
        details (str): Additional details.
    """
    ACTION_CHOICES = [
        ('create', 'Create'),
        ('update', 'Update'),
        ('extend', 'Extend'),
        ('cancel', 'Cancel'),
        ('expire', 'Expire'),
    ]

    admin_user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='performed_subscription_actions')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='subscription_logs')
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=20, choices=ACTION_CHOICES)
    details = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} - {self.action}"

class Notification(models.Model):
    """
    System notifications for users.
    
    Attributes:
        user (User): Recipient of the notification.
        title (str): Notification title.
        message (str): Notification body.
        action_url (str): URL to direct the user to.
        is_read (bool): Read status.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=255)
    message = models.TextField()
    action_url = models.CharField(max_length=255, null=True, blank=True, help_text="URL to redirect to when clicked")
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
             models.Index(fields=['user', 'is_read']),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.title}"

class ReferralCode(models.Model):
    """
    Referral codes for discounts.
    
    Attributes:
        code (str): The actual code string (e.g., 'SAVE20').
        description (str): Internal/External description.
        discount_type (str): 'fixed' or 'percent'.
        discount_value (Decimal): Amount or percentage off.
        valid_from (datetime): Start of validity.
        valid_until (datetime): End of validity.
        is_active (bool): Master switch for the code.
        usage_limit (int): Max number of uses allowed.
        usage_count (int): Current usage count.
    """
    DISCOUNT_TYPE_CHOICES = [
        ('fixed', 'Fixed Amount (₹)'),
        ('percent', 'Percentage (%)'),
    ]

    code = models.CharField(max_length=20, unique=True, help_text="Unique referral code (e.g., SAVE20)")
    description = models.TextField(blank=True, help_text="Internal note or user-facing description")
    discount_type = models.CharField(max_length=10, choices=DISCOUNT_TYPE_CHOICES, default='percent')
    discount_value = models.DecimalField(max_digits=10, decimal_places=2, help_text="Value of the discount")
    
    # Validity
    valid_from = models.DateTimeField(default=timezone.now)
    valid_until = models.DateTimeField(null=True, blank=True, help_text="Leave empty for no expiry")
    is_active = models.BooleanField(default=True)
    
    # Usage limits
    usage_limit = models.PositiveIntegerField(null=True, blank=True, help_text="Total number of times this code can be used. Leave empty for unlimited.")
    usage_count = models.PositiveIntegerField(default=0, help_text="Current number of times used")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def is_valid(self):
        now = timezone.now()
        if not self.is_active:
            return False
        if self.valid_until and now > self.valid_until:
            return False
        if self.valid_from and now < self.valid_from:
            return False
        if self.usage_limit is not None and self.usage_count >= self.usage_limit:
            return False
        return True

    def __str__(self):
        return self.code

class PrivacyPolicy(models.Model):
    """
    Stores the content of the Privacy Policy page.
    Allows dynamic updates via admin panel.
    """
    title = models.CharField(max_length=200, default='Privacy Policy')
    content = models.TextField(help_text="HTML content is allowed")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Privacy Policies"
        ordering = ['-updated_at']

    def __str__(self):
        return f"{self.title} (Updated: {self.updated_at.strftime('%Y-%m-%d')})"

class SystemBackup(models.Model):
    """
    Tracks database or file backups.
    
    Attributes:
        name (str): Filename of the backup.
        file (FileField): The backup file itself.
        created_by (User): User who triggered the backup.
        size_bytes (int): Size of the backup in bytes.
        is_auto_generated (bool): Whether it was an automated backup.
    """
    name = models.CharField(max_length=255, help_text="Backup filename")
    file = models.FileField(upload_to='backups/')
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    size_bytes = models.BigIntegerField(default=0)
    is_auto_generated = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.name

class EmailConfiguration(models.Model):
    """
    Singleton model to store Global Google SMTP email settings.
    Only one instance of this model should exist and be active.
    """
    email_host = models.CharField(max_length=255, default='smtp.gmail.com', help_text="SMTP Host (e.g., smtp.gmail.com)")
    email_port = models.IntegerField(default=587, help_text="SMTP Port (e.g., 587 for TLS)")
    email_host_user = models.EmailField(help_text="Your Google Email Address")
    email_host_password = models.CharField(max_length=255, help_text="Your App Password (not your Gmail password)")
    email_use_tls = models.BooleanField(default=True, help_text="Use TLS (recommended)")
    email_use_ssl = models.BooleanField(default=False, help_text="Use SSL")
    default_from_email = models.EmailField(help_text="Default From Email", blank=True, null=True)
    is_active = models.BooleanField(default=True, help_text="Use these settings for sending emails")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Email Configuration"
        verbose_name_plural = "Email Configuration"

    def save(self, *args, **kwargs):
        # Ensure only one configuration is active at a time
        if self.is_active:
            EmailConfiguration.objects.filter(is_active=True).exclude(pk=self.pk).update(is_active=False)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Email Config ({self.email_host_user})"

    @classmethod
    def get_solo(cls):
        obj, created = cls.objects.get_or_create(is_active=True)
        return obj

class SavedTest(models.Model):
    """
    Represents a test bookmarked by a user for later access.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='saved_tests')
    test = models.ForeignKey(Test, on_delete=models.CASCADE, related_name='users_saved')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['user', 'test']
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username} - {self.test.title}"

from .models_contact import ContactQuery

class EmailCampaign(models.Model):
    """
    Manages bulk email campaigns.
    
    Attributes:
        subject (str): Email subject.
        message (str): Email body.
        audience (str): Target group.
        status (str): Delivery status.
        total_recipients (int): Count of targeted users.
        sent_count (int): Count of successfully sent emails.
    """
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]

    subject = models.CharField(max_length=255)
    message = models.TextField()
    audience = models.CharField(max_length=50, help_text="Target audience (all, subscribers, non_subscribers)")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    total_recipients = models.IntegerField(default=0)
    sent_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.subject} ({self.get_status_display()})"

from .models_quote import MotivationQuote
