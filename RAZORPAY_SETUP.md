# Razorpay Setup Guide

## Quick Setup

### Step 1: Get Your Razorpay API Keys

1. Go to [Razorpay Dashboard](https://dashboard.razorpay.com/)
2. Sign in or create an account
3. Navigate to **Settings** → **API Keys**
4. Copy your **Key ID** and **Key Secret**

**Note**: 
- Use **Test Keys** for development/testing
- Use **Live Keys** for production
- Test keys start with `rzp_test_`
- Live keys start with `rzp_live_`

### Step 2: Configure Keys in Settings

**Option A: Direct Configuration (Recommended for Development)**

Edit `exam_project/settings.py`:

```python
RAZORPAY_KEY_ID = 'rzp_test_xxxxxxxxxxxxx'  # Your actual Key ID
RAZORPAY_KEY_SECRET = 'xxxxxxxxxxxxxxxxxxxxx'  # Your actual Key Secret
```

**Option B: Environment Variables (Recommended for Production)**

Create a `.env` file in the project root:

```env
RAZORPAY_KEY_ID=rzp_test_xxxxxxxxxxxxx
RAZORPAY_KEY_SECRET=xxxxxxxxxxxxxxxxxxxxx
```

Then update `settings.py` (already configured):

```python
RAZORPAY_KEY_ID = os.environ.get('RAZORPAY_KEY_ID', 'your_razorpay_key_id')
RAZORPAY_KEY_SECRET = os.environ.get('RAZORPAY_KEY_SECRET', 'your_razorpay_key_secret')
```

### Step 3: Verify Configuration

1. Restart your Django server
2. Go to the "Add Funds" page
3. If keys are configured correctly, you'll see the payment form
4. If not configured, you'll see a configuration error message

## Testing Payments

### Using Test Keys

1. Use test card numbers from [Razorpay Test Cards](https://razorpay.com/docs/payments/test-card-details/)
2. Example test cards:
   - Success: `4111 1111 1111 1111`
   - CVV: `123`
   - Expiry: Any future date (e.g., `12/25`)
   - Name: Any name

### Test Cards

| Card Number | Result |
|------------|--------|
| 4111 1111 1111 1111 | Success |
| 5104 0600 0000 0008 | Success (International) |
| 5267 3181 8797 5449 | Failure |

## Common Issues

### Error: "Authentication failed"

**Cause**: Invalid or missing Razorpay API keys

**Solution**:
1. Verify keys are copied correctly (no extra spaces)
2. Ensure you're using Test keys for testing
3. Check if keys are set in environment variables correctly

### Error: "Invalid Razorpay API keys"

**Cause**: Keys are incorrect or from wrong environment

**Solution**:
1. Regenerate keys in Razorpay Dashboard
2. Update keys in settings.py
3. Restart Django server

### Error: "Payment verification failed"

**Cause**: Signature verification error (usually after payment)

**Solution**:
1. Check if keys match (test vs live)
2. Verify payment was actually successful in Razorpay Dashboard
3. Check server logs for detailed error

## Production Checklist

- [ ] Switch to Live API keys
- [ ] Store keys in environment variables (never commit to git)
- [ ] Enable webhooks for payment notifications
- [ ] Set up proper error logging
- [ ] Test payment flow thoroughly
- [ ] Configure proper SSL certificate (HTTPS required)
- [ ] Update callback URLs in Razorpay Dashboard

## Security Best Practices

1. **Never commit API keys to git** - Use environment variables
2. **Use different keys for test and production**
3. **Rotate keys periodically**
4. **Monitor transactions in Razorpay Dashboard**
5. **Enable webhook signature verification**

## Support

- [Razorpay Documentation](https://razorpay.com/docs/)
- [Razorpay Support](https://razorpay.com/support/)
- [Test Card Details](https://razorpay.com/docs/payments/test-card-details/)

