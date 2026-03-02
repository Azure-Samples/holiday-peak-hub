# 007: Payments Fully Stubbed

**Severity**: Medium  
**Category**: Backend  
**Discovered**: February 2026  
**Status**: ✅ Resolved — March 2026

## Summary

Payment processing was completely stubbed in both the backend CRUD service and the frontend checkout flow. This has been replaced with a real Stripe integration.

## Previous State

### Backend (`apps/crud-service/src/crud_service/routes/payments.py`)
- `POST /payments/intent` — Returned a fake `PaymentIntent` object with a hardcoded client secret
- `POST /payments/{id}/confirm` — Always returned success without calling any payment API
- Stripe SDK was listed as a dependency but never used for real API calls
- No webhook handler for Stripe events

### Frontend (`apps/ui/app/checkout/page.tsx`)
- Checkout form collected raw card details but did not submit to Stripe
- No Stripe Elements integration
- Payment confirmation was simulated client-side

## Current Implementation

### Backend

#### `POST /api/payments/intent`
Creates a real Stripe `PaymentIntent` and returns the `client_secret` for frontend confirmation.  
Requires `STRIPE_SECRET_KEY` environment variable (loaded from Key Vault).

#### `POST /api/payments`
Server-side payment confirmation: creates a `PaymentIntent` with `confirm=True`, updates the
order status to `paid`, and publishes a `PaymentProcessed` event to Event Hubs.

#### `POST /webhooks/stripe`
Stripe webhook endpoint with signature verification (`STRIPE_WEBHOOK_SECRET`).  
Handles:
- `payment_intent.succeeded` → marks order paid, publishes event
- `payment_intent.payment_failed` → logs the failure

### Frontend

- Added `@stripe/stripe-js` and `@stripe/react-stripe-js` dependencies.
- Step 2 of checkout now wraps `<PaymentElement>` in an `<Elements>` provider using the
  `client_secret` fetched from `POST /api/payments/intent`.
- `stripe.confirmPayment()` is called on form submit (no raw card data touches the server).
- Falls back to a demo mode placeholder when `NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY` is not set.

## Configuration

### Environment Variables

| Variable | Where | Description |
|---|---|---|
| `STRIPE_SECRET_KEY` | Key Vault / CRUD service env | Stripe secret key (`sk_live_…` / `sk_test_…`) |
| `STRIPE_WEBHOOK_SECRET` | Key Vault / CRUD service env | Webhook signing secret (`whsec_…`) |
| `NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY` | Frontend env / SWA config | Stripe publishable key (`pk_live_…` / `pk_test_…`) |

### Testing with Stripe

Use Stripe test keys and test card numbers.  
Simulate webhooks locally:

```bash
stripe listen --forward-to localhost:8000/webhooks/stripe
stripe trigger payment_intent.succeeded
```

## Files Modified

- `apps/crud-service/src/crud_service/routes/payments.py`
- `apps/crud-service/src/crud_service/routes/webhooks.py` (new)
- `apps/crud-service/src/crud_service/routes/__init__.py`
- `apps/crud-service/src/crud_service/main.py`
- `apps/crud-service/tests/unit/test_payments.py` (new)
- `apps/ui/app/checkout/page.tsx`
- `apps/ui/lib/services/checkoutService.ts`
- `apps/ui/lib/api/endpoints.ts`
- `apps/ui/lib/types/api.ts`
- `apps/ui/package.json`

