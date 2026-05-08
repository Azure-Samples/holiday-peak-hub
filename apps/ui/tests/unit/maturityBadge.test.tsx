import '@testing-library/jest-dom';
import { render, screen } from '@testing-library/react';
import { MaturityBadge } from '@/components/atoms/MaturityBadge';

/**
 * MaturityBadge contract tests (ADR-035 §54 / Issue #1057).
 *
 * The badge is the honesty-enforcement atom — composites that render
 * claims must compose it. These tests pin the visible label per level,
 * the `data-maturity` attribute (used by visual regression and analytics),
 * and the accessible status role.
 */
describe('MaturityBadge', () => {
  it('renders the production label for level=production', () => {
    render(<MaturityBadge level="production" testId="badge" />);
    const badge = screen.getByTestId('badge');
    expect(badge).toHaveTextContent(/production/i);
    expect(badge).toHaveAttribute('data-maturity', 'production');
    expect(badge.getAttribute('role')).toBe('status');
  });

  it('renders the design partner label for level=design-partner', () => {
    render(<MaturityBadge level="design-partner" testId="badge" />);
    const badge = screen.getByTestId('badge');
    expect(badge).toHaveTextContent(/design partner/i);
    expect(badge).toHaveAttribute('data-maturity', 'design-partner');
  });

  it('renders the preview label for level=preview', () => {
    render(<MaturityBadge level="preview" testId="badge" />);
    expect(screen.getByTestId('badge')).toHaveTextContent(/preview/i);
  });

  it('renders the internal label for level=internal', () => {
    render(<MaturityBadge level="internal" testId="badge" />);
    expect(screen.getByTestId('badge')).toHaveTextContent(/internal/i);
  });

  it('exposes a default aria-label naming the maturity', () => {
    render(<MaturityBadge level="production" testId="badge" />);
    const badge = screen.getByTestId('badge');
    expect(badge).toHaveAttribute('aria-label', 'Production maturity');
  });

  it('honors a custom aria-label', () => {
    render(
      <MaturityBadge
        level="design-partner"
        ariaLabel="Currently piloting with two retailers"
        testId="badge"
      />,
    );
    expect(screen.getByTestId('badge')).toHaveAttribute(
      'aria-label',
      'Currently piloting with two retailers',
    );
  });
});
