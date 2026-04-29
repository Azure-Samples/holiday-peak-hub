import semanticSearchService from '../../lib/services/semanticSearchService';
import agentApiClient from '../../lib/api/agentClient';
import { recordAgentInvocationTelemetry } from '../../lib/hooks/useAgentInvocationTelemetry';
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

jest.mock('../../lib/hooks/useAgentInvocationTelemetry', () => ({
  recordAgentInvocationTelemetry: jest.fn(),
}));

describe('semanticSearchService.searchWithMode', () => {
  let consoleErrorSpy: jest.SpyInstance;

  beforeEach(() => {
    jest.clearAllMocks();
    consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation(() => {});
    (productService.search as jest.Mock).mockResolvedValue([]);
  });

  afterEach(() => {
    consoleErrorSpy.mockRestore();
  });

  it('records backend telemetry for agent-backed results', async () => {
    (agentApiClient.post as jest.Mock).mockResolvedValue({
      data: {
        items: [],
        mode: 'intelligent',
        _telemetry: {
          model_tier: 'slm',
          total_tokens: 321,
          cost_usd: 0.012,
          latency_ms: 845,
        },
      },
    });

    await semanticSearchService.searchWithMode('running shoes', 'intelligent', 20);

    expect(recordAgentInvocationTelemetry).toHaveBeenCalledWith(
      'ecommerce-catalog-search',
      expect.objectContaining({
        _telemetry: expect.objectContaining({
          model_tier: 'slm',
          total_tokens: 321,
        }),
      }),
    );
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

  it('accepts example.com placeholder URLs as valid agent results', async () => {
    (agentApiClient.post as jest.Mock).mockResolvedValue({
      data: {
        items: [
          {
            item_id: 'SKU-1',
            title: 'Trail runner',
            image_url: 'https://example.com/mock.jpg',
            url: 'https://example.com/products/SKU-1',
          },
        ],
        mode: 'intelligent',
      },
    });

    const result = await semanticSearchService.searchWithMode('running shoes', 'intelligent', 20);

    expect(result.source).toBe('agent');
    expect(result.mode).toBe('intelligent');
    expect(result.fallback_reason).toBeUndefined();
    expect(result.items[0]).toMatchObject({
      sku: 'SKU-1',
    });
    expect(result.items[0].thumbnail).toMatch(/^\/images\/products\/p\d+\.jpg$/);
    expect(productService.search).not.toHaveBeenCalled();
  });

  it('falls back to CRUD for explicit mock-like agent payloads', async () => {
    (agentApiClient.post as jest.Mock).mockResolvedValue({
      data: {
        items: [
          {
            item_id: 'SKU-2',
            title: 'Mock Trail Runner',
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

  it('falls back to CRUD with agent_unavailable on generic agent request failures', async () => {
    (agentApiClient.post as jest.Mock).mockRejectedValue(new Error('connect ETIMEDOUT'));

    const result = await semanticSearchService.searchWithMode('running shoes', 'intelligent', 20);

    expect(productService.search).toHaveBeenCalledWith('running shoes', 20);
    expect(result.source).toBe('crud');
    expect(result.fallback_reason).toBe('agent_unavailable');
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
