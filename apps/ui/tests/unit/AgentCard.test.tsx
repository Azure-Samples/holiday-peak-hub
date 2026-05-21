import { render, screen } from '@testing-library/react';

import { AgentCard } from '@/components/molecules/AgentCard';
import { AgentCardCluster } from '@/components/molecules/AgentCardCluster';

describe('AgentCard (Issue #1059)', () => {
  it('renders domain, name, description, and links to /builders/agents/<slug>', () => {
    render(
      <AgentCard
        domain="Inventory"
        name="JIT Replenishment"
        description="Proposes vendor orders."
        href="/builders/agents/inventory-jit-replenishment"
        testId="card"
      />,
    );
    const card = screen.getByTestId('card');
    expect(card).toBeInTheDocument();
    expect(card).toHaveAttribute('href', '/builders/agents/inventory-jit-replenishment');
    expect(screen.getByText('Inventory')).toBeInTheDocument();
    expect(screen.getByText('JIT Replenishment')).toBeInTheDocument();
    expect(screen.getByText('Proposes vendor orders.')).toBeInTheDocument();
  });
});

describe('AgentCardCluster (Issue #1059)', () => {
  it('renders heading and one card per agent', () => {
    render(
      <AgentCardCluster
        testId="cluster"
        headline="Six representative agents"
        agents={[
          {
            domain: 'Inventory',
            name: 'JIT Replenishment',
            description: 'A',
            href: '/builders/agents/a',
          },
          {
            domain: 'Inventory',
            name: 'Reservation Validation',
            description: 'B',
            href: '/builders/agents/b',
          },
        ]}
      />,
    );
    expect(screen.getByText(/Six representative agents/)).toBeInTheDocument();
    expect(screen.getByText('JIT Replenishment')).toBeInTheDocument();
    expect(screen.getByText('Reservation Validation')).toBeInTheDocument();
  });
});
