import React from 'react';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import CheckoutPage from '../../app/checkout/page';
import checkoutService from '../../lib/services/checkoutService';
import inventoryService from '../../lib/services/inventoryService';

const push = jest.fn();

jest.mock('next/navigation', () => ({
  useRouter: () => ({ push }),
}));

jest.mock('../../lib/hooks/useCart', () => ({
  useCart: () => ({
    data: {
      user_id: 'user-1',
      items: [
        {
          product_id: 'sku-1',
          quantity: 2,
          price: 10,
        },
      ],
      total: 20,
    },
    isLoading: false,
    isError: false,
  }),
}));

jest.mock('../../lib/hooks/useInventory', () => ({
  useInventoryHealth: () => ({
    data: {
      total_skus: 1,
      healthy: 1,
      low_stock: 0,
      out_of_stock: 0,
      items: [],
    },
    isLoading: false,
    isError: false,
  }),
  useReservationOutcomeQueries: () => [],
}));

jest.mock('../../lib/services/checkoutService', () => ({
  __esModule: true,
  default: {
    validate: jest.fn(),
    createOrder: jest.fn(),
    createPaymentIntent: jest.fn(),
    confirmPaymentIntent: jest.fn(),
  },
}));

jest.mock('../../lib/services/inventoryService', () => ({
  __esModule: true,
  default: {
    createReservation: jest.fn(),
    confirmReservation: jest.fn(),
    releaseReservation: jest.fn(),
  },
}));

function fillShippingForm(container: HTMLElement) {
  const inputs = container.querySelectorAll('input');
  const values = ['Ada', 'Lovelace', 'ada@example.com', '+5511999999999', '123 Main St', 'Sao Paulo', 'SP', '01000-000'];

  values.forEach((value, index) => {
    const input = inputs[index] as HTMLInputElement | undefined;
    if (input) {
      fireEvent.change(input, { target: { value } });
    }
  });
}

describe('CheckoutPage flow', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    (inventoryService.createReservation as jest.Mock).mockResolvedValue({
      id: 'res-1',
      sku: 'sku-1',
      quantity: 2,
      status: 'created',
      created_at: '2026-03-12T00:00:00Z',
      updated_at: '2026-03-12T00:00:00Z',
      created_by: 'user-1',
      updated_by: 'user-1',
      status_history: [],
      audit_log: [],
    });
    (inventoryService.confirmReservation as jest.Mock).mockResolvedValue({
      id: 'res-1',
      sku: 'sku-1',
      quantity: 2,
      status: 'confirmed',
      created_at: '2026-03-12T00:00:00Z',
      updated_at: '2026-03-12T00:00:00Z',
      created_by: 'user-1',
      updated_by: 'user-1',
      status_history: [],
      audit_log: [],
    });
  });

  it('runs checkout setup and finalizes to order route using real order id', async () => {
    (checkoutService.validate as jest.Mock).mockResolvedValue({
      valid: true,
      errors: [],
      warnings: [],
      estimated_total: 20,
      estimated_shipping: 0,
      estimated_tax: 0,
    });
    (checkoutService.createOrder as jest.Mock).mockResolvedValue({
      id: 'order-123',
      user_id: 'user-1',
      items: [{ product_id: 'sku-1', quantity: 2, price: 10 }],
      total: 20,
      status: 'pending',
      created_at: '2026-03-12T00:00:00Z',
    });
    (checkoutService.createPaymentIntent as jest.Mock).mockResolvedValue({
      client_secret: 'cs_test_123',
      payment_intent_id: 'pi_test_123',
      amount: 20,
      currency: 'usd',
      status: 'requires_payment_method',
    });
    (checkoutService.confirmPaymentIntent as jest.Mock).mockResolvedValue({
      id: 'pay-1',
      order_id: 'order-123',
      amount: 20,
      status: 'completed',
      transaction_id: 'pi_test_123',
      created_at: '2026-03-12T00:00:00Z',
    });

    const { container } = render(<CheckoutPage />);
    fillShippingForm(container);

    fireEvent.click(screen.getByRole('button', { name: 'Continue to Payment' }));

    await waitFor(() => {
      expect(checkoutService.validate).toHaveBeenCalledTimes(1);
      expect(inventoryService.createReservation).toHaveBeenCalledWith({
        sku: 'sku-1',
        quantity: 2,
        reason: 'checkout_hold',
      });
      expect(checkoutService.createOrder).toHaveBeenCalledTimes(1);
      expect(checkoutService.createPaymentIntent).toHaveBeenCalledWith({
        order_id: 'order-123',
        amount: 20,
        currency: 'usd',
      });
    });

    fireEvent.click(screen.getByRole('button', { name: 'Pay & Place Order' }));

    await waitFor(() => {
      expect(checkoutService.confirmPaymentIntent).toHaveBeenCalledWith({
        order_id: 'order-123',
        payment_intent_id: 'pi_test_123',
      });
      expect(inventoryService.confirmReservation).toHaveBeenCalledWith('res-1', {
        reason: 'payment_confirmed_for_order_order-123',
      });
      expect(push).toHaveBeenCalledWith('/order/order-123');
    });
  });

  it('shows recoverable payment finalization error and supports retry', async () => {
    (checkoutService.validate as jest.Mock).mockResolvedValue({
      valid: true,
      errors: [],
      warnings: [],
      estimated_total: 20,
      estimated_shipping: 0,
      estimated_tax: 0,
    });
    (checkoutService.createOrder as jest.Mock).mockResolvedValue({
      id: 'order-456',
      user_id: 'user-1',
      items: [{ product_id: 'sku-1', quantity: 2, price: 10 }],
      total: 20,
      status: 'pending',
      created_at: '2026-03-12T00:00:00Z',
    });
    (checkoutService.createPaymentIntent as jest.Mock).mockResolvedValue({
      client_secret: 'cs_test_456',
      payment_intent_id: 'pi_test_456',
      amount: 20,
      currency: 'usd',
      status: 'requires_payment_method',
    });
    (checkoutService.confirmPaymentIntent as jest.Mock)
      .mockRejectedValueOnce(new Error('temporary finalization failure'))
      .mockResolvedValueOnce({
        id: 'pay-2',
        order_id: 'order-456',
        amount: 20,
        status: 'completed',
        transaction_id: 'pi_test_456',
        created_at: '2026-03-12T00:00:00Z',
      });

    const { container } = render(<CheckoutPage />);
    fillShippingForm(container);

    fireEvent.click(screen.getByRole('button', { name: 'Continue to Payment' }));
    await screen.findByText('Payment Information');

    fireEvent.click(screen.getByRole('button', { name: 'Pay & Place Order' }));

    await screen.findByText('temporary finalization failure');
    fireEvent.click(screen.getByRole('button', { name: 'Retry Finalization' }));

    await waitFor(() => {
      expect(checkoutService.confirmPaymentIntent).toHaveBeenCalledTimes(2);
      expect(push).toHaveBeenCalledWith('/order/order-456');
    });
  });

  it('releases created reservations when setup fails before order creation', async () => {
    (checkoutService.validate as jest.Mock).mockResolvedValue({
      valid: true,
      errors: [],
      warnings: [],
      estimated_total: 20,
      estimated_shipping: 0,
      estimated_tax: 0,
    });
    (checkoutService.createOrder as jest.Mock).mockRejectedValue(new Error('order creation failed'));

    const { container } = render(<CheckoutPage />);
    fillShippingForm(container);

    fireEvent.click(screen.getByRole('button', { name: 'Continue to Payment' }));

    await screen.findByText('order creation failed');

    await waitFor(() => {
      expect(inventoryService.createReservation).toHaveBeenCalledWith({
        sku: 'sku-1',
        quantity: 2,
        reason: 'checkout_hold',
      });
      expect(inventoryService.releaseReservation).toHaveBeenCalledWith('res-1', {
        reason: 'checkout_setup_failed_before_order_creation_rollback',
      });
      expect(checkoutService.createPaymentIntent).not.toHaveBeenCalled();
    });
  });
});
