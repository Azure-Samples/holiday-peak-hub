'use client';

import React, { useEffect, useMemo, useRef, useState } from 'react';
import { Elements, PaymentElement, useElements, useStripe } from '@stripe/react-stripe-js';
import { loadStripe } from '@stripe/stripe-js';
import { useRouter } from 'next/navigation';
import { CheckoutLayout } from '@/components/templates/CheckoutLayout';
import { Card } from '@/components/molecules/Card';
import { Button } from '@/components/atoms/Button';
import { Input } from '@/components/atoms/Input';
import { Checkbox } from '@/components/atoms/Checkbox';
import { Radio } from '@/components/atoms/Radio';
import { Badge } from '@/components/atoms/Badge';
import { FiGift, FiTruck } from 'react-icons/fi';
import checkoutService from '@/lib/services/checkoutService';
import inventoryService from '@/lib/services/inventoryService';
import { useCart } from '@/lib/hooks/useCart';
import { useInventoryHealth, useReservationOutcomeQueries } from '@/lib/hooks/useInventory';

const stripePromise = process.env.NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY
  ? loadStripe(process.env.NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY)
  : null;

interface CheckoutItem {
  productId: string;
  quantity: number;
  price: number;
}

interface StripePaymentFormProps {
  onSuccess: (paymentIntentId?: string) => Promise<void>;
  onBack: () => void;
  isFinalizing: boolean;
}

function StripePaymentForm({ onSuccess, onBack, isFinalizing }: StripePaymentFormProps) {
  const stripe = useStripe();
  const elements = useElements();
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const isPaymentActionPending = isSubmitting || isFinalizing;

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!stripe || !elements || isSubmitting || isFinalizing) {
      return;
    }

    setIsSubmitting(true);
    setErrorMessage(null);

    const result = await stripe.confirmPayment({
      elements,
      redirect: 'if_required',
    });

    if (result.error) {
      setErrorMessage(result.error.message ?? 'Payment confirmation failed. Please try again.');
      setIsSubmitting(false);
      return;
    }

    await onSuccess(result.paymentIntent?.id);
    setIsSubmitting(false);
  };

  return (
    <form
      onSubmit={handleSubmit}
      className="space-y-6"
      aria-busy={isPaymentActionPending}
      aria-describedby={errorMessage ? 'stripe-payment-error' : undefined}
    >
      <PaymentElement />

      {isPaymentActionPending ? (
        <p className="sr-only" role="status" aria-live="polite">
          Processing your payment. Please wait.
        </p>
      ) : null}

      {errorMessage && (
        <p
          id="stripe-payment-error"
          className="text-sm text-red-600 dark:text-red-400"
          role="alert"
          aria-live="assertive"
        >
          {errorMessage}
        </p>
      )}

      <div className="flex gap-4">
        <Button
          type="button"
          variant="ghost"
          onClick={onBack}
          disabled={isPaymentActionPending}
          className="flex-1"
        >
          Back
        </Button>
        <Button
          type="submit"
          size="lg"
          disabled={!stripe || isPaymentActionPending}
          aria-busy={isPaymentActionPending}
          className="flex-1 bg-ocean-500 hover:bg-ocean-600 dark:bg-ocean-300 dark:hover:bg-ocean-400 text-white dark:text-gray-900"
        >
          {isPaymentActionPending ? 'Processing…' : 'Pay & Place Order'}
        </Button>
      </div>
    </form>
  );
}

function getErrorMessage(error: unknown, fallback: string): string {
  if (error instanceof Error && error.message.trim().length > 0) {
    return error.message;
  }
  return fallback;
}

function buildShippingAddressId(shippingData: {
  firstName: string;
  lastName: string;
  zipCode: string;
  address: string;
}): string {
  const stableId = [shippingData.firstName, shippingData.lastName, shippingData.zipCode]
    .join('-')
    .toLowerCase()
    .replace(/[^a-z0-9-]/g, '');

  return stableId.length > 0 ? `addr-${stableId}` : `addr-${shippingData.address.length}`;
}

export default function CheckoutPage() {
  const router = useRouter();
  const { data: cart, isLoading: isCartLoading, isError: isCartError } = useCart();
  const {
    data: inventoryHealth,
    isLoading: isInventoryHealthLoading,
    isError: isInventoryHealthError,
    isFetching: isInventoryHealthFetching,
    refetch: refetchInventoryHealth,
  } = useInventoryHealth();

  const [currentStep, setCurrentStep] = useState(1);
  const [shippingData, setShippingData] = useState({
    firstName: '',
    lastName: '',
    email: '',
    phone: '',
    address: '',
    city: '',
    state: '',
    zipCode: '',
    country: 'US',
    saveAddress: false,
  });
  const [shippingMethod, setShippingMethod] = useState('standard');
  const [orderId, setOrderId] = useState<string | null>(null);
  const [orderTotal, setOrderTotal] = useState<number | null>(null);
  const [clientSecret, setClientSecret] = useState<string | null>(null);
  const [paymentIntentId, setPaymentIntentId] = useState<string | null>(null);
  const [reservationIds, setReservationIds] = useState<string[]>([]);
  const [lockedItems, setLockedItems] = useState<CheckoutItem[]>([]);
  const [setupError, setSetupError] = useState<string | null>(null);
  const [paymentError, setPaymentError] = useState<string | null>(null);
  const [isPreparingCheckout, setIsPreparingCheckout] = useState(false);
  const [isFinalizingPayment, setIsFinalizingPayment] = useState(false);
  const [isOrderPaymentConfirmed, setIsOrderPaymentConfirmed] = useState(false);

  const hasCompletedCheckoutRef = useRef(false);
  const reservationIdsRef = useRef<string[]>([]);

  useEffect(() => {
    reservationIdsRef.current = reservationIds;
  }, [reservationIds]);

  useEffect(() => {
    return () => {
      if (hasCompletedCheckoutRef.current || reservationIdsRef.current.length === 0) {
        return;
      }

      void Promise.allSettled(
        reservationIdsRef.current.map((reservationId) =>
          inventoryService.releaseReservation(reservationId, {
            reason: 'checkout_abandoned_before_payment_confirmation',
          })
        )
      );
    };
  }, []);

  const fieldIds = {
    firstName: 'checkout-first-name',
    lastName: 'checkout-last-name',
    email: 'checkout-email',
    phone: 'checkout-phone',
    address: 'checkout-address',
    city: 'checkout-city',
    state: 'checkout-state',
    zipCode: 'checkout-zip',
  };

  const liveCartItems: CheckoutItem[] = useMemo(
    () =>
      (cart?.items ?? []).map((item) => ({
        productId: item.product_id,
        quantity: item.quantity,
        price: item.price,
      })),
    [cart?.items]
  );

  const summaryItems = orderId ? lockedItems : liveCartItems;
  const reservationOutcomeQueries = useReservationOutcomeQueries(reservationIds);
  const reservationOutcomes = useMemo(
    () => reservationOutcomeQueries.map((query) => query.data).filter(Boolean),
    [reservationOutcomeQueries]
  );
  const subtotal = summaryItems.reduce((sum, item) => sum + item.price * item.quantity, 0);
  const shippingCost =
    shippingMethod === 'express' ? 15.99 : shippingMethod === 'overnight' ? 29.99 : 5.99;
  const tax = subtotal * 0.08;
  const total = orderTotal ?? subtotal + shippingCost + tax;
  const thresholdBreaches = (inventoryHealth?.low_stock ?? 0) + (inventoryHealth?.out_of_stock ?? 0);
  const replenishmentTriggers = thresholdBreaches;

  const reservationSignalsError = reservationOutcomeQueries.find((query) => query.isError)?.error;
  const hasReservationQueries = reservationOutcomeQueries.length > 0;
  const areReservationSignalsLoading = reservationOutcomeQueries.some((query) => query.isLoading);
  const areReservationSignalsFetching = reservationOutcomeQueries.some((query) => query.isFetching);

  const retryInventoryHealth = () => {
    void refetchInventoryHealth();
  };

  const retryReservationOutcomes = () => {
    void Promise.allSettled(reservationOutcomeQueries.map((query) => query.refetch()));
  };

  const createReservationsForItems = async (items: CheckoutItem[]): Promise<string[]> => {
    const createdReservationIds: string[] = [];

    try {
      for (const item of items) {
        const reservation = await inventoryService.createReservation({
          sku: item.productId,
          quantity: item.quantity,
          reason: 'checkout_hold',
        });
        createdReservationIds.push(reservation.id);
      }

      return createdReservationIds;
    } catch (error) {
      if (createdReservationIds.length > 0) {
        await Promise.allSettled(
          createdReservationIds.map((reservationId) =>
            inventoryService.releaseReservation(reservationId, {
              reason: 'checkout_setup_failed_partial_reservation_rollback',
            })
          )
        );
      }

      throw error;
    }
  };

  const confirmReservationsForCheckout = async (activeOrderId: string) => {
    if (reservationIds.length === 0) {
      return;
    }

    await Promise.all(
      reservationIds.map((reservationId) =>
        inventoryService.confirmReservation(reservationId, {
          reason: `payment_confirmed_for_order_${activeOrderId}`,
        })
      )
    );
  };

  const globalStatusMessage =
    isPreparingCheckout
      ? 'Preparing checkout. Please wait.'
      : isFinalizingPayment
        ? 'Finalizing your order. Please wait.'
        : isCartLoading
          ? 'Loading cart details.'
          : null;

  const handleShippingSubmit = async (event: React.FormEvent) => {
    event.preventDefault();

    if (!orderId && summaryItems.length === 0) {
      setSetupError('Your cart is empty. Add items before checking out.');
      return;
    }

    if (!stripePromise) {
      setSetupError('Payments are currently unavailable. Please try again later.');
      return;
    }

    setSetupError(null);
    setPaymentError(null);
    setIsPreparingCheckout(true);

    let activeOrderId = orderId;
    let activeOrderTotal = orderTotal;
    let createdReservationIdsForAttempt: string[] = [];

    try {
      if (!activeOrderId) {
        const validation = await checkoutService.validate();
        if (!validation.valid) {
          throw new Error(validation.errors[0] ?? 'Checkout validation failed.');
        }

        createdReservationIdsForAttempt = await createReservationsForItems(liveCartItems);

        const createdOrder = await checkoutService.createOrder({
          shipping_address_id: buildShippingAddressId(shippingData),
          payment_method_id: 'stripe_intent',
        });

        activeOrderId = createdOrder.id;
        activeOrderTotal = createdOrder.total;
        setOrderId(createdOrder.id);
        setOrderTotal(createdOrder.total);
        setReservationIds(createdReservationIdsForAttempt);
        setLockedItems(liveCartItems);
      }

      const paymentIntent = await checkoutService.createPaymentIntent({
        order_id: activeOrderId,
        amount: activeOrderTotal ?? total,
        currency: 'usd',
      });

      setClientSecret(paymentIntent.client_secret);
      setPaymentIntentId(paymentIntent.payment_intent_id);
      setIsOrderPaymentConfirmed(false);
      setCurrentStep(2);
    } catch (error) {
      if (!activeOrderId && createdReservationIdsForAttempt.length > 0) {
        await Promise.allSettled(
          createdReservationIdsForAttempt.map((reservationId) =>
            inventoryService.releaseReservation(reservationId, {
              reason: 'checkout_setup_failed_before_order_creation_rollback',
            })
          )
        );
        setReservationIds([]);
        setLockedItems([]);
      }

      setSetupError(getErrorMessage(error, 'Unable to prepare checkout. Please retry.'));
    } finally {
      setIsPreparingCheckout(false);
    }
  };

  const finalizeConfirmedPayment = async (confirmedPaymentIntentId?: string) => {
    if (!orderId) {
      setPaymentError('Order was not created. Please return to shipping and retry.');
      return;
    }

    const resolvedPaymentIntentId = confirmedPaymentIntentId ?? paymentIntentId;
    if (!resolvedPaymentIntentId) {
      setPaymentError('Payment intent is missing. Please retry payment confirmation.');
      return;
    }

    setPaymentError(null);
    setIsFinalizingPayment(true);

    try {
      if (!isOrderPaymentConfirmed) {
        await checkoutService.confirmPaymentIntent({
          order_id: orderId,
          payment_intent_id: resolvedPaymentIntentId,
        });
        setIsOrderPaymentConfirmed(true);
      }

      await confirmReservationsForCheckout(orderId);
      hasCompletedCheckoutRef.current = true;
      router.push(`/order/${encodeURIComponent(orderId)}`);
    } catch (error) {
      setPaymentError(
        getErrorMessage(
          error,
          'Payment was authorized, but order finalization failed. Retry finalization.'
        )
      );
    } finally {
      setIsFinalizingPayment(false);
    }
  };

  return (
    <CheckoutLayout currentStep={currentStep}>
      {globalStatusMessage ? (
        <p className="sr-only" role="status" aria-live="polite">
          {globalStatusMessage}
        </p>
      ) : null}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div className="lg:col-span-2 space-y-6">
          {currentStep === 1 ? (
            <Card className="p-6">
              <div className="flex items-center gap-3 mb-6">
                <div className="w-10 h-10 bg-ocean-500 dark:bg-ocean-300 rounded-full flex items-center justify-center text-white dark:text-gray-900 font-bold">
                  1
                </div>
                <h2 className="text-2xl font-bold text-gray-900 dark:text-white">
                  Shipping Information
                </h2>
              </div>

              {isCartLoading ? (
                <p
                  className="text-sm text-gray-600 dark:text-gray-400 mb-4"
                  role="status"
                  aria-live="polite"
                >
                  Loading cart…
                </p>
              ) : null}

              {isCartError ? (
                <p
                  className="text-sm text-red-600 dark:text-red-400 mb-4"
                  role="alert"
                  aria-live="assertive"
                >
                  Cart could not be loaded. Please refresh and try again.
                </p>
              ) : null}

              {setupError ? (
                <p
                  id="checkout-setup-error"
                  className="text-sm text-red-600 dark:text-red-400 mb-4"
                  role="alert"
                  aria-live="assertive"
                >
                  {setupError}
                </p>
              ) : null}

              <form
                onSubmit={handleShippingSubmit}
                className="space-y-4"
                aria-busy={isPreparingCheckout}
                aria-describedby={setupError ? 'checkout-setup-error' : undefined}
              >
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label
                      htmlFor={fieldIds.firstName}
                      className="block text-sm font-semibold text-gray-900 dark:text-white mb-2"
                    >
                      First Name *
                    </label>
                    <Input
                      id={fieldIds.firstName}
                      type="text"
                      autoComplete="given-name"
                      value={shippingData.firstName}
                      onChange={(e) => setShippingData({ ...shippingData, firstName: e.target.value })}
                      required
                    />
                  </div>
                  <div>
                    <label
                      htmlFor={fieldIds.lastName}
                      className="block text-sm font-semibold text-gray-900 dark:text-white mb-2"
                    >
                      Last Name *
                    </label>
                    <Input
                      id={fieldIds.lastName}
                      type="text"
                      autoComplete="family-name"
                      value={shippingData.lastName}
                      onChange={(e) => setShippingData({ ...shippingData, lastName: e.target.value })}
                      required
                    />
                  </div>
                </div>

                <div>
                  <label
                    htmlFor={fieldIds.email}
                    className="block text-sm font-semibold text-gray-900 dark:text-white mb-2"
                  >
                    Email Address *
                  </label>
                  <Input
                    id={fieldIds.email}
                    type="email"
                    autoComplete="email"
                    value={shippingData.email}
                    onChange={(e) => setShippingData({ ...shippingData, email: e.target.value })}
                    required
                  />
                </div>

                <div>
                  <label
                    htmlFor={fieldIds.phone}
                    className="block text-sm font-semibold text-gray-900 dark:text-white mb-2"
                  >
                    Phone Number *
                  </label>
                  <Input
                    id={fieldIds.phone}
                    type="tel"
                    autoComplete="tel"
                    value={shippingData.phone}
                    onChange={(e) => setShippingData({ ...shippingData, phone: e.target.value })}
                    required
                  />
                </div>

                <div>
                  <label
                    htmlFor={fieldIds.address}
                    className="block text-sm font-semibold text-gray-900 dark:text-white mb-2"
                  >
                    Street Address *
                  </label>
                  <Input
                    id={fieldIds.address}
                    type="text"
                    autoComplete="street-address"
                    value={shippingData.address}
                    onChange={(e) => setShippingData({ ...shippingData, address: e.target.value })}
                    required
                  />
                </div>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div>
                    <label
                      htmlFor={fieldIds.city}
                      className="block text-sm font-semibold text-gray-900 dark:text-white mb-2"
                    >
                      City *
                    </label>
                    <Input
                      id={fieldIds.city}
                      type="text"
                      autoComplete="address-level2"
                      value={shippingData.city}
                      onChange={(e) => setShippingData({ ...shippingData, city: e.target.value })}
                      required
                    />
                  </div>
                  <div>
                    <label
                      htmlFor={fieldIds.state}
                      className="block text-sm font-semibold text-gray-900 dark:text-white mb-2"
                    >
                      State *
                    </label>
                    <Input
                      id={fieldIds.state}
                      type="text"
                      autoComplete="address-level1"
                      value={shippingData.state}
                      onChange={(e) => setShippingData({ ...shippingData, state: e.target.value })}
                      required
                    />
                  </div>
                  <div>
                    <label
                      htmlFor={fieldIds.zipCode}
                      className="block text-sm font-semibold text-gray-900 dark:text-white mb-2"
                    >
                      ZIP Code *
                    </label>
                    <Input
                      id={fieldIds.zipCode}
                      type="text"
                      autoComplete="postal-code"
                      value={shippingData.zipCode}
                      onChange={(e) => setShippingData({ ...shippingData, zipCode: e.target.value })}
                      required
                    />
                  </div>
                </div>

                <Checkbox
                  label="Save this address for future orders"
                  checked={shippingData.saveAddress}
                  onChange={(e) => setShippingData({ ...shippingData, saveAddress: e.target.checked })}
                />

                <Button
                  type="submit"
                  size="lg"
                  disabled={isPreparingCheckout || isCartLoading || isCartError}
                  aria-busy={isPreparingCheckout}
                  className="w-full bg-ocean-500 hover:bg-ocean-600 dark:bg-ocean-300 dark:hover:bg-ocean-400 text-white dark:text-gray-900"
                >
                  {isPreparingCheckout ? 'Preparing checkout…' : 'Continue to Payment'}
                </Button>
              </form>
            </Card>
          ) : null}

          {currentStep === 2 ? (
            <>
              <Card className="p-6">
                <div className="flex items-center gap-3 mb-6">
                  <FiTruck className="w-6 h-6 text-ocean-500 dark:text-ocean-300" />
                  <h3 className="text-xl font-bold text-gray-900 dark:text-white">
                    Shipping Method
                  </h3>
                </div>

                <div className="space-y-3">
                  <ShippingOption
                    id="standard"
                    title="Standard Shipping"
                    description="5-7 business days"
                    price={5.99}
                    selected={shippingMethod === 'standard'}
                    onSelect={() => setShippingMethod('standard')}
                  />
                  <ShippingOption
                    id="express"
                    title="Express Shipping"
                    description="2-3 business days"
                    price={15.99}
                    selected={shippingMethod === 'express'}
                    onSelect={() => setShippingMethod('express')}
                  />
                  <ShippingOption
                    id="overnight"
                    title="Overnight Shipping"
                    description="Next business day"
                    price={29.99}
                    selected={shippingMethod === 'overnight'}
                    onSelect={() => setShippingMethod('overnight')}
                    badge="Fastest"
                  />
                </div>
              </Card>

              <Card className="p-6">
                <div className="flex items-center gap-3 mb-6">
                  <div className="w-10 h-10 bg-ocean-500 dark:bg-ocean-300 rounded-full flex items-center justify-center text-white dark:text-gray-900 font-bold">
                    2
                  </div>
                  <h2 className="text-2xl font-bold text-gray-900 dark:text-white">
                    Payment Information
                  </h2>
                </div>

                {paymentError ? (
                  <div className="space-y-3 mb-4">
                    <p className="text-sm text-red-600 dark:text-red-400" role="alert" aria-live="assertive">
                      {paymentError}
                    </p>
                    {orderId && paymentIntentId ? (
                      <Button
                        type="button"
                        variant="outline"
                        onClick={() => finalizeConfirmedPayment(paymentIntentId)}
                        disabled={isFinalizingPayment}
                        aria-busy={isFinalizingPayment}
                      >
                        {isFinalizingPayment ? 'Retrying…' : 'Retry Finalization'}
                      </Button>
                    ) : null}
                  </div>
                ) : null}

                {stripePromise && clientSecret ? (
                  <Elements stripe={stripePromise} options={{ clientSecret }}>
                    <StripePaymentForm
                      onSuccess={finalizeConfirmedPayment}
                      onBack={() => setCurrentStep(1)}
                      isFinalizing={isFinalizingPayment}
                    />
                  </Elements>
                ) : (
                  <div className="space-y-4">
                    <p className="text-sm text-red-600 dark:text-red-400" role="alert" aria-live="assertive">
                      Payment intent is not available. Return to shipping and retry checkout setup.
                    </p>
                    <Button type="button" variant="outline" onClick={() => setCurrentStep(1)}>
                      Back to Shipping
                    </Button>
                  </div>
                )}
              </Card>
            </>
          ) : null}
        </div>

        <div className="lg:col-span-1">
          <Card className="p-6 sticky top-8">
            <h3 className="text-xl font-bold text-gray-900 dark:text-white mb-6">
              Order Summary
            </h3>

            <div className="space-y-4 mb-6">
              {summaryItems.map((item) => (
                <div key={item.productId} className="flex gap-3">
                  <div className="w-16 h-16 bg-gradient-to-br from-gray-100 to-gray-200 dark:from-gray-800 dark:to-gray-700 rounded-lg flex-shrink-0" />
                  <div className="flex-1">
                    <h4 className="font-medium text-gray-900 dark:text-white text-sm">
                      {item.productId}
                    </h4>
                    <p className="text-sm text-gray-600 dark:text-gray-400">
                      Qty: {item.quantity}
                    </p>
                    <p className="text-sm font-semibold text-ocean-500 dark:text-ocean-300">
                      ${(item.price * item.quantity).toFixed(2)}
                    </p>
                  </div>
                </div>
              ))}

              {summaryItems.length === 0 ? (
                <p className="text-sm text-gray-600 dark:text-gray-400">No items available for checkout.</p>
              ) : null}
            </div>

            <div className="space-y-3 pt-6 border-t border-gray-200 dark:border-gray-700">
              <div className="flex justify-between text-gray-600 dark:text-gray-400">
                <span>Subtotal</span>
                <span>${subtotal.toFixed(2)}</span>
              </div>
              <div className="flex justify-between text-gray-600 dark:text-gray-400">
                <span>Shipping</span>
                <span>${shippingCost.toFixed(2)}</span>
              </div>
              <div className="flex justify-between text-gray-600 dark:text-gray-400">
                <span>Tax</span>
                <span>${tax.toFixed(2)}</span>
              </div>
              <div className="flex justify-between text-xl font-bold text-gray-900 dark:text-white pt-3 border-t border-gray-200 dark:border-gray-700">
                <span>Total</span>
                <span>${total.toFixed(2)}</span>
              </div>
            </div>

            <div className="mt-6 p-4 bg-lime-50 dark:bg-lime-950 rounded-lg border border-lime-200 dark:border-lime-800">
              <div className="flex items-center gap-2 text-lime-700 dark:text-lime-300">
                <FiGift className="w-5 h-5" />
                <span className="text-sm font-semibold">Free gift with orders over $200!</span>
              </div>
            </div>

            <section
              className="mt-4 p-4 bg-gray-50 dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 space-y-3"
              aria-labelledby="checkout-inventory-signals-title"
              aria-busy={isInventoryHealthLoading || isInventoryHealthFetching || areReservationSignalsFetching}
            >
              <h4 id="checkout-inventory-signals-title" className="text-sm font-semibold text-gray-900 dark:text-white">
                Scenario 04 Signals
              </h4>

              {isInventoryHealthFetching || areReservationSignalsFetching ? (
                <p className="sr-only" role="status" aria-live="polite">
                  Refreshing inventory and reservation signals.
                </p>
              ) : null}

              {isInventoryHealthLoading ? (
                <p className="text-sm text-gray-600 dark:text-gray-400" role="status" aria-live="polite">
                  Checking inventory health signals…
                </p>
              ) : null}

              {isInventoryHealthError ? (
                <div className="space-y-2" role="alert" aria-live="assertive">
                  <p className="text-sm text-red-600 dark:text-red-400">
                    Inventory health signals are temporarily unavailable. Retry to refresh current stock risk.
                  </p>
                  <Button type="button" variant="outline" size="sm" onClick={retryInventoryHealth}>
                    Retry health check
                  </Button>
                </div>
              ) : null}

              {inventoryHealth ? (
                <div className="text-sm text-gray-700 dark:text-gray-300 space-y-1">
                  <p>Health: {inventoryHealth.healthy} healthy • {inventoryHealth.low_stock} low • {inventoryHealth.out_of_stock} out</p>
                  <p>Threshold breaches: {thresholdBreaches}</p>
                  <p>Replenishment triggers: {replenishmentTriggers}</p>
                </div>
              ) : null}

              {reservationSignalsError ? (
                <div className="space-y-2" role="alert" aria-live="assertive">
                  <p className="text-sm text-red-600 dark:text-red-400">
                    Reservation outcomes are temporarily unavailable. Retry to confirm hold status before payment.
                  </p>
                  <Button type="button" variant="outline" size="sm" onClick={retryReservationOutcomes}>
                    Retry reservation outcomes
                  </Button>
                </div>
              ) : null}

              <div className="text-sm text-gray-700 dark:text-gray-300 space-y-1" role="status" aria-live="polite">
                <p className="font-medium text-gray-900 dark:text-white">Reservation outcomes</p>
                {areReservationSignalsLoading ? (
                  <p>Checking reservation outcomes…</p>
                ) : reservationOutcomes.length > 0 ? (
                  reservationOutcomes.map((reservation) => (
                    <p key={reservation.id}>
                      {reservation.sku}: {reservation.status}
                    </p>
                  ))
                ) : (
                  <p>
                    {hasReservationQueries
                      ? 'Reservation outcomes are pending. Refresh if this takes longer than expected.'
                      : 'No reservation outcomes yet. Continue checkout to create item holds.'}
                  </p>
                )}
              </div>
            </section>
          </Card>
        </div>
      </div>
    </CheckoutLayout>
  );
}

function ShippingOption({ id, title, description, price, selected, onSelect, badge }: {
  id: string;
  title: string;
  description: string;
  price: number;
  selected: boolean;
  onSelect: () => void;
  badge?: string;
}) {
  const handleKeyDown = (event: React.KeyboardEvent<HTMLDivElement>) => {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault();
      onSelect();
    }
  };

  return (
    <div
      id={`shipping-option-${id}`}
      onClick={onSelect}
      onKeyDown={handleKeyDown}
      role="button"
      tabIndex={0}
      aria-pressed={selected}
      className={`p-4 border-2 rounded-lg cursor-pointer transition-colors ${
        selected
          ? 'border-ocean-500 bg-ocean-50 dark:border-ocean-300 dark:bg-ocean-950'
          : 'border-gray-200 dark:border-gray-700'
      } focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-ocean-500 dark:focus:ring-ocean-300`}
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Radio name="shipping" checked={selected} onChange={onSelect} />
          <div>
            <div className="flex items-center gap-2">
              <span className="font-semibold text-gray-900 dark:text-white">{title}</span>
              {badge && (
                <Badge className="bg-cyan-500 text-white text-xs">{badge}</Badge>
              )}
            </div>
            <p className="text-sm text-gray-600 dark:text-gray-400">{description}</p>
          </div>
        </div>
        <span className="font-bold text-ocean-500 dark:text-ocean-300">
          ${price.toFixed(2)}
        </span>
      </div>
    </div>
  );
}

