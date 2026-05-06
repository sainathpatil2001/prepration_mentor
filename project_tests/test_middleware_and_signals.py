"""Tests for session-control middleware and login signal handlers."""

from __future__ import annotations

from django.contrib.sessions.backends.db import SessionStore
from django.contrib.sessions.middleware import SessionMiddleware
from django.contrib.sessions.models import Session
from django.http import HttpResponse
from django.test import RequestFactory, TestCase

from accounts.middleware import SingleSessionMiddleware
from accounts.models import UserSession
from accounts.signals import create_user_session
from project_tests.factories import TestDataFactory


class SessionControlTests(TestCase):
    """Validate one-session-per-user enforcement logic."""

    def setUp(self):
        self.user = TestDataFactory.create_user(username="session_user")
        self.factory = RequestFactory()

    def _request_with_session(self):
        """Build a request object with a persisted session."""
        request = self.factory.get("/")
        middleware = SessionMiddleware(lambda req: HttpResponse("ok"))
        middleware.process_request(request)
        request.session.save()
        return request

    def test_login_signal_replaces_previous_user_session(self):
        """`create_user_session` should keep only the newest session for a user."""
        first_request = self._request_with_session()
        create_user_session(sender=None, request=first_request, user=self.user)
        first_key = first_request.session.session_key
        self.assertTrue(UserSession.objects.filter(user=self.user, session_key=first_key).exists())

        second_request = self._request_with_session()
        create_user_session(sender=None, request=second_request, user=self.user)
        second_key = second_request.session.session_key

        self.assertNotEqual(first_key, second_key)
        self.assertEqual(UserSession.objects.filter(user=self.user).count(), 1)
        self.assertTrue(UserSession.objects.filter(user=self.user, session_key=second_key).exists())
        self.assertFalse(UserSession.objects.filter(user=self.user, session_key=first_key).exists())
        self.assertFalse(Session.objects.filter(session_key=first_key).exists())

    def test_single_session_middleware_removes_other_sessions(self):
        """Middleware should remove stale sessions when a newer session is active."""
        old_store = SessionStore()
        old_store["source"] = "old-session"
        old_store.save()
        old_key = old_store.session_key

        UserSession.objects.create(user=self.user, session_key=old_key)
        self.assertTrue(Session.objects.filter(session_key=old_key).exists())

        new_request = self._request_with_session()
        new_key = new_request.session.session_key
        new_request.user = self.user

        middleware = SingleSessionMiddleware(lambda req: HttpResponse("ok"))
        response = middleware(new_request)
        self.assertEqual(response.status_code, 200)

        self.assertEqual(UserSession.objects.filter(user=self.user).count(), 1)
        self.assertTrue(UserSession.objects.filter(user=self.user, session_key=new_key).exists())
        self.assertFalse(UserSession.objects.filter(user=self.user, session_key=old_key).exists())
        self.assertFalse(Session.objects.filter(session_key=old_key).exists())

