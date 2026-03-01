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

jest.mock('../../lib/hooks/useProducts', () => ({
  useProductSearch: () => ({
    data: [],
    isLoading: false,
  }),
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
  });

  it('prefills the query from the URL and shows source badge', () => {
    render(<SearchPage />);

    expect(screen.getByDisplayValue('headphones')).toBeInTheDocument();
    expect(screen.getByText('Source: Catalog Search')).toBeInTheDocument();
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
