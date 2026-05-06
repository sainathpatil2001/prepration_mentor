from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import *

router = DefaultRouter()
router.register(r'users', UserViewSet)
router.register(r'categories', TestCategoryViewSet)
router.register(r'tests', TestViewSet)
router.register(r'attempts', TestAttemptViewSet, basename='test-attempt')
router.register(r'plans', SubscriptionPlanViewSet)
router.register(r'subscriptions', SubscriptionViewSet, basename='subscription')
router.register(r'tickets', SupportTicketViewSet, basename='support-ticket')
router.register(r'notifications', NotificationViewSet, basename='notification')

from .views_payments import PaymentViewSet
router.register(r'payments', PaymentViewSet, basename='api_payment')

urlpatterns = [
    path('', include(router.urls)),
    path('auth/login/', CustomAuthToken.as_view(), name='api_login'),
    path('auth/register/', RegisterView.as_view(), name='api_register'),
    path('auth/password-reset/request/', RequestPasswordResetView.as_view(), name='api_request_password_reset'),
    path('auth/verify-email/', VerifyEmailView.as_view(), name='api_verify_email'),
    path('auth/resend-verification/', ResendVerificationView.as_view(), name='api_resend_verification'),
    path('auth/password-reset-otp/send/', SendPasswordResetOTPView.as_view(), name='api_send_password_reset_otp'),
    path('auth/password-reset-otp/confirm/', ResetPasswordWithOTPView.as_view(), name='api_reset_password_with_otp'),
    path('dashboard/', DashboardView.as_view(), name='api_dashboard'),
    path('change-password/', ChangePasswordView.as_view(), name='api_change_password'),
    path('contact/', ContactView.as_view(), name='api_contact'),
]
