from django.contrib.sessions.models import Session
from django.utils import timezone
from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse
from accounts.models import UserSession


class SingleSessionMiddleware:
    """Middleware to ensure single session per user"""
    
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Check if user was logged out due to concurrent session
        # This logic relies on the fact that when a session is deleted from DB, 
        # the browser still sends the session cookie, but request.user becomes AnonymousUser
        # We can't easily detect "why" they are anonymous here without more complex logic,
        # but we can handle the active session enforcement.
        
        if request.user.is_authenticated:
            # Ensure session is saved
            if not request.session.session_key:
                request.session.save()
            
            current_session_key = request.session.session_key
            
            if current_session_key:
                # Get or create UserSession for current session
                UserSession.objects.get_or_create(
                    user=request.user,
                    session_key=current_session_key,
                    defaults={'last_activity': timezone.now()}
                )
                
                # Delete other active sessions for this user
                other_sessions = UserSession.objects.filter(
                    user=request.user
                ).exclude(
                    session_key=current_session_key
                )
                
                if other_sessions.exists():
                    # Delete Django sessions for other sessions
                    for user_session in other_sessions:
                        try:
                            # Get the session object to set a flag before deleting
                            # Note: We can't easily modify the session data of another session directly 
                            # without loading it. 
                            # However, since we are deleting it, the user will be logged out.
                            # The standard way to notify them is difficult because the session is gone.
                            # A common workaround is to not delete it immediately but mark it as invalid,
                            # OR just accept that they get logged out.
                            
                            # BUT, to show a message, we can't use the deleted session.
                            # We will just delete it as per strict security requirement.
                            Session.objects.filter(session_key=user_session.session_key).delete()
                        except:
                            pass
                    
                    # Delete UserSession records
                    other_sessions.delete()

        response = self.get_response(request)
        return response
