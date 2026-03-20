import React from 'react';
import { fireEvent, render, screen } from '@testing-library/react';
import SearchPage from '../../app/search/page';

const push = jest.fn();
const getParam = jest.fn();

jest.mock('next/navigation', () => ({
  useRouter: () => ({
    push,
  }),
  useSearchParams: () => ({
    get: getParam,
  }),
}));

const mockUseIntelligentSearch = jest.fn();
const mockUseRelatedProducts = jest.fn();

jest.mock('../../lib/hooks/useIntelligentSearch', () => ({
  useIntelligentSearch: (...args: unknown[]) => mockUseIntelligentSearch(...args),
}));

jest.mock('../../lib/hooks/useRelatedProducts', () => ({
  useRelatedProducts: (...args: unknown[]) => mockUseRelatedProducts(...args),
}));

jest.mock('../../components/atoms/ThemeToggle', () => ({
  ThemeToggle: () => <div data-testid="theme-toggle" />,
}));

describe('SearchPage', () => {
  const setPreference = jest.fn();

  beforeEach(() => {
    push.mockClear();
    setPreference.mockClear();
    getParam.mockReturnValue('headphones');
    mockUseRelatedProducts.mockReturnValue({ data: {} });
    mockUseIntelligentSearch.mockReturnValue({
      data: {
        items: [],
        source: 'agent',
        mode: 'keyword',
        intent: null,
        subqueries: [],
      },
      isLoading: false,
      error: null,
      isFetching: false,
      refetch: jest.fn(),
      preference: 'auto',
      setPreference,
      resolvedMode: 'keyword',
    });
  });

  it('prefills the query from the URL and shows mode badge', () => {
    render(<SearchPage />);

    expect(screen.getByDisplayValue('headphones')).toBeInTheDocument();
    expect(screen.getAllByText('Keyword Search').length).toBeGreaterThan(0);
    expect(screen.getByText('No products matched your search.')).toBeInTheDocument();
  });

  it('shows intent panel details in intelligent mode when available', () => {
    mockUseIntelligentSearch.mockReturnValue({
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
      isLoading: false,
      error: null,
      isFetching: false,
      refetch: jest.fn(),
      preference: 'intelligent',
      setPreference,
      resolvedMode: 'intelligent',
    });

    render(<SearchPage />);

    expect(screen.getByText('Intent details')).toBeInTheDocument();
    expect(screen.getByText('use_case_lookup')).toBeInTheDocument();
    expect(screen.getByText('wireless noise cancelling')).toBeInTheDocument();
  });

  it('changes search mode preference from toggle', () => {
    render(<SearchPage />);
    fireEvent.click(screen.getByRole('radio', { name: 'Search mode Intelligent' }));
    expect(setPreference).toHaveBeenCalledWith('intelligent');
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
    mockUseIntelligentSearch.mockReturnValue({
      data: { items: [], source: 'crud', mode: 'keyword', intent: null, subqueries: [] },
      isLoading: false,
      isFetching: false,
      error: {
        status: 502,
        details: {
          proxy: {
            failureKind: 'network',
          },
        },
      },
      refetch,
      preference: 'auto',
      setPreference,
      resolvedMode: 'keyword',
    });

    render(<SearchPage />);

    expect(screen.getByRole('alert')).toBeInTheDocument();
    expect(screen.getByText('Catalog search is temporarily unavailable')).toBeInTheDocument();
    expect(screen.getByText('Catalog search backend is temporarily unreachable.')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'Retry search' }));
    expect(refetch).toHaveBeenCalledTimes(1);
  });
});
