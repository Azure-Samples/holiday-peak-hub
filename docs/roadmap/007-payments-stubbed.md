# 007: Payments Fully Stubbed

**Severity**: Medium  
**Category**: Backend  
**Discovered**: February 2026

## Summary

Payment processing is completely stubbed in both the backend CRUD service and the frontend checkout flow. No actual payment provider integration exists.

## Current State

### Backend (`apps/crud-service/src/crud_service/routes/payments.py`)
- `POST /payments/intent` — Returns a fake `PaymentIntent` object with a hardcoded client secret
- `POST /payments/{id}/confirm` — Always returns success without calling any payment API
- Stripe SDK is listed as a dependency but never used for real API calls
- No webhook handler for Stripe events

### Frontend (`apps/ui/app/checkout/page.tsx`)
- Checkout form collects card details but does not submit to Stripe
- No Stripe Elements integration
- Payment confirmation is simulated client-side

## Expected Behavior

- Backend should create real Stripe PaymentIntents via the Stripe SDK
- Frontend should render Stripe Elements for PCI-compliant card collection
- Webhook handler should process `payment_intent.succeeded` events
- Payment events should be published to the `payment-events` Event Hub topic

## Suggested Fix

### Phase 1: Backend
1. Implement real Stripe PaymentIntent creation in `payments.py`
2. Add webhook endpoint: `POST /webhooks/stripe`
3. Verify Stripe signature on webhook events
4. Publish payment events to Event Hubs on success/failure

### Phase 2: Frontend
1. Add `@stripe/stripe-js` and `@stripe/react-stripe-js` dependencies
2. Render `<Elements>` + `<PaymentElement>` in checkout
3. Handle `confirmPayment()` result
4. Show payment confirmation/error states

### Phase 3: Testing
1. Use Stripe test keys and test card numbers
2. Add integration tests for payment flow
3. Test webhook handler with Stripe CLI: `stripe trigger payment_intent.succeeded`

## Files to Modify

- `apps/crud-service/src/crud_service/routes/payments.py`
- `apps/crud-service/src/crud_service/routes/checkout.py`
- `apps/ui/app/checkout/page.tsx`
- `apps/ui/lib/services/checkoutService.ts`
- `apps/ui/package.json` — Add Stripe dependencies
