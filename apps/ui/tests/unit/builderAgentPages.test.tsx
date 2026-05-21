import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';

import BuilderAgentsCatalogPage from '../../app/(builder)/builders/agents/page';
import BuilderAgentDetailPage, {
  generateMetadata,
  generateStaticParams,
} from '../../app/(builder)/builders/agents/[slug]/page';

const mockNotFound = jest.fn(() => {
  throw new Error('NEXT_NOT_FOUND');
});

jest.mock('next/navigation', () => ({
  notFound: () => mockNotFound(),
}));

describe('/builders/agents', () => {
  beforeEach(() => {
    render(<BuilderAgentsCatalogPage />);
  });

  it('renders the builder agent catalog page', () => {
    expect(screen.getByTestId('builder-agents-hero')).toBeInTheDocument();
    expect(screen.getByTestId('builder-agents-catalog')).toBeInTheDocument();
  });

  it('links known agent cards to builder detail routes', () => {
    expect(
      screen.getAllByRole('link', { name: 'Open builder detail' }).some(
        (link) => link.getAttribute('href') === '/builders/agents/ecommerce-product-detail-enrichment',
      ),
    ).toBe(true);
  });
});

describe('/builders/agents/[slug]', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('enumerates known agent slugs for static generation', () => {
    expect(generateStaticParams()).toEqual(
      expect.arrayContaining([
        { slug: 'ecommerce-product-detail-enrichment' },
      ]),
    );
  });

  it('renders the product detail enrichment builder page', async () => {
    const element = await BuilderAgentDetailPage({
      params: Promise.resolve({ slug: 'ecommerce-product-detail-enrichment' }),
    });

    render(element);

    expect(screen.getByTestId('builder-agent-detail-hero')).toBeInTheDocument();
    expect(
      screen.getByRole('heading', { name: 'eCommerce Product Detail Enrichment' }),
    ).toBeInTheDocument();
    expect(screen.getByTestId('builder-agent-runtime')).toBeInTheDocument();
    expect(screen.getByTestId('builder-agent-kpis')).toBeInTheDocument();
    expect(screen.getByTestId('builder-agent-contract-json')).toBeInTheDocument();
  });

  it('builds page metadata from the known agent profile', async () => {
    const metadata = await generateMetadata({
      params: Promise.resolve({ slug: 'ecommerce-product-detail-enrichment' }),
    });

    expect(metadata.title).toBe('eCommerce Product Detail Enrichment — For Builders — Holiday Peak Hub');
    expect(metadata.alternates?.canonical).toContain('/builders/agents/ecommerce-product-detail-enrichment');
  });

  it('returns notFound for unknown agent slugs', async () => {
    await expect(
      BuilderAgentDetailPage({ params: Promise.resolve({ slug: 'unknown-agent' }) }),
    ).rejects.toThrow('NEXT_NOT_FOUND');
    expect(mockNotFound).toHaveBeenCalledTimes(1);
  });
});