import { useMutation, useQuery } from '@tanstack/react-query';
import { ApiError } from '../../lib/api/client';
import { useCategories } from '../../lib/hooks/useCategories';
import { useProducts } from '../../lib/hooks/useProducts';

jest.mock('@tanstack/react-query', () => ({
  useQuery: jest.fn(),
  useMutation: jest.fn(),
}));

jest.mock('../../lib/services/categoryService', () => ({
  categoryService: {
    list: jest.fn(),
    get: jest.fn(),
  },
}));

jest.mock('../../lib/services/productService', () => ({
  productService: {
    list: jest.fn(),
    listEnriched: jest.fn(),
    get: jest.fn(),
    getEnriched: jest.fn(),
    search: jest.fn(),
    getByCategory: jest.fn(),
    triggerEnrichment: jest.fn(),
  },
}));

describe('catalog fallback hook resiliency', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    (useQuery as jest.Mock).mockReturnValue({ data: [] });
    (useMutation as jest.Mock).mockReturnValue({ mutate: jest.fn() });
  });

  it('uses bounded retry + no retry-on-mount policy for categories', () => {
    useCategories();

    const options = (useQuery as jest.Mock).mock.calls[0][0] as {
      retry: (failureCount: number, error: unknown) => boolean;
      retryOnMount: boolean;
      refetchOnReconnect: boolean;
      staleTime: number;
    };

    expect(options.retryOnMount).toBe(false);
    expect(options.refetchOnReconnect).toBe(false);
    expect(options.staleTime).toBe(5 * 60 * 1000);
    expect(options.retry(0, new ApiError(503, 'Service Unavailable'))).toBe(true);
    expect(options.retry(1, new ApiError(503, 'Service Unavailable'))).toBe(false);
    expect(options.retry(0, new ApiError(404, 'Not Found'))).toBe(false);
    expect(options.retry(0, new Error('Unknown failure'))).toBe(false);
  });

  it('uses bounded retry + no retry-on-mount policy for products', () => {
    useProducts({ limit: 24 });

    const options = (useQuery as jest.Mock).mock.calls[0][0] as {
      retry: (failureCount: number, error: unknown) => boolean;
      retryOnMount: boolean;
      refetchOnReconnect: boolean;
      staleTime: number;
    };

    expect(options.retryOnMount).toBe(false);
    expect(options.refetchOnReconnect).toBe(false);
    expect(options.staleTime).toBe(5 * 60 * 1000);
    expect(options.retry(0, new ApiError(504, 'Gateway Timeout'))).toBe(true);
    expect(options.retry(1, new ApiError(504, 'Gateway Timeout'))).toBe(false);
    expect(options.retry(0, new ApiError(400, 'Bad Request'))).toBe(false);
    expect(options.retry(0, new Error('Unknown failure'))).toBe(false);
  });
});
