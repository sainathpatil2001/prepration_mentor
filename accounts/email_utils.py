from django.core.mail import get_connection, EmailMultiAlternatives
from django.conf import settings
from .models import EmailConfiguration
import logging

logger = logging.getLogger(__name__)

def get_email_connection():
    """
    Returns a Django email connection object based on EmailConfiguration.
    Falls back to settings.py configuration if no active configuration is found.
    """
    try:
        config = EmailConfiguration.get_solo()
        if config and config.is_active:
            return get_connection(
                host=config.email_host,
                port=config.email_port,
                username=config.email_host_user,
                password=config.email_host_password,
                use_tls=config.email_use_tls,
                use_ssl=config.email_use_ssl,
            )
    except Exception as e:
        logger.error(f"Error fetching EmailConfiguration: {e}")
    
    # Fallback to default settings
    return get_connection(
        host=settings.EMAIL_HOST,
        port=settings.EMAIL_PORT,
        username=settings.EMAIL_HOST_USER,
        password=settings.EMAIL_HOST_PASSWORD,
        use_tls=settings.EMAIL_USE_TLS,
    )

def send_custom_email(subject, message, from_email, recipient_list, 
                      fail_silently=False, auth_user=None, auth_password=None, 
                      connection=None, html_message=None, **kwargs):
    """
    Sends an email using the dynamic request configuration.
    Matches signature of django.core.mail.send_mail exactly.
    """
    try:
        # Resolve from_email if not provided (handling None)
        if not from_email:
             config = EmailConfiguration.get_solo()
             if config and config.is_active:
                 from_email = config.default_from_email or config.email_host_user
             else:
                 from_email = settings.DEFAULT_FROM_EMAIL

        # Get connection if not provided
        if not connection:
            connection = get_email_connection()
        
        email = EmailMultiAlternatives(
            subject=subject,
            body=message,
            from_email=from_email,
            to=recipient_list,
            connection=connection
        )
        
        if html_message:
            email.attach_alternative(html_message, "text/html")
            
        return email.send(fail_silently=fail_silently)
    except Exception as e:
        logger.error(f"Error sending email: {e}")
        if not fail_silently:
            raise
        return 0
