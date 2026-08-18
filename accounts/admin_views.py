import json
import csv
from django.db import transaction
from django.http import HttpResponse

from functools import wraps



from django.contrib import messages

from django.contrib.auth import authenticate, login, logout

from django.contrib.auth.decorators import login_required

from django.core.exceptions import PermissionDenied

from django.core.paginator import Paginator

from django.db.models import Q

from django.shortcuts import get_object_or_404, redirect, render

from django.urls import reverse

from django.utils import timezone

from django.views.decorators.http import require_POST
from django.core.management import call_command
from django.http import HttpResponse
import io
import os
import zipfile
import shutil
from django.conf import settings
from django.core.files.base import ContentFile



from .forms import AdminTestSetForm, QuestionFormSet, get_answer_formset, AnswerFormSet, QuestionForm, AnswerForm
from django.forms import inlineformset_factory

from .models import AdminLog, Test, TestCategory, SystemBackup, Question, Answer, Subscription
from support.models import SupportTicket
from django.contrib.auth.models import User





def staff_member_required(view_func):
    """
    Decorator requesting that the user be logged in and a staff member.
    
    Redirects to the admin login page if not authenticated or not staff.
    Raises PermissionDenied if logged in but not staff (though redirects in practice).
    """

    @wraps(view_func)
    @login_required(login_url='admin_login')
    def _wrapped(request, *args, **kwargs):
        if not request.user.is_staff:
            raise PermissionDenied("You do not have permission to access this area.")

        return view_func(request, *args, **kwargs)

    return _wrapped





def admin_login_view(request):
    """
    Custom login view for administrators/staff.
    
    Redirects already authenticated staff to the dashboard.
    Authenticates username/password and logs the user in.
    """
    if request.user.is_authenticated and request.user.is_staff:
        return redirect('admin_dashboard_overview')

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '').strip()

        user = authenticate(request, username=username, password=password)

        if user is not None and user.is_staff:
            login(request, user)
            messages.success(request, f'Welcome back, {user.get_full_name() or user.username}!')
            next_url = request.GET.get('next') or reverse('admin_dashboard_overview')
            return redirect(next_url)
        else:
            messages.error(request, 'Invalid credentials or insufficient permissions.')

    return render(request, 'admin_panel/login.html')





@staff_member_required
def admin_logout_view(request):
    """
    Logs out the current admin user and redirects to login page.
    """
    logout(request)
    messages.info(request, 'You have been logged out.')
    return redirect('admin_login')





def _log_admin_action(user, action, test, message, metadata=None):
    """
    Internal helper to record administrative actions in the database.
    
    Args:
        user (User): The admin user performing the action.
        action (str): The type of action (e.g., 'create', 'update', 'delete').
        test (Test, optional): The test object involved, if any.
        message (str): A human-readable description of the action.
        metadata (dict, optional): Additional context to store as JSON.
    """
    if metadata is not None:
        try:
            metadata_value = json.dumps(metadata)
        except TypeError:
            metadata_value = json.dumps({'value': str(metadata)})
    else:
        metadata_value = None

    AdminLog.objects.create(
        admin_user=user,
        action=action,
        test=test,
        message=message,
        metadata=metadata_value,
    )





@staff_member_required
def dashboard_overview(request):
    """
    Main admin dashboard view.
    
    Displays key metrics including:
    - Test statistics (total, published, drafts, hidden).
    - Support ticket counts.
    - User registration and subscription counts.
    """
    tests = Test.objects.all()
    total_tests = tests.count()
    published_tests = tests.filter(status='published', is_hidden=False).count()
    drafts = tests.filter(status='draft').count()
    hidden_tests = tests.filter(is_hidden=True).count()

    context = {
        'active_tab': 'overview',
        'total_tests': total_tests,
        'published_tests': published_tests,
        'draft_tests': drafts,
        'hidden_tests': hidden_tests,
        'queries_solved': SupportTicket.objects.filter(status='resolved').count(),
        'new_queries': SupportTicket.objects.filter(status='sent').count(),
        'total_students': User.objects.filter(is_staff=False).count(),
        'subscribed_students': Subscription.objects.filter(status='active').values('user').distinct().count(),
    }

    return render(request, 'admin_panel/dashboard_overview.html', context)





@staff_member_required
def test_list(request):
    """
    View to list and manage all tests.
    
    Supports filtering by:
    - Search query (title/description)
    - Status (draft/published)
    - Visibility (hidden/visible)
    
    Includes pagination.
    """
    query = request.GET.get('q', '').strip()
    status_filter = request.GET.get('status', '').strip()
    visibility_filter = request.GET.get('visibility', '').strip()

    tests = Test.objects.select_related('category').order_by('-updated_at')

    if query:
        tests = tests.filter(Q(title__icontains=query) | Q(description__icontains=query))

    if status_filter in {'draft', 'published'}:
        tests = tests.filter(status=status_filter)

    if visibility_filter == 'hidden':
        tests = tests.filter(is_hidden=True)
    elif visibility_filter == 'visible':
        tests = tests.filter(is_hidden=False)

    paginator = Paginator(tests, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'active_tab': 'manage',
        'page_obj': page_obj,
        'query': query,
        'status_filter': status_filter,
        'visibility_filter': visibility_filter,
    }

    return render(request, 'admin_panel/test_list.html', context)





@staff_member_required

def drafts_list(request):

    """Show tests saved as drafts."""

    drafts = Test.objects.filter(status='draft').select_related('category').order_by('-updated_at')

    paginator = Paginator(drafts, 10)

    page_obj = paginator.get_page(request.GET.get('page'))



    context = {

        'active_tab': 'drafts',

        'page_obj': page_obj,

    }

    return render(request, 'admin_panel/drafts.html', context)





@staff_member_required
def admin_logs(request):
    """
    View to display the audit log of administrative actions.
    
    Supports filtering by:
    - Search query (message, test title, admin username)
    - Action type (create, update, delete, etc.)
    """
    query = request.GET.get('q', '').strip()
    action_filter = request.GET.get('action', '').strip()

    logs = AdminLog.objects.select_related('admin_user', 'test').order_by('-created_at')

    if query:
        logs = logs.filter(Q(message__icontains=query) | Q(test__title__icontains=query) | Q(admin_user__username__icontains=query))

    if action_filter:
        logs = logs.filter(action=action_filter)

    paginator = Paginator(logs, 15)
    page_obj = paginator.get_page(request.GET.get('page'))

    context = {
        'active_tab': 'logs',
        'page_obj': page_obj,
        'query': query,
        'action_filter': action_filter,
        'action_choices': AdminLog.ACTION_CHOICES,
    }

    return render(request, 'admin_panel/logs.html', context)


@staff_member_required
@require_POST
def delete_logs(request):
    """Delete selected admin logs."""
    log_ids = request.POST.getlist('log_ids')
    if log_ids:
        count, _ = AdminLog.objects.filter(id__in=log_ids).delete()
        messages.success(request, f'Successfully deleted {count} logs.')
    else:
        messages.warning(request, 'No logs selected for deletion.')
    
    return redirect('admin_dashboard_logs')





@staff_member_required
def test_create(request):
    """
    View to create a new test set.
    
    Handles complex form validation for:
    - Main Test details
    - Inline Questions (via formset)
    - Inline Answers for each Question (via nested formsets logic managed manually)
    
    Allows saving as 'draft' or 'published'.
    """
    form = AdminTestSetForm(request.POST or None)
    question_formset = QuestionFormSet(request.POST or None, request.FILES or None, instance=None, prefix='questions')
    answer_formsets = []

    # For GET, empty answer formsets; for POST, bind data
    if request.method == 'POST':
        for q_idx, q_form in enumerate(question_formset.forms):
            prefix = f'answers-{q_idx}'
            ans_fs = get_answer_formset(request.POST, request.FILES, instance=q_form.instance, prefix=prefix)
            answer_formsets.append(ans_fs)
    else:
        for q_idx, q_form in enumerate(question_formset.forms):
            prefix = f'answers-{q_idx}'
            ans_fs = get_answer_formset(instance=q_form.instance, prefix=prefix)
            answer_formsets.append(ans_fs)

    all_valid = form.is_valid() and question_formset.is_valid() and all(fs.is_valid() for fs in answer_formsets)
    
    # Debug: Print validation errors
    if request.method == 'POST' and not all_valid:
        print("=== FORM VALIDATION ERRORS ===")
        if not form.is_valid():
            print(f"Main Form Errors: {form.errors}")
        if not question_formset.is_valid():
            print(f"Question Formset Errors: {question_formset.errors}")
            print(f"Question Formset Non-Form Errors: {question_formset.non_form_errors()}")
        for idx, ans_fs in enumerate(answer_formsets):
            if not ans_fs.is_valid():
                print(f"Answer Formset {idx} Errors: {ans_fs.errors}")
                print(f"Answer Formset {idx} Non-Form Errors: {ans_fs.non_form_errors()}")
    
    if request.method == 'POST' and all_valid:
        test = form.save(commit=False)
        submit_action = request.POST.get('submit_action')

        if submit_action == 'publish':
            test.publish(save=False)
        else:
            test.status = 'draft'
            test.published_at = None

        test.save()
        form.save_m2m()
        question_formset.instance = test
        questions = question_formset.save()

        for idx, (q, ans_fs) in enumerate(zip(questions, answer_formsets)):
            ans_fs.instance = q  # link to Question
            ans_fs.save()
        
        # Update total questions count
        test.total_questions = test.questions.count()
        test.save(update_fields=['total_questions'])

        _log_admin_action(request.user, 'create', test, f'Created test set "{test.title}".')

        if submit_action == 'publish':
            _log_admin_action(request.user, 'publish', test, f'Published test set "{test.title}".')
            messages.success(request, f'Test set "{test.title}" published successfully.')
        else:
            _log_admin_action(request.user, 'draft', test, f'Saved test set "{test.title}" as draft.')
            messages.success(request, f'Test set "{test.title}" saved as draft.')

        return redirect('admin_dashboard_manage')

    context = {
        'active_tab': 'add',
        'form': form,
        'question_formset': question_formset,
        'answer_formsets': answer_formsets,
        'question_answer_zipped': zip(question_formset.forms, answer_formsets),
    }

    return render(request, 'admin_panel/test_form.html', context)







@staff_member_required
def test_edit(request, test_id):
    """
    View to edit an existing test set.
    
    Uses inline formsets for questions and nested formsets for answers.
    Handles 'publish', 'draft', and 'update' actions separately.
    """
    test = get_object_or_404(Test, id=test_id)

    # Use strict factories to prevent extra empty forms on edit
    EditQuestionFormSet = inlineformset_factory(
        Test, Question, form=QuestionForm, extra=0, can_delete=True
    )
    
    # Helper for strict answer formset
    def get_edit_answer_formset(instance=None, prefix=None, data=None, files=None):
        EditAnswerFormSet = inlineformset_factory(
            Question, Answer, form=AnswerForm, 
            extra=0, min_num=2, max_num=6, 
            can_delete=True, validate_min=True, validate_max=True
        )
        return EditAnswerFormSet(data, files, instance=instance, prefix=prefix)

    form = AdminTestSetForm(request.POST or None, instance=test)

    question_formset = EditQuestionFormSet(request.POST or None, request.FILES or None, instance=test, prefix='questions')
    answer_formsets = []

    if request.method == 'POST':
        for q_idx, q_form in enumerate(question_formset.forms):
            prefix = f'answers-{q_idx}'
            ans_fs = get_edit_answer_formset(data=request.POST, files=request.FILES, instance=q_form.instance, prefix=prefix)
            answer_formsets.append(ans_fs)
    else:
        for q_idx, q_form in enumerate(question_formset.forms):
            prefix = f'answers-{q_idx}'
            ans_fs = get_edit_answer_formset(instance=q_form.instance, prefix=prefix)
            answer_formsets.append(ans_fs)
            
    all_valid = form.is_valid() and question_formset.is_valid() and all(fs.is_valid() for fs in answer_formsets)

    if request.method == 'POST' and all_valid:
        test = form.save(commit=False)
        submit_action = request.POST.get('submit_action')

        if submit_action == 'publish':
            test.publish(save=False)
            action = 'publish'
            success_message = f'Test set "{test.title}" published successfully.'
        elif submit_action == 'draft':
            test.mark_draft(save=False)
            action = 'draft'
            success_message = f'Test set "{test.title}" saved as draft.'
        else:
            action = 'update'
            success_message = f'Test set "{test.title}" updated successfully.'

        test.save()
        form.save_m2m()
        question_formset.instance = test
        questions = question_formset.save()

        for idx, (q, ans_fs) in enumerate(zip(questions, answer_formsets)):
            ans_fs.instance = q
            ans_fs.save()
            
        # Update total questions count
        test.total_questions = test.questions.count()
        test.save(update_fields=['total_questions'])

        action_message = {
            'publish': f'Published test set "{test.title}".',
            'draft': f'Marked test set "{test.title}" as draft.',
            'update': f'Updated test set "{test.title}".',
        }[action]
        _log_admin_action(request.user, action, test, action_message)
        messages.success(request, success_message)
        return redirect('admin_dashboard_manage')

    context = {
        'active_tab': 'manage',
        'form': form,
        'test': test,
        'question_formset': question_formset,
        'answer_formsets': answer_formsets,
        'question_answer_zipped': zip(question_formset.forms, answer_formsets),
    }

    return render(request, 'admin_panel/test_form.html', context)





@staff_member_required

@require_POST

@staff_member_required
@require_POST
def test_delete(request, test_id):
    """
    Deletes a specific test set.
    """
    test = get_object_or_404(Test, id=test_id)
    title = test.title
    test.delete()
    _log_admin_action(request.user, 'delete', None, f'Deleted test set "{title}".', metadata={'test_id': test_id})
    messages.success(request, f'Test set "{title}" deleted.')
    return redirect('admin_dashboard_manage')





@staff_member_required

@require_POST

@staff_member_required
@require_POST
def toggle_visibility(request, test_id):
    """
    Toggles the visibility (hidden/visible) status of a test.
    """
    test = get_object_or_404(Test, id=test_id)
    test.is_hidden = not test.is_hidden
    test.save(update_fields=['is_hidden', 'updated_at'])

    if test.is_hidden:
        action = 'hide'
        log_message = f'Hidden test set "{test.title}".'
        toast_message = 'hidden'
    else:
        action = 'unhide'
        log_message = f'Unhid test set "{test.title}".'
        toast_message = 'visible'

    _log_admin_action(request.user, action, test, log_message)
    messages.success(request, f'Test set "{test.title}" is now {toast_message}.')
    return redirect('admin_dashboard_manage')





@staff_member_required

@require_POST

@staff_member_required
@require_POST
def publish_test(request, test_id):
    """
    Publishes a draft test, making it available to users.
    """
    test = get_object_or_404(Test, id=test_id)
    test.publish()
    _log_admin_action(request.user, 'publish', test, f'Published test set "{test.title}".')
    messages.success(request, f'Test set "{test.title}" published.')
    return redirect(request.POST.get('redirect_to') or 'admin_dashboard_manage')





@staff_member_required

@require_POST

@staff_member_required
@require_POST
def save_as_draft(request, test_id):
    """
    Reverts a published test to draft status.
    """
    test = get_object_or_404(Test, id=test_id)
    test.mark_draft()
    _log_admin_action(request.user, 'draft', test, f'Marked test set "{test.title}" as draft.')
    messages.success(request, f'Test set "{test.title}" saved as draft.')
    return redirect(request.POST.get('redirect_to') or 'admin_dashboard_manage')





@staff_member_required

@staff_member_required
def category_list(request):
    """
    List all test categories with pagination.
    """
    categories = TestCategory.objects.all().order_by('display_order', 'name')
    paginator = Paginator(categories, 10)
    page_obj = paginator.get_page(request.GET.get('page'))

    context = {
        'active_tab': 'categories',
        'page_obj': page_obj,
    }
    return render(request, 'admin_panel/category_list.html', context)





@staff_member_required

@staff_member_required
def category_create(request):
    """
    Create a new test category.
    """
    from .forms import TestCategoryForm
    form = TestCategoryForm(request.POST or None)

    if request.method == 'POST' and form.is_valid():
        category = form.save()
        _log_admin_action(request.user, 'create', None, f'Created category "{category.name}".')
        messages.success(request, f'Category "{category.name}" created successfully.')
        return redirect('admin_dashboard_categories')

    context = {
        'active_tab': 'categories',
        'form': form,
        'title': 'Add Category'
    }
    return render(request, 'admin_panel/category_form.html', context)





@staff_member_required

@staff_member_required
def category_edit(request, pk):
    """
    Edit an existing test category.
    """
    from .forms import TestCategoryForm
    category = get_object_or_404(TestCategory, pk=pk)
    form = TestCategoryForm(request.POST or None, instance=category)

    if request.method == 'POST' and form.is_valid():
        category = form.save()
        _log_admin_action(request.user, 'update', None, f'Updated category "{category.name}".')
        messages.success(request, f'Category "{category.name}" updated successfully.')
        return redirect('admin_dashboard_categories')

    context = {
        'active_tab': 'categories',
        'form': form,
        'title': 'Edit Category'
    }
    return render(request, 'admin_panel/category_form.html', context)





@staff_member_required

@require_POST

@staff_member_required
@require_POST
def category_delete(request, pk):
    """
    Delete a test category.
    """
    category = get_object_or_404(TestCategory, pk=pk)
    name = category.name
    category.delete()
    _log_admin_action(request.user, 'delete', None, f'Deleted category "{name}".')
    messages.success(request, f'Category "{name}" deleted.')
    return redirect('admin_dashboard_categories')





# Subscription Management



def _log_subscription_action(user, action, subscription, message, details=''):
    """
    Helper to record subscription-related actions in the audit log.
    
    Args:
        user (User): Admin user performing the action.
        action (str): Type of action.
        subscription (Subscription): Subscription object involved.
        message (str): Core log message.
        details (str, optional): Additional details.
    """
    from .models import SubscriptionLog
    
    SubscriptionLog.objects.create(
        admin_user=user,
        user=subscription.user,
        plan=subscription.plan,
        action=action,
        details=message + ('\n' + details if details else '')
    )



@staff_member_required

@staff_member_required
def subscription_list(request):
    """
    View to list and manage subscriptions.
    
    Supports filtering by:
    - Search query (username, email, plan name)
    - Status
    """
    from .models import Subscription
    query = request.GET.get('q', '').strip()
    status_filter = request.GET.get('status', '').strip()

    subscriptions = Subscription.objects.select_related('user', 'plan').order_by('-created_at')

    if query:
        subscriptions = subscriptions.filter(
            Q(user__username__icontains=query) | 
            Q(user__email__icontains=query) |
            Q(plan__name__icontains=query)
        )

    if status_filter:
        subscriptions = subscriptions.filter(status=status_filter)

    paginator = Paginator(subscriptions, 15)
    page_obj = paginator.get_page(request.GET.get('page'))

    context = {
        'active_tab': 'subscriptions',
        'page_obj': page_obj,
        'query': query,
        'status_filter': status_filter,
    }
    return render(request, 'admin_panel/subscription_list.html', context)



@staff_member_required

@staff_member_required
def subscription_add(request):
    """
    Manually add a subscription for a user.
    """
    from .forms import AddSubscriptionForm
    from .models import Subscription
    from django.contrib.auth.models import User
    from dateutil.relativedelta import relativedelta
    
    form = AddSubscriptionForm(request.POST or None)
    
    if request.method == 'POST' and form.is_valid():
        username_or_email = form.cleaned_data['username_or_email']
        plan = form.cleaned_data['plan']
        
        user = User.objects.filter(Q(username=username_or_email) | Q(email=username_or_email), is_active=True).first()
        
        if not user:
            messages.error(request, f"User '{username_or_email}' not found.")
        else:
            # Create subscription
            start_date = timezone.now()
            end_date = start_date + relativedelta(months=plan.duration_months)
            
            sub = Subscription.objects.create(
                user=user,
                plan=plan,
                status='active',
                expires_at=end_date,
                is_active=True
            )
            
            _log_subscription_action(request.user, 'create', sub, f"Created {plan.name} subscription for {user.username}.")
            messages.success(request, f"Subscription added for {user.username}.")
            return redirect('admin_dashboard_subscriptions')

    context = {
        'active_tab': 'subscriptions',
        'form': form,
        'title': 'Add Subscription'
    }
    return render(request, 'admin_panel/subscription_add.html', context)



@staff_member_required

@staff_member_required
def subscription_edit(request, pk):
    """
    Edit details of an existing subscription.
    """
    from .forms import SubscriptionForm
    from .models import Subscription
    
    sub = get_object_or_404(Subscription, pk=pk)
    form = SubscriptionForm(request.POST or None, instance=sub)
    
    if request.method == 'POST' and form.is_valid():
        sub = form.save()
        _log_subscription_action(request.user, 'update', sub, f"Updated subscription for {sub.user.username}.")
        messages.success(request, f"Subscription updated successfully.")
        return redirect('admin_dashboard_subscriptions')

    context = {
        'active_tab': 'subscriptions',
        'form': form,
        'subscription': sub,
        'title': 'Edit Subscription'
    }
    return render(request, 'admin_panel/subscription_form.html', context)



@staff_member_required

@staff_member_required
def subscription_extend(request, pk):
    """
    Quickly extend the duration of a subscription.
    """
    from .models import Subscription
    from dateutil.relativedelta import relativedelta
    
    sub = get_object_or_404(Subscription, pk=pk)
    
    if request.method == 'POST':
        months = int(request.POST.get('months', 0))
        if months > 0:
            if sub.status == 'expired':
                # If expired, start from now
                sub.expires_at = timezone.now() + relativedelta(months=months)
                sub.status = 'active'
                sub.is_active = True
            else:
                # Extend from current expiry
                sub.expires_at += relativedelta(months=months)
            
            sub.save()
            _log_subscription_action(request.user, 'extend', sub, f"Extended subscription by {months} months.")
            messages.success(request, f"Subscription extended by {months} months.")
        else:
            messages.error(request, "Invalid duration.")
            
    return redirect('admin_dashboard_subscriptions')



@staff_member_required

@staff_member_required
def subscription_logs(request):
    """
    View to display subscription audit logs.
    """
    from .models import SubscriptionLog
    
    query = request.GET.get('q', '').strip()
    logs = SubscriptionLog.objects.select_related('user', 'admin_user', 'plan').order_by('-created_at')
    
    if query:
        logs = logs.filter(
            Q(user__username__icontains=query) | 
            Q(user__email__icontains=query) |
            Q(admin_user__username__icontains=query)
        )
        
    paginator = Paginator(logs, 20)
    page_obj = paginator.get_page(request.GET.get('page'))
    
    context = {
        'active_tab': 'subscription_logs',
        'page_obj': page_obj,
        'query': query
    }
    return render(request, 'admin_panel/subscription_logs.html', context)





@staff_member_required

@staff_member_required
def search_users(request):
    """
    AJAX endpoint for user autocomplete fields.
    
    Returns a JSON list of users matching the query string.
    """
    from django.http import JsonResponse
    
    query = request.GET.get('q', '').strip()
    if len(query) < 2:
        return JsonResponse({'results': []})
    
    users = User.objects.filter(
        Q(username__icontains=query) | Q(email__icontains=query),
        is_active=True
    )[:10]
    
    results = [
        {
            'id': u.id,
            'text': f"{u.username} ({u.email})",
            'username': u.username,
            'email': u.email
        }
        for u in users
    ]
    return JsonResponse({'results': results})


# Referral Management
@staff_member_required
def referral_list(request):
    """
    List all referral codes with usage stats.
    """
    from .models import ReferralCode
    codes = ReferralCode.objects.all().order_by('-created_at')
    
    paginator = Paginator(codes, 15)
    page_obj = paginator.get_page(request.GET.get('page'))
    
    context = {
        'active_tab': 'referrals',
        'page_obj': page_obj,
    }
    return render(request, 'admin_panel/referral_list.html', context)

@staff_member_required
def referral_add(request):
    """
    Create a new referral code.
    """
    from .forms import ReferralCodeForm
    from .models import ReferralCode
    
    form = ReferralCodeForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        code = form.save()
        _log_admin_action(request.user, 'create', None, f"Created referral code '{code.code}'.")
        messages.success(request, f"Referral code '{code.code}' created successfully.")
        return redirect('admin_referral_list')
        
    context = {
        'active_tab': 'referrals',
        'form': form,
        'title': 'Add Referral Code'
    }
    return render(request, 'admin_panel/referral_form.html', context)

@staff_member_required
def referral_edit(request, pk):
    """
    Edit an existing referral code.
    """
    from .forms import ReferralCodeForm
    from .models import ReferralCode
    
    code = get_object_or_404(ReferralCode, pk=pk)
    form = ReferralCodeForm(request.POST or None, instance=code)
    if request.method == 'POST' and form.is_valid():
        code = form.save()
        _log_admin_action(request.user, 'update', None, f"Updated referral code '{code.code}'.")
        messages.success(request, f"Referral code '{code.code}' updated successfully.")
        return redirect('admin_referral_list')
        
    context = {
        'active_tab': 'referrals',
        'form': form,
        'title': 'Edit Referral Code'
    }
    return render(request, 'admin_panel/referral_form.html', context)

@staff_member_required
@require_POST
def referral_delete(request, pk):
    """
    Delete a referral code.
    """
    from .models import ReferralCode
    
    code = get_object_or_404(ReferralCode, pk=pk)
    code_str = code.code
    code.delete()
    _log_admin_action(request.user, 'delete', None, f"Deleted referral code '{code_str}'.")
    messages.success(request, f"Referral code '{code_str}' deleted.")
    return redirect('admin_referral_list')

@staff_member_required
def privacy_policy_edit(request):
    """
    View to view and edit the Privacy Policy.
    
    Usually restricted to singleton policy management.
    """
    from .models import PrivacyPolicy
    from .forms import PrivacyPolicyForm
    
    # Get the active policy or the most recently updated one
    policy = PrivacyPolicy.objects.first()
    
    form = PrivacyPolicyForm(request.POST or None, instance=policy)
    if request.method == 'POST' and form.is_valid():
        policy = form.save()
        action = 'update' if policy else 'create'
        _log_admin_action(request.user, action, None, f"{action.title()}d Privacy Policy.")
        messages.success(request, "Privacy Policy saved successfully.")
        return redirect('admin_privacy_policy_edit')

    context = {
        'active_tab': 'privacy',
        'form': form,
        'title': 'Privacy Policy Management',
        'last_updated': policy.updated_at if policy else None
    }
    return render(request, 'admin_panel/privacy_form.html', context)


@staff_member_required
def backup_restore_view(request):
    """
    System Backup and Restore Management.
    
    - 'backup': Creates a ZIP containing database dump (JSON) and media files.
    - 'restore': Uploads a ZIP, restores DB from dump, and restores media files.
    
    This is a critical system function and should be used with caution (implied).
    """
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'backup':
            try:
                # 1. Generate DB Dump
                buf = io.StringIO()
                # Dump data (excluding problematic tables)
                call_command('dumpdata', exclude=['contenttypes', 'auth.permission', 'sessions', 'admin.logentry', 'accounts.adminlog', 'accounts.systembackup'], indent=2, stdout=buf)
                db_json = buf.getvalue()
                
                # 2. Create ZIP in memory
                zip_buffer = io.BytesIO()
                with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                    # Add DB Dump
                    zip_file.writestr('db_dump.json', db_json)
                    
                    # Add Media Files
                    media_root = settings.MEDIA_ROOT
                    for root, dirs, files in os.walk(media_root):
                        for file in files:
                            file_path = os.path.join(root, file)
                            # Relative path inside zip
                            rel_path = os.path.relpath(file_path, start=media_root)
                            # Avoid recursive backup loop if backups stored in media/backups
                            if 'backups' in rel_path:
                                continue
                            try:
                                zip_file.write(file_path, arcname=os.path.join('media', rel_path))
                            except Exception:
                                pass # Skip errors for individual files
                                
                # 3. Save to SystemBackup model
                filename = f"backup_full_{timezone.now().strftime('%Y%m%d_%H%M%S')}.zip"
                backup_record = SystemBackup.objects.create(
                    name=filename,
                    created_by=request.user,
                    size_bytes=zip_buffer.tell()
                )
                backup_record.file.save(filename, ContentFile(zip_buffer.getvalue()))
                
                _log_admin_action(request.user, 'backup', None, f'Created full system backup "{filename}".')
                messages.success(request, f'Backup "{filename}" created successfully.')
                return redirect('admin_backup_restore')
                
            except Exception as e:
                import traceback
                traceback.print_exc()
                messages.error(request, f"Error creating backup: {str(e)}")
                return redirect('admin_backup_restore')
                
        elif action == 'restore':
            backup_file = request.FILES.get('backup_file')
            if not backup_file:
                 messages.error(request, "Please select a file to upload.")
                 return redirect('admin_backup_restore')
            
            # Simple check: json vs zip
            is_zip = backup_file.name.lower().endswith('.zip')
            
            try:
                # Save temp
                temp_dir = os.path.join(settings.MEDIA_ROOT, 'temp_restore')
                if os.path.exists(temp_dir):
                    shutil.rmtree(temp_dir)
                os.makedirs(temp_dir)
                
                temp_file_path = os.path.join(temp_dir, 'restore_pkg')
                with open(temp_file_path, 'wb+') as dest:
                    for chunk in backup_file.chunks():
                        dest.write(chunk)
                
                if is_zip:
                    # Extract
                    with zipfile.ZipFile(temp_file_path, 'r') as zip_ref:
                        zip_ref.extractall(temp_dir)
                    
                    # Look for db_dump.json
                    db_dump_path = os.path.join(temp_dir, 'db_dump.json')
                    if os.path.exists(db_dump_path):
                        call_command('loaddata', db_dump_path)
                    else:
                        messages.warning(request, "No 'db_dump.json' found in zip. Only media might have been restored if present.")
                        
                    # Move media
                    extracted_media = os.path.join(temp_dir, 'media')
                    if os.path.exists(extracted_media):
                        # Copy contents to real MEDIA_ROOT
                        # shutil.copytree requires dest not to exist, so we use distutils or manual walk

                        def recursive_copy(src, dst):
                            if not os.path.exists(dst):
                                os.makedirs(dst)
                            for item in os.listdir(src):
                                s = os.path.join(src, item)
                                d = os.path.join(dst, item)
                                if os.path.isdir(s):
                                    recursive_copy(s, d)
                                else:
                                    shutil.copy2(s, d)
                        recursive_copy(extracted_media, settings.MEDIA_ROOT)
                        
                else:
                    # Assume JSON Legacy
                    call_command('loaddata', temp_file_path)
                
                # Cleanup
                shutil.rmtree(temp_dir)
                
                _log_admin_action(request.user, 'restore', None, f'Restored system from "{backup_file.name}".')
                messages.success(request, "System restored successfully!")
                
            except Exception as e:
                import traceback
                traceback.print_exc()
                messages.error(request, f"Restore failed: {str(e)}")
                if os.path.exists(os.path.join(settings.MEDIA_ROOT, 'temp_restore')):
                    shutil.rmtree(os.path.join(settings.MEDIA_ROOT, 'temp_restore'))

            return redirect('admin_backup_restore')
    
    # Get recent logs
    recent_logs = AdminLog.objects.filter(
        Q(message__icontains='backup') | Q(message__icontains='restor')
    ).order_by('-created_at')[:10]
    
    # Get stored backups
    stored_backups = SystemBackup.objects.all()[:10]
    
    return render(request, 'admin_panel/backup_restore.html', {
        'active_tab': 'backup',
        'recent_logs': recent_logs,
        'stored_backups': stored_backups
    })

@staff_member_required
def email_settings_view(request):
    """
    Manage Global Email SMTP Settings configuration.
    
    Allows admins to update SMTP credentials dynamically.
    """
    from .models import EmailConfiguration
    from .forms import EmailConfigurationForm
    
    config = EmailConfiguration.get_solo()
    form = EmailConfigurationForm(request.POST or None, instance=config)
    
    if request.method == 'POST':
        if form.is_valid():
            form.save()
            messages.success(request, 'Email settings updated successfully.')
            # Create standard log
            _log_admin_action(request.user, 'update', None, 'Updated Email Settings configuration.')
            return redirect('admin_email_settings')
        else:
            messages.error(request, 'Please correct the errors below.')
    
    return render(request, 'admin_panel/email_settings.html', {
        'form': form,
        'active_tab': 'email_settings',
        'config': config
    })


@staff_member_required
def report_list(request):
    """
    List all question reports submitted by users.
    
    Allows filtering by status (open/resolved).
    """
    from .models import QuestionReport
    
    reports = QuestionReport.objects.select_related('user', 'question', 'question__test').order_by('-updated_at')
    
    status_filter = request.GET.get('status')
    if status_filter == 'resolved':
        reports = reports.filter(is_resolved=True)
    elif status_filter == 'open':
        reports = reports.filter(is_resolved=False)
        
    paginator = Paginator(reports, 10)
    page_obj = paginator.get_page(request.GET.get('page'))
    
    context = {
        'active_tab': 'reports',
        'page_obj': page_obj,
        'status_filter': status_filter
    }
    return render(request, 'admin_panel/report_list.html', context)

@staff_member_required
@require_POST
def delete_report(request, report_id):
    """
    Delete a specific question report.
    """
    from .models import QuestionReport
    report = get_object_or_404(QuestionReport, id=report_id)
    report.delete()
    messages.success(request, 'Report deleted successfully')
    return redirect('admin_report_list')
    
@staff_member_required
@require_POST
def toggle_report_status(request, report_id):
    """
    Toggle the resolved state of a report.
    """
    from .models import QuestionReport
    report = get_object_or_404(QuestionReport, id=report_id)
    report.is_resolved = not report.is_resolved
    report.save()
    status = "Resolved" if report.is_resolved else "Open"
    messages.success(request, f'Report marked as {status}')
    return redirect('admin_report_list')


@staff_member_required

def process_email_campaign(campaign_id):
    """
    Background worker to process email campaigns.
    Fetches recipients in chunks to conserve memory.
    """
    from .models import EmailCampaign, EmailConfiguration
    from .email_utils import get_email_connection
    from django.core.mail import EmailMultiAlternatives
    from django.conf import settings
    import time
    from django.db import connection as django_connection, connections

    # Ensure thread has its own DB connection
    django_connection.close()

    try:
        campaign = EmailCampaign.objects.get(id=campaign_id)
        if campaign.status != 'pending':
            return
        
        campaign.status = 'processing'
        campaign.save(update_fields=['status'])
        
        # Determine Audience
        users_qs = User.objects.filter(is_active=True, email__isnull=False).exclude(email='').exclude(is_staff=True)
        
        if campaign.audience == 'subscribers':
            users_qs = users_qs.filter(
                subscriptions__status='active',
                subscriptions__expires_at__gt=timezone.now()
            ).distinct()
        elif campaign.audience == 'non_subscribers':
            # Subquery approach for exclusion
            from django.db.models import Subquery
            subscribers = User.objects.filter(
                 subscriptions__status='active',
                 subscriptions__expires_at__gt=timezone.now()
            ).values('id')
            users_qs = users_qs.exclude(id__in=Subquery(subscribers))
        
        # Update estimate total
        total_count = users_qs.count()
        campaign.total_recipients = total_count
        campaign.save(update_fields=['total_recipients'])

        if total_count == 0:
            campaign.status = 'completed'
            campaign.completed_at = timezone.now()
            campaign.save(update_fields=['status', 'completed_at'])
            return

        # Setup Email Connection
        connection = get_email_connection()
        config = EmailConfiguration.get_solo()
        from_email = config.default_from_email or config.email_host_user if (config and config.is_active) else settings.DEFAULT_FROM_EMAIL
        
        # Process in chunks
        CHUNK_SIZE = 50
        processed_count = 0
        
        # Using iterator to avoid loading all objects
        recipients_iterator = users_qs.iterator(chunk_size=CHUNK_SIZE)
        
        batch_messages = []
        
        for user in recipients_iterator:
            email = EmailMultiAlternatives(
                subject=campaign.subject,
                body=campaign.message,
                from_email=from_email,
                to=[user.email],
                connection=connection
            )
            batch_messages.append(email)
            
            # Send batch
            if len(batch_messages) >= CHUNK_SIZE:
                sent = connection.send_messages(batch_messages)
                processed_count += sent
                
                # Update progress
                campaign.sent_count = processed_count
                campaign.save(update_fields=['sent_count'])
                
                # Clear batch
                batch_messages = []
                
                # Small sleep to be nice to SMTP server?
                # time.sleep(0.5) 

        # Send remaining
        if batch_messages:
            sent = connection.send_messages(batch_messages)
            processed_count += sent
            campaign.sent_count = processed_count
            campaign.save(update_fields=['sent_count'])
            
        campaign.status = 'completed'
        campaign.completed_at = timezone.now()
        campaign.save()

    except Exception as e:
        print(f"Error processing campaign {campaign_id}: {e}")
        try:
            campaign = EmailCampaign.objects.get(id=campaign_id)
            campaign.status = 'failed'
            campaign.save()
        except:
            pass
            
    finally:
        # Close email connection
        try:
            connection.close()
        except:
            pass
        
        # Close DB connection for this thread
        django_connection.close()


@staff_member_required
def email_marketing_view(request):
    """
    View for Email Marketing dashboard.
    
    Allows creating and monitoring email campaigns.
    Spawns a background thread to process email sending.
    """
    from .models import EmailConfiguration, EmailCampaign
    import threading

    # Check for active email configuration
    try:
        config = EmailConfiguration.get_solo()
        email_config_active = config and config.is_active
    except:
        email_config_active = False

    # Define audiences for stats
    users_qs = User.objects.filter(is_active=True).exclude(is_staff=True)
    all_qs = users_qs
    
    subscribers_qs = users_qs.filter(
        subscriptions__status='active',
        subscriptions__expires_at__gt=timezone.now()
    ).distinct()
    
    non_subscribers_qs = users_qs.exclude(id__in=subscribers_qs.values('id'))

    if request.method == 'POST':
        if not email_config_active:
             messages.error(request, "Cannot send emails: No active Email Configuration found.")
             return redirect('admin_email_marketing')

        audience = request.POST.get('audience')
        subject = request.POST.get('subject')
        message_body = request.POST.get('message')

        if not all([audience, subject, message_body]):
            messages.error(request, "All fields are required.")
            return redirect('admin_email_marketing')

        # Create Campaign Record
        campaign = EmailCampaign.objects.create(
            subject=subject,
            message=message_body,
            audience=audience,
            created_by=request.user,
            status='pending'
        )
        
        # Start Background Thread
        t = threading.Thread(target=process_email_campaign, args=(campaign.id,))
        t.daemon = True # Daemon so it doesn't block server shutdown
        t.start()
        
        messages.success(request, "Email campaign started in background! Status will update below.")
        return redirect('admin_email_marketing')

    # Fetch recent campaigns
    recent_campaigns = EmailCampaign.objects.all()[:10]

    context = {
        'active_tab': 'email_marketing',
        'email_config_active': email_config_active,
        'total_users': all_qs.count(),
        'subscribers_count': subscribers_qs.count(),
        'non_subscribers_count': non_subscribers_qs.count(),
        'recent_campaigns': recent_campaigns,
    }
    return render(request, 'admin_panel/email_marketing.html', context)


import csv
from django.db import transaction
from django.http import HttpResponse

@staff_member_required
def download_sample_csv(request):
    """View to download a sample CSV for bulk upload."""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="sample_questions.csv"'
    writer = csv.writer(response)
    writer.writerow(['Question Text', 'Marks', 'Explanation', 'Option 1', 'Option 2', 'Option 3', 'Option 4', 'Correct Option Number (1-4)'])
    writer.writerow(['What is the capital of France?', '1', 'Paris is the capital of France.', 'London', 'Berlin', 'Paris', 'Madrid', '3'])
    writer.writerow(['What is 2 + 2?', '2', '2 + 2 equals 4.', '3', '4', '5', '6', '2'])
    return response

@staff_member_required
def bulk_upload_questions(request, test_id):
    """View to bulk upload questions from a CSV file."""
    test = get_object_or_404(Test, id=test_id)
    
    if request.method == 'POST':
        csv_file = request.FILES.get('csv_file')
        if not csv_file:
            messages.error(request, "Please upload a CSV file.")
            return redirect('admin_dashboard_bulk_upload', test_id=test_id)
            
        if not csv_file.name.endswith('.csv'):
            messages.error(request, "Please upload a valid CSV file.")
            return redirect('admin_dashboard_bulk_upload', test_id=test_id)
            
        try:
            file_data = csv_file.read().decode('utf-8-sig')
            lines = file_data.split('\n')
            
            reader = csv.reader(lines)
            header = next(reader, None)
            
            if not header or len(header) < 8:
                messages.error(request, "Invalid CSV format. Please ensure it has the required 8 columns.")
                return redirect('admin_dashboard_bulk_upload', test_id=test_id)
                
            questions_added = 0
            
            with transaction.atomic():
                current_order = test.questions.count()
                
                for row in reader:
                    if not row or len(row) == 0 or not any(row):
                        continue
                        
                    if len(row) < 8:
                        messages.warning(request, f"Skipped a row due to missing columns: {row[:3]}")
                        continue
                        
                    question_text = row[0].strip()
                    marks_str = row[1].strip()
                    explanation = row[2].strip()
                    opt1 = row[3].strip()
                    opt2 = row[4].strip()
                    opt3 = row[5].strip()
                    opt4 = row[6].strip()
                    correct_opt_str = row[7].strip()
                    
                    if not question_text:
                        continue
                        
                    try:
                        marks = int(marks_str) if marks_str else 1
                    except ValueError:
                        marks = 1
                        
                    try:
                        correct_opt = int(correct_opt_str)
                        if correct_opt < 1 or correct_opt > 4:
                            correct_opt = 1
                    except ValueError:
                        correct_opt = 1
                        
                    current_order += 1
                    
                    q = Question.objects.create(
                        test=test,
                        question_text=question_text,
                        marks=marks,
                        explanation=explanation,
                        order=current_order
                    )
                    
                    options = [opt1, opt2, opt3, opt4]
                    for i, opt_text in enumerate(options):
                        is_correct = (i + 1 == correct_opt)
                        Answer.objects.create(
                            question=q,
                            answer_text=opt_text,
                            is_correct=is_correct,
                            order=i + 1
                        )
                        
                    questions_added += 1
            
            test.total_questions = test.questions.count()
            test.save(update_fields=['total_questions'])
            
            _log_admin_action(request.user, 'update', test, f'Bulk uploaded {questions_added} questions to test "{test.title}".')
            messages.success(request, f"Successfully uploaded {questions_added} questions to '{test.title}'.")
            return redirect('admin_dashboard_manage')
            
        except UnicodeDecodeError:
            messages.error(request, "The file could not be decoded. Please make sure it is saved with UTF-8 encoding.")
            return redirect('admin_dashboard_bulk_upload', test_id=test_id)
        except Exception as e:
            messages.error(request, f"An error occurred during upload: {str(e)}")
            return redirect('admin_dashboard_bulk_upload', test_id=test_id)
            
    context = {
        'active_tab': 'manage',
        'test': test,
    }
    return render(request, 'admin_panel/bulk_upload.html', context)

@staff_member_required
@require_POST
def bulk_action_tests(request):
    """
    Handles bulk operations on Test Sets.
    """
    action = request.POST.get('action')
    selected_tests = request.POST.getlist('selected_tests')
    select_across_pages = request.POST.get('select_across_pages') == 'true'
    
    if not action:
        messages.warning(request, "No action selected.")
        return redirect('admin_dashboard_manage')
        
    if select_across_pages:
        query = request.POST.get('q', '').strip()
        status_filter = request.POST.get('status', '').strip()
        visibility_filter = request.POST.get('visibility', '').strip()
        tests = Test.objects.all()
        if query:
            from django.db.models import Q
            tests = tests.filter(Q(title__icontains=query) | Q(description__icontains=query))
        if status_filter in {'draft', 'published'}:
            tests = tests.filter(status=status_filter)
        if visibility_filter == 'hidden':
            tests = tests.filter(is_hidden=True)
        elif visibility_filter == 'visible':
            tests = tests.filter(is_hidden=False)
    else:
        if not selected_tests:
            messages.warning(request, "No tests selected.")
            return redirect('admin_dashboard_manage')
        tests = Test.objects.filter(id__in=selected_tests)
        
    count = tests.count()
    
    if count == 0:
        messages.warning(request, "No valid tests found for the selected operation.")
        return redirect('admin_dashboard_manage')

    if action == 'publish':
        for test in tests:
            test.publish(save=True)
        _log_admin_action(request.user, 'update', None, f'Bulk published {count} test sets.')
        messages.success(request, f'Successfully published {count} test sets.')
    elif action == 'draft':
        for test in tests:
            test.mark_draft(save=True)
        _log_admin_action(request.user, 'update', None, f'Bulk marked {count} test sets as draft.')
        messages.success(request, f'Successfully marked {count} test sets as draft.')
    elif action == 'hide':
        tests.update(is_hidden=True)
        _log_admin_action(request.user, 'update', None, f'Bulk hidden {count} test sets.')
        messages.success(request, f'Successfully hidden {count} test sets.')
    elif action == 'unhide':
        tests.update(is_hidden=False)
        _log_admin_action(request.user, 'update', None, f'Bulk unhidden {count} test sets.')
        messages.success(request, f'Successfully unhidden {count} test sets.')
    elif action == 'delete':
        tests.delete()
        _log_admin_action(request.user, 'delete', None, f'Bulk deleted {count} test sets.')
        messages.success(request, f'Successfully deleted {count} test sets.')
    else:
        messages.error(request, "Invalid action selected.")

    return redirect('admin_dashboard_manage')
