import apiClient from '../../lib/api/client';
import agentApiClient from '../../lib/api/agentClient';
import { recordAgentInvocationTelemetry } from '../../lib/hooks/useAgentInvocationTelemetry';
import { productService } from '../../lib/services/productService';

jest.mock('../../lib/api/client', () => ({
  __esModule: true,
  default: {
    get: jest.fn(),
    post: jest.fn(),
  },
  handleApiError: (error: unknown) => error,
}));

jest.mock('../../lib/api/agentClient', () => ({
  __esModule: true,
  default: {
    post: jest.fn(),
  },
}));

jest.mock('../../lib/hooks/useAgentInvocationTelemetry', () => ({
  recordAgentInvocationTelemetry: jest.fn(),
}));

describe('productService.getEnriched', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('records backend telemetry for enrichment-backed product loads', async () => {
    (apiClient.get as jest.Mock).mockResolvedValue({
      data: {
        id: 'sku-1',
        name: 'Trail Backpack',
        description: 'Base product description',
        price: 129.99,
        category_id: 'packs',
        image_url: '/images/products/p1.jpg',
        in_stock: true,
      },
    });

    (agentApiClient.post as jest.Mock).mockResolvedValue({
      data: {
        enriched_product: {
          title: 'Trail Backpack',
          description: 'Agent summary for the product page',
          enriched_description: 'Expanded detail from the enrichment agent',
          rating: 4.8,
        },
        _telemetry: {
          model_tier: 'slm',
          total_tokens: 144,
          latency_ms: 612,
        },
      },
    });

    const product = await productService.getEnriched('sku-1');

    expect(agentApiClient.post).toHaveBeenCalledWith('/ecommerce-product-detail-enrichment/invoke', {
      sku: 'sku-1',
    });
    expect(recordAgentInvocationTelemetry).toHaveBeenCalledWith(
      'ecommerce-product-detail-enrichment',
      expect.objectContaining({
        _telemetry: expect.objectContaining({
          model_tier: 'slm',
          total_tokens: 144,
        }),
      }),
    );
    expect(product).toMatchObject({
      id: 'sku-1',
      name: 'Trail Backpack',
      description: 'Agent summary for the product page',
      enriched_description: 'Expanded detail from the enrichment agent',
      rating: 4.8,
    });
  });
});