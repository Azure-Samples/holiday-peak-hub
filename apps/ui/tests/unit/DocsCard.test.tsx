import { render, screen } from '@testing-library/react';

import { DocsCard } from '@/components/molecules/DocsCard';
import { DocsCardCluster } from '@/components/molecules/DocsCardCluster';

describe('DocsCard (Issue #1059)', () => {
  it('renders kicker, title, description, and an internal link', () => {
    render(
      <DocsCard
        kicker="Architecture"
        title="System overview"
        description="How the agents fit together."
        href="/docs/architecture"
        testId="dc"
      />,
    );
    const card = screen.getByTestId('dc');
    expect(card).toHaveAttribute('href', '/docs/architecture');
    expect(screen.getByText('Architecture')).toBeInTheDocument();
    expect(screen.getByText('System overview')).toBeInTheDocument();
    expect(screen.getByText('How the agents fit together.')).toBeInTheDocument();
  });

  it('opens external links in a new tab with rel="noreferrer noopener"', () => {
    render(
      <DocsCard
        title="Cost calculator"
        description="Canonical Azure cost calculator."
        href="https://azure.microsoft.com/pricing/calculator"
        external
        testId="dc"
      />,
    );
    const card = screen.getByTestId('dc');
    expect(card).toHaveAttribute('target', '_blank');
    expect(card).toHaveAttribute('rel', 'noreferrer noopener');
  });
});

describe('DocsCardCluster (Issue #1059)', () => {
  it('renders the heading and one card per entry', () => {
    render(
      <DocsCardCluster
        testId="dcc"
        headline="Read the docs"
        cards={[
          { title: 'Architecture', description: 'A', href: '/docs/a' },
          { title: 'Governance', description: 'G', href: '/docs/g' },
        ]}
      />,
    );
    expect(screen.getByText('Read the docs')).toBeInTheDocument();
    expect(screen.getByText('Architecture')).toBeInTheDocument();
    expect(screen.getByText('Governance')).toBeInTheDocument();
  });
});
