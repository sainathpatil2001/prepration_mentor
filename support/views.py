from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse
import csv
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.core.paginator import Paginator
from django.core.mail import send_mail  # Added import
from django.conf import settings  # Added import
from django.utils import timezone
from django.template.loader import render_to_string
from datetime import timedelta
from .models import SupportTicket, TicketMessage, TicketFeedback
from .forms import SupportTicketForm, TicketMessageForm
from accounts.admin_views import staff_member_required

@login_required
def user_support(request):
    """
    User-facing view to list existing support tickets and create a new one.
    
    Handles form submission for creating a new ticket.
    Sends a confirmation email upon successful ticket creation.
    """
    if request.method == 'POST':
        form = SupportTicketForm(request.POST)
        if form.is_valid():
            ticket = form.save(commit=False)
            ticket.user = request.user
            ticket.save()
            messages.success(request, 'Support ticket created successfully.')
            
            # Send confirmation email
            try:
                send_mail(
                    subject=f'Ticket Created: #{ticket.ticket_id} - Prepration Mentor',
                    message=f"""Hello {request.user.get_full_name() or request.user.username},

We have received your support request (Ticket #{ticket.ticket_id}).
Category: {ticket.get_category_display()}
Subject: {ticket.subject}

Our support team checks tickets and will reply as soon as possible.

Best regards,
Prepration Mentor Support""",
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[request.user.email],
                    fail_silently=True,
                )
            except Exception:
                pass
            
            return redirect('user_support')
    else:
        form = SupportTicketForm()

    tickets = SupportTicket.objects.filter(user=request.user).order_by('-created_at')
    
    status_filter = request.GET.get('status')
    if status_filter == 'open':
        tickets = tickets.filter(status__in=['sent', 'seen'])
    elif status_filter == 'resolved':
        tickets = tickets.filter(status='resolved')

    context = {
        'form': form,
        'tickets': tickets,
        'active_tab': 'support',
        'status_filter': status_filter
    }
    return render(request, 'support/user_support.html', context)

@login_required
def user_ticket_detail(request, ticket_id):
    """
    User-facing view for a single ticket detail.
    
    Allows the user to view the conversation history and post new messages.
    Handles AJAX requests for posting messages.
    """
    ticket = get_object_or_404(SupportTicket, ticket_id=ticket_id, user=request.user)
    messages_list = ticket.messages.all().order_by('created_at')
    
    if request.method == 'POST':
        form = TicketMessageForm(request.POST, request.FILES)
        if form.is_valid():
            message = form.save(commit=False)
            message.ticket = ticket
            message.sender = request.user
            message.is_admin_reply = False
            message.save()

            # Mark ticket as unread for admin
            ticket.is_read_by_admin = False
            ticket.save()
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'status': 'success',
                    'message': 'Message sent.'
                })
            
            messages.success(request, 'Message sent successfully.')
            return redirect('user_ticket_detail', ticket_id=ticket.ticket_id)
        else:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'status': 'error', 'errors': form.errors}, status=400)
    else:
        form = TicketMessageForm()

    # Check if feedback already submitted
    feedback_exists = False
    if ticket.status == 'resolved':
        feedback_exists = TicketFeedback.objects.filter(ticket_id=str(ticket.ticket_id)).exists()

    context = {
        'ticket': ticket,
        'chat_messages': messages_list, # Unified variable name
        'form': form,
        'active_tab': 'support',
        'feedback_exists': feedback_exists,
    }
    return render(request, 'support/user_ticket_detail.html', context)

@staff_member_required
def admin_support_list(request):
    """
    Admin-facing view to list all support tickets.
    
    Supports filtering by search query, status, and category.
    Includes pagination.
    """
    query = request.GET.get('q', '').strip()
    status_filter = request.GET.get('status', '').strip()
    category_filter = request.GET.get('category', '').strip()

    tickets = SupportTicket.objects.select_related('user').order_by('-created_at')

    if query:
        tickets = tickets.filter(
            Q(ticket_id__icontains=query) |
            Q(user__username__icontains=query) |
            Q(subject__icontains=query) |
            Q(description__icontains=query)
        )

    if status_filter:
        tickets = tickets.filter(status=status_filter)
    
    if category_filter:
        tickets = tickets.filter(category=category_filter)

    paginator = Paginator(tickets, 15)
    page_obj = paginator.get_page(request.GET.get('page'))

    context = {
        'page_obj': page_obj,
        'query': query,
        'status_filter': status_filter,
        'category_filter': category_filter,
        'status_choices': SupportTicket.STATUS_CHOICES,
        'category_choices': SupportTicket.CATEGORY_CHOICES,
        'active_tab': 'support_management'
    }
    
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return render(request, 'support/_admin_ticket_rows.html', context)
        
    return render(request, 'support/admin_support_list.html', context)

@staff_member_required
def admin_support_detail(request, ticket_id):
    """
    Admin-facing view to manage a single ticket.
    
    Allows:
    - Updating ticket status.
    - Replying to the user (is_admin_reply=True).
    - Marking the ticket as read by admin.
    """
    ticket = get_object_or_404(SupportTicket, ticket_id=ticket_id)
    messages_list = ticket.messages.all().order_by('created_at')

    # Auto-update status to 'seen' if it is 'sent'
    if ticket.status == 'sent':
        ticket.status = 'seen'
    
    # Mark as read by admin
    if not ticket.is_read_by_admin:
        ticket.is_read_by_admin = True
        ticket.save()
    elif ticket.status == 'seen':
         ticket.save()

    if request.method == 'POST':
        if 'status_update' in request.POST:
            new_status = request.POST.get('status')
            if new_status in dict(SupportTicket.STATUS_CHOICES):
                ticket.status = new_status
                ticket.save()
                messages.success(request, f'Ticket status updated to {ticket.get_status_display()}.')
                return redirect('admin_support_detail', ticket_id=ticket.ticket_id)
        elif 'message_send' in request.POST:
            form = TicketMessageForm(request.POST, request.FILES)
            if form.is_valid():
                message = form.save(commit=False)
                message.ticket = ticket
                message.sender = request.user
                message.is_admin_reply = True
                message.save()
                
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'status': 'success',
                        'message': 'Message sent.'
                    })
                    
                messages.success(request, 'Message sent successfully.')
                return redirect('admin_support_detail', ticket_id=ticket.ticket_id)
            else:
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'status': 'error', 'errors': form.errors}, status=400)
    
    form = TicketMessageForm()

    context = {
        'ticket': ticket,
        'chat_messages': messages_list,
        'form': form,
        'status_choices': SupportTicket.STATUS_CHOICES,
    }
    return render(request, 'support/admin_support_detail.html', context)

@login_required
def update_typing_status(request, ticket_id):
    """
    Update typing status for a user or admin.
    
    Sets a short expiration for the typing indicator (5 seconds).
    Returns JSON response.
    """
    ticket = get_object_or_404(SupportTicket, ticket_id=ticket_id)
    
    # Permission check
    if not request.user.is_staff and ticket.user != request.user:
        return JsonResponse({'status': 'error', 'message': 'Unauthorized'}, status=403)
        
    until = timezone.now() + timedelta(seconds=5)
    
    if request.user.is_staff:
        ticket.admin_typing_until = until
    else:
        ticket.user_typing_until = until
        
    ticket.save()
    return JsonResponse({'status': 'success'})

@login_required
def get_messages(request, ticket_id):
    """
    AJAX view to retrieve latest messages and typing status.
    
    Renders the message list partial and returns it along with typing status indicators.
    """
    if request.user.is_staff:
        ticket = get_object_or_404(SupportTicket, ticket_id=ticket_id)
    else:
        ticket = get_object_or_404(SupportTicket, ticket_id=ticket_id, user=request.user)
    
    chat_messages = ticket.messages.all().order_by('created_at')
    
    # Check typing status
    now = timezone.now()
    is_typing = False
    if request.user.is_staff:
        # Admin is viewing, check if user is typing
        if ticket.user_typing_until and ticket.user_typing_until > now:
            is_typing = True
    else:
        # User is viewing, check if admin is typing
        if ticket.admin_typing_until and ticket.admin_typing_until > now:
            is_typing = True
            
    html = render_to_string('support/_message_list.html', {
        'chat_messages': chat_messages,
        'request': request
    })
    
    return JsonResponse({
        'html': html,
        'is_typing': is_typing,
        'message_count': chat_messages.count()
    })

@staff_member_required
def export_tickets(request):
    """
    Export all tickets to a CSV file.
    
    Includes ticket details like ID, user, category, subject, status, etc.
    """
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="support_tickets.csv"'

    writer = csv.writer(response)
    writer.writerow(['Ticket ID', 'User', 'Category', 'Subject', 'Description', 'Status', 'Created At', 'Last Updated', 'Is Read'])

    tickets = SupportTicket.objects.select_related('user').all().order_by('-created_at')
    
    for ticket in tickets:
        writer.writerow([
            ticket.ticket_id,
            ticket.user.username,
            ticket.get_category_display(),
            ticket.subject,
            ticket.description,
            ticket.get_status_display(),
            ticket.created_at,
            ticket.updated_at,
            'Yes' if ticket.is_read_by_admin else 'No'
        ])

    return response

@staff_member_required
def delete_tickets(request):
    """
    Bulk delete tickets.
    
    Only allows deletion of 'resolved' tickets.
    """
    if request.method == 'POST':
        # Get list of ticket IDs from POST data
        ticket_ids = request.POST.getlist('ticket_ids[]')
        
        if not ticket_ids:
            return JsonResponse({'status': 'error', 'message': 'No tickets selected.'}, status=400)

        # Count total expected
        total_requested = len(ticket_ids)
        
        # Delete resolved tickets from the selection
        count, _ = SupportTicket.objects.filter(ticket_id__in=ticket_ids, status='resolved').delete()
        
        skipped_count = total_requested - count
        
        message = f"Successfully deleted {count} resolved tickets."
        if skipped_count > 0:
            message += f" {skipped_count} tickets were skipped because they are not resolved."
            
        return JsonResponse({'status': 'success', 'message': message})
        
    return JsonResponse({'status': 'error', 'message': 'Invalid request method.'}, status=405)

@login_required
def submit_feedback(request, ticket_id):
    """
    Handle user feedback submission for resolved tickets.
    
    Prevents duplicate feedback for the same ticket.
    """
    ticket = get_object_or_404(SupportTicket, ticket_id=ticket_id, user=request.user)
    
    if ticket.status != 'resolved':
        messages.error(request, "Feedback can only be submitted for resolved tickets.")
        return redirect('user_ticket_detail', ticket_id=ticket.ticket_id)

    if request.method == 'POST':
        # Check if already submitted
        if TicketFeedback.objects.filter(ticket_id=str(ticket.ticket_id)).exists():
             messages.warning(request, "Feedback already submitted for this ticket.")
             return redirect('user_ticket_detail', ticket_id=ticket.ticket_id)

        try:
            feedback = TicketFeedback.objects.create(
                user=request.user,
                ticket_subject=ticket.subject,
                ticket_description=ticket.description,
                ticket_id=str(ticket.ticket_id),
                rating=int(request.POST.get('rating')),
                feedback_text=request.POST.get('feedback_text', '')
            )
            messages.success(request, "Thank you for your feedback!")
        except Exception as e:
             messages.error(request, f"Error submitting feedback: {str(e)}")
             
        return redirect('user_ticket_detail', ticket_id=ticket.ticket_id)
    
    return redirect('user_support')

@login_required
def super_admin_reviews(request):
    """
    Super Admin view to view all user feedback/reviews.
    """
    if not request.user.is_superuser:
        messages.error(request, "Access denied. Super Admin only.")
        return redirect('admin_dashboard_overview')

    reviews = TicketFeedback.objects.select_related('user').all().order_by('-created_at')

    # Handle filters if needed, but basic list first
    
    context = {
        'reviews': reviews,
        'active_tab': 'super_admin_reviews'
    }
    return render(request, 'support/super_admin_reviews.html', context)

@login_required
def delete_reviews(request):
    """
    Super Admin: Bulk delete reviews.
    """
    if not request.user.is_superuser:
        return JsonResponse({'status': 'error', 'message': 'Unauthorized'}, status=403)

    if request.method == 'POST':
        review_ids = request.POST.getlist('review_ids[]')
        if not review_ids:
             return JsonResponse({'status': 'error', 'message': 'No reviews selected.'}, status=400)
             
        TicketFeedback.objects.filter(id__in=review_ids).delete()
        return JsonResponse({'status': 'success', 'message': f'Successfully deleted {len(review_ids)} reviews.'})

    return JsonResponse({'status': 'error', 'message': 'Invalid request method.'}, status=405)

@login_required
def export_reviews(request):
    """
    Super Admin: Export feedback/reviews to CSV.
    """
    if not request.user.is_superuser:
        messages.error(request, "Unauthorized")
        return redirect('admin_dashboard_overview')

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="feedback_reviews.csv"'

    writer = csv.writer(response)
    writer.writerow(['Date', 'User', 'Ticket ID', 'Rating', 'Subject', 'Feedback'])

    reviews = TicketFeedback.objects.select_related('user').all().order_by('-created_at')
    
    for rev in reviews:
        writer.writerow([
            rev.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            rev.user.username if rev.user else 'Deleted User',
            rev.ticket_id,
            rev.rating,
            rev.ticket_subject,
            rev.feedback_text
        ])

    return response
