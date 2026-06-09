import React from 'react';
import { fireEvent, render, screen } from '@testing-library/react';
import SearchPage from '../../app/search/page';

const push = jest.fn();
const getParam = jest.fn();
const mockUseQuery = jest.fn();
const mockPrefetchQuery = jest.fn();

jest.mock('next/navigation', () => ({
  useRouter: () => ({
    push,
  }),
  useSearchParams: () => ({
    get: getParam,
  }),
  usePathname: () => '/search',
}));

const mockUseRelatedProducts = jest.fn();
const mockUseAuth = jest.fn();

jest.mock('@tanstack/react-query', () => ({
  useQuery: (...args: unknown[]) => mockUseQuery(...args),
  useQueryClient: () => ({
    prefetchQuery: mockPrefetchQuery,
  }),
}));

jest.mock('../../lib/hooks/useRelatedProducts', () => ({
  useRelatedProducts: (...args: unknown[]) => mockUseRelatedProducts(...args),
}));

jest.mock('../../contexts/AuthContext', () => ({
  useAuth: () => mockUseAuth(),
}));

jest.mock('../../components/atoms/ThemeToggle', () => ({
  ThemeToggle: () => <div data-testid="theme-toggle" />,
}));

jest.mock('../../components/organisms/Navigation', () => ({
  Navigation: ({ onSearch }: { onSearch?: (query: string) => void }) => (
    <nav data-testid="navigation-mock">
      {onSearch && <button onClick={() => onSearch('test')}>search</button>}
    </nav>
  ),
}));

function buildSearchQueryResult(overrides: Record<string, unknown> = {}) {
  return {
    data: {
      items: [],
      source: 'agent',
      mode: 'intelligent',
      intent: null,
      subqueries: [],
    },
    isLoading: false,
    error: null,
    isFetching: false,
    refetch: jest.fn(),
    ...overrides,
  };
}

function readQueryOptions(options: unknown): { enabled?: boolean; queryKey?: unknown[] } {
  if (!options || typeof options !== 'object') {
    return {};
  }

  return options as { enabled?: boolean; queryKey?: unknown[] };
}

function configureSearchQueryResults({
  baseline = buildSearchQueryResult(),
  rerank = buildSearchQueryResult({ data: undefined }),
}: {
  baseline?: ReturnType<typeof buildSearchQueryResult>;
  rerank?: ReturnType<typeof buildSearchQueryResult>;
} = {}) {
  mockUseQuery.mockImplementation((options: unknown) => {
    const { enabled, queryKey } = readQueryOptions(options);
    if (enabled === false) {
      return buildSearchQueryResult({ data: undefined });
    }

    return queryKey?.[4] === 'rerank' ? rerank : baseline;
  });
}

describe('SearchPage', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    push.mockClear();
    window.localStorage.clear();
    window.sessionStorage.clear();
    mockUseAuth.mockReturnValue({
      user: {
        user_id: 'customer-123',
      },
    });
    getParam.mockReturnValue('headphones');
    mockUseRelatedProducts.mockReturnValue({ data: {} });
    configureSearchQueryResults();
  });

  it('prefills the query from the URL and shows intelligent mode badge', () => {
    render(<SearchPage />);

    expect(mockUseQuery).toHaveBeenCalledWith(
      expect.objectContaining({
        queryKey: expect.arrayContaining([
          'semantic-search',
          'headphones',
          20,
          'intelligent',
          'baseline',
        ]),
      }),
    );
    expect(screen.getByDisplayValue('headphones')).toBeInTheDocument();
    expect(screen.getAllByText('Intelligent Search').length).toBeGreaterThan(0);
    expect(screen.getByText('No products matched your search.')).toBeInTheDocument();
  });

  it('shows intent panel details in intelligent mode when available', () => {
    configureSearchQueryResults({
      baseline: buildSearchQueryResult({
        data: {
          items: [],
          source: 'agent',
          mode: 'intelligent',
          intent: {
            intent: 'use_case_lookup',
            confidence: 0.88,
            entities: { category: 'audio' },
          },
          subqueries: ['wireless noise cancelling'],
        },
      }),
    });

    render(<SearchPage />);

    expect(screen.getByText('Search mode: Agent enrichment')).toBeInTheDocument();
    expect(screen.getByText('Intent details')).toBeInTheDocument();
    expect(screen.getAllByText('use_case_lookup').length).toBeGreaterThan(0);
    expect(screen.getByText('wireless noise cancelling')).toBeInTheDocument();
  });

  it('changes search mode preference from toggle', () => {
    render(<SearchPage />);
    fireEvent.click(screen.getByRole('radio', { name: 'Search mode Keyword' }));
    expect(window.localStorage.getItem('hp.search.mode.preference')).toBe('keyword');
    expect(screen.getByRole('radio', { name: 'Search mode Keyword' })).toHaveAttribute(
      'aria-checked',
      'true',
    );
  });

  it('updates the URL when searching', () => {
    render(<SearchPage />);

    const inputs = screen.getAllByPlaceholderText('Search products...');
    const input = inputs.find((node) => (node as HTMLInputElement).value === 'headphones');
    expect(input).toBeDefined();
    if (!input) {
      return;
    }
    fireEvent.change(input, { target: { value: 'boots' } });
    fireEvent.keyDown(input, { key: 'Enter', code: 'Enter' });

    expect(push).toHaveBeenCalledWith('/search?q=boots');
  });

  it('shows a recoverable proxy error with retry affordance on 502 failures', () => {
    const refetch = jest.fn();
    configureSearchQueryResults({
      baseline: buildSearchQueryResult({
        data: { items: [], source: 'crud', mode: 'keyword', intent: null, subqueries: [] },
        error: {
          status: 502,
          details: {
            proxy: {
              failureKind: 'network',
            },
          },
        },
        refetch,
      }),
    });

    render(<SearchPage />);

    expect(screen.getByRole('alert')).toBeInTheDocument();
    expect(screen.getByText('Catalog search is temporarily unavailable')).toBeInTheDocument();
    expect(screen.getByText('Catalog search backend is temporarily unreachable.')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'Retry search' }));
    expect(refetch).toHaveBeenCalledTimes(1);
  });

  it('does not show unavailable warning for agent mock fallback', () => {
    configureSearchQueryResults({
      baseline: buildSearchQueryResult({
        data: {
          items: [],
          source: 'crud',
          mode: 'keyword',
          requested_mode: 'intelligent',
          fallback_reason: 'agent_mock',
          intent: null,
          subqueries: [],
        },
      }),
    });

    render(<SearchPage />);

    expect(
      screen.queryByText('Results are from CRUD catalog search because the agent path was unavailable.')
    ).not.toBeInTheDocument();
  });

  it('shows unavailable warning for agent_unavailable fallback', () => {
    configureSearchQueryResults({
      baseline: buildSearchQueryResult({
        data: {
          items: [],
          source: 'crud',
          mode: 'keyword',
          requested_mode: 'intelligent',
          fallback_reason: 'agent_unavailable',
          intent: null,
          subqueries: [],
        },
      }),
    });

    render(<SearchPage />);

    expect(
      screen.getByText('Results are from CRUD catalog search because the agent path was unavailable.')
    ).toBeInTheDocument();
  });

  it('shows degraded fallback warning when agent model synthesis fails', () => {
    configureSearchQueryResults({
      baseline: buildSearchQueryResult({
        data: {
          items: [],
          source: 'agent',
          mode: 'intelligent',
          requested_mode: 'intelligent',
          degraded: true,
          degraded_reason: 'model_timeout',
          degraded_message:
            'Showing the best available catalog guidance while intelligent generation is temporarily unavailable.',
          fallback_keywords: ['winter', 'jacket', 'boots'],
          intent: null,
          subqueries: [],
        },
      }),
    });

    render(<SearchPage />);

    expect(screen.getByText('Intelligent synthesis is temporarily degraded')).toBeInTheDocument();
    expect(screen.getByText('Fallback keywords: winter, jacket, boots')).toBeInTheDocument();
  });

  it('announces reranking progress with a polite status message', () => {
    window.localStorage.setItem('hp.search.mode.preference', 'auto');
    configureSearchQueryResults({
      baseline: buildSearchQueryResult({
        data: {
          items: [
            {
              sku: 'sku-1',
              title: 'Sample Product',
            },
          ],
          source: 'crud',
          mode: 'keyword',
          intent: null,
          subqueries: [],
        },
      }),
      rerank: buildSearchQueryResult({
        data: undefined,
        isFetching: true,
      }),
    });

    render(<SearchPage />);

    expect(screen.getByText('Reranking baseline results in the background...')).toBeInTheDocument();
  });
});
