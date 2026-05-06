from django.core.management.base import BaseCommand
from accounts.models import SubscriptionPlan

class Command(BaseCommand):
    help = 'Initialize default subscription plans'

    def handle(self, *args, **kwargs):
        plans = [
            {
                'name': 'Monthly Plan',
                'plan_type': 'monthly',
                'duration_months': 1,
                'price': 99.00,
                'description': 'Access for 1 month'
            },
            {
                'name': 'Half-Yearly Plan',
                'plan_type': 'half_yearly',
                'duration_months': 6,
                'price': 499.00,
                'description': 'Access for 6 months'
            },
            {
                'name': 'Yearly Plan',
                'plan_type': 'yearly',
                'duration_months': 12,
                'price': 899.00,
                'description': 'Access for 1 year'
            }
        ]

        for plan_data in plans:
            plan, created = SubscriptionPlan.objects.get_or_create(
                plan_type=plan_data['plan_type'],
                defaults=plan_data
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f"Created plan: {plan.name}"))
            else:
                # Update price if changed
                if plan.price != plan_data['price']:
                    plan.price = plan_data['price']
                    plan.save()
                    self.stdout.write(self.style.SUCCESS(f"Updated price for plan: {plan.name}"))
                else:
                    self.stdout.write(self.style.SUCCESS(f"Plan already exists: {plan.name}"))
