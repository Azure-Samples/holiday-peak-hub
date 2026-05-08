import { render, screen } from '@testing-library/react';

import { CodeBlock } from '@/components/molecules/CodeBlock';
import { CodeBlockCluster } from '@/components/molecules/CodeBlockCluster';

describe('CodeBlock (Issue #1059)', () => {
  it('renders the snippet collapsed by default with a canonical-doc link', () => {
    render(
      <CodeBlock
        label="Call an agent over MCP"
        language="python"
        code="print('hi')"
        canonical={{ label: 'lib/holiday_peak_lib/mcp', href: '/docs/lib/mcp' }}
        testId="cb"
      />,
    );
    const block = screen.getByTestId('cb') as HTMLDetailsElement;
    expect(block.tagName).toBe('DETAILS');
    expect(block.open).toBe(false);
    expect(screen.getByText('Call an agent over MCP')).toBeInTheDocument();
    expect(screen.getByText('python')).toBeInTheDocument();
    expect(screen.getByText("print('hi')")).toBeInTheDocument();
    expect(screen.getByText(/lib\/holiday_peak_lib\/mcp/)).toBeInTheDocument();
  });
});

describe('CodeBlockCluster (Issue #1059)', () => {
  it('renders 3 collapsed snippets', () => {
    render(
      <CodeBlockCluster
        testId="cluster"
        headline="Three things you'll do on day one"
        blocks={[
          {
            label: 'Call',
            language: 'python',
            code: 'a',
            canonical: { label: 'A', href: '/a' },
          },
          {
            label: 'Register',
            language: 'python',
            code: 'b',
            canonical: { label: 'B', href: '/b' },
          },
          {
            label: 'Read',
            language: 'python',
            code: 'c',
            canonical: { label: 'C', href: '/c' },
          },
        ]}
      />,
    );
    expect(screen.getByText(/Three things you'll do on day one/)).toBeInTheDocument();
    expect(screen.getByText('Call')).toBeInTheDocument();
    expect(screen.getByText('Register')).toBeInTheDocument();
    expect(screen.getByText('Read')).toBeInTheDocument();
  });
});
