import { act, renderHook } from '@testing-library/react';
import { useIntelligentSearch } from '@/src/features/search';

const mockUseQuery = jest.fn();
const mockPrefetchQuery = jest.fn();

jest.mock('@tanstack/react-query', () => ({
  useQuery: (...args: unknown[]) => mockUseQuery(...args),
  useQueryClient: () => ({
    prefetchQuery: mockPrefetchQuery,
  }),
}));

describe('useIntelligentSearch', () => {
  function buildQueryResult(overrides: Record<string, unknown> = {}) {
    return {
      data: {
        items: [],
        mode: 'keyword',
        source: 'crud',
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

  beforeEach(() => {
    jest.clearAllMocks();
    jest.useFakeTimers();
    window.localStorage.clear();
    window.sessionStorage.clear();
    mockUseQuery.mockImplementation((options: unknown) => {
      const { enabled, queryKey } = readQueryOptions(options);
      if (!enabled) {
        return buildQueryResult({ data: undefined });
      }

      const mode = queryKey?.[3];
      if (mode === 'intelligent') {
        return buildQueryResult({
          data: {
            items: [],
            mode: 'intelligent',
            source: 'agent',
          },
        });
      }

      return buildQueryResult();
    });
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  it('defaults to intelligent preference and intelligent resolved mode', () => {
    const { result } = renderHook(() => useIntelligentSearch('headphones', 20));
    act(() => {
      jest.advanceTimersByTime(300);
    });

    expect(result.current.preference).toBe('intelligent');
    expect(result.current.resolvedMode).toBe('intelligent');
    expect(mockUseQuery).toHaveBeenCalledWith(
      expect.objectContaining({
        enabled: true,
        queryKey: expect.arrayContaining([
          'semantic-search',
          'headphones',
          20,
          'intelligent',
          'baseline',
        ]),
      }),
    );
  });

  it('reads persisted preference from localStorage', () => {
    window.localStorage.setItem('hp.search.mode.preference', 'intelligent');

    const { result } = renderHook(() => useIntelligentSearch('headphones', 20));
    act(() => {
      jest.advanceTimersByTime(300);
    });

    expect(result.current.preference).toBe('intelligent');
  });

  it('persists preference updates to localStorage', () => {
    const { result } = renderHook(() => useIntelligentSearch('headphones', 20));

    act(() => {
      result.current.setPreference('keyword');
    });

    expect(window.localStorage.getItem('hp.search.mode.preference')).toBe('keyword');
  });

  it('returns baseline results first and replaces them with reranked results when available', () => {
    let rerankReady = false;
    window.localStorage.setItem('hp.search.mode.preference', 'auto');

    mockUseQuery.mockImplementation((options: unknown) => {
      const { enabled, queryKey } = readQueryOptions(options);
      const mode = queryKey?.[3];
      if (mode === 'keyword') {
        return buildQueryResult({
          data: {
            items: [
              {
                sku: 'sku-baseline',
                complementaryProducts: [],
                substituteProducts: [],
              },
            ],
            mode: 'keyword',
            source: 'crud',
          },
        });
      }

      if (!enabled || !rerankReady) {
        return buildQueryResult({
          data: undefined,
          isFetching: enabled,
        });
      }

      return buildQueryResult({
        data: {
          items: [
            {
              sku: 'sku-reranked',
              complementaryProducts: [],
              substituteProducts: [],
            },
          ],
          mode: 'intelligent',
          source: 'agent',
        },
      });
    });

    const { result, rerender } = renderHook(() => useIntelligentSearch('headphones', 20));

    act(() => {
      jest.advanceTimersByTime(300);
    });

    expect(result.current.preference).toBe('auto');
    expect(result.current.searchStage).toBe('baseline');
    expect(result.current.data?.items[0].sku).toBe('sku-baseline');
    expect(result.current.isReranking).toBe(true);

    rerankReady = true;
    rerender();

    expect(result.current.searchStage).toBe('rerank');
    expect(result.current.data?.items[0].sku).toBe('sku-reranked');
    expect(result.current.resolvedMode).toBe('intelligent');
  });

  it('prefetches related product cards from search results', () => {
    window.localStorage.setItem('hp.search.mode.preference', 'keyword');

    mockUseQuery.mockReturnValue({
      data: {
        items: [
          {
            sku: 'sku-1',
            title: 'Pack',
            description: 'desc',
            brand: 'Holiday Peak',
            category: 'bags',
            price: 10,
            currency: 'USD',
            images: ['/images/products/p1.jpg'],
            thumbnail: '/images/products/p1.jpg',
            inStock: true,
            complementaryProducts: ['sku-2'],
            substituteProducts: ['sku-3'],
          },
        ],
        mode: 'intelligent',
        source: 'agent',
      },
      isLoading: false,
      error: null,
      isFetching: false,
      refetch: jest.fn(),
    });

    renderHook(() => useIntelligentSearch('headphones', 20));

    act(() => {
      jest.advanceTimersByTime(300);
    });

    expect(mockPrefetchQuery).toHaveBeenCalledWith(
      expect.objectContaining({
        queryKey: ['related-product-preview', 'sku-2'],
      }),
    );
    expect(mockPrefetchQuery).toHaveBeenCalledWith(
      expect.objectContaining({
        queryKey: ['related-product-preview', 'sku-3'],
      }),
    );
  });
});
