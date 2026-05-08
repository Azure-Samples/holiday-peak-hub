import '@testing-library/jest-dom';
import { render, screen } from '@testing-library/react';
import { ConfidenceInterval } from '@/components/atoms/ConfidenceInterval';

/**
 * ConfidenceInterval contract tests (ADR-035 §54 / Issue #1057).
 *
 * The atom carries the honest-beats-marketing rule — every metric ships
 * with its band, sample size, and methodology. These tests pin the visible
 * shape of the citation.
 */
describe('ConfidenceInterval', () => {
  it('renders the lower–upper band with the unit', () => {
    render(
      <ConfidenceInterval
        lower="35"
        upper="55"
        unit="minutes"
        sampleSize={3}
        population="design partners"
        methodology="observed Jan 2026"
        testId="ci"
      />,
    );
    const ci = screen.getByTestId('ci');
    expect(ci).toHaveTextContent(/35.{1,3}55 minutes/);
  });

  it('renders the citation footer with sample size and methodology', () => {
    render(
      <ConfidenceInterval
        lower="35"
        upper="55"
        unit="minutes"
        sampleSize={3}
        population="design partners"
        methodology="observed Jan 2026"
        testId="ci"
      />,
    );
    expect(screen.getByTestId('ci')).toHaveTextContent(/n=3 design partners, observed Jan 2026/);
  });

  it('renders before→after when baseline is provided', () => {
    render(
      <ConfidenceInterval
        lower="35"
        upper="55"
        unit="minutes"
        baseline={{ lower: '4', upper: '7', unit: 'hours' }}
        sampleSize={3}
        population="design partners"
        methodology="observed Jan 2026"
        testId="ci"
      />,
    );
    const ci = screen.getByTestId('ci');
    expect(ci).toHaveTextContent(/4.{1,3}7 hours/);
    expect(ci).toHaveTextContent(/35.{1,3}55 minutes/);
  });
});
