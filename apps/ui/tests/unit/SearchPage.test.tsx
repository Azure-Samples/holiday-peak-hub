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

const mockUseSemanticSearch = jest.fn();

jest.mock('../../lib/hooks/useSemanticSearch', () => ({
  useSemanticSearch: (...args: unknown[]) => mockUseSemanticSearch(...args),
}));

jest.mock('../../components/atoms/ThemeToggle', () => ({
  ThemeToggle: () => <div data-testid="theme-toggle" />,
}));

jest.mock('../../components/organisms/ProductGrid', () => ({
  ProductGrid: ({ emptyMessage }: { emptyMessage: string }) => (
    <div>{emptyMessage}</div>
  ),
}));

describe('SearchPage', () => {
  beforeEach(() => {
    push.mockClear();
    getParam.mockReturnValue('headphones');
    mockUseSemanticSearch.mockReturnValue({
      data: { items: [], source: 'agent' },
      isLoading: false,
    });
  });

  it('prefills the query from the URL and shows source badge', () => {
    render(<SearchPage />);

    expect(screen.getByDisplayValue('headphones')).toBeInTheDocument();
    expect(screen.getByText('Search source: Catalog Search Agent')).toBeInTheDocument();
    expect(screen.getByRole('status')).toBeInTheDocument();
  });

  it('shows CRUD fallback source badge when semantic source is unavailable', () => {
    mockUseSemanticSearch.mockReturnValue({
      data: { items: [], source: 'crud' },
      isLoading: false,
    });

    render(<SearchPage />);

    expect(
      screen.getByText('Search source: Catalog Search fallback (agent unavailable)')
    ).toBeInTheDocument();
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
});
