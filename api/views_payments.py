
# -------------------------
# Payment Integration (Razorpay)
# -------------------------
import razorpay
from django.conf import settings
from datetime import timedelta
from django.db import transaction
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.utils import timezone
from .serializers import PaymentOrderSerializer, PaymentVerifySerializer
from accounts.models import SubscriptionPlan, Subscription, PaymentTransaction

def get_razorpay_client():
    key_id = getattr(settings, 'RAZORPAY_KEY_ID', None)
    key_secret = getattr(settings, 'RAZORPAY_KEY_SECRET', None)
    if not key_id or not key_secret:
        raise ValueError("Razorpay keys not configured")
    return razorpay.Client(auth=(key_id, key_secret))

class PaymentViewSet(viewsets.ViewSet):
    """
    API endpoint for handling payments via Razorpay.
    """
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=False, methods=['post'])
    def create_order(self, request):
        """
        Create a Razorpay order for a subscription plan.
        Payload: { "plan_id": <int> }
        Returns: Razorpay Order ID and details.
        """
        serializer = PaymentOrderSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)
            
        plan_id = serializer.validated_data['plan_id']
        plan = get_object_or_404(SubscriptionPlan, id=plan_id, is_active=True)
        
        amount_paisa = int(plan.price * 100) # Convert to paisa
        
        try:
            client = get_razorpay_client()
            order_data = {
                'amount': amount_paisa,
                'currency': 'INR',
                'receipt': f'order_rcptid_{request.user.id}_{int(timezone.now().timestamp())}',
                'notes': {
                    'user_id': request.user.id,
                    'plan_id': plan.id,
                    'type': 'subscription'
                }
            }
            order = client.order.create(data=order_data)
            order_id = order['id']
            
            # Log transaction as pending
            PaymentTransaction.objects.create(
                user=request.user,
                transaction_type='subscription',
                subscription_plan=plan,
                razorpay_order_id=order_id,
                amount=plan.price,
                status='pending'
            )
            
            return Response({
                'order_id': order_id,
                'amount': amount_paisa,
                'currency': 'INR',
                'key_id': settings.RAZORPAY_KEY_ID,
                'prefill': {
                    'name': request.user.get_full_name(),
                    'email': request.user.email
                }
            })
            
        except Exception as e:
            # Fallback for dev/test without keys or network errors
            # Only if in DEBUG mode or explicitly allowed? 
            # For now, return error
            return Response({'error': str(e)}, status=500)

    @action(detail=False, methods=['post'])
    def verify_payment(self, request):
        """
        Verify payment signature and activate subscription.
        Payload: { razorpay_order_id, razorpay_payment_id, razorpay_signature }
        """
        serializer = PaymentVerifySerializer(data=request.data)
        if not serializer.is_valid():
             return Response(serializer.errors, status=400)
             
        data = serializer.validated_data
        
        try:
            client = get_razorpay_client()
            # Verify signature
            client.utility.verify_payment_signature(data)
            
            # Fetch transaction
            txn = get_object_or_404(PaymentTransaction, razorpay_order_id=data['razorpay_order_id'])
            
            if txn.status == 'success':
                 return Response({'status': 'already verified'})
            
            with transaction.atomic():
                txn.razorpay_payment_id = data['razorpay_payment_id']
                txn.razorpay_signature = data['razorpay_signature']
                txn.status = 'success'
                txn.save()
                
                # Activate subscription
                if txn.subscription_plan:
                    plan = txn.subscription_plan
                    # Check existing sub
                    active_sub = Subscription.objects.filter(
                        user=request.user, 
                        status='active', 
                        expires_at__gt=timezone.now()
                    ).order_by('-expires_at').first()
                    
                    if active_sub:
                        active_sub.expires_at += timedelta(days=plan.duration_months*30)
                        active_sub.save()
                        sub = active_sub
                    else:
                        expires_at = timezone.now() + timedelta(days=plan.duration_months*30)
                        sub = Subscription.objects.create(
                            user=request.user,
                            plan=plan,
                            status='active',
                            expires_at=expires_at, 
                            is_active=True
                        )
                    
                    txn.subscription = sub
                    txn.save()
                    
            return Response({'status': 'payment verified', 'subscription_active': True})
            
        except Exception as e:
             return Response({'error': str(e)}, status=500)

    @action(detail=False, methods=['get'])
    def history(self, request):
        """
        Get payment history for the current user.
        """
        transactions = PaymentTransaction.objects.filter(user=request.user).order_by('-created_at')
        # We need a serializer. Importing inside method to avoid circular imports if any, 
        # or assuming it will be available. 
        # Let's use a simple inline construction or better, add to serializers.py.
        # Since I can't easily jump to serializers.py and back in one step, 
        # I'll just return data manually or use a serializer I'll add.
        
        data = []
        for txn in transactions:
            data.append({
                'id': txn.id,
                'amount': txn.amount,
                'status': txn.status,
                'date': txn.created_at,
                'plan_name': txn.subscription_plan.name if txn.subscription_plan else 'N/A',
                'order_id': txn.razorpay_order_id
            })
        return Response(data)
