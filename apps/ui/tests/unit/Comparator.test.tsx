import { render, screen } from '@testing-library/react';

import { Comparator } from '@/components/molecules/Comparator';

describe('Comparator (Issue #1059)', () => {
  it('renders headline, columns, rows, and per-row maturity', () => {
    render(
      <Comparator
        kind="before-after"
        headline="Where the time goes"
        columns={['Manual workflow', 'Agent-assisted']}
        rows={[
          { label: 'Replenishment', before: 'Hours', after: 'Minutes', maturity: 'design-partner' },
          { label: 'Returns', before: 'Manual', after: 'Drafted', maturity: 'preview' },
          { label: 'Segmentation', before: 'SQL', after: 'Brief', maturity: 'design-partner' },
        ]}
        maturity="design-partner"
        testId="cmp"
      />,
    );
    expect(screen.getByTestId('cmp')).toBeInTheDocument();
    expect(screen.getByText(/Where the time goes/)).toBeInTheDocument();
    expect(screen.getByText(/Manual workflow/)).toBeInTheDocument();
    expect(screen.getByText(/Agent-assisted/)).toBeInTheDocument();
    expect(screen.getByText('Replenishment')).toBeInTheDocument();
    expect(screen.getByText('Returns')).toBeInTheDocument();
    expect(screen.getByText('Segmentation')).toBeInTheDocument();
    // Per-row maturity badges render.
    expect(screen.getAllByText(/Design partner|Preview/).length).toBeGreaterThanOrEqual(3);
  });

  it('honors the comparator-level maturity attribute', () => {
    render(
      <Comparator
        kind="before-after"
        headline="X"
        columns={['A', 'B']}
        rows={[{ label: 'r', before: 'b', after: 'a', maturity: 'preview' }]}
        maturity="preview"
        testId="cmp"
      />,
    );
    expect(screen.getByTestId('cmp')).toHaveAttribute('data-maturity', 'preview');
  });
});
