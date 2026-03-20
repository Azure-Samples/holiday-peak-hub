import React from 'react';
import { render, screen } from '@testing-library/react';
import { EnrichmentPipelineStatus } from '../../components/enrichment/EnrichmentPipelineStatus';
import { AttributeDiffView } from '../../components/enrichment/AttributeDiffView';
import { SearchModeIndicator } from '../../components/enrichment/SearchModeIndicator';
import { IntentPanel } from '../../components/enrichment/IntentPanel';
import { UseCaseTags } from '../../components/enrichment/UseCaseTags';
import { RelatedProductsRail } from '../../components/enrichment/RelatedProductsRail';
import { SearchResultCard } from '../../components/enrichment/SearchResultCard';

describe('enrichment components', () => {
  it('renders pipeline status badge', () => {
    render(<EnrichmentPipelineStatus status="approved" />);
    expect(screen.getByLabelText('Pipeline status approved')).toBeInTheDocument();
    expect(screen.getByText('approved')).toBeInTheDocument();
  });

  it('renders diff content with intent information', () => {
    render(
      <AttributeDiffView
        diffs={[
          {
            field_name: 'material',
            original_value: 'cotton',
            enriched_value: 'organic cotton',
            confidence: 0.92,
            source_type: 'image_ocr',
            intent: 'attribute_enrichment',
            intent_confidence: 0.87,
            reasoning: 'Image label confirms organic cotton composition.',
          },
        ]}
      />
    );

    expect(screen.getByText('material')).toBeInTheDocument();
    expect(screen.getByText('cotton')).toBeInTheDocument();
    expect(screen.getByText('organic cotton')).toBeInTheDocument();
    expect(screen.getByText('attribute_enrichment')).toBeInTheDocument();
    expect(screen.getByText('Image label confirms organic cotton composition.')).toBeInTheDocument();
  });

  it('renders search mode indicator labels', () => {
    const { rerender } = render(<SearchModeIndicator source="agent" />);
    expect(screen.getByText('Search mode: Agent enrichment')).toBeInTheDocument();

    rerender(<SearchModeIndicator source="fallback" />);
    expect(screen.getByText('Search mode: Fallback catalog')).toBeInTheDocument();
  });

  it('renders intelligent intent panel details when present', () => {
    render(
      <IntentPanel
        mode="intelligent"
        intent={{
          intent: 'scenario_search',
          confidence: 0.79,
          entities: { category: 'backpacks' },
        }}
        subqueries={['travel backpack', 'lightweight carry on']}
      />,
    );

    expect(screen.getByText('Intent details')).toBeInTheDocument();
    expect(screen.getByText('scenario_search')).toBeInTheDocument();
    expect(screen.getByText('travel backpack')).toBeInTheDocument();
  });

  it('renders enriched result details with graceful optional sections', () => {
    render(
      <SearchResultCard
        product={{
          sku: 'sku-1',
          title: 'Trail Backpack',
          description: 'Base description',
          enrichedDescription: 'Enriched trail-ready description',
          brand: 'Holiday Peak',
          category: 'outdoor',
          price: 129,
          currency: 'USD',
          images: ['/images/products/p1.jpg'],
          thumbnail: '/images/products/p1.jpg',
          inStock: true,
          useCases: ['hiking', 'travel'],
          complementaryProducts: ['Rain Cover'],
          substituteProducts: ['Urban Backpack'],
        }}
      />,
    );

    expect(screen.getByText('Enriched trail-ready description')).toBeInTheDocument();
    expect(screen.getByText('hiking')).toBeInTheDocument();
    expect(screen.getByText('Rain Cover')).toBeInTheDocument();
    expect(screen.getByText('Urban Backpack')).toBeInTheDocument();
  });

  it('renders standalone use-case and related rails only when data exists', () => {
    const { rerender } = render(<UseCaseTags useCases={['daily commute']} />);
    expect(screen.getByText('daily commute')).toBeInTheDocument();

    rerender(
      <RelatedProductsRail
        title="Alternatives"
        items={['sku-10']}
        productMap={{
          'sku-10': {
            sku: 'sku-10',
            title: 'Compact Sleeve',
            description: 'Compact travel sleeve',
            brand: 'Holiday Peak',
            category: 'travel',
            price: 49,
            currency: 'USD',
            images: ['/images/products/p1.jpg'],
            thumbnail: '/images/products/p1.jpg',
            inStock: true,
          },
        }}
      />,
    );
    expect(screen.getByText('Compact Sleeve')).toBeInTheDocument();
  });
});
