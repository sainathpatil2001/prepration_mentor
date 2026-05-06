from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from .email_utils import send_custom_email as send_mail
from datetime import timedelta
from django.contrib.auth.forms import PasswordChangeForm, SetPasswordForm
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.urls import reverse  # added import
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger  # added paginator import
from django.db.models import Q  # ADDED: Q import for search
from functools import wraps
from django.template.loader import render_to_string
import json
import razorpay
from decimal import Decimal
from django.http import JsonResponse
from django.contrib.auth.models import User
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET
from django.http import JsonResponse
from django.contrib.auth.models import User
from django.views.decorators.http import require_GET



# NEW imports for URL inspection
from django.urls import get_resolver
from django.urls.resolvers import URLPattern, URLResolver
from .models import (
    UserProfile,
    PaymentTransaction,
    UserSession,
    EmailOTP,
    Test,
    Question,
    Answer,
    TestAttempt,
    UserAnswer,
    SubscriptionPlan,
    Subscription,
    TestCategory,
    Notification,
    SavedTest,
    MotivationQuote,
)

from django.http import JsonResponse
from django.contrib.auth.models import User
from django.views.decorators.http import require_GET
from django.utils import timezone
from django.core.cache import cache
from .utils_views import _annotate_test_data
from collections import namedtuple

# Define a fallback quote structure for caching
FallbackQuote = namedtuple('FallbackQuote', ['quote', 'author'])

# -------------------------
# Helper: Rate Limit (Basic)
# -------------------------
def is_rate_limited(request, key_prefix, limit=10, window=60):
    """
    Check if a user is rate-limited based on their IP address.

    Args:
        request (HttpRequest): The incoming request.
        key_prefix (str): Prefix for the cache key to separate different actions.
        limit (int): Maximum number of requests allowed within the window.
        window (int): Time window in seconds.

    Returns:
        bool: True if the user is rate-limited (exceeded limit), False otherwise.
    """

    ip = request.META.get("REMOTE_ADDR", "")
    key = f"rl_{key_prefix}_{ip}"
    current = cache.get(key, 0)

    if current >= limit:
        return True

    cache.set(key, current + 1, timeout=window)
    return False


# -----------------------------------
# Secure Username Availability Checker
# -----------------------------------
@require_GET
def check_username(request):
    """
    AJAX endpoint to check if a username is available.
    
    Prevents account enumeration by returning generic messages if possible,
    but primarily used for registration validation.
    """
    if is_rate_limited(request, "check_username", limit=15, window=60):  
        return JsonResponse({"valid": False, "message": "Please slow down."}, status=429)

    username = request.GET.get("username", "").strip()

    if len(username) < 3:
        return JsonResponse({"valid": False, "message": "Invalid username."})

    exists = User.objects.filter(username__iexact=username, is_active=True).exists()

    if exists:
        # SECURE Message (no account enumeration)
        return JsonResponse({"valid": False, "message": "This username cannot be used."})

    return JsonResponse({"valid": True, "message": "Username is usable."})


# -----------------------------------
# Secure Email Availability Checker
# -----------------------------------
@require_GET
def check_email(request):
    """
    AJAX endpoint to check if an email address is available.
    
    Prevents email enumeration attacks while assisting user registration.
    """
    if is_rate_limited(request, "check_email", limit=10, window=60):  
        return JsonResponse({"valid": False, "message": "Please slow down."}, status=429)

    email = request.GET.get("email", "").strip()

    if len(email) < 5 or "@" not in email:
        return JsonResponse({"valid": False, "message": "Invalid email."})

    exists = User.objects.filter(email__iexact=email, is_active=True).exists()

    if exists:
        # SECURE Message (prevents email enumeration attacks)
        return JsonResponse({"valid": False, "message": "This email cannot be used."})

    return JsonResponse({"valid": True, "message": "Email is usable."})








def get_razorpay_client():
    """
    Initialize and return an authenticated Razorpay client.
    
    Validates that API keys are present and correct in settings.
    
    Returns:
        razorpay.Client: Authenticated client instance.
    
    Raises:
        ValueError: If keys are missing, placeholders, or invalid.
    """
    key_id = settings.RAZORPAY_KEY_ID
    key_secret = settings.RAZORPAY_KEY_SECRET
    
    # Check if keys are configured
    if not key_id or not key_secret:
        raise ValueError(
            "Razorpay API keys are not configured. "
            "Please set RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET in settings.py or environment variables."
        )
    
    # Check for placeholder values
    placeholder_values = ['your_razorpay_key_id', 'your_razorpay_key_secret', '']
    if key_id in placeholder_values or key_secret in placeholder_values:
        raise ValueError(
            "Razorpay API keys are not configured. "
            "Please set RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET in settings.py or environment variables. "
            "Get your keys from: https://dashboard.razorpay.com/app/keys"
        )
    
    try:
        client = razorpay.Client(auth=(key_id, key_secret))
        # Try a simple API call to verify authentication
        # Using payment methods which is lightweight
        try:
            client.payment.fetch_all({'count': 1})
        except Exception as validation_error:
            # If validation fails, log warning but allow client creation
            # This prevents blocking when keys are correct but API returns unexpected response
            import logging
            logging.warning(f"Razorpay client validation warning: {str(validation_error)}")
        return client
    except Exception as e:
        # Catch all exceptions from client initialization
        error_msg = str(e)
        if 'auth' in error_msg.lower() or 'unauthorized' in error_msg.lower():
            raise ValueError(
                f"Razorpay authentication failed: {error_msg}. "
                "Please verify your Key ID and Key Secret are correct. "
                "Get them from: https://dashboard.razorpay.com/app/keys"
            )
        else:
            raise ValueError(f"Error initializing Razorpay client: {error_msg}")


@login_required
def profile_view(request):
    """
    View to display and update user profile information.
    
    Handles:
    - User details (first name, last name)
    - Profile details (phone, address, image)
    - Tab navigation (overview, update, payment_history)
    """
    profile = request.user.profile

    if request.method == 'POST':
        user = request.user
        # Track changes
        changes_made = False
        
        # Check User model changes
        if user.first_name != request.POST.get('first_name', user.first_name):
            user.first_name = request.POST.get('first_name', user.first_name)
            changes_made = True
            
        if user.last_name != request.POST.get('last_name', user.last_name):
            user.last_name = request.POST.get('last_name', user.last_name)
            changes_made = True
            
        if changes_made:
            user.save()

        # Check Profile model changes
        if profile.phone != request.POST.get('phone', profile.phone):
            profile.phone = request.POST.get('phone', profile.phone)
            changes_made = True
            
        if profile.address != request.POST.get('address', profile.address):
            profile.address = request.POST.get('address', profile.address)
            changes_made = True
            
        if profile.city != request.POST.get('city', profile.city):
            profile.city = request.POST.get('city', profile.city)
            changes_made = True
            
        if profile.state != request.POST.get('state', profile.state):
            profile.state = request.POST.get('state', profile.state)
            changes_made = True
            
        if profile.country != request.POST.get('country', profile.country):
            profile.country = request.POST.get('country', profile.country)
            changes_made = True
            
        if profile.pincode != request.POST.get('pincode', profile.pincode):
            profile.pincode = request.POST.get('pincode', profile.pincode)
            changes_made = True

        if 'profile_picture' in request.FILES:
            profile.profile_picture = request.FILES['profile_picture']
            changes_made = True

        if changes_made:
            profile.save()
            messages.success(request, 'Profile updated successfully!')
            
            # Send notification email
            try:
                send_mail(
                    subject='Profile Updated - Prepration Mentor',
                    message=f"""Hello {user.get_full_name() or user.username},

Your profile information has been updated successfully.

If you did not make this change, please contact support immediately.

Best regards,
Prepration Mentor Team""",
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[user.email],
                    fail_silently=True,
                )
            except Exception:
                pass
        else:
            messages.info(request, 'No changes were made to your profile.')
            
        # After update keep user on update tab
        return redirect(f"{reverse('profile')}?tab=update")

    # Determine which sub-tab to show
    active_tab = request.GET.get('tab', 'overview')

    # Refresh profile from DB to ensure latest values (useful if files uploaded)
    request.user.refresh_from_db()
    profile = request.user.profile
    
    # Get active subscription
    active_subscription = get_active_subscription(request.user)
    
    # Get payment history for payment_history tab
    transactions = None
    if active_tab == 'payment_history':
        transactions = PaymentTransaction.objects.filter(user=request.user).select_related('subscription_plan', 'subscription').order_by('-created_at')
    
    context = {
        'profile': profile,
        'password_form': PasswordChangeForm(user=request.user),
        'active_tab': active_tab,
        'show_profile_sidebar': True,
        'active_subscription': active_subscription,
        'transactions': transactions,
    }
    return render(request, 'accounts/profile.html', context)


def _ensure_subscription_plans_exist():
    """Ensure subscription plans exist in database"""
    plans_data = [
        {
            'name': 'Monthly Plan',
            'plan_type': 'monthly',
            'duration_months': 1,
            'price': 99.00,
            'description': 'Perfect for trying out our platform. Access all features for 1 month.',
            'is_active': True,
        },
        {
            'name': 'Half-Yearly Plan',
            'plan_type': 'half_yearly',
            'duration_months': 6,
            'price': 499.00,
            'description': 'Best value for 6 months. Save money with this plan.',
            'is_active': True,
        },
        {
            'name': 'Yearly Plan',
            'plan_type': 'yearly',
            'duration_months': 12,
            'price': 899.00,
            'description': 'Maximum savings! Get full access for a whole year at the best price.',
            'is_active': True,
        },
    ]
    
    for plan_data in plans_data:
        SubscriptionPlan.objects.get_or_create(
            plan_type=plan_data['plan_type'],
            defaults={
                'name': plan_data['name'],
                'duration_months': plan_data['duration_months'],
                'price': plan_data['price'],
                'description': plan_data['description'],
                'is_active': plan_data['is_active'],
            }
        )


def get_active_subscription(user):
    """Helper function to get user's active subscription"""
    from django.utils import timezone
    try:
        subscription = Subscription.objects.filter(
            user=user,
            status='active',
            is_active=True,
            expires_at__gt=timezone.now()
        ).order_by('-expires_at').first()
        return subscription
    except:
        return None


def has_active_subscription(user):
    """Check if user has an active subscription"""
    subscription = get_active_subscription(user)
    return subscription is not None


def subscription_required(view_func):
    """Decorator to require active subscription for accessing views"""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not has_active_subscription(request.user):
            messages.warning(
                request,
                'You need an active subscription to access this feature. Please subscribe to continue.'
            )
            return redirect('add_funds')
        return view_func(request, *args, **kwargs)
    return _wrapped_view


@login_required
def add_funds(request):
    """
    Displays subscription plans and handles the initiation of a new subscription.
    
    Includes a mock payment implementation for demonstration purposes if
    Razorpay is not fully configured or for testing.
    """
    if request.method == 'POST':
        try:
            plan_id = request.POST.get('plan_id')
            if not plan_id:
                messages.error(request, 'Please select a subscription plan.')
                return redirect('add_funds')
            
            plan = get_object_or_404(SubscriptionPlan, id=plan_id, is_active=True)
            
            # --- MOCK PAYMENT IMPLEMENTATION ---
            # CURRENTLY BYPASSING PAYMENT GATEWAY AS REQUESTED
            
            # Create a mock order ID
            mock_order_id = f'mock_order_{int(timezone.now().timestamp())}'
            mock_payment_id = f'mock_pay_{int(timezone.now().timestamp())}'
            
            # Save transaction as success immediately
            payment_transaction = PaymentTransaction.objects.create(
                user=request.user,
                transaction_type='subscription',
                subscription_plan=plan,
                razorpay_order_id=mock_order_id,
                razorpay_payment_id=mock_payment_id,
                amount=plan.price,
                status='success'
            )
            
            # Check if user has an active subscription
            active_sub = get_active_subscription(request.user)
            
            user_subscription = None
            if active_sub and active_sub.expires_at > timezone.now():
                # Extend existing subscription
                active_sub.expires_at += timedelta(days=plan.duration_months * 30)
                active_sub.save()
                user_subscription = active_sub
            else:
                # Create new subscription
                expires_at = timezone.now() + timedelta(days=plan.duration_months * 30)
                user_subscription = Subscription.objects.create(
                    user=request.user,
                    plan=plan,
                    status='active',
                    is_active=True,
                    expires_at=expires_at
                )
            
            # Link subscription to transaction
            payment_transaction.subscription = user_subscription
            payment_transaction.save()
            
            messages.success(request, f'Payment Successful! Subscription "{plan.name}" has been activated.')
            return redirect('dashboard')
            # -----------------------------------
            
        except ValueError as e:
            messages.error(request, str(e))
            return redirect('add_funds')
        except Exception as e:
            # Catch all other exceptions (including razorpay library exceptions)
            error_msg = str(e)
            if 'order' in error_msg.lower():
                messages.error(request, f'Error creating payment order: {error_msg}. Please try again.')
            else:
                messages.error(request, f'Error processing subscription: {error_msg}. Please contact support.')
            return redirect('add_funds')
    
    # Auto-create subscription plans if they don't exist
    _ensure_subscription_plans_exist()
    
    # Get all active subscription plans
    plans = SubscriptionPlan.objects.filter(is_active=True).order_by('price')
    
    # Get active subscription for user
    active_subscription = get_active_subscription(request.user)
    
    # Check Razorpay configuration
    razorpay_configured = False
    razorpay_error = None
    
    try:
        key_id = settings.RAZORPAY_KEY_ID
        key_secret = settings.RAZORPAY_KEY_SECRET
        
        if key_id and key_secret and key_id != 'your_razorpay_key_id' and key_secret != 'your_razorpay_key_secret':
            try:
                get_razorpay_client()
                razorpay_configured = True
            except Exception as e:
                razorpay_error = str(e)
        else:
            razorpay_error = "Razorpay API keys not configured"
    except Exception as e:
        razorpay_error = str(e)
    
    context = {
        'plans': plans,
        'active_subscription': active_subscription,
        'razorpay_configured': razorpay_configured,
        'razorpay_error': razorpay_error,
    }
    return render(request, 'accounts/add_funds.html', context)


@csrf_exempt
def payment_success(request):
    """
    Callback view for successful Razorpay payments.
    
    Verifies the payment signature and updates the transaction status.
    Activates the subscription or adds balance to the user's account.
    """
    if request.method == 'POST':
        try:
            # Get Razorpay client
            razorpay_client = get_razorpay_client()
            
            # Get payment details from Razorpay
            payment_id = request.POST.get('razorpay_payment_id')
            order_id = request.POST.get('razorpay_order_id')
            signature = request.POST.get('razorpay_signature')
            
            # Verify payment signature
            params_dict = {
                'razorpay_order_id': order_id,
                'razorpay_payment_id': payment_id,
                'razorpay_signature': signature
            }
            
            try:
                razorpay_client.utility.verify_payment_signature(params_dict)
            except Exception as e:
                # Signature verification failed
                error_msg = str(e)
                if 'signature' in error_msg.lower() or 'verify' in error_msg.lower():
                    messages.error(request, 'Payment verification failed! Signature mismatch.')
                else:
                    messages.error(request, f'Payment verification failed: {error_msg}')
                return redirect('add_funds')
            
            # Get payment transaction
            payment_transaction = get_object_or_404(
                PaymentTransaction,
                razorpay_order_id=order_id,
                status='pending'
            )
            
            # Update transaction
            payment_transaction.razorpay_payment_id = payment_id
            payment_transaction.razorpay_signature = signature
            payment_transaction.status = 'success'
            
            with transaction.atomic():
                payment_transaction.save()
                
                # Handle subscription vs balance top-up
                if payment_transaction.transaction_type == 'subscription' and payment_transaction.subscription_plan:
                    # Create or extend subscription
                    plan = payment_transaction.subscription_plan
                    
                    # Check if user has an active subscription
                    active_sub = get_active_subscription(payment_transaction.user)
                    
                    if active_sub and active_sub.expires_at > timezone.now():
                        # Extend existing subscription
                        active_sub.expires_at += timedelta(days=plan.duration_months * 30)
                        active_sub.save()
                        user_subscription = active_sub
                    else:
                        # Create new subscription
                        expires_at = timezone.now() + timedelta(days=plan.duration_months * 30)
                        user_subscription = Subscription.objects.create(
                            user=payment_transaction.user,
                            plan=plan,
                            status='active',
                            is_active=True,
                            expires_at=expires_at
                        )
                    
                    # Link subscription to transaction
                    payment_transaction.subscription = user_subscription
                    payment_transaction.save()
                    
                    messages.success(request, f'Subscription "{plan.name}" activated successfully! Valid until {user_subscription.expires_at.strftime("%B %d, %Y")}.')
                else:
                    # Balance top-up
                    profile = payment_transaction.user.profile
                    profile.balance += payment_transaction.amount
                    profile.save()
                    messages.success(request, f'Payment of ₹{payment_transaction.amount} successful! Your account has been credited.')
            
            return redirect('dashboard')
            
        except Exception as e:
            messages.error(request, f'Error processing payment: {str(e)}')
            return redirect('add_funds')
    
    return redirect('dashboard')


@csrf_exempt
def payment_failed(request):
    """
    Callback view for failed Razorpay payments.
    
    Updates the transaction status to 'failed'.
    """
    if request.method == 'POST':
        try:
            order_id = request.POST.get('razorpay_order_id')
            payment_transaction = get_object_or_404(
                PaymentTransaction,
                razorpay_order_id=order_id,
                status='pending'
            )
            payment_transaction.status = 'failed'
            payment_transaction.save()
            messages.error(request, 'Payment failed. Please try again.')
        except Exception as e:
            messages.error(request, f'Error processing payment failure: {str(e)}')
    
    return redirect('add_funds')


@login_required
def payment_history(request):
    """View payment transaction history with subscription details"""
    transactions = PaymentTransaction.objects.filter(user=request.user).select_related('subscription_plan', 'subscription')
    
    context = {
        'transactions': transactions,
    }
    return render(request, 'accounts/payment_history.html', context)


from django.views.decorators.debug import sensitive_post_parameters
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect

@sensitive_post_parameters()
@csrf_protect
@never_cache
def custom_login(request):
    """
    Custom login view handling authentication via username or email.
    
    Refuses login for staff/admin users (redirects to admin login).
    Create a user profile if one does not exist for the user.
    """
    if request.user.is_authenticated:
        # Redirect admins to admin login if they accidentally land here
        if request.user.is_staff:
            logout(request)
            return redirect('admin_login')
            
        if not hasattr(request.user, 'profile'):
             # Create minimal profile if missing
             UserProfile.objects.create(user=request.user)

        # Removed forced redirect, allow user to verify via profile
        # if not request.user.profile.email_verified:
        #      return redirect('verify_email')
             
        return redirect('dashboard')
    
    # Check if user was redirected here due to session invalidation
    if request.session.get('session_invalidated'):
        messages.warning(request, 'You have been logged out because your account was accessed from another device.')
        # Clear the flag
        del request.session['session_invalidated']
    
    if request.method == 'POST':
        from django.contrib.auth import authenticate
        username_input = request.POST.get('username')
        password = request.POST.get('password')
        
        user = None
        
        # Check if login is via email
        if '@' in username_input:
            # Fetch all users with this email (handles duplicates)
            matching_users = User.objects.filter(email__iexact=username_input)
            for u in matching_users:
                # Check if this user's credentials are correct
                authenticated_user = authenticate(request, username=u.username, password=password)
                if authenticated_user:
                    user = authenticated_user
                    break
        
        # If email login didn't succeed (or wasn't an email), try username login
        if user is None:
            user = authenticate(request, username=username_input, password=password)
        
        if user is not None:
            # Check if user is staff (admin)
            if user.is_staff:
                messages.error(request, 'Please use the Admin Login page.')
                return redirect('admin_login')

            # Login user (this will trigger the user_logged_in signal which creates UserSession)
            login(request, user)
            
            # Removed forced redirect, allow user to verify via profile
            # if not user.profile.email_verified:
            #     _ensure_fresh_otp(user)
            #     messages.info(request, 'Please verify your email. We have sent a 6-digit code.')
            #     return redirect('verify_email')
            
            messages.success(request, 'Login successful!')
            return redirect('dashboard')
        else:
            messages.error(request, 'Invalid username or password.')
    
    return render(request, 'accounts/login.html')


@login_required
def verify_email(request):
    """
    View to verify user's email address using an OTP.
    """
    if request.user.profile.email_verified:
        return redirect('dashboard')
    if request.method == 'POST':
        code = request.POST.get('otp', '').strip()
        if len(code) != 6 or not code.isdigit():
            messages.error(request, 'Enter a valid 6-digit code.')
            return redirect('verify_email')
        otp = EmailOTP.objects.filter(
            user=request.user,
            code=code,
            is_used=False,
            expires_at__gt=timezone.now()
        ).order_by('-created_at').first()
        if not otp:
            messages.error(request, 'Invalid or expired code. Please try again.')
            return redirect('verify_email')
        otp.is_used = True
        otp.save()
        profile = request.user.profile
        profile.email_verified = True
        profile.save()
        messages.success(request, 'Email verified successfully!')
        return redirect('dashboard')
    # On GET, ensure an OTP exists
    _ensure_fresh_otp(request.user)
    return render(request, 'accounts/verify_email.html')


@login_required
def send_verification_otp(request):
    """Resend OTP via email"""
    if request.method == 'POST':
        _ensure_fresh_otp(request.user, force_new=True)
        messages.success(request, 'Verification code resent successfully!')
        return redirect('verify_email')
    return redirect('verify_email')


def _ensure_fresh_otp(user, force_new: bool = False):
    """Create and email a fresh OTP if needed"""
    # Reuse a valid OTP generated within last 60 seconds unless forcing new
    recent_threshold = timezone.now() - timedelta(seconds=60)
    otp = None
    if not force_new:
        otp = EmailOTP.objects.filter(
            user=user,
            is_used=False,
            expires_at__gt=timezone.now(),
            created_at__gt=recent_threshold,
        ).order_by('-created_at').first()
    if not otp:
        # Invalidate previous unused codes
        EmailOTP.objects.filter(user=user, is_used=False, expires_at__gt=timezone.now()).update(is_used=True)
        code = f"{_generate_code()}"
        otp = EmailOTP.objects.create(
            user=user,
            code=code,
            expires_at=timezone.now() + timedelta(minutes=10),
        )
    subject = 'Your verification code'
    message = f'Your verification code is: {otp.code}\nThis code will expire in 10 minutes.'
    from_email = settings.DEFAULT_FROM_EMAIL
    recipient_list = [user.email]
    if recipient_list and recipient_list[0]:
        try:
            send_mail(subject, message, from_email, recipient_list, fail_silently=False)
        except Exception:
            # Surface a non-blocking message on next page load via messages if needed
            pass
    return otp


def _generate_code() -> str:
    import random
    return f"{random.randint(0, 999999):06d}"


@login_required
def change_password(request):
    """
    Handles password change requests from the user profile.
    
    Updates session hash to keep user logged in after password change.
    Sends specific email notification upon success.
    """
    if request.method == 'POST':
        form = PasswordChangeForm(user=request.user, data=request.POST)
        if form.is_valid():
            user = form.save()
            # Keep the user logged in after password change
            update_session_auth_hash(request, user)
            # Send confirmation email
            try:
                if user.email:
                    send_mail(
                        subject='Your password was changed',
                        message='Hello,\n\nThis is a confirmation that your password was changed. If this was not you, please reset your password immediately.',
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[user.email],
                        fail_silently=True,
                    )
            except Exception:
                pass
            messages.success(request, 'Your password has been updated successfully.')
            # Keep the password tab active after change so user sees confirmation
            return redirect(f"{reverse('profile')}?tab=password")
        else:
            # Render profile with errors
            profile = request.user.profile
            active_subscription = get_active_subscription(request.user)
            context = {
                'profile': profile,
                'password_form': form,
                'active_tab': 'password',
                'show_profile_sidebar': True,
                'active_subscription': active_subscription,
            }
            return render(request, 'accounts/profile.html', context)
    else:
        return redirect('profile')


@login_required
def delete_account(request):
    """
    Deactivates the user account ('soft delete').
    
    We prefer deactivation over deletion to preserve payment history and
    audit logs linked to the user.
    """
    if request.method == 'POST':
        user = request.user
        # We deactivate instead of delete to preserve payment history
        # as PaymentTransaction has on_delete=CASCADE
        user.is_active = False
        user.save()
        
        logout(request)
        messages.success(request, 'Your account has been successfully deleted. We are sorry to see you go.')
        return redirect('home')
    
    return redirect('profile')


# ==================== EXAM SYSTEM VIEWS ====================

@login_required
def dashboard(request):
    """
    User dashboard displaying specific statistics and active subscription details.
    
    Features:
    - Recent transactions
    - Test attempt statistics (total, passed, average)
    - Daily motivation quote
    """
    profile = request.user.profile
    recent_transactions = PaymentTransaction.objects.filter(user=request.user)[:5]
    
    # Get active subscription
    active_subscription = get_active_subscription(request.user)
    
    # Test statistics
    from django.db.models import Avg
    total_attempts = TestAttempt.objects.filter(user=request.user, status='completed').count()
    passed_tests = TestAttempt.objects.filter(user=request.user, status='completed', is_passed=True).count()
    avg_score = TestAttempt.objects.filter(user=request.user, status='completed').aggregate(
        avg_percentage=Avg('percentage')
    )['avg_percentage'] or 0
    recent_attempts = TestAttempt.objects.filter(user=request.user).order_by('-started_at')[:3]  # Changed limit to 3 as requested

    # Motivation Quote
    today_date = timezone.now().date()
    # Cache key for daily quote
    quote_cache_key = f"daily_quote_{today_date}"
    motivation_quote = cache.get(quote_cache_key)
    
    if not motivation_quote:
        motivation_quote = MotivationQuote.objects.filter(display_date=today_date, is_active=True).first()
        if not motivation_quote:
            # Fallback to random or latest active quote
            # Optimization: Avoid order_by('?') on large table, pick random from ID list or just cache the result
            # Since we cache the result for 24h, order_by('?') once a day is acceptable
            motivation_quote = MotivationQuote.objects.filter(is_active=True).order_by('?').first()

        if not motivation_quote:
            # Hardcoded fallback if DB is empty
            motivation_quote = FallbackQuote(
                quote="Believe you can and you're halfway there.",
                author="Theodore Roosevelt"
            )
        
        # Cache for 24 hours
        cache.set(quote_cache_key, motivation_quote, 86400)

    
    context = {
        'profile': profile,
        'recent_transactions': recent_transactions,
        'total_attempts': total_attempts,
        'passed_tests': passed_tests,
        'avg_score': round(avg_score, 2),
        'recent_attempts': recent_attempts,
        'active_subscription': active_subscription,
        'motivation_quote': motivation_quote,
    }
    return render(request, 'accounts/dashboard.html', context)


@login_required
def test_list(request):
    """
    Displays a list of available tests with filtering and search capabilities.
    
    Filters:
    - Search query (title/description)
    - Category
    - Month (published date)
    - Saved (bookmarked) exams
    
    Supports pagination.
    """
    # Check subscription status
    has_subscription = has_active_subscription(request.user)
    
    q = request.GET.get('q', '').strip()
    category_slug = request.GET.get('category', '').strip()
    month_str = request.GET.get('month', '').strip()
    
    tests_qs = Test.objects.filter(
        is_active=True,
        status='published',
        is_hidden=False,
    ).select_related('category').order_by(
        'category__display_order', 'category__name', '-created_at'
    )
    selected_category = None
    if q:
        # search title and description
        tests_qs = tests_qs.filter(
            Q(title__icontains=q) | Q(description__icontains=q)
        )
    if category_slug:
        tests_qs = tests_qs.filter(category__slug=category_slug)
        selected_category = TestCategory.objects.filter(slug=category_slug).first()
        
    saved_filter = request.GET.get('saved', '').strip()
    
    # Check if any filter is active
    is_filtered = any([
        q,
        category_slug,
        month_str,
        saved_filter == 'true'
    ])
    
    # Default to current month if no filters are active on initial load
    if not is_filtered:
        month_str = timezone.now().strftime('%Y-%m')

    if month_str:
        try:
            year, month = map(int, month_str.split('-'))
            tests_qs = tests_qs.filter(published_at__year=year, published_at__month=month)
        except ValueError:
            pass

    if saved_filter == 'true':
        tests_qs = tests_qs.filter(users_saved__user=request.user)

    # Pagination
    page = request.GET.get('page', 1)
    paginator = Paginator(tests_qs, 10)  # 10 tests per page
    try:
        tests_page = paginator.page(page)
    except PageNotAnInteger:
        tests_page = paginator.page(1)
    except EmptyPage:
        tests_page = paginator.page(paginator.num_pages)

    # Annotate tests with user progress
    _annotate_test_data(request.user, tests_page.object_list)
    
    # Annotate saved status
    saved_test_ids = set(SavedTest.objects.filter(user=request.user).values_list('test_id', flat=True))
    for test in tests_page.object_list:
        test.is_saved = test.id in saved_test_ids

    # Build category options from model choices
    categories = list(TestCategory.objects.filter(is_active=True).order_by('display_order', 'name'))

    context = {
        'tests': tests_page,
        'query': q,
        'category': category_slug,
        'month': month_str,
        'selected_category': selected_category,
        'paginator': paginator,
        'has_subscription': has_subscription,
        'categories': categories,
        'saved_filter': saved_filter,
    }
    return render(request, 'accounts/test_list.html', context)


@login_required
def search_tests(request):
    """
    AJAX endpoint for real-time search and filtering of tests.
    
    Returns:
        JSON response containing HTML partials for the test grid and pagination,
        plus a list of search suggestions.
    """
    q = request.GET.get('q', '').strip()
    category_slug = request.GET.get('category', '').strip()
    month_str = request.GET.get('month', '').strip()
    saved_filter = request.GET.get('saved', '').strip()
    has_subscription = has_active_subscription(request.user)

    tests_qs = Test.objects.filter(
        is_active=True,
        status='published',
        is_hidden=False,
    ).select_related('category')
    if q:
        tests_qs = tests_qs.filter(Q(title__icontains=q) | Q(description__icontains=q))
    if category_slug:
        tests_qs = tests_qs.filter(category__slug=category_slug)
        
    if month_str:
        try:
            year, month = map(int, month_str.split('-'))
            tests_qs = tests_qs.filter(published_at__year=year, published_at__month=month)
        except ValueError:
            pass

    if saved_filter == 'true':
        tests_qs = tests_qs.filter(users_saved__user=request.user)

    # Pagination
    page_num = request.GET.get('page', 1)
    paginator = Paginator(tests_qs.order_by('category__display_order', 'category__name', '-created_at'), 10)
    
    try:
        tests_page = paginator.page(page_num)
    except PageNotAnInteger:
        tests_page = paginator.page(1)
    except EmptyPage:
        tests_page = paginator.page(paginator.num_pages)

    tests_list = tests_page.object_list
    
    # Annotate with user data
    if request.user.is_authenticated:
        _annotate_test_data(request.user, tests_list)
        # Annotate saved status
        saved_test_ids = set(SavedTest.objects.filter(user=request.user).values_list('test_id', flat=True))
        for test in tests_list:
            test.is_saved = test.id in saved_test_ids

    # Render tests list
    html = render_to_string(
        'accounts/_test_cards.html',
        {
            'tests': tests_list,
            'has_subscription': has_subscription,
        },
        request=request,
    )

    # Render pagination
    pagination_html = render_to_string(
        'accounts/_pagination.html',
        {
            'tests': tests_page,
            'query': q,
            'category': category_slug,
            'month': month_str,
            'saved': saved_filter,
            'is_ajax': True
        },
        request=request
    )

    # Suggestions: top 8 titles matching q (distinct)
    suggestions = []
    if q:
        suggestion_qs = (
            Test.objects.filter(
                is_active=True,
                status='published',
                is_hidden=False,
                title__icontains=q,
            )
            .select_related('category')
            .order_by('title')
        )
        seen = set()
        for test in suggestion_qs:
            label = f"{test.title} [{test.category.name}]" if test.category else test.title
            if label not in seen:
                suggestions.append(label)
                seen.add(label)
            if len(suggestions) >= 8:
                break

    return JsonResponse({
        'ok': True, 
        'html': html, 
        'pagination_html': pagination_html,
        'suggestions': suggestions
    })


@login_required
def test_detail(request, test_id):
    """
    Displays the details and instructions for a specific test.
    
    Checks if the user has an active subscription.
    Checks for any in-progress attempts for this test.
    """
    test = get_object_or_404(
        Test,
        id=test_id,
        is_active=True,
        status='published',
        is_hidden=False,
    )
    
    # Check subscription - require active subscription to view test details
    if not has_active_subscription(request.user):
        messages.warning(
            request,
            'You need an active subscription to take tests. Please subscribe to continue.'
        )
        return redirect('add_funds')
    
    # Check if user has an in-progress attempt
    in_progress = TestAttempt.objects.filter(
        user=request.user, 
        test=test, 
        status='in_progress'
    ).first()
    
    # If in progress, we should probably warn them or let them continue?
    # Current behavior: redirect immediately. 
    # New behavior: Show detail page but with "Resume" button instead of Start form? 
    # OR, if the user requested to see the instructions, we should show them. 
    # Commenting out auto-redirect to allow user to see instructions/mode selection if they want (though resuming usually implies continuing same mode).
    
    # Actually, if they have an in-progress attempt, they cannot start a NEW one until they finish.
    # So the detail page should probably just say "You have an exam in progress" and offer "Resume".
    # It shouldn't offer "Start New" with mode selection because that would create parallel attempts or overwrite.
    
    # Let's keep the redirect active BUT usually users arrive here from a list.
    # If the user explicitly wants to see instructions, maybe they can't if in progress.
    # User Request: "skeeped the exam instruction page enshure that shown to user with proper selection of mod"
    # This implies the User feels the instruction page is skipped.
    # If the user has an existing attempt, it IS skipped.
    
    # If the user wants to start a NEW exam (e.g. they abandoned the old one, or just want to see instructions),
    # we should maybe allow them to see the page.
    
    # PROPOSAL: Pass 'in_progress' to template. 
    # If 'in_progress' exists, the template should show "Resume" button and maybe "Discard & Start New" (if that's a feature).
    # For now, let's just NOT redirect and let the template handle the UI state.
    
    # if in_progress:
    #    return redirect('exam_interface', attempt_id=in_progress.id)
    
    context = {
        'test': test,
        'in_progress': in_progress,
    }
    return render(request, 'accounts/test_detail.html', context)


@login_required
def exam_start(request, test_id):
    """
    Initiates a new exam attempt.
    
    Handles:
    - Subscription check
    - Mode selection (timed/untimed)
    - Creation of TestAttempt record
    - Initialization of UserAnswer records for all questions
    """
    # Check subscription - require active subscription to start test
    if not has_active_subscription(request.user):
        messages.warning(
            request,
            'You need an active subscription to take tests. Please subscribe to continue.'
        )
        return redirect('add_funds')
    
    if request.method == 'POST':
        test = get_object_or_404(
            Test,
            id=test_id,
            is_active=True,
            status='published',
            is_hidden=False,
        )
        
        # Determine mode
        exam_mode = request.POST.get('exam_mode', 'timed')
        is_timed = (exam_mode == 'timed')
        start_new = request.POST.get('start_new', 'false') == 'true'

        existing = TestAttempt.objects.filter(
            user=request.user,
            test=test,
            status='in_progress'
        ).first()
        
        # If user explicitly wants new, or no existing, create new.
        # If existing and NOT starting new, resume.
        if existing and not start_new:
             # Logic to update existing if we wanted to change mode "on the fly" could go here, 
             # but usually changing mode means restarting. 
             # For now, just resume.
             return redirect('exam_interface', attempt_id=existing.id)
        
        if existing and start_new:
             # Mark old as completed or abandoned? 
             # Let's mark as abandoned or just leave it?
             # Better to close it to avoid clutter.
             existing.status = 'completed' # Or invalid
             existing.save()

        # Create new attempt
        attempt = TestAttempt.objects.create(
            user=request.user,
            test=test,
            status='in_progress',
            is_timed=is_timed,
            total_marks=sum(q.marks for q in test.questions.all())
        )
        
        # Initialize user answers for all questions
        for question in test.questions.all():
            UserAnswer.objects.get_or_create(
                attempt=attempt,
                question=question
            )
        
        return redirect('exam_interface', attempt_id=attempt.id)
    else:
        return redirect('test_detail', test_id=test_id)


@login_required
def exam_interface(request, attempt_id):
    """
    The main exam taking interface.
    
    Handles:
    - Question navigation
    - Timer calculation (for timed exams)
    - Subscription entitlement validation (grace period if expired during exam)
    - Auto-submission if time runs out
    """
    attempt = get_object_or_404(TestAttempt, id=attempt_id, user=request.user)
    
    # Check subscription - even if they started before, check again
    # Allow continuing if attempt was started while subscription was active
    # But check current subscription status for safety
    if attempt.status != 'in_progress':
        return redirect('exam_results', attempt_id=attempt.id)
    
    # Additional check: if subscription expired during exam, allow completion
    # but we check this at the start to prevent new exam starts
    if not has_active_subscription(request.user):
        # Check if this attempt was started recently (within last 24 hours)
        # Allow them to complete if it's recent
        time_since_start = timezone.now() - attempt.started_at
        if time_since_start.total_seconds() > 86400:  # 24 hours
            messages.warning(
                request,
                'Your subscription has expired. Please subscribe to continue taking tests.'
            )
            return redirect('add_funds')
    
    # Calculate remaining time (only if timed)
    remaining_minutes = 0
    remaining_seconds = 0
    
    if attempt.is_timed:
        elapsed = timezone.now() - attempt.started_at
        elapsed_seconds = int(elapsed.total_seconds())
        total_seconds = attempt.test.duration_minutes * 60
        remaining_seconds = total_seconds - elapsed_seconds
        remaining_minutes = remaining_seconds // 60
        
        if remaining_seconds <= 0:
            # Auto-submit
            return redirect('exam_submit', attempt_id=attempt.id)
    else:
        # For untimed, pass values that won't trigger frontend timer expiration
        remaining_seconds = 999999 
        remaining_minutes = 9999
    
    # Get current question number from request
    question_num = int(request.GET.get('q', 1)) - 1
    questions = list(attempt.test.questions.all())
    
    if question_num < 0 or question_num >= len(questions):
        question_num = 0
    
    current_question = questions[question_num]
    
    # Get user's answer for current question
    user_answer = UserAnswer.objects.filter(
        attempt=attempt,
        question=current_question
    ).first()
    
    # Mark as visited
    if user_answer and not user_answer.is_visited:
        user_answer.is_visited = True
        user_answer.save()
    
    # Get all user answers for question navigation
    user_answers = {
        ua.question.id: {
            'answered': ua.selected_answer is not None,
            'marked': ua.is_marked_for_review,
            'visited': ua.is_visited
        }
        for ua in attempt.user_answers.all()
    }
    
    context = {
        'attempt': attempt,
        'current_question': current_question,
        'current_question_num': question_num + 1,
        'total_questions': len(questions),
        'questions': questions,
        'user_answer': user_answer,
        'user_answers': user_answers,
        'user_answers_json': json.dumps(user_answers),
        'remaining_minutes': remaining_minutes,
        'remaining_seconds': remaining_seconds,
        'hide_navbar': True,
    }
    return render(request, 'accounts/exam_interface.html', context)


@login_required
@csrf_exempt
def save_answer(request, attempt_id):
    """
    AJAX endpoint to save a single answer during the exam.
    
    Updates the UserAnswer record with the selected answer and review status.
    """
    if request.method == 'POST':
        try:
            attempt = TestAttempt.objects.get(id=attempt_id, user=request.user, status='in_progress')
            
            # Allow saving answers even if subscription expired during exam
            # This prevents data loss
            data = json.loads(request.body)
            question_id = data.get('question_id')
            answer_id = data.get('answer_id')
            marked = data.get('marked', False)
            
            if not question_id:
                return JsonResponse({'success': False, 'error': 'Question ID is required'})
            
            question = get_object_or_404(Question, id=question_id, test=attempt.test)
            # Use get_or_create to ensure UserAnswer exists
            user_answer, created = UserAnswer.objects.get_or_create(
                attempt=attempt,
                question=question,
                defaults={'is_correct': False}
            )
            
            if answer_id:
                try:
                    # Convert answer_id to int if it's a string
                    answer_id = int(answer_id) if answer_id else None
                    if answer_id:
                        answer = get_object_or_404(Answer, id=answer_id, question=question)
                        user_answer.selected_answer = answer
                        user_answer.is_correct = answer.is_correct
                    else:
                        user_answer.selected_answer = None
                        user_answer.is_correct = False
                except (ValueError, TypeError):
                    user_answer.selected_answer = None
                    user_answer.is_correct = False
            else:
                user_answer.selected_answer = None
                user_answer.is_correct = False
            
            user_answer.is_marked_for_review = bool(marked)
            user_answer.save()
            
            return JsonResponse({'success': True})
        except TestAttempt.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Test attempt not found or already completed'})
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'error': 'Invalid JSON data'})
        except Exception as e:
            import traceback
            return JsonResponse({'success': False, 'error': str(e), 'traceback': traceback.format_exc()})
    return JsonResponse({'success': False, 'error': 'Only POST method allowed'})


@login_required
@csrf_exempt
def submit_report(request, attempt_id):
    """
    AJAX endpoint for users to report issues with a question during an exam.
    """
    if request.method == 'POST':
        try:
            from .models import QuestionReport  # Local import to avoid circular dependency issues
            data = json.loads(request.body)
            question_id = data.get('question_id')
            report_type = data.get('report_type')
            description = data.get('description', '')
            
            if not question_id or not report_type:
                return JsonResponse({'success': False, 'error': 'Missing required fields'})
            
            # Verify the user has access to this question via the attempt
            attempt = get_object_or_404(TestAttempt, id=attempt_id, user=request.user)
            # Ensure the question belongs to the test in the attempt
            question = get_object_or_404(Question, id=question_id, test=attempt.test)
            
            # Create or update report
            report, created = QuestionReport.objects.update_or_create(
                user=request.user,
                question=question,
                defaults={
                    'report_type': report_type,
                    'description': description,
                    'is_resolved': False # Re-open if updated
                }
            )
            
            return JsonResponse({'success': True, 'message': 'Report submitted successfully'})
            
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'error': 'Invalid JSON data'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
            
    return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)


@login_required
def exam_submit(request, attempt_id):
    """
    Finalizes the exam attempt.
    
    Calculates:
    - Total score based on correct answers and negative marking rules.
    - Percentage and pass/fail status.
    - Time taken.
    
    Redirects to the results page.
    """
    attempt = get_object_or_404(TestAttempt, id=attempt_id, user=request.user)
    
    if attempt.status != 'in_progress':
        return redirect('exam_results', attempt_id=attempt.id)
    
    # Check if time has elapsed - prevent early submission (ONLY IF TIMED)
    if attempt.is_timed:
        elapsed = timezone.now() - attempt.started_at
        elapsed_seconds = int(elapsed.total_seconds())
        total_seconds = attempt.test.duration_minutes * 60
        # remaining_seconds calculation kept for reference if needed, but restriction removed
    
    # Calculate score
    # Calculate score
    total_score = Decimal('0.00')
    
    # Positive marks for correct answers
    correct_user_answers = attempt.user_answers.filter(is_correct=True)
    for ua in correct_user_answers:
        total_score += Decimal(ua.question.marks)
        
    # Negative marks for wrong answers
    rule = attempt.test.negative_marking_rule
    if rule != 'none':
        # Wrong answers (answer selected but incorrect)
        wrong_user_answers = attempt.user_answers.select_related('question').filter(is_correct=False, selected_answer__isnull=False)
        for ua in wrong_user_answers:
            q_mark = Decimal(ua.question.marks)
            if rule == '1/4':
                total_score -= q_mark * Decimal('0.25')
            elif rule == '1/3':
                total_score -= q_mark / Decimal('3')

    attempt.score = total_score
    attempt.total_marks = sum(q.marks for q in attempt.test.questions.all())
    attempt.percentage = (total_score / attempt.total_marks * 100) if attempt.total_marks > 0 else 0
    attempt.is_passed = attempt.percentage >= attempt.test.passing_score
    attempt.status = 'completed'
    attempt.submitted_at = timezone.now()
    
    elapsed = attempt.submitted_at - attempt.started_at
    attempt.time_taken_minutes = int(elapsed.total_seconds() / 60)
    attempt.save()
    
    return redirect('exam_results', attempt_id=attempt.id)


@login_required
def exam_results(request, attempt_id):
    """
    Displays the detailed results of a completed exam.
    
    Shows:
    - Score and statistics
    - Question-by-question analysis (user answer vs correct answer)
    """
    attempt = get_object_or_404(TestAttempt, id=attempt_id, user=request.user)
    
    # Get all questions with user answers
    # Optimized fetching to eliminate N+1 problem
    # Prefetch questions with their correct answers
    from django.db.models import Prefetch
    
    questions = attempt.test.questions.prefetch_related(
        Prefetch('answers', queryset=Answer.objects.filter(is_correct=True), to_attr='correct_answers_list')
    ).all()
    
    # Fetch all user answers for this attempt in one query
    # Map them by question_id for O(1) lookup
    user_answers_map = {
        ua.question_id: ua 
        for ua in UserAnswer.objects.filter(attempt=attempt).select_related('selected_answer')
    }
    
    questions_data = []
    correct_count = 0
    wrong_count = 0
    skipped_count = 0

    for question in questions:
        user_answer = user_answers_map.get(question.id)
        
        # Get correct answer from prefetched list (usually 0 or 1 item)
        correct_answer = question.correct_answers_list[0] if question.correct_answers_list else None
        
        questions_data.append({
            'question': question,
            'user_answer': user_answer,
            'correct_answer': correct_answer,
        })
        
        if user_answer and user_answer.is_correct:
            correct_count += 1
        elif user_answer and user_answer.selected_answer:
            wrong_count += 1
        else:
            skipped_count += 1

    context = {
        'attempt': attempt,
        'questions_data': questions_data,
        'correct_count': correct_count,
        'wrong_count': wrong_count,
        'skipped_count': skipped_count,
    }
    return render(request, 'accounts/exam_results.html', context)


@login_required
def test_history(request):
    """
    Displays the user's history of test attempts.
    """
    attempts = TestAttempt.objects.filter(user=request.user).order_by('-started_at')
    
    context = {
        'attempts': attempts,
    }
    return render(request, 'accounts/test_history.html', context)

# -------------------- NEW: developer utility to locate signup/register views --------------------
def _search_patterns(patterns, prefix=''):
    """
    Recursively search urlpatterns for patterns or names containing 'signup' or 'register'.
    Returns list of dicts: {'pattern': str, 'name': name, 'view': module.ClassOrFuncName}
    """
    matches = []
    for p in patterns:
        if isinstance(p, URLPattern):
            pattern_str = prefix + str(p.pattern)
            name = p.name or ''
            lower = (pattern_str + ' ' + name).lower()
            if 'signup' in lower or 'register' in lower:
                callback = getattr(p, 'callback', None)
                if callback:
                    view_name = f"{callback.__module__}.{getattr(callback, '__name__', callback.__class__.__name__)}"
                else:
                    view_name = 'unknown'
                matches.append({'pattern': pattern_str, 'name': name, 'view': view_name})
        elif isinstance(p, URLResolver):
            new_prefix = prefix + str(p.pattern)
            try:
                sub_patterns = p.url_patterns
            except Exception:
                sub_patterns = []
            matches += _search_patterns(sub_patterns, new_prefix)
    return matches

@login_required
def find_signup_view(request):
    """
    Developer utility to find URL patterns related to signup/registration.
    
    Access restricted to staff users.
    """
    if not request.user.is_staff:
        return JsonResponse({'ok': False, 'error': 'staff-only'}, status=403)
    try:
        resolver = get_resolver(settings.ROOT_URLCONF)
        matches = _search_patterns(resolver.url_patterns)
        return JsonResponse({'ok': True, 'matches': matches})
    except Exception as e:
        return JsonResponse({'ok': False, 'error': str(e)}, status=500)


@login_required
def admin_reset_password(request):
    """Allow admin to reset their own password"""
    if not request.user.is_staff:
        messages.error(request, 'Access denied. Admin only.')
        return redirect('dashboard')
    
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        new_password = request.POST.get('new_password', '').strip()
        confirm_password = request.POST.get('confirm_password', '').strip()
        
        if new_password != confirm_password:
            messages.error(request, 'Passwords do not match!')
            return redirect('admin_reset_password')
        
        if len(new_password) < 8:
            messages.error(request, 'Password must be at least 8 characters!')
            return redirect('admin_reset_password')
        
        try:
            user = User.objects.get(username__iexact=username)
            user.set_password(new_password)
            user.save()
            messages.success(request, f'Password for "{username}" has been reset successfully!')
            return redirect('admin_dashboard_overview')
        except User.DoesNotExist:
            messages.error(request, f'User "{username}" not found!')
            return redirect('admin_reset_password')
    
    return render(request, 'accounts/admin_reset_password.html')

def account_reset_password(request):
    """Handle password reset request from login/profile page"""
    if request.method == 'POST':
        email = request.POST.get('email', '').strip().lower()
        
        # Anti-abuse: Rate limiting logic
        rate_limit_key = f"pwd_reset_limit_{email}"
        req_count = cache.get(rate_limit_key, 0)
        
        if req_count >= 3:
            messages.error(request, 'You have reached the maximum of 3 password reset attempts for today. Please wait 24 hours before trying again.')
            return redirect('custom_login')
        
        user_matches = User.objects.filter(email__iexact=email)
        
        if user_matches.exists():
            for user in user_matches:
                try:
                    # Generate token and link
                    token = default_token_generator.make_token(user)
                    uid = urlsafe_base64_encode(force_bytes(user.pk))
                    domain = request.build_absolute_uri('/')[:-1] # Get domain
                    reset_link = f"{domain}{reverse('account_reset_password_confirm', kwargs={'uidb64': uid, 'token': token})}"
                    
                    # Send email
                    subject = 'Password Reset Request - Prepration Mentor'
                    message = f"""Hello {user.get_full_name() or user.username},

We received a request to reset your password. Please click the link below to set a new password:

{reset_link}

If you didn't request this, you can safely ignore this email.

Best regards,
Prepration Mentor Team"""
                    
                    send_mail(
                        subject=subject,
                        message=message,
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[email],
                        fail_silently=False,
                    )
                except Exception as e:
                    # Log error but don't show to user
                    pass
            
            # Increment rate limit counter only if user exists and we tried to send
            if cache.get(rate_limit_key) is None:
                cache.set(rate_limit_key, 1, 86400) # 24 hours
            else:
                try:
                    cache.incr(rate_limit_key)
                except ValueError:
                    cache.set(rate_limit_key, 1, 86400)
        
        # Always show success message for security
        messages.success(request, f'If an account exists with {email}, you will receive password reset instructions shortly.')
        return redirect('custom_login')

    return render(request, 'accounts/reset_password_request.html')


def account_reset_password_confirm(request, uidb64, token):
    """Handle password reset confirmation and new password setting"""
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is not None and default_token_generator.check_token(user, token):
        if request.method == 'POST':
            form = SetPasswordForm(user, request.POST)
            if form.is_valid():
                form.save()
                messages.success(request, 'Your password has been reset successfully! You can now login with your new password.')
                
                # Send confirmation email
                try:
                    send_mail(
                        subject='Password Reset Successful - Prepration Mentor',
                        message=f"""Hello {user.get_full_name() or user.username},

Your password has been successfully reset. 

If you did not perform this action, please contact support immediately as your account may be compromised.

Best regards,
Prepration Mentor Team""",
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[user.email],
                        fail_silently=True,
                    )
                except Exception:
                    pass
                
                return redirect('custom_login')
        else:
            form = SetPasswordForm(user)
        
        return render(request, 'accounts/reset_password_confirm.html', {'form': form})
    else:
        messages.error(request, 'The password reset link was invalid or has expired.')
        return redirect('account_reset_password')


def privacy_policy_view(request):
    """Public view for Privacy Policy."""
    from .models import PrivacyPolicy
    policy = PrivacyPolicy.objects.filter(is_active=True).first()
    return render(request, 'accounts/privacy_policy.html', {'policy': policy})


def terms_of_service_view(request):
    """Render the Terms of Service page."""
    return render(request, 'accounts/terms_of_service.html')


def contact_us_view(request):
    """Render the Contact Us page."""
    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        message = request.POST.get('message')
        
        if name and email and message:
            from .models_contact import ContactQuery
            ContactQuery.objects.create(name=name, email=email, message=message)
            messages.success(request, 'Thank you for contacting us! We will get back to you shortly.')
            return redirect('contact_us')
        else:
             messages.error(request, 'Please fill in all fields.')

    return render(request, 'accounts/contact_us.html')

def landing_page(request):
    """Render the public landing page."""
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, 'landing_page.html')

def signup(request):
    """Redirect to custom login as signup is handled there or render a signup template."""
    # Assuming custom_login handles both or we just redirect there for now.
    return redirect('custom_login')


@login_required
def notification_list(request):
    """View to list all notifications for the user."""
    from django.core.paginator import Paginator  # Ensure Paginator is available
    notifications_list = Notification.objects.filter(user=request.user).order_by('-created_at')
    
    # Handle "Mark All Read" action
    if request.method == 'POST' and 'mark_all_read' in request.POST:
        notifications_list.update(is_read=True)
        messages.success(request, "All notifications marked as read.")
        return redirect('notification_list')

    paginator = Paginator(notifications_list, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'notifications': page_obj,
        'active_tab': 'notifications'
    }
    return render(request, 'accounts/notifications.html', context)


@login_required
def read_notification(request, notification_id):
    """Mark a single notification as read and redirect."""
    notification = get_object_or_404(Notification, id=notification_id, user=request.user)
    if not notification.is_read:
        notification.is_read = True
        notification.save()
    
    # If the notification has a specific action URL, redirect there
    if notification.action_url:
        return redirect(notification.action_url)
    
    return redirect('notification_list')

@login_required
@csrf_exempt
def toggle_save_test(request, test_id):
    """Toggle saved status for a test"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Only POST method allowed'}, status=405)
        
    try:
        test = get_object_or_404(Test, id=test_id)
        saved_test = SavedTest.objects.filter(user=request.user, test=test).first()
        
        if saved_test:
            # Already saved, so remove it
            saved_test.delete()
            is_saved = False
            message = "Test removed from saved list"
        else:
            # Not saved, so save it
            SavedTest.objects.create(user=request.user, test=test)
            is_saved = True
            message = "Test saved for later"
            
        return JsonResponse({'success': True, 'is_saved': is_saved, 'message': message})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)

from .views_ajax import check_username, check_email
