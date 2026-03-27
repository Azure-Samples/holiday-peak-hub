import semanticSearchService from '../../lib/services/semanticSearchService';
import agentApiClient from '../../lib/api/agentClient';

jest.mock('../../lib/api/agentClient', () => ({
  __esModule: true,
  default: {
    post: jest.fn(),
  },
}));

describe('semanticSearchService.searchWithMode', () => {
  beforeEach(() => {
    jest.clearAllMocks();
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
});
