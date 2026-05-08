import '@testing-library/jest-dom';
import { render, screen } from '@testing-library/react';
import { ValueProp } from '@/components/molecules/ValueProp';
import { ValuePropGrid } from '@/components/molecules/ValuePropGrid';

/**
 * ValueProp / ValuePropGrid contract tests (ADR-035 §54 / Issue #1057).
 *
 * Pin the honesty-enforcement composition: every card renders its
 * MaturityBadge; quantitative cards always render their ConfidenceInterval.
 * The strict cardinality lock on the home grid is enforced by TypeScript
 * (compile time) — at runtime the flexible variant rejects 0–2 and 6+.
 */

describe('ValueProp', () => {
  it('renders qualitative card with maturity badge and no confidence', () => {
    render(
      <ValueProp
        kind="qualitative"
        headline="MCP-only agent-to-agent"
        body="Every cross-agent call rides MCP — including memory and skills."
        maturity="production"
        testId="vp"
      />,
    );
    const card = screen.getByTestId('vp');
    expect(card).toHaveAttribute('data-valueprop-kind', 'qualitative');
    expect(card).toHaveAttribute('data-maturity', 'production');
    expect(card).toHaveTextContent(/MCP-only agent-to-agent/);
    expect(card).toHaveTextContent(/production/i);
  });

  it('renders quantitative card with maturity badge and confidence interval', () => {
    render(
      <ValueProp
        kind="quantitative"
        headline="Replenishment review time"
        body="Cuts the manual replenishment loop substantially."
        maturity="design-partner"
        confidence={{
          lower: '35',
          upper: '55',
          unit: 'minutes',
          baseline: { lower: '4', upper: '7', unit: 'hours' },
          sampleSize: 3,
          population: 'design partners',
          methodology: 'observed Jan 2026',
        }}
        testId="vp"
      />,
    );
    const card = screen.getByTestId('vp');
    expect(card).toHaveAttribute('data-valueprop-kind', 'quantitative');
    expect(card).toHaveTextContent(/n=3 design partners/);
  });
});

describe('ValuePropGrid', () => {
  const items3 = [1, 2, 3].map((i) => ({
    kind: 'qualitative' as const,
    headline: `Card ${i}`,
    body: 'Body copy.',
    maturity: 'production' as const,
  }));

  it('strict three renders exactly three cards', () => {
    render(
      <ValuePropGrid
        cardinality="three"
        items={[items3[0], items3[1], items3[2]]}
        testId="grid"
      />,
    );
    const grid = screen.getByTestId('grid');
    expect(grid).toHaveAttribute('data-valueprop-grid', 'three');
    expect(grid.querySelectorAll('[data-valueprop-kind]')).toHaveLength(3);
  });

  it('three-to-five accepts 4 cards', () => {
    const items4 = [...items3, { ...items3[0], headline: 'Card 4' }];
    render(<ValuePropGrid cardinality="three-to-five" items={items4} testId="grid" />);
    expect(screen.getByTestId('grid').querySelectorAll('[data-valueprop-kind]')).toHaveLength(4);
  });

  it('three-to-five throws on 2 cards', () => {
    expect(() =>
      render(
        <ValuePropGrid
          cardinality="three-to-five"
          items={[items3[0], items3[1]]}
          testId="grid"
        />,
      ),
    ).toThrow(/cardinality must be 3.{1,3}5/);
  });

  it('three-to-five throws on 6 cards', () => {
    const items6 = [...items3, ...items3];
    expect(() =>
      render(<ValuePropGrid cardinality="three-to-five" items={items6} testId="grid" />),
    ).toThrow(/cardinality must be 3.{1,3}5/);
  });
});
