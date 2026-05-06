from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver
from .models import UserSession


@receiver(user_logged_in)
def create_user_session(sender, request, user, **kwargs):
    """Create UserSession when user logs in (works for both regular and social login)"""
    # Ensure session is saved and has a session_key
    if not request.session.session_key:
        request.session.save()
    
    session_key = request.session.session_key
    
    if session_key:
        # Delete all existing sessions for this user
        user_sessions = UserSession.objects.filter(user=user)
        for us in user_sessions:
            try:
                from django.contrib.sessions.models import Session
                Session.objects.filter(session_key=us.session_key).delete()
            except:
                pass
        user_sessions.delete()
        
        # Create new session record (use get_or_create to handle any race conditions)
        UserSession.objects.get_or_create(
            user=user,
            session_key=session_key
        )

