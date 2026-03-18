import React from 'react';
import { fireEvent, render, screen } from '@testing-library/react';
import HomePage from '../../app/page';

const mockUseProducts = jest.fn();
const mockRefetch = jest.fn();

jest.mock('../../lib/hooks/useCategories', () => ({
  useCategories: jest.fn(() => ({
    data: [],
    isLoading: false,
    isError: false,
  })),
}));

jest.mock('../../lib/hooks/useProducts', () => ({
  useProducts: (...args: unknown[]) => mockUseProducts(...args),
}));

jest.mock('../../lib/utils/productMappers', () => ({
  mapApiProductsToUi: (products: unknown[]) => products,
}));

jest.mock('@/components/templates/MainLayout', () => ({
  MainLayout: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="main-layout">{children}</div>
  ),
}));

jest.mock('@/components/organisms/ProductGraphCanvas', () => ({
  ProductGraphCanvas: ({ products }: { products: unknown[] }) => (
    <div data-testid="product-graph-canvas">graph products: {products.length}</div>
  ),
}));

describe('HomePage fail-safe states', () => {
  beforeEach(() => {
    mockRefetch.mockClear();
    mockUseProducts.mockReset();
  });

  it('shows loading state while fetching products', () => {
    mockUseProducts.mockReturnValue({
      data: [],
      isLoading: true,
      isError: false,
      refetch: mockRefetch,
      isFetching: false,
    });

    render(<HomePage />);

    expect(screen.getByText('Loading products...')).toBeInTheDocument();
    expect(screen.queryByTestId('product-graph-canvas')).not.toBeInTheDocument();
  });

  it('shows error state and retries products query', () => {
    mockUseProducts.mockReturnValue({
      data: [],
      isLoading: false,
      isError: true,
      refetch: mockRefetch,
      isFetching: false,
    });

    render(<HomePage />);

    expect(screen.getByRole('alert')).toBeInTheDocument();
    expect(screen.getByText('Products are temporarily unavailable.')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: 'Retry products' }));
    expect(mockRefetch).toHaveBeenCalledTimes(1);
    expect(screen.queryByTestId('product-graph-canvas')).not.toBeInTheDocument();
  });

  it('shows empty state when products query succeeds with no products', () => {
    mockUseProducts.mockReturnValue({
      data: [],
      isLoading: false,
      isError: false,
      refetch: mockRefetch,
      isFetching: false,
    });

    render(<HomePage />);

    expect(screen.getByText('No products available right now.')).toBeInTheDocument();
    expect(screen.queryByTestId('product-graph-canvas')).not.toBeInTheDocument();
  });

  it('renders product graph only when products are available', () => {
    mockUseProducts.mockReturnValue({
      data: [
        {
          id: 'seed-product-0001',
          name: 'Wireless Headphones',
        },
      ],
      isLoading: false,
      isError: false,
      refetch: mockRefetch,
      isFetching: false,
    });

    render(<HomePage />);

    expect(screen.getByTestId('product-graph-canvas')).toHaveTextContent('graph products: 1');
    expect(screen.queryByText('Loading products...')).not.toBeInTheDocument();
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    expect(screen.queryByText('No products available right now.')).not.toBeInTheDocument();
  });
});
