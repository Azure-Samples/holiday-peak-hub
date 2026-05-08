import { render, screen } from '@testing-library/react';

import { Quote } from '@/components/molecules/Quote';

describe('Quote (Issue #1059)', () => {
  it('renders body and attribution', () => {
    render(
      <Quote
        body="Replenishment review went from hours to minutes."
        attribution={{ name: 'A. Buyer', role: 'Senior buyer', org: 'Design partner' }}
        maturity="design-partner"
        testId="q"
      />,
    );
    expect(screen.getByTestId('q')).toBeInTheDocument();
    expect(screen.getByText(/Replenishment review went from hours to minutes/)).toBeInTheDocument();
    expect(screen.getByText(/A. Buyer/)).toBeInTheDocument();
    expect(screen.getByText(/Senior buyer/)).toBeInTheDocument();
    // "Design partner" appears twice (org attribution + maturity badge).
    expect(screen.getAllByText(/Design partner/).length).toBeGreaterThanOrEqual(1);
  });

  it('renders a maturity badge (honesty contract)', () => {
    render(
      <Quote
        body="Useful."
        attribution={{ name: 'A. B.', role: 'Role' }}
        maturity="production"
        testId="q"
      />,
    );
    expect(screen.getByTestId('q')).toHaveAttribute('data-maturity', 'production');
  });
});
