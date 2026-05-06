from django.urls import path
from django.views.generic import RedirectView
from django.contrib.auth import logout
from django.shortcuts import redirect
from . import views, admin_views
from .views import check_username
from .views import check_username, check_email
def custom_logout(request):
    """Custom logout view with session cleanup"""
    if request.user.is_authenticated:
        # Delete user session record
        from .models import UserSession
        UserSession.objects.filter(user=request.user).delete()
    logout(request)
    return redirect('custom_login')

urlpatterns = [
    path('', views.landing_page, name='home'),
    
    #check username and email here 
    path("check-email/", check_email, name="check_email"),
    path("check-username/", check_username, name="check_username"),
    
    path('login/', views.custom_login, name='custom_login'),
    # path('signup/', views.signup, name='signup'),  # Removed to prevent shadowing allauth signup or custom redirect loop
    path('logout/', custom_logout, name='custom_logout'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('profile/', views.profile_view, name='profile'),
    path('add-funds/', views.add_funds, name='add_funds'),
    path('payment-success/', views.payment_success, name='payment_success'),
    path('payment-failed/', views.payment_failed, name='payment_failed'),
    path('payment-history/', views.payment_history, name='payment_history'),
    path('verify-email/', views.verify_email, name='verify_email'),
    path('verify-email/send/', views.send_verification_otp, name='send_verification_otp'),
    path('change-password/', views.change_password, name='change_password'),
    path('reset-password/', views.account_reset_password, name='account_reset_password'),
    path('reset-password/confirm/<str:uidb64>/<str:token>/', views.account_reset_password_confirm, name='account_reset_password_confirm'),
    path('delete-account/', views.delete_account, name='delete_account'),
    # Exam system URLs
    path('tests/', views.test_list, name='test_list'),
    path('tests/search/', views.search_tests, name='search_tests'),
    path('tests/<int:test_id>/', views.test_detail, name='test_detail'),
    path('tests/<int:test_id>/toggle-save/', views.toggle_save_test, name='toggle_save_test'),
    path('tests/<int:test_id>/start/', views.exam_start, name='exam_start'),
    path('exam/<int:attempt_id>/', views.exam_interface, name='exam_interface'),
    path('exam/<int:attempt_id>/save/', views.save_answer, name='save_answer'),
    path('exam/<int:attempt_id>/report/', views.submit_report, name='submit_report'),
    path('exam/<int:attempt_id>/submit/', views.exam_submit, name='exam_submit'),
    path('exam/<int:attempt_id>/results/', views.exam_results, name='exam_results'),
    path('notifications/', views.notification_list, name='notification_list'),
    path('notifications/<int:notification_id>/read/', views.read_notification, name='read_notification'),
    path('test-history/', views.test_history, name='test_history'),
    # Custom admin dashboard routes
    path('admin-login/', admin_views.admin_login_view, name='admin_login'),
    path('admin-logout/', admin_views.admin_logout_view, name='admin_logout'),
    path('admin-dashboard/', admin_views.dashboard_overview, name='admin_dashboard_overview'),
    path('admin-dashboard/test-sets/', admin_views.test_list, name='admin_dashboard_manage'),
    path('admin-dashboard/test-sets/add/', admin_views.test_create, name='admin_dashboard_add'),
    path('admin-dashboard/test-sets/<int:test_id>/edit/', admin_views.test_edit, name='admin_dashboard_edit'),
    path('admin-dashboard/test-sets/<int:test_id>/delete/', admin_views.test_delete, name='admin_dashboard_delete'),
    path('admin-dashboard/test-sets/<int:test_id>/toggle-visibility/', admin_views.toggle_visibility, name='admin_dashboard_toggle_visibility'),
    path('admin-dashboard/test-sets/<int:test_id>/publish/', admin_views.publish_test, name='admin_dashboard_publish'),
    path('admin-dashboard/test-sets/<int:test_id>/save-draft/', admin_views.save_as_draft, name='admin_dashboard_save_draft'),
    path('admin-dashboard/drafts/', admin_views.drafts_list, name='admin_dashboard_drafts'),
    path('admin-dashboard/logs/', admin_views.admin_logs, name='admin_dashboard_logs'),
    path('admin-dashboard/logs/delete/', admin_views.delete_logs, name='admin_dashboard_logs_delete'),
    
    # Category management
    path('admin-dashboard/categories/', admin_views.category_list, name='admin_dashboard_categories'),
    path('admin-dashboard/categories/add/', admin_views.category_create, name='admin_dashboard_category_add'),
    path('admin-dashboard/categories/<int:pk>/edit/', admin_views.category_edit, name='admin_dashboard_category_edit'),
    path('admin-dashboard/categories/<int:pk>/delete/', admin_views.category_delete, name='admin_dashboard_category_delete'),
    
    # Privacy Policy Management
    path('admin-dashboard/privacy-policy/', admin_views.privacy_policy_edit, name='admin_privacy_policy_edit'),
    path('privacy-policy/', views.privacy_policy_view, name='privacy_policy'),
    path('terms-of-service/', views.terms_of_service_view, name='terms_of_service'),
    path('contact-us/', views.contact_us_view, name='contact_us'),
    path('check-username/', views.check_username, name='check_username'),
    path('check-email/', views.check_email, name='check_email'),
    
    # Referral code management
    path('admin-dashboard/referrals/', admin_views.referral_list, name='admin_referral_list'),
    path('admin-dashboard/referrals/add/', admin_views.referral_add, name='admin_referral_add'),
    path('admin-dashboard/referrals/<int:pk>/edit/', admin_views.referral_edit, name='admin_referral_edit'),
    path('admin-dashboard/referrals/<int:pk>/delete/', admin_views.referral_delete, name='admin_referral_delete'),

    # Subscription management
    path('admin-dashboard/subscriptions/', admin_views.subscription_list, name='admin_dashboard_subscriptions'),
    path('admin-dashboard/subscriptions/add/', admin_views.subscription_add, name='admin_dashboard_subscription_add'),
    path('admin-dashboard/subscriptions/<int:pk>/edit/', admin_views.subscription_edit, name='admin_dashboard_subscription_edit'),
    path('admin-dashboard/subscriptions/<int:pk>/extend/', admin_views.subscription_extend, name='admin_dashboard_subscription_extend'),
    path('admin-dashboard/subscription-logs/', admin_views.subscription_logs, name='admin_dashboard_subscription_logs'),
    path('admin-dashboard/users/search/', admin_views.search_users, name='admin_dashboard_search_users'),

    path('admin-reset-password/', views.admin_reset_password, name='admin_reset_password'),
    
    # Backup & Restore
    path('admin-dashboard/backup/', admin_views.backup_restore_view, name='admin_backup_restore'),
    
    # Email Settings
    path('admin-dashboard/email-settings/', admin_views.email_settings_view, name='admin_email_settings'),
    path('admin-dashboard/email-marketing/', admin_views.email_marketing_view, name='admin_email_marketing'),
    
    # Reports
    path('admin-dashboard/reports/', admin_views.report_list, name='admin_report_list'),
    path('admin-dashboard/reports/<int:report_id>/delete/', admin_views.delete_report, name='admin_report_delete'),
    path('admin-dashboard/reports/<int:report_id>/toggle/', admin_views.toggle_report_status, name='admin_report_toggle'),
]

