from django.core.management.base import BaseCommand
from accounts.models import SubscriptionPlan


class Command(BaseCommand):
    help = 'Populate subscription plans (Monthly, Half-Yearly, Yearly)'

    def handle(self, *args, **options):
        plans_data = [
            {
                'name': 'Monthly Plan',
                'plan_type': 'monthly',
                'duration_months': 1,
                'price': 99.00,
                'description': 'Perfect for trying out our platform. Access all features for 1 month.',
                'is_active': True,
            },
            {
                'name': 'Half-Yearly Plan',
                'plan_type': 'half_yearly',
                'duration_months': 6,
                'price': 499.00,
                'description': 'Best value for 6 months. Save money with this plan.',
                'is_active': True,
            },
            {
                'name': 'Yearly Plan',
                'plan_type': 'yearly',
                'duration_months': 12,
                'price': 899.00,
                'description': 'Maximum savings! Get full access for a whole year at the best price.',
                'is_active': True,
            },
        ]

        created_count = 0
        updated_count = 0

        for plan_data in plans_data:
            plan, created = SubscriptionPlan.objects.update_or_create(
                plan_type=plan_data['plan_type'],
                defaults={
                    'name': plan_data['name'],
                    'duration_months': plan_data['duration_months'],
                    'price': plan_data['price'],
                    'description': plan_data['description'],
                    'is_active': plan_data['is_active'],
                }
            )
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'Created plan: {plan.name}')
                )
            else:
                updated_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'Updated plan: {plan.name}')
                )

        self.stdout.write(
            self.style.SUCCESS(
                f'\nSuccessfully populated subscription plans!\n'
                f'Created: {created_count}, Updated: {updated_count}'
            )
        )

