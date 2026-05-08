import '@testing-library/jest-dom';
import { render, screen } from '@testing-library/react';
import { CallToAction } from '@/components/molecules/CallToAction';

/**
 * CallToAction contract tests (ADR-035 §54 / Issue #1057).
 *
 * Discriminated by tone — pin the rendered shape per tone.
 */
describe('CallToAction', () => {
  it('audience-pair renders both equally-weighted CTAs', () => {
    render(
      <CallToAction
        tone="audience-pair"
        headline="Ready to pick a lane?"
        primary={{ label: "I'm a retailer", href: '/retailers' }}
        secondary={{ label: "I'm a builder", href: '/builders' }}
        testId="cta"
      />,
    );
    const cta = screen.getByTestId('cta');
    expect(cta).toHaveAttribute('data-cta-tone', 'audience-pair');
    expect(screen.getAllByRole('link')).toHaveLength(2);
  });

  it('single tone renders one primary + optional caption', () => {
    render(
      <CallToAction
        tone="single"
        headline="Book a 20-minute walkthrough"
        primary={{ label: 'Book walkthrough', href: '/contact/walkthrough' }}
        caption="20 minutes. No slides."
        testId="cta"
      />,
    );
    expect(screen.getByTestId('cta')).toHaveAttribute('data-cta-tone', 'single');
    expect(screen.getAllByRole('link')).toHaveLength(1);
    expect(screen.getByText(/no slides/i)).toBeInTheDocument();
  });

  it('procurement tone renders primary + Trust Center link', () => {
    render(
      <CallToAction
        tone="procurement"
        headline="RFP / procurement contact"
        primary={{ label: 'Send an RFP', href: 'mailto:rfp@example.com' }}
        trustCenter={{ label: 'Microsoft Trust Center', href: 'https://www.microsoft.com/trust-center' }}
        testId="cta"
      />,
    );
    expect(screen.getByTestId('cta')).toHaveAttribute('data-cta-tone', 'procurement');
    expect(screen.getAllByRole('link')).toHaveLength(2);
    expect(screen.getByRole('link', { name: /trust center/i })).toBeInTheDocument();
  });
});
