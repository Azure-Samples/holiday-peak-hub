/**
 * CheckoutForm Organism Component
 * Multi-step checkout process with validation
 */

import React from 'react';
import { FiCheck, FiLock, FiTruck, FiCreditCard } from 'react-icons/fi';
import { cn, formatCurrency } from '../utils';
import { Button } from '../atoms/Button';
import { Badge } from '../atoms/Badge';
import { Divider } from '../atoms/Divider';
import { Text } from '../atoms/Text';
import { Input } from '../atoms/Input';
import { Select } from '../atoms/Select';
import { Checkbox } from '../atoms/Checkbox';
import { FormField } from '../molecules/FormField';
import { Alert } from '../molecules/Alert';
import type {
  ShippingAddress,
  PaymentMethod,
  OrderSummary,
  BaseComponentProps,
} from '../types';

export interface CheckoutStep {
  id: string;
  label: string;
  icon: React.ReactNode;
  completed: boolean;
}

export interface CheckoutFormProps extends BaseComponentProps {
  /** Current step (0-based index) */
  currentStep: number;
  /** Checkout steps */
  steps?: CheckoutStep[];
  /** Shipping address */
  shippingAddress?: ShippingAddress;
  /** Billing address (if different from shipping) */
  billingAddress?: ShippingAddress;
  /** Payment method */
  paymentMethod?: PaymentMethod;
  /** Order summary */
  orderSummary: OrderSummary;
  /** Step navigation handler */
  onStepChange?: (step: number) => void;
  /** Shipping address submit handler */
  onShippingSubmit?: (address: ShippingAddress) => void;
  /** Payment submit handler */
  onPaymentSubmit?: (payment: PaymentMethod) => void;
  /** Place order handler */
  onPlaceOrder?: () => void;
  /** Form validation errors */
  errors?: Record<string, string>;
  /** Loading state */
  loading?: boolean;
  /** Whether billing address is same as shipping */
  billingIsSameAsShipping?: boolean;
  /** Toggle billing address */
  onToggleBillingAddress?: (isSame: boolean) => void;
}

const defaultSteps: CheckoutStep[] = [
  { id: 'shipping', label: 'Shipping', icon: <FiTruck className="w-5 h-5" />, completed: false },
  { id: 'payment', label: 'Payment', icon: <FiCreditCard className="w-5 h-5" />, completed: false },
  { id: 'review', label: 'Review', icon: <FiCheck className="w-5 h-5" />, completed: false },
];

export const CheckoutForm: React.FC<CheckoutFormProps> = ({
  currentStep = 0,
  steps = defaultSteps,
  shippingAddress,
  billingAddress,
  paymentMethod,
  orderSummary,
  onStepChange,
  onShippingSubmit,
  onPaymentSubmit,
  onPlaceOrder,
  errors = {},
  loading = false,
  billingIsSameAsShipping = true,
  onToggleBillingAddress,
  className,
  testId,
  ariaLabel,
}) => {
  const [formData, setFormData] = React.useState({
    // Shipping
    email: shippingAddress?.email || '',
    firstName: shippingAddress?.firstName || '',
    lastName: shippingAddress?.lastName || '',
    address: shippingAddress?.address || '',
    city: shippingAddress?.city || '',
    state: shippingAddress?.state || '',
    zipCode: shippingAddress?.zipCode || '',
    country: shippingAddress?.country || 'US',
    phone: shippingAddress?.phone || '',
    // Payment
    cardNumber: '',
    cardName: '',
    cardExpiry: '',
    cardCvc: '',
  });

  const updateField = (field: string, value: string) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
  };

  const handleShippingNext = () => {
    const address: ShippingAddress = {
      email: formData.email,
      firstName: formData.firstName,
      lastName: formData.lastName,
      address: formData.address,
      city: formData.city,
      state: formData.state,
      zipCode: formData.zipCode,
      country: formData.country,
      phone: formData.phone,
    };
    onShippingSubmit?.(address);
    onStepChange?.(currentStep + 1);
  };

  const handlePaymentNext = () => {
    const payment: PaymentMethod = {
      type: 'card',
      cardNumber: formData.cardNumber,
      cardName: formData.cardName,
      cardExpiry: formData.cardExpiry,
      cardCvc: formData.cardCvc,
    };
    onPaymentSubmit?.(payment);
    onStepChange?.(currentStep + 1);
  };

  return (
    <div
      data-testid={testId}
      aria-label={ariaLabel || 'Checkout form'}
      className={cn('w-full', className)}
    >
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Checkout Form */}
        <div className="lg:col-span-2 space-y-6">
          {/* Step Indicator */}
          <div className="flex items-center justify-between">
            {steps.map((step, index) => (
              <React.Fragment key={step.id}>
                <div className="flex flex-col items-center flex-1">
                  <button
                    onClick={() => index < currentStep && onStepChange?.(index)}
                    disabled={index > currentStep}
                    className={cn(
                      'w-12 h-12 rounded-full flex items-center justify-center transition-colors',
                      index < currentStep &&
                        'bg-green-500 text-white cursor-pointer hover:bg-green-600',
                      index === currentStep &&
                        'bg-blue-500 text-white',
                      index > currentStep &&
                        'bg-gray-200 dark:bg-gray-700 text-gray-400 cursor-not-allowed'
                    )}
                  >
                    {index < currentStep ? (
                      <FiCheck className="w-6 h-6" />
                    ) : (
                      step.icon
                    )}
                  </button>
                  <Text variant="caption" className="mt-2 text-center">
                    {step.label}
                  </Text>
                </div>
                {index < steps.length - 1 && (
                  <div className="flex-1 h-0.5 bg-gray-200 dark:bg-gray-700 mx-2 -mt-6" />
                )}
              </React.Fragment>
            ))}
          </div>

          {/* Step Content */}
          <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-6">
            {/* Step 1: Shipping */}
            {currentStep === 0 && (
              <div className="space-y-4">
                <Text variant="h3">Shipping Information</Text>

                <FormField label="Email" required error={errors.email}>
                  <Input
                    type="email"
                    value={formData.email}
                    onChange={(e) => updateField('email', e.target.value)}
                    placeholder="john@example.com"
                  />
                </FormField>

                <div className="grid grid-cols-2 gap-4">
                  <FormField label="First Name" required error={errors.firstName}>
                    <Input
                      value={formData.firstName}
                      onChange={(e) => updateField('firstName', e.target.value)}
                      placeholder="John"
                    />
                  </FormField>

                  <FormField label="Last Name" required error={errors.lastName}>
                    <Input
                      value={formData.lastName}
                      onChange={(e) => updateField('lastName', e.target.value)}
                      placeholder="Doe"
                    />
                  </FormField>
                </div>

                <FormField label="Address" required error={errors.address}>
                  <Input
                    value={formData.address}
                    onChange={(e) => updateField('address', e.target.value)}
                    placeholder="123 Main St"
                  />
                </FormField>

                <div className="grid grid-cols-3 gap-4">
                  <FormField label="City" required error={errors.city}>
                    <Input
                      value={formData.city}
                      onChange={(e) => updateField('city', e.target.value)}
                      placeholder="New York"
                    />
                  </FormField>

                  <FormField label="State" required error={errors.state}>
                    <Input
                      value={formData.state}
                      onChange={(e) => updateField('state', e.target.value)}
                      placeholder="NY"
                    />
                  </FormField>

                  <FormField label="ZIP Code" required error={errors.zipCode}>
                    <Input
                      value={formData.zipCode}
                      onChange={(e) => updateField('zipCode', e.target.value)}
                      placeholder="10001"
                    />
                  </FormField>
                </div>

                <FormField label="Phone" required error={errors.phone}>
                  <Input
                    type="tel"
                    value={formData.phone}
                    onChange={(e) => updateField('phone', e.target.value)}
                    placeholder="(555) 123-4567"
                  />
                </FormField>

                <Button
                  variant="primary"
                  size="lg"
                  onClick={handleShippingNext}
                  fullWidth
                >
                  Continue to Payment
                </Button>
              </div>
            )}

            {/* Step 2: Payment */}
            {currentStep === 1 && (
              <div className="space-y-4">
                <Text variant="h3">Payment Information</Text>

                <Alert variant="info" borderLeft>
                  <FiLock className="inline mr-2" />
                  Your payment information is secure and encrypted
                </Alert>

                <FormField label="Card Number" required error={errors.cardNumber}>
                  <Input
                    value={formData.cardNumber}
                    onChange={(e) => updateField('cardNumber', e.target.value)}
                    placeholder="1234 5678 9012 3456"
                    maxLength={19}
                  />
                </FormField>

                <FormField label="Name on Card" required error={errors.cardName}>
                  <Input
                    value={formData.cardName}
                    onChange={(e) => updateField('cardName', e.target.value)}
                    placeholder="John Doe"
                  />
                </FormField>

                <div className="grid grid-cols-2 gap-4">
                  <FormField label="Expiration" required error={errors.cardExpiry}>
                    <Input
                      value={formData.cardExpiry}
                      onChange={(e) => updateField('cardExpiry', e.target.value)}
                      placeholder="MM/YY"
                      maxLength={5}
                    />
                  </FormField>

                  <FormField label="CVC" required error={errors.cardCvc}>
                    <Input
                      value={formData.cardCvc}
                      onChange={(e) => updateField('cardCvc', e.target.value)}
                      placeholder="123"
                      maxLength={4}
                    />
                  </FormField>
                </div>

                <Divider spacing="md" />

                <Checkbox
                  label="Billing address is same as shipping"
                  checked={billingIsSameAsShipping}
                  onChange={(e) => onToggleBillingAddress?.(e.target.checked)}
                />

                <div className="flex gap-3">
                  <Button
                    variant="secondary"
                    onClick={() => onStepChange?.(currentStep - 1)}
                  >
                    Back
                  </Button>
                  <Button
                    variant="primary"
                    size="lg"
                    onClick={handlePaymentNext}
                    fullWidth
                  >
                    Review Order
                  </Button>
                </div>
              </div>
            )}

            {/* Step 3: Review */}
            {currentStep === 2 && (
              <div className="space-y-6">
                <Text variant="h3">Review Your Order</Text>

                {/* Shipping Info */}
                <div>
                  <Text variant="h4" className="mb-2">Shipping Address</Text>
                  <div className="text-sm text-gray-600 dark:text-gray-400">
                    <p>{formData.firstName} {formData.lastName}</p>
                    <p>{formData.address}</p>
                    <p>{formData.city}, {formData.state} {formData.zipCode}</p>
                    <p>{formData.phone}</p>
                  </div>
                </div>

                <Divider spacing="sm" />

                {/* Payment Info */}
                <div>
                  <Text variant="h4" className="mb-2">Payment Method</Text>
                  <div className="text-sm text-gray-600 dark:text-gray-400">
                    <p>Card ending in {formData.cardNumber.slice(-4)}</p>
                    <p>{formData.cardName}</p>
                  </div>
                </div>

                <Divider spacing="sm" />

                <Alert variant="info">
                  By placing this order, you agree to our Terms of Service and Privacy Policy
                </Alert>

                <div className="flex gap-3">
                  <Button
                    variant="secondary"
                    onClick={() => onStepChange?.(currentStep - 1)}
                  >
                    Back
                  </Button>
                  <Button
                    variant="primary"
                    size="lg"
                    onClick={onPlaceOrder}
                    loading={loading}
                    fullWidth
                  >
                    Place Order
                  </Button>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Order Summary Sidebar */}
        <div className="lg:col-span-1">
          <div className="sticky top-4 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg p-6 space-y-4">
            <Text variant="h4">Order Summary</Text>

            <Divider spacing="sm" />

            <div className="space-y-3">
              <div className="flex justify-between text-sm">
                <span className="text-gray-600 dark:text-gray-400">Subtotal</span>
                <span>{formatCurrency(orderSummary.subtotal, orderSummary.currency)}</span>
              </div>

              <div className="flex justify-between text-sm">
                <span className="text-gray-600 dark:text-gray-400">Shipping</span>
                <span>
                  {orderSummary.shipping === 0
                    ? 'Free'
                    : formatCurrency(orderSummary.shipping, orderSummary.currency)}
                </span>
              </div>

              <div className="flex justify-between text-sm">
                <span className="text-gray-600 dark:text-gray-400">Tax</span>
                <span>{formatCurrency(orderSummary.tax, orderSummary.currency)}</span>
              </div>

              {orderSummary.discount > 0 && (
                <div className="flex justify-between text-sm text-green-600 dark:text-green-400">
                  <span>Discount</span>
                  <span>-{formatCurrency(orderSummary.discount, orderSummary.currency)}</span>
                </div>
              )}
            </div>

            <Divider spacing="sm" />

            <div className="flex justify-between items-baseline">
              <Text variant="h4">Total</Text>
              <Text variant="h3">
                {formatCurrency(orderSummary.total, orderSummary.currency)}
              </Text>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

CheckoutForm.displayName = 'CheckoutForm';
