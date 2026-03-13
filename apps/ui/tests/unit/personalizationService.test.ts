import personalizationService from '../../lib/services/personalizationService';
import apiClient from '../../lib/api/client';

jest.mock('../../lib/api/client', () => ({
  __esModule: true,
  default: {
    get: jest.fn(),
    post: jest.fn(),
  },
  handleApiError: (error: unknown) => error,
}));

describe('personalizationService.runFlow', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('executes live endpoint pipeline in order and returns composed payload', async () => {
    (apiClient.get as jest.Mock)
      .mockResolvedValueOnce({
        data: {
          sku: 'SKU-100',
          name: 'Product SKU-100',
          description: 'desc',
          category_id: 'mock-category',
          price: 50,
          currency: 'usd',
          in_stock: true,
        },
      })
      .mockResolvedValueOnce({
        data: {
          customer_id: 'customer-100',
          email: 'customer@example.com',
          name: 'Customer',
          tier: 'silver',
        },
      });

    (apiClient.post as jest.Mock)
      .mockResolvedValueOnce({
        data: {
          customer_id: 'customer-100',
          sku: 'SKU-100',
          quantity: 2,
          currency: 'usd',
          base_price: 100,
          offers: [{ code: 'bulk-5', title: 'Bulk', amount: 5, offer_type: 'bulk', source: 'rule' }],
          final_price: 95,
        },
      })
      .mockResolvedValueOnce({
        data: {
          customer_id: 'customer-100',
          ranked: [{ sku: 'SKU-100', score: 0.53, reason_codes: ['input_score'] }],
        },
      })
      .mockResolvedValueOnce({
        data: {
          customer_id: 'customer-100',
          headline: 'Top picks for customer-100',
          recommendations: [
            {
              sku: 'SKU-100',
              title: 'Product SKU-100',
              score: 0.53,
              message: 'Recommended',
            },
          ],
        },
      });

    const result = await personalizationService.runFlow({
      customerId: 'customer-100',
      sku: 'SKU-100',
      quantity: 2,
      maxItems: 3,
    });

    expect(apiClient.get).toHaveBeenNthCalledWith(1, '/api/catalog/products/SKU-100');
    expect(apiClient.get).toHaveBeenNthCalledWith(2, '/api/customers/customer-100/profile');
    expect(apiClient.post).toHaveBeenNthCalledWith(
      1,
      '/api/pricing/offers',
      expect.objectContaining({ customer_id: 'customer-100', sku: 'SKU-100', quantity: 2 }),
    );
    expect(apiClient.post).toHaveBeenNthCalledWith(
      2,
      '/api/recommendations/rank',
      expect.objectContaining({ customer_id: 'customer-100' }),
    );
    expect(apiClient.post).toHaveBeenNthCalledWith(
      3,
      '/api/recommendations/compose',
      expect.objectContaining({ customer_id: 'customer-100', max_items: 3 }),
    );

    expect(result.composed.recommendations[0].sku).toBe('SKU-100');
  });
});
