import '@testing-library/jest-dom';

import { render, screen, fireEvent } from '@testing-library/react';

import { LaneSwitch, type LaneAudience } from '@/components/shared/LaneSwitch';

describe('LaneSwitch', () => {
  beforeEach(() => {
    // Reset cookies between tests so persona-update assertions are isolated.
    document.cookie.split(';').forEach((entry) => {
      const name = entry.split('=')[0]?.trim();
      if (name) {
        document.cookie = `${name}=; Max-Age=0; Path=/`;
      }
    });
  });

  const PAIRS: Array<[LaneAudience, LaneAudience, string, string]> = [
    [
      'retailer',
      'builder',
      "I'm building on this platform — show me the architecture",
      '/builders',
    ],
    [
      'builder',
      'retailer',
      'I run a retail business — show me the value',
      '/retailers',
    ],
    [
      'retailer',
      'deploy',
      'Skip ahead — let me deploy it',
      '/deploy',
    ],
    [
      'builder',
      'deploy',
      'Skip ahead — let me deploy it',
      '/deploy',
    ],
  ];

  describe('copy snapshot — covers all from→to permutations', () => {
    it.each(PAIRS)(
      'renders correct copy and href for %s → %s',
      (from, to, expectedCopy, expectedHref) => {
        render(<LaneSwitch from={from} to={to} />);
        const link = screen.getByRole('link', {
          name: `Switch to the ${to} lane`,
        });
        expect(link).toHaveAttribute('href', expectedHref);
        expect(link).toHaveTextContent(expectedCopy);
        expect(link).toHaveAttribute('data-lane-from', from);
        expect(link).toHaveAttribute('data-lane-to', to);
      },
    );
  });

  it('renders nothing when from === to (defensive guard)', () => {
    const { container } = render(
      <LaneSwitch from="retailer" to={'retailer' as LaneAudience} />,
    );
    expect(container.firstChild).toBeNull();
  });

  it('updates the persona cookie on click for retailer/builder targets', () => {
    render(<LaneSwitch from="retailer" to="builder" />);
    const link = screen.getByRole('link', {
      name: 'Switch to the builder lane',
    });
    fireEvent.click(link);
    expect(document.cookie).toContain('persona=builder');
  });

  it('does NOT set the persona cookie when target is deploy (deploy is procedural, not a persona)', () => {
    render(<LaneSwitch from="retailer" to="deploy" />);
    const link = screen.getByRole('link', {
      name: 'Switch to the deploy lane',
    });
    fireEvent.click(link);
    expect(document.cookie).not.toContain('persona=');
  });

  it('exposes a label for screen readers', () => {
    render(<LaneSwitch from="builder" to="retailer" />);
    expect(
      screen.getByRole('link', { name: /switch to the retailer lane/i }),
    ).toBeInTheDocument();
  });
});
