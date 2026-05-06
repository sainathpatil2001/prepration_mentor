from django.conf import settings


def installed_apps(request):
    """Add context variables to all templates"""
    has_google_oauth = 'allauth.socialaccount' in settings.INSTALLED_APPS
    
    context = {
        'has_google_oauth': has_google_oauth,
        'unread_notifications_count': 0
    }
    
    if request.user.is_authenticated:
        try:
            # Avoid circular import by importing inside function
            from django.apps import apps
            Notification = apps.get_model('accounts', 'Notification')
            count = Notification.objects.filter(user=request.user, is_read=False).count()
            context['unread_notifications_count'] = count
        except Exception:
            pass
            
    return context
