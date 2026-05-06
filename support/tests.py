from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from .models import SupportTicket, TicketMessage
from .forms import SupportTicketForm, TicketMessageForm
import uuid

class SupportTestFactory:
    @staticmethod
    def create_user(username='testuser', password='password', is_staff=False):
        user = User.objects.create_user(username=username, password=password)
        user.is_staff = is_staff
        user.save()
        return user

    @staticmethod
    def create_ticket(user, category='technical', description='Test issue'):
        return SupportTicket.objects.create(
            user=user,
            category=category,
            description=description
        )

class SupportModelTest(TestCase):
    def setUp(self):
        self.user = SupportTestFactory.create_user()
        self.ticket = SupportTestFactory.create_ticket(self.user)

    def test_ticket_creation(self):
        self.assertTrue(isinstance(self.ticket, SupportTicket))
        self.assertEqual(self.ticket.status, 'sent')
        self.assertTrue(isinstance(self.ticket.ticket_id, uuid.UUID))

    def test_ticket_str(self):
        self.assertEqual(str(self.ticket), f"Ticket {self.ticket.ticket_id} - {self.user.username}")

    def test_message_creation(self):
        message = TicketMessage.objects.create(
            ticket=self.ticket,
            sender=self.user,
            message="Hello"
        )
        self.assertEqual(message.ticket, self.ticket)
        self.assertFalse(message.is_admin_reply)

class SupportViewTest(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = SupportTestFactory.create_user()
        self.admin = SupportTestFactory.create_user(username='admin', is_staff=True)
        self.ticket = SupportTestFactory.create_ticket(self.user)

    def test_user_support_list_view(self):
        self.client.login(username='testuser', password='password')
        response = self.client.get(reverse('user_support'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.ticket.ticket_id)

    def test_create_ticket(self):
        self.client.login(username='testuser', password='password')
        response = self.client.post(reverse('user_support'), {
            'category': 'billing',
            'description': 'Billing issue'
        })
        self.assertEqual(response.status_code, 302) # Redirects after success
        self.assertEqual(SupportTicket.objects.count(), 2)

    def test_user_ticket_detail_view(self):
        self.client.login(username='testuser', password='password')
        response = self.client.get(reverse('user_ticket_detail', args=[self.ticket.ticket_id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.ticket.description)

    def test_user_reply_to_ticket(self):
        self.client.login(username='testuser', password='password')
        response = self.client.post(reverse('user_ticket_detail', args=[self.ticket.ticket_id]), {
            'message': 'My reply'
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.ticket.messages.count(), 1)
        self.assertEqual(self.ticket.messages.first().message, 'My reply')

    def test_admin_support_list_view(self):
        self.client.login(username='admin', password='password')
        response = self.client.get(reverse('admin_support_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.ticket.ticket_id)

    def test_admin_support_detail_view(self):
        self.client.login(username='admin', password='password')
        response = self.client.get(reverse('admin_support_detail', args=[self.ticket.ticket_id]))
        self.assertEqual(response.status_code, 200)
        
        # Check status auto-update to 'seen'
        self.ticket.refresh_from_db()
        self.assertEqual(self.ticket.status, 'seen')

    def test_admin_reply_to_ticket(self):
        self.client.login(username='admin', password='password')
        response = self.client.post(reverse('admin_support_detail', args=[self.ticket.ticket_id]), {
            'message_send': 'true',
            'message': 'Admin reply'
        })
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.ticket.messages.count(), 1)
        self.assertTrue(self.ticket.messages.first().is_admin_reply)

    def test_resolved_ticket_restrictions(self):
        self.ticket.status = 'resolved'
        self.ticket.save()
        
        self.client.login(username='testuser', password='password')
        response = self.client.get(reverse('user_ticket_detail', args=[self.ticket.ticket_id]))
        self.assertNotContains(response, 'Send Reply') # Should not show reply button
        self.assertContains(response, 'This ticket has been resolved')

        self.client.login(username='admin', password='password')
        response = self.client.get(reverse('admin_support_detail', args=[self.ticket.ticket_id]))
        self.assertNotContains(response, 'name="message_send"') # Should not show reply form input
