import { render, screen } from '@testing-library/react';

import { FeatureMatrix } from '@/components/molecules/FeatureMatrix';

describe('FeatureMatrix (Issue #1059)', () => {
  it('renders capabilities, summaries, availability pills, and per-row maturity badges', () => {
    render(
      <FeatureMatrix
        headline="Capabilities"
        rows={[
          {
            capability: 'MCP-only A2A',
            summary: 'All cross-agent calls go through MCP.',
            availability: 'available',
            maturity: 'design-partner',
          },
          {
            capability: 'AGC blue-green',
            summary: 'AppGW for Containers, weighted canary.',
            availability: 'preview',
            maturity: 'preview',
          },
          {
            capability: 'Multi-region active/active',
            summary: 'Two regions writing simultaneously.',
            availability: 'roadmap',
            maturity: 'internal',
          },
        ]}
        testId="fm"
      />,
    );
    expect(screen.getByText('Capabilities')).toBeInTheDocument();
    expect(screen.getByText('MCP-only A2A')).toBeInTheDocument();
    expect(screen.getByText('AGC blue-green')).toBeInTheDocument();
    expect(screen.getByText('Multi-region active/active')).toBeInTheDocument();
    expect(screen.getByText('Available')).toBeInTheDocument();
    // 'Preview' appears as both the availability pill and the maturity badge label.
    expect(screen.getAllByText('Preview').length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText('Roadmap')).toBeInTheDocument();
  });

  it('shows a Region column when showRegion=true', () => {
    render(
      <FeatureMatrix
        headline="What gets deployed"
        showRegion
        rows={[
          {
            capability: 'CRUD service',
            summary: 'X',
            availability: 'available',
            maturity: 'design-partner',
            region: 'East US 2',
          },
        ]}
        testId="fm"
      />,
    );
    expect(screen.getByText('Region')).toBeInTheDocument();
    expect(screen.getByText('East US 2')).toBeInTheDocument();
  });

  it('hides the Region column when showRegion is omitted', () => {
    render(
      <FeatureMatrix
        headline="X"
        rows={[
          {
            capability: 'a',
            summary: 'x',
            availability: 'available',
            maturity: 'production',
          },
        ]}
        testId="fm"
      />,
    );
    expect(screen.queryByText('Region')).not.toBeInTheDocument();
  });
});
