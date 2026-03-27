import React from 'react';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { ChatWidget } from '../../components/organisms/ChatWidget';

const usePathnameMock = jest.fn();
const searchParamsGetMock = jest.fn();
const searchWithModeMock = jest.fn();

jest.mock('next/navigation', () => ({
  usePathname: () => usePathnameMock(),
  useSearchParams: () => ({
    get: searchParamsGetMock,
  }),
}));

jest.mock('../../lib/services/semanticSearchService', () => ({
  semanticSearchService: {
    searchWithMode: (...args: unknown[]) => searchWithModeMock(...args),
  },
}));

describe('ChatWidget', () => {
  beforeEach(() => {
    usePathnameMock.mockReturnValue('/search');
    searchParamsGetMock.mockReturnValue(null);
    searchWithModeMock.mockReset();
    window.history.replaceState(null, '', '/search');
  });

  it('opens from launcher and shows dialog shell', async () => {
    render(<ChatWidget />);

    const launcher = screen.getByRole('button', { name: 'Open product enrichment chat' });
    fireEvent.click(launcher);

    expect(screen.getByRole('dialog', { name: 'Product Enrichment Agent' })).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByLabelText('Ask the product enrichment agent')).toHaveFocus();
    });
  });

  it('closes on Escape and returns focus to launcher', async () => {
    render(<ChatWidget />);

    fireEvent.click(screen.getByRole('button', { name: 'Open product enrichment chat' }));

    fireEvent.keyDown(window, { key: 'Escape' });

    await waitFor(() => {
      expect(screen.queryByRole('dialog', { name: 'Product Enrichment Agent' })).not.toBeInTheDocument();
    });

    await waitFor(() => {
      expect(screen.getByRole('button', { name: 'Open product enrichment chat' })).toHaveFocus();
    });
  });

  it('renders comparison results after a successful send', async () => {
    searchWithModeMock.mockImplementation(async (_query: string, mode: 'intelligent' | 'keyword') => ({
      items: mode === 'intelligent'
        ? [{ sku: 'intel-1', title: 'Intelligent Pick', score: 0.98 }]
        : [{ sku: 'key-1', title: 'Keyword Pick', score: 0.52 }],
    }));

    render(<ChatWidget />);

    fireEvent.click(screen.getByRole('button', { name: 'Open product enrichment chat' }));

    const input = await screen.findByLabelText('Ask the product enrichment agent');
    fireEvent.change(input, { target: { value: 'headphones under 200' } });
    fireEvent.click(screen.getByRole('button', { name: 'Send message' }));

    expect(await screen.findByText('Intelligent agent results')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /Intelligent Pick/ })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /Keyword Pick/ })).toBeInTheDocument();
  });

  it('shows fallback message when both comparison calls fail', async () => {
    searchWithModeMock.mockRejectedValue(new Error('backend unavailable'));

    render(<ChatWidget />);

    fireEvent.click(screen.getByRole('button', { name: 'Open product enrichment chat' }));

    const input = await screen.findByLabelText('Ask the product enrichment agent');
    fireEvent.change(input, { target: { value: 'compare smartwatches' } });
    fireEvent.click(screen.getByRole('button', { name: 'Send message' }));

    expect(
      await screen.findByText('Search agent is temporarily unavailable. Retry in a few seconds or use /search directly.')
    ).toBeInTheDocument();
  });
});
