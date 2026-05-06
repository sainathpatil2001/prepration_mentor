from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth.models import User

from accounts.models import SubscriptionPlan, Subscription


class Command(BaseCommand):
	help = 'Grant or extend an active subscription for a user by email.'

	def add_arguments(self, parser):
		parser.add_argument('--email', required=True, help='User email to grant subscription to')
		parser.add_argument('--plan', required=False, choices=['monthly', 'half_yearly', 'yearly'], default='monthly', help='Plan type to grant')

	def handle(self, *args, **options):
		email = options['email'].strip().lower()
		plan_type = options['plan']

		try:
			user = User.objects.get(email__iexact=email)
		except User.DoesNotExist:
			raise CommandError(f'No user found with email: {email}')

		try:
			plan = SubscriptionPlan.objects.get(plan_type=plan_type, is_active=True)
		except SubscriptionPlan.DoesNotExist:
			raise CommandError(f'Active SubscriptionPlan not found for plan_type: {plan_type}. Create plans first.')

		now = timezone.now()
		duration_days = plan.duration_months * 30

		# Find active subscription, if any
		active_sub = Subscription.objects.filter(user=user, status='active', is_active=True, expires_at__gt=now).order_by('-expires_at').first()

		if active_sub:
			# Extend existing subscription
			active_sub.expires_at = active_sub.expires_at + timedelta(days=duration_days)
			active_sub.save()
			self.stdout.write(self.style.SUCCESS(
				f'Extended subscription for {email}: {plan.name} until {active_sub.expires_at.strftime("%Y-%m-%d %H:%M:%S")}'
			))
		else:
			# Create new subscription
			expires_at = now + timedelta(days=duration_days)
			sub = Subscription.objects.create(
				user=user,
				plan=plan,
				status='active',
				is_active=True,
				expires_at=expires_at,
			)
			self.stdout.write(self.style.SUCCESS(
				f'Created subscription for {email}: {plan.name} valid until {sub.expires_at.strftime("%Y-%m-%d %H:%M:%S")}'
			))
