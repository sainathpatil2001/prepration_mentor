from django.db import models
from django.contrib.auth.models import User
import uuid

class SupportTicket(models.Model):
    """
    Model representing a support ticket submitted by a user.
    """
    STATUS_CHOICES = (
        ('sent', 'Sent'),
        ('seen', 'Seen'),
        ('resolved', 'Resolved'),
    )

    CATEGORY_CHOICES = (
        ('technical', 'Technical Issue'),
        ('billing', 'Billing Inquiry'),
        ('account', 'Account Issue'),
        ('other', 'Other'),
    )

    ticket_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, help_text="Unique identifier for the ticket.")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='support_tickets', help_text="User who submitted the ticket.")
    subject = models.CharField(max_length=200, default='No Subject')
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)
    description = models.TextField(help_text="Detailed description of the issue.")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='sent')
    user_typing_until = models.DateTimeField(null=True, blank=True)
    admin_typing_until = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_read_by_admin = models.BooleanField(default=False)

    def __str__(self):
        return f"Ticket {self.ticket_id} - {self.user.username}"

class TicketMessage(models.Model):
    """
    Model representing a message within a support ticket thread.
    """
    ticket = models.ForeignKey(SupportTicket, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE)
    message = models.TextField(blank=True, null=True, help_text="The content of the message.")
    attachment = models.FileField(upload_to='support_attachments/', blank=True, null=True, help_text="Optional file attachment.")
    created_at = models.DateTimeField(auto_now_add=True)
    is_admin_reply = models.BooleanField(default=False, help_text="Indicates if the message is from an admin.")

    def __str__(self):
        return f"Message on {self.ticket.ticket_id} by {self.sender.username}"

class TicketFeedback(models.Model):
    """
    Model to store user feedback on resolved support tickets.
    """
    RATING_CHOICES = (
        (1, '1 Star'),
        (2, '2 Stars'),
        (3, '3 Stars'),
        (4, '4 Stars'),
        (5, '5 Stars'),
    )
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    ticket_subject = models.CharField(max_length=200)
    ticket_description = models.TextField()
    ticket_id = models.CharField(max_length=100, blank=True, null=True, help_text="Original Ticket ID (string representation)")
    rating = models.IntegerField(choices=RATING_CHOICES, default=5, help_text="User rating for the support experience.")
    feedback_text = models.TextField(blank=True, null=True, help_text="Optional comments from the user.")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Feedback for {self.ticket_subject} - {self.rating} stars"
