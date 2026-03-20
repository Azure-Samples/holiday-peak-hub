import { act, renderHook } from '@testing-library/react';
import { useIntelligentSearch } from '../../lib/hooks/useIntelligentSearch';

const mockUseSemanticSearch = jest.fn();
const mockPrefetchQuery = jest.fn();

jest.mock('../../lib/hooks/useSemanticSearch', () => ({
  useSemanticSearch: (...args: unknown[]) => mockUseSemanticSearch(...args),
}));

jest.mock('@tanstack/react-query', () => ({
  useQueryClient: () => ({
    prefetchQuery: mockPrefetchQuery,
  }),
}));

describe('useIntelligentSearch', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    jest.useFakeTimers();
    window.localStorage.clear();
    mockUseSemanticSearch.mockReturnValue({
      data: {
        items: [],
        mode: 'keyword',
        source: 'crud',
      },
      isLoading: false,
      error: null,
      isFetching: false,
      refetch: jest.fn(),
    });
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  it('defaults to auto preference and keyword resolved mode', () => {
    const { result } = renderHook(() => useIntelligentSearch('headphones', 20));
    act(() => {
      jest.advanceTimersByTime(300);
    });

    expect(result.current.preference).toBe('auto');
    expect(result.current.resolvedMode).toBe('keyword');
    expect(mockUseSemanticSearch).toHaveBeenCalledWith('headphones', 20, 'auto');
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

  it('prefetches related product cards from search results', () => {
    mockUseSemanticSearch.mockReturnValue({
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

    expect(mockPrefetchQuery).toHaveBeenCalledTimes(2);
  });
});
