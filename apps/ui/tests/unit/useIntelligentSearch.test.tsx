import { act, renderHook } from '@testing-library/react';
import { useIntelligentSearch } from '../../lib/hooks/useIntelligentSearch';

const mockUseSemanticSearch = jest.fn();

jest.mock('../../lib/hooks/useSemanticSearch', () => ({
  useSemanticSearch: (...args: unknown[]) => mockUseSemanticSearch(...args),
}));

describe('useIntelligentSearch', () => {
  beforeEach(() => {
    jest.clearAllMocks();
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

  it('defaults to auto preference and keyword resolved mode', () => {
    const { result } = renderHook(() => useIntelligentSearch('headphones', 20));

    expect(result.current.preference).toBe('auto');
    expect(result.current.resolvedMode).toBe('keyword');
  });

  it('reads persisted preference from localStorage', () => {
    window.localStorage.setItem('hp.search.mode.preference', 'intelligent');

    const { result } = renderHook(() => useIntelligentSearch('headphones', 20));

    expect(result.current.preference).toBe('intelligent');
  });

  it('persists preference updates to localStorage', () => {
    const { result } = renderHook(() => useIntelligentSearch('headphones', 20));

    act(() => {
      result.current.setPreference('keyword');
    });

    expect(window.localStorage.getItem('hp.search.mode.preference')).toBe('keyword');
  });
});
