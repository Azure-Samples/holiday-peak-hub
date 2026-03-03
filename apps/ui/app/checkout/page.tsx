'use client';

import React, { useCallback, useEffect, useState } from 'react';
import { Elements, PaymentElement, useElements, useStripe } from '@stripe/react-stripe-js';
import { loadStripe } from '@stripe/stripe-js';
import { CheckoutLayout } from '@/components/templates/CheckoutLayout';
import { Card } from '@/components/molecules/Card';
import { Button } from '@/components/atoms/Button';
import { Input } from '@/components/atoms/Input';
import { Checkbox } from '@/components/atoms/Checkbox';
import { Radio } from '@/components/atoms/Radio';
import { Badge } from '@/components/atoms/Badge';
import { FiGift, FiLock, FiTruck } from 'react-icons/fi';
import checkoutService from '@/lib/services/checkoutService';

const stripePromise = process.env.NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY
  ? loadStripe(process.env.NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY)
  : null;

// Mock order id used until real order creation is wired up
const DEMO_ORDER_ID = 'demo-order-id';

// ─── Stripe Payment Form ──────────────────────────────────────────────────────

interface StripePaymentFormProps {
  onSuccess: () => void;
  onBack: () => void;
}

function StripePaymentForm({ onSuccess, onBack }: StripePaymentFormProps) {
  const stripe = useStripe();
  const elements = useElements();
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!stripe || !elements) return;

    setIsSubmitting(true);
    setErrorMessage(null);

    const { error } = await stripe.confirmPayment({
      elements,
      confirmParams: {
        return_url: `${window.location.origin}/orders`,
      },
      redirect: 'if_required',
    });

    if (error) {
      setErrorMessage(error.message ?? 'Payment failed. Please try again.');
      setIsSubmitting(false);
    } else {
      onSuccess();
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      <PaymentElement />

      {errorMessage && (
        <p className="text-sm text-red-600 dark:text-red-400">{errorMessage}</p>
      )}

      <div className="flex gap-4">
        <Button type="button" variant="ghost" onClick={onBack} className="flex-1">
          Back
        </Button>
        <Button
          type="submit"
          size="lg"
          disabled={!stripe || isSubmitting}
          className="flex-1 bg-ocean-500 hover:bg-ocean-600 dark:bg-ocean-300 dark:hover:bg-ocean-400 text-white dark:text-gray-900"
        >
          {isSubmitting ? 'Processing…' : 'Review Order'}
        </Button>
      </div>
    </form>
  );
}

// ─── Main Checkout Page ───────────────────────────────────────────────────────

export default function CheckoutPage() {
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
  const [clientSecret, setClientSecret] = useState<string | null>(null);
  const [intentError, setIntentError] = useState<string | null>(null);

  // Mock cart data – replaced by the cart hook once issue #28 is addressed
  const cartItems = [
    { id: 1, name: 'Wireless Headphones', price: 199.99, quantity: 1, image: '/placeholder.jpg' },
    { id: 2, name: 'Phone Case', price: 29.99, quantity: 2, image: '/placeholder.jpg' },
  ];

  const subtotal = cartItems.reduce((sum, item) => sum + item.price * item.quantity, 0);
  const shippingCost =
    shippingMethod === 'express' ? 15.99 : shippingMethod === 'overnight' ? 29.99 : 5.99;
  const tax = subtotal * 0.08;
  const total = subtotal + shippingCost + tax;

  // Create a PaymentIntent when moving to Step 2
  const createIntent = useCallback(async () => {
    if (!stripePromise) {
      // Stripe not configured – skip (demo/dev mode)
      return;
    }
    try {
      const intent = await checkoutService.createPaymentIntent({
        order_id: DEMO_ORDER_ID,
        amount: total,
        currency: 'usd',
      });
      setClientSecret(intent.client_secret);
    } catch {
      setIntentError('Unable to initialise payment. Please try again.');
    }
  }, [total]);

  const handleShippingSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    await createIntent();
    setCurrentStep(2);
  };

  const handlePlaceOrder = () => {
    // Will be replaced with real order-placement call
    console.log('Order placed');
  };

  // Re-create intent if shipping method changes while on step 2
  useEffect(() => {
    if (currentStep === 2) {
      createIntent();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [shippingMethod]);

  return (
    <CheckoutLayout currentStep={currentStep}>
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Main Content */}
        <div className="lg:col-span-2 space-y-6">
          {/* Step 1: Shipping Information */}
          {currentStep === 1 && (
            <Card className="p-6">
              <div className="flex items-center gap-3 mb-6">
                <div className="w-10 h-10 bg-ocean-500 dark:bg-ocean-300 rounded-full flex items-center justify-center text-white dark:text-gray-900 font-bold">
                  1
                </div>
                <h2 className="text-2xl font-bold text-gray-900 dark:text-white">
                  Shipping Information
                </h2>
              </div>

              <form onSubmit={handleShippingSubmit} className="space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-semibold text-gray-900 dark:text-white mb-2">
                      First Name *
                    </label>
                    <Input
                      type="text"
                      value={shippingData.firstName}
                      onChange={(e) => setShippingData({ ...shippingData, firstName: e.target.value })}
                      required
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-semibold text-gray-900 dark:text-white mb-2">
                      Last Name *
                    </label>
                    <Input
                      type="text"
                      value={shippingData.lastName}
                      onChange={(e) => setShippingData({ ...shippingData, lastName: e.target.value })}
                      required
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-semibold text-gray-900 dark:text-white mb-2">
                    Email Address *
                  </label>
                  <Input
                    type="email"
                    value={shippingData.email}
                    onChange={(e) => setShippingData({ ...shippingData, email: e.target.value })}
                    required
                  />
                </div>

                <div>
                  <label className="block text-sm font-semibold text-gray-900 dark:text-white mb-2">
                    Phone Number *
                  </label>
                  <Input
                    type="tel"
                    value={shippingData.phone}
                    onChange={(e) => setShippingData({ ...shippingData, phone: e.target.value })}
                    required
                  />
                </div>

                <div>
                  <label className="block text-sm font-semibold text-gray-900 dark:text-white mb-2">
                    Street Address *
                  </label>
                  <Input
                    type="text"
                    value={shippingData.address}
                    onChange={(e) => setShippingData({ ...shippingData, address: e.target.value })}
                    required
                  />
                </div>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div>
                    <label className="block text-sm font-semibold text-gray-900 dark:text-white mb-2">
                      City *
                    </label>
                    <Input
                      type="text"
                      value={shippingData.city}
                      onChange={(e) => setShippingData({ ...shippingData, city: e.target.value })}
                      required
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-semibold text-gray-900 dark:text-white mb-2">
                      State *
                    </label>
                    <Input
                      type="text"
                      value={shippingData.state}
                      onChange={(e) => setShippingData({ ...shippingData, state: e.target.value })}
                      required
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-semibold text-gray-900 dark:text-white mb-2">
                      ZIP Code *
                    </label>
                    <Input
                      type="text"
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
                  className="w-full bg-ocean-500 hover:bg-ocean-600 dark:bg-ocean-300 dark:hover:bg-ocean-400 text-white dark:text-gray-900"
                >
                  Continue to Payment
                </Button>
              </form>
            </Card>
          )}

          {/* Step 2: Shipping Method + Payment */}
          {currentStep === 2 && (
            <>
              {/* Shipping Method */}
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

              {/* Payment Method */}
              <Card className="p-6">
                <div className="flex items-center gap-3 mb-6">
                  <div className="w-10 h-10 bg-ocean-500 dark:bg-ocean-300 rounded-full flex items-center justify-center text-white dark:text-gray-900 font-bold">
                    2
                  </div>
                  <h2 className="text-2xl font-bold text-gray-900 dark:text-white">
                    Payment Information
                  </h2>
                </div>

                {intentError && (
                  <p className="text-sm text-red-600 dark:text-red-400 mb-4">{intentError}</p>
                )}

                {stripePromise && clientSecret ? (
                  <Elements stripe={stripePromise} options={{ clientSecret }}>
                    <StripePaymentForm
                      onSuccess={() => setCurrentStep(3)}
                      onBack={() => setCurrentStep(1)}
                    />
                  </Elements>
                ) : (
                  /* Fallback: Stripe not configured (demo / local dev without keys) */
                  <div className="space-y-6">
                    <p className="text-sm text-amber-600 dark:text-amber-400">
                      Payment provider is not configured. Using demo mode.
                    </p>
                    <div className="flex gap-4">
                      <Button
                        type="button"
                        variant="ghost"
                        className="flex-1"
                      >
                        Back
                      </Button>
                      <Button
                        type="button"
                        size="lg"
                        onClick={() => setCurrentStep(3)}
                        className="flex-1 bg-ocean-500 hover:bg-ocean-600 dark:bg-ocean-300 dark:hover:bg-ocean-400 text-white dark:text-gray-900"
                      >
                        Review Order
                      </Button>
                    </div>
                  </div>
                )}
              </Card>
            </>
          )}

          {/* Step 3: Review Order */}
          {currentStep === 3 && (
            <Card className="p-6">
              <div className="flex items-center gap-3 mb-6">
                <div className="w-10 h-10 bg-ocean-500 dark:bg-ocean-300 rounded-full flex items-center justify-center text-white dark:text-gray-900 font-bold">
                  3
                </div>
                <h2 className="text-2xl font-bold text-gray-900 dark:text-white">
                  Review Your Order
                </h2>
              </div>

              <div className="space-y-6">
                <div>
                  <h3 className="font-semibold text-gray-900 dark:text-white mb-3">Shipping Address</h3>
                  <div className="text-gray-600 dark:text-gray-400">
                    <p>{shippingData.firstName} {shippingData.lastName}</p>
                    <p>{shippingData.address}</p>
                    <p>{shippingData.city}, {shippingData.state} {shippingData.zipCode}</p>
                    <p>{shippingData.phone}</p>
                  </div>
                </div>

                <div>
                  <h3 className="font-semibold text-gray-900 dark:text-white mb-3">Shipping Method</h3>
                  <p className="text-gray-600 dark:text-gray-400">
                    {shippingMethod === 'standard' ? 'Standard Shipping (5-7 days)' :
                     shippingMethod === 'express' ? 'Express Shipping (2-3 days)' :
                     'Overnight Shipping (Next day)'}
                  </p>
                </div>

                <div className="flex gap-4 pt-6">
                  <Button
                    variant="outline"
                    onClick={() => setCurrentStep(2)}
                    className="flex-1"
                  >
                    Back
                  </Button>
                  <Button
                    size="lg"
                    onClick={handlePlaceOrder}
                    className="flex-1 bg-lime-500 hover:bg-lime-600 dark:bg-lime-400 dark:hover:bg-lime-500 text-white dark:text-gray-900"
                  >
                    <FiLock className="mr-2" />
                    Place Order
                  </Button>
                </div>
              </div>
            </Card>
          )}
        </div>

        {/* Order Summary Sidebar */}
        <div className="lg:col-span-1">
          <Card className="p-6 sticky top-8">
            <h3 className="text-xl font-bold text-gray-900 dark:text-white mb-6">
              Order Summary
            </h3>

            <div className="space-y-4 mb-6">
              {cartItems.map((item) => (
                <div key={item.id} className="flex gap-3">
                  <div className="w-16 h-16 bg-gradient-to-br from-gray-100 to-gray-200 dark:from-gray-800 dark:to-gray-700 rounded-lg flex-shrink-0" />
                  <div className="flex-1">
                    <h4 className="font-medium text-gray-900 dark:text-white text-sm">
                      {item.name}
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
  return (
    <div
      onClick={onSelect}
      className={`p-4 border-2 rounded-lg cursor-pointer transition-colors ${
        selected
          ? 'border-ocean-500 bg-ocean-50 dark:border-ocean-300 dark:bg-ocean-950'
          : 'border-gray-200 dark:border-gray-700'
      }`}
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

