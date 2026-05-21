import { render, screen } from '@testing-library/react';

import { DeployStep } from '@/components/molecules/DeployStep';
import { DeployStepCluster } from '@/components/molecules/DeployStepCluster';

describe('DeployStep (Issue #1059)', () => {
  it('renders the ordinal, headline, and summary', () => {
    render(
      <DeployStep
        ordinal={1}
        headline="Sign in"
        summary="Authenticate with the Microsoft Entra tenant."
        stateful
        testId="step"
      />,
    );
    expect(screen.getByText(/Step 1/)).toBeInTheDocument();
    expect(screen.getByText('Sign in')).toBeInTheDocument();
    expect(screen.getByText(/Microsoft Entra tenant/)).toBeInTheDocument();
    expect(screen.getByTestId('step')).toHaveAttribute('data-stateful', 'true');
  });
});

describe('DeployStepCluster (Issue #1059)', () => {
  it('renders 5 numbered steps in order', () => {
    render(
      <DeployStepCluster
        testId="cluster"
        headline="Five steps, end to end"
        steps={[
          { headline: 'Sign in', summary: '1', stateful: true },
          { headline: 'Pick subscription', summary: '2' },
          { headline: 'Name deployment', summary: '3' },
          { headline: 'Review estimated cost', summary: '4', stateful: true },
          { headline: 'Launch', summary: '5' },
        ]}
      />,
    );
    expect(screen.getByText(/Five steps, end to end/)).toBeInTheDocument();
    expect(screen.getByText('Step 1')).toBeInTheDocument();
    expect(screen.getByText('Step 2')).toBeInTheDocument();
    expect(screen.getByText('Step 3')).toBeInTheDocument();
    expect(screen.getByText('Step 4')).toBeInTheDocument();
    expect(screen.getByText('Step 5')).toBeInTheDocument();
    expect(screen.getByText('Sign in')).toBeInTheDocument();
    expect(screen.getByText('Launch')).toBeInTheDocument();
  });
});
