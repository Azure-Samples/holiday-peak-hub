import semanticSearchService from '../../lib/services/semanticSearchService';
import agentApiClient from '../../lib/api/agentClient';
import { productService } from '../../lib/services/productService';

jest.mock('../../lib/api/agentClient', () => ({
  __esModule: true,
  default: {
    post: jest.fn(),
  },
}));

jest.mock('../../lib/services/productService', () => ({
  productService: {
    search: jest.fn(),
  },
}));

describe('semanticSearchService.searchWithMode', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    (productService.search as jest.Mock).mockResolvedValue([]);
  });

  it('forwards optional context fields in the request payload', async () => {
    (agentApiClient.post as jest.Mock).mockResolvedValue({
      data: {
        items: [],
        mode: 'intelligent',
      },
    });

    await semanticSearchService.searchWithMode('running shoes', 'intelligent', 12, {
      user_id: 'user-123',
      tenant_id: 'tenant-456',
      session_id: 'session-789',
      query_history: ['boots', 'trail shoes'],
      search_stage: 'rerank',
      baseline_candidate_skus: ['SKU-1', 'SKU-2'],
      correlation_id: 'corr-abc',
    });

    expect(agentApiClient.post).toHaveBeenCalledWith(
      '/ecommerce-catalog-search/invoke',
      expect.objectContaining({
        query: 'running shoes',
        limit: 12,
        mode: 'intelligent',
        user_id: 'user-123',
        tenant_id: 'tenant-456',
        session_id: 'session-789',
        query_history: ['boots', 'trail shoes'],
        search_stage: 'rerank',
        baseline_candidate_skus: ['SKU-1', 'SKU-2'],
        correlation_id: 'corr-abc',
      }),
    );
  });

  it('falls back to CRUD when agent payload uses example.com host content', async () => {
    (agentApiClient.post as jest.Mock).mockResolvedValue({
      data: {
        items: [
          {
            item_id: 'SKU-1',
            title: 'Trail runner',
            image_url: 'https://example.com/mock.jpg',
          },
        ],
        mode: 'intelligent',
      },
    });

    const result = await semanticSearchService.searchWithMode('running shoes', 'intelligent', 20);

    expect(productService.search).toHaveBeenCalledWith('running shoes', 20);
    expect(result.source).toBe('crud');
    expect(result.fallback_reason).toBe('agent_mock');
  });

  it('does not treat example.com in path/query text as a mock host', async () => {
    (agentApiClient.post as jest.Mock).mockResolvedValue({
      data: {
        items: [
          {
            item_id: 'SKU-2',
            title: 'Trail runner pro',
            image_url: 'https://cdn.contoso.com/assets/example.com/banner.jpg',
            url: 'https://shop.contoso.com/product/sku-2?ref=example.com',
          },
        ],
        mode: 'intelligent',
      },
    });

    const result = await semanticSearchService.searchWithMode('running shoes', 'intelligent', 20);

    expect(result.source).toBe('agent');
    expect(result.items[0].sku).toBe('SKU-2');
    expect(productService.search).not.toHaveBeenCalled();
  });

  it('maps degraded fallback metadata from agent responses', async () => {
    (agentApiClient.post as jest.Mock).mockResolvedValue({
      data: {
        results: [
          {
            item_id: 'SKU-9',
            title: 'Winter Shell Jacket',
          },
        ],
        mode: 'intelligent',
        answer_source: 'agent_fallback',
        result_type: 'degraded_fallback',
        degraded: true,
        degraded_reason: 'model_timeout',
        degraded_message:
          'Showing the best available catalog guidance while intelligent generation is temporarily unavailable.',
        fallback_keywords: ['winter', 'jacket'],
      },
    });

    const result = await semanticSearchService.searchWithMode('winter jacket', 'intelligent', 20);

    expect(result.source).toBe('agent');
    expect(result.answer_source).toBe('agent_fallback');
    expect(result.result_type).toBe('degraded_fallback');
    expect(result.degraded).toBe(true);
    expect(result.degraded_reason).toBe('model_timeout');
    expect(result.fallback_keywords).toEqual(['winter', 'jacket']);
    expect(productService.search).not.toHaveBeenCalled();
  });
});
