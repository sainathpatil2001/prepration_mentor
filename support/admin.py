from django.contrib import admin
from .models import SupportTicket, TicketMessage, TicketFeedback

@admin.register(SupportTicket)
class SupportTicketAdmin(admin.ModelAdmin):
    """
    Admin configuration for SupportTicket.
    """
    list_display = ('ticket_id', 'user', 'category', 'status', 'created_at', 'is_read_by_admin')
    list_filter = ('status', 'category', 'is_read_by_admin', 'created_at')
    search_fields = ('ticket_id', 'user__username', 'subject', 'description')
    readonly_fields = ('ticket_id', 'created_at', 'updated_at')
    date_hierarchy = 'created_at'

@admin.register(TicketMessage)
class TicketMessageAdmin(admin.ModelAdmin):
    """
    Admin configuration for TicketMessage.
    """
    list_display = ('ticket', 'sender', 'created_at', 'is_admin_reply')
    list_filter = ('is_admin_reply', 'created_at')
    search_fields = ('ticket__ticket_id', 'sender__username', 'message')
    readonly_fields = ('created_at',)

@admin.register(TicketFeedback)
class TicketFeedbackAdmin(admin.ModelAdmin):
    """
    Admin configuration for TicketFeedback.
    """
    list_display = ('ticket_id', 'user', 'rating', 'created_at')
    list_filter = ('rating', 'created_at')
    search_fields = ('ticket_id', 'user__username', 'feedback_text')
    readonly_fields = ('created_at',)
