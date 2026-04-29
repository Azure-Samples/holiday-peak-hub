import React from 'react';
import { act, render, waitFor } from '@testing-library/react';

import type { Product } from '../../components/types';
import { ProductGraphCanvas } from '../../components/organisms/ProductGraphCanvas';
import agentApiClient from '../../lib/api/agentClient';
import { recordAgentInvocationTelemetry } from '../../lib/hooks/useAgentInvocationTelemetry';

const pushMock = jest.fn();

jest.mock('next/navigation', () => ({
  useRouter: () => ({
    push: pushMock,
  }),
}));

jest.mock('../../lib/api/agentClient', () => ({
  __esModule: true,
  default: {
    post: jest.fn(),
  },
}));

jest.mock('../../lib/hooks/useAgentInvocationTelemetry', () => ({
  recordAgentInvocationTelemetry: jest.fn(),
}));

const product: Product = {
  sku: 'sku-graph-1',
  title: 'Trail Backpack',
  description: 'Carry-on sized pack for demo coverage.',
  brand: 'Holiday Peak',
  category: 'packs',
  price: 149.99,
  currency: 'USD',
  images: [],
  thumbnail: '/images/products/p1.jpg',
  inStock: true,
};

describe('ProductGraphCanvas', () => {
  let originalGetContext: HTMLCanvasElement['getContext'];
  let intersectionCallback: ((entries: Array<{ isIntersecting: boolean }>) => void) | null;

  beforeAll(() => {
    originalGetContext = HTMLCanvasElement.prototype.getContext;
    Object.defineProperty(HTMLCanvasElement.prototype, 'getContext', {
      configurable: true,
      value: jest.fn(() => null),
    });
    Object.defineProperty(globalThis, 'IntersectionObserver', {
      configurable: true,
      value: class MockIntersectionObserver {
        constructor(callback: (entries: Array<{ isIntersecting: boolean }>) => void) {
          intersectionCallback = callback;
        }

        observe() {}

        disconnect() {}

        unobserve() {}
      },
    });
  });

  afterAll(() => {
    Object.defineProperty(HTMLCanvasElement.prototype, 'getContext', {
      configurable: true,
      value: originalGetContext,
    });
    delete (globalThis as typeof globalThis & { IntersectionObserver?: unknown }).IntersectionObserver;
  });

  beforeEach(() => {
    jest.clearAllMocks();
    pushMock.mockReset();
    intersectionCallback = null;
  });

  it('records backend telemetry for graph summary enrichment calls after the graph becomes visible', async () => {
    (agentApiClient.post as jest.Mock).mockResolvedValue({
      data: {
        message: 'Compact graph summary from the agent.',
        _telemetry: {
          model_tier: 'slm',
          total_tokens: 58,
          latency_ms: 441,
        },
      },
    });

    render(<ProductGraphCanvas products={[product]} />);

    expect(agentApiClient.post).not.toHaveBeenCalled();

    await act(async () => {
      intersectionCallback?.([{ isIntersecting: true }]);
    });

    await waitFor(() => {
      expect(agentApiClient.post).toHaveBeenCalledWith(
        '/ecommerce-product-detail-enrichment/invoke',
        expect.objectContaining({
          sku: 'sku-graph-1',
        }),
      );
    });

    expect(recordAgentInvocationTelemetry).toHaveBeenCalledWith(
      'ecommerce-product-detail-enrichment',
      expect.objectContaining({
        _telemetry: expect.objectContaining({
          model_tier: 'slm',
          total_tokens: 58,
        }),
      }),
    );
  });
});