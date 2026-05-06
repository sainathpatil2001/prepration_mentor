from django.urls import path
from . import views

urlpatterns = [
    path('user/', views.user_support, name='user_support'),
    path('user/<uuid:ticket_id>/', views.user_ticket_detail, name='user_ticket_detail'),
    path('user/feedback/<uuid:ticket_id>/', views.submit_feedback, name='submit_feedback'),
    path('admin/', views.admin_support_list, name='admin_support_list'),
    path('admin/<uuid:ticket_id>/', views.admin_support_detail, name='admin_support_detail'),
    path('messages/<uuid:ticket_id>/', views.get_messages, name='get_messages'),
    path('typing/<uuid:ticket_id>/', views.update_typing_status, name='update_typing_status'),
    path('export/', views.export_tickets, name='export_tickets'),
    path('delete/', views.delete_tickets, name='delete_tickets'),
    path('super-admin/reviews/', views.super_admin_reviews, name='super_admin_reviews'),
    path('super-admin/reviews/delete/', views.delete_reviews, name='delete_reviews'),
    path('super-admin/reviews/export/', views.export_reviews, name='export_reviews'),
]
