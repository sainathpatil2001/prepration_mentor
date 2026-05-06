from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from .models import (
    UserProfile,
    PaymentTransaction,
    UserSession,
    Test,
    Question,
    Answer,
    TestAttempt,
    UserAnswer,
    SubscriptionPlan,
    Subscription,
    TestCategory,
    AdminLog,
    ContactQuery,
    MotivationQuote,
    EmailCampaign,
)

@admin.register(EmailCampaign)
class EmailCampaignAdmin(admin.ModelAdmin):
    """
    Admin configuration for EmailCampaign model.
    """
    list_display = ('subject', 'audience', 'status', 'total_recipients', 'sent_count', 'created_at')
    list_filter = ('status', 'audience', 'created_at')
    search_fields = ('subject', 'message')
    readonly_fields = ('total_recipients', 'sent_count', 'completed_at', 'created_at')

@admin.register(MotivationQuote)
class MotivationQuoteAdmin(admin.ModelAdmin):
    """
    Admin configuration for MotivationQuote model.
    """
    list_display = ('quote', 'author', 'display_date', 'is_active', 'created_at')
    search_fields = ('quote', 'author')
    list_filter = ('is_active', 'display_date')
    date_hierarchy = 'display_date'


@admin.register(ContactQuery)
class ContactQueryAdmin(admin.ModelAdmin):
    """
    Admin configuration for ContactQuery model.
    Disables individual delete action in favor of bulk delete or custom logic if needed.
    """
    list_display = ('name', 'email', 'submitted_at', 'is_read')
    search_fields = ('name', 'email', 'message')
    list_filter = ('is_read', 'submitted_at')
    readonly_fields = ('submitted_at',)
    
    def get_actions(self, request):
        actions = super().get_actions(request)
        if 'delete_selected' in actions:
            del actions['delete_selected']
        return actions

    actions = ['delete_queryset']

    def delete_queryset(self, request, queryset):
        queryset.delete()

@admin.register(TestCategory)
class TestCategoryAdmin(admin.ModelAdmin):
    """
    Admin configuration for TestCategory.
    """
    list_display = ['name', 'display_order', 'is_active', 'updated_at']
    search_fields = ['name', 'description']
    list_filter = ['is_active']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    """
    Admin configuration for UserProfile.
    """
    list_display = ['user', 'phone', 'balance', 'created_at']
    search_fields = ['user__username', 'user__email', 'phone']
    list_filter = ['created_at']


@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    """
    Admin configuration for SubscriptionPlan.
    """
    list_display = ['name', 'plan_type', 'duration_months', 'price', 'is_active', 'created_at']
    search_fields = ['name', 'plan_type']
    list_filter = ['is_active', 'plan_type', 'created_at']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    """
    Admin configuration for Subscription.
    """
    list_display = ['user', 'plan', 'status', 'started_at', 'expires_at', 'is_active']
    search_fields = ['user__username', 'plan__name']
    list_filter = ['status', 'is_active', 'plan', 'created_at']
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'expires_at'


@admin.register(PaymentTransaction)
class PaymentTransactionAdmin(admin.ModelAdmin):
    """
    Admin configuration for PaymentTransaction.
    """
    list_display = ['user', 'transaction_type', 'subscription_plan', 'amount', 'status', 'razorpay_order_id', 'created_at']
    search_fields = ['user__username', 'razorpay_order_id', 'razorpay_payment_id']
    list_filter = ['status', 'transaction_type', 'created_at']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(UserSession)
class UserSessionAdmin(admin.ModelAdmin):
    """
    Admin configuration for UserSession.
    """
    list_display = ['user', 'session_key', 'created_at', 'last_activity']
    search_fields = ['user__username']
    list_filter = ['created_at']


class AnswerInline(admin.TabularInline):
    model = Answer
    extra = 4


class QuestionInline(admin.TabularInline):
    model = Question
    extra = 1


@admin.register(Test)
class TestAdmin(admin.ModelAdmin):
    """
    Admin configuration for Test model with inline questions.
    """
    list_display = ['title', 'category', 'duration_minutes', 'total_questions', 'is_active', 'created_at']
    search_fields = ['title', 'description']
    list_filter = ['category', 'is_active', 'status', 'is_hidden', 'created_at']
    inlines = [QuestionInline]


@admin.register(AdminLog)
class AdminLogAdmin(admin.ModelAdmin):
    """
    Admin configuration for AdminLog (audit logs).
    """
    list_display = ['admin_user', 'action', 'test', 'created_at']
    search_fields = ['admin_user__username', 'message', 'test__title']
    list_filter = ['action', 'created_at']
    readonly_fields = ['admin_user', 'action', 'test', 'message', 'metadata', 'created_at']
    ordering = ['-created_at']


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    """
    Admin configuration for Question model with inline answers.
    """
    list_display = ['test', 'order', 'question_text', 'marks']
    list_filter = ['test', 'created_at']
    search_fields = ['question_text']
    inlines = [AnswerInline]
    ordering = ['test', 'order']


@admin.register(Answer)
class AnswerAdmin(admin.ModelAdmin):
    """
    Admin configuration for Answer model.
    """
    list_display = ['question', 'answer_text', 'is_correct', 'order']
    list_filter = ['is_correct', 'question__test']
    search_fields = ['answer_text']


@admin.register(TestAttempt)
class TestAttemptAdmin(admin.ModelAdmin):
    """
    Admin configuration for TestAttempt.
    """
    list_display = ['user', 'test', 'status', 'score', 'percentage', 'is_passed', 'started_at']
    list_filter = ['status', 'is_passed', 'started_at']
    search_fields = ['user__username', 'test__title']
    readonly_fields = ['started_at', 'submitted_at']


@admin.register(UserAnswer)
class UserAnswerAdmin(admin.ModelAdmin):
    """
    Admin configuration for UserAnswer.
    """
    list_display = ['attempt', 'question', 'selected_answer', 'is_correct', 'is_marked_for_review']
    list_filter = ['is_correct', 'is_marked_for_review']
    search_fields = ['attempt__user__username', 'question__question_text']
