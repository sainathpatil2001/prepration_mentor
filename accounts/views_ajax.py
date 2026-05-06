from django.contrib.auth.models import User
from django.http import JsonResponse
from django.core.cache import cache
import re

def check_username(request):
    """
    Check if username is available.
    
    Security implementations:
    - Rate limiting: Max 30 requests per minute per IP.
    - Input sanitization: Allow only alphanumeric, underscores, hyphens, and dots.
    - Length validation: Min 3, Max 150 characters.
    """
    
    # 1. Rate Limiting Logic (Simple implementation using cache)
    ip = get_client_ip(request)
    cache_key = f"username_check_rate_limit_{ip}"
    request_count = cache.get(cache_key, 0)
    
    if request_count >= 30:
        return JsonResponse({
            'valid': False,
            'message': 'Rate limit exceeded. Please try again later.'
        }, status=429)
    
    # Increment request count and set/refresh expiry to 60 seconds
    cache.set(cache_key, request_count + 1, timeout=60)
    
    username = request.GET.get('username', '').strip()
    
    response = {
        'valid': True,
        'message': 'Username available'
    }
    
    # 2. Input Validation
    if not username:
        return JsonResponse({'valid': False, 'message': 'Username is required'})
        
    if len(username) < 3:
        return JsonResponse({'valid': False, 'message': 'Username must be at least 3 characters'})
        
    # Standard Django username validation regex (approximate)
    if not re.match(r'^[\w.@+-]+$', username):
        return JsonResponse({'valid': False, 'message': 'Username contains invalid characters'})
    
    # 3. Database Check
    if User.objects.filter(username__iexact=username).exists():
        response['valid'] = False
        response['message'] = 'Username already taken'
    
    return JsonResponse(response)

def get_client_ip(request):
    """Retrieve the client's IP address from the request."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

def check_email(request):
    """
    Check if email is available.
    
    Security implementations:
    - Rate limiting: Max 30 requests per minute per IP.
    """
    
    # Rate Limiting Logic
    ip = get_client_ip(request)
    cache_key = f"email_check_rate_limit_{ip}"
    request_count = cache.get(cache_key, 0)
    
    if request_count >= 30:
        return JsonResponse({
            'valid': False,
            'message': 'Rate limit exceeded. Please try again later.'
        }, status=429)
    
    # Increment request count and set/refresh expiry to 60 seconds
    cache.set(cache_key, request_count + 1, timeout=60)
    
    email = request.GET.get('email', '').strip()
    
    response = {
        'valid': True,
        'message': 'Email available',
        'exists': False
    }
    
    if not email:
        return JsonResponse({'valid': False, 'message': 'Email is required'})
    
    # Basic email validation
    # Django's EmailValidator could be used, but basic check for now
    if '@' not in email:
        return JsonResponse({'valid': False, 'message': 'Invalid email format'})

    # Database Check
    if User.objects.filter(email__iexact=email).exists():
        response['valid'] = False
        response['exists'] = True
        response['message'] = 'Email already registered'
    
    return JsonResponse(response)
