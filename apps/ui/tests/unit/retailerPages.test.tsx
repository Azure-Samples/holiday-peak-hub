import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import RetailerValuePage from '../../app/(retailer)/retailers/value/page';
import RetailerAgentsCatalogPage from '../../app/(retailer)/retailers/agents/page';
import RetailerRoiPage from '../../app/(retailer)/retailers/roi/page';
import RetailerComparatorsPage from '../../app/(retailer)/retailers/comparators/page';
import RetailerCaseStudiesPage from '../../app/(retailer)/retailers/case-studies/page';

/**
 * Pin the retailer-page composition order from Epic #1046.
 *
 * Each page must render an audience-page hero followed by the page-specific
 * primary section, then a CallToAction (or the audience-pair CTA pattern).
 */

describe('/retailers/value (#1040)', () => {
  beforeEach(() => {
    render(<RetailerValuePage />);
  });

  it('renders the value hero', () => {
    expect(screen.getByTestId('retailer-value-hero')).toBeInTheDocument();
  });

  it('renders the three-pillar value-prop grid', () => {
    expect(screen.getByTestId('retailer-value-pillars')).toBeInTheDocument();
  });

  it('links the "Why us, not them?" CTA to /retailers/comparators', () => {
    const cta = screen.getByTestId('retailer-value-cta-comparators');
    expect(cta.querySelector('a[href="/retailers/comparators"]')).toBeInTheDocument();
  });
});

describe('/retailers/agents (#1041)', () => {
  beforeEach(() => {
    render(<RetailerAgentsCatalogPage />);
  });

  it('renders the agents hero', () => {
    expect(screen.getByTestId('retailer-agents-hero')).toBeInTheDocument();
  });

  it('renders the agent catalog molecule', () => {
    expect(screen.getByTestId('retailer-agents-catalog')).toBeInTheDocument();
  });

  it('renders all 7 domain blocks', () => {
    const expected = [
      'crm',
      'ecommerce',
      'inventory',
      'logistics',
      'product-management',
      'search',
      'truth',
    ];
    for (const k of expected) {
      expect(screen.getByTestId(`retailer-agents-domain-${k}`)).toBeInTheDocument();
    }
  });
});

describe('/retailers/roi (#1042)', () => {
  beforeEach(() => {
    render(<RetailerRoiPage />);
  });

  it('renders the ROI hero', () => {
    expect(screen.getByTestId('retailer-roi-hero')).toBeInTheDocument();
  });

  it('renders the ROI calculator', () => {
    expect(screen.getByTestId('retailer-roi-calculator')).toBeInTheDocument();
  });

  it('renders the "Illustrative" label as required by Epic #1046', () => {
    const calc = screen.getByTestId('retailer-roi-calculator');
    expect(calc.querySelector('[data-illustrative-label]')).toBeInTheDocument();
  });

  it('emits a result region for the live calculation output', () => {
    const calc = screen.getByTestId('retailer-roi-calculator');
    expect(calc.querySelector('[data-roi-output]')).toBeInTheDocument();
  });
});

describe('/retailers/comparators (#1043)', () => {
  beforeEach(() => {
    render(<RetailerComparatorsPage />);
  });

  it('renders the comparators hero', () => {
    expect(screen.getByTestId('retailer-comparators-hero')).toBeInTheDocument();
  });

  it('renders the comparator matrix', () => {
    expect(screen.getByTestId('retailer-comparators-matrix')).toBeInTheDocument();
  });

  it('includes the locked point-solution AI vendors', () => {
    const expected = [
      'algolia',
      'klaviyo',
      'yotpo',
      'einstein-retail',
      'aws-bedrock',
      'vertex-agent-builder',
    ];
    const matrix = screen.getByTestId('retailer-comparators-matrix');
    for (const v of expected) {
      expect(matrix.querySelector(`[data-vendor-key="${v}"]`)).toBeInTheDocument();
    }
  });

  it('discloses the comparator scope (excludes commerce platforms)', () => {
    expect(
      screen.getByText(/excludes full commerce platforms/i),
    ).toBeInTheDocument();
  });
});

describe('/retailers/case-studies (#1044)', () => {
  beforeEach(() => {
    render(<RetailerCaseStudiesPage />);
  });

  it('renders the case-studies hero', () => {
    expect(screen.getByTestId('retailer-case-studies-hero')).toBeInTheDocument();
  });

  it('renders the empty-state surface (honest-beats-marketing)', () => {
    const empty = screen.getByTestId('retailer-case-studies-empty');
    expect(empty).toBeInTheDocument();
    expect(
      screen.getByText(/no published case studies yet/i),
    ).toBeInTheDocument();
  });
});
