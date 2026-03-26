import React from 'react';
import AuthLayout from '../../app/auth/layout';
import RootLayout from '../../app/layout';

function countTagNodes(node: React.ReactNode, tagName: string): number {
  if (!React.isValidElement(node)) {
    return 0;
  }

  const element = node as React.ReactElement<{ children?: React.ReactNode }>;
  const currentCount = typeof element.type === 'string' && element.type === tagName ? 1 : 0;
  const childCount = React.Children.toArray(element.props.children).reduce<number>(
    (total, child) => total + countTagNodes(child, tagName),
    0
  );

  return currentCount + childCount;
}

describe('auth layout hydration regression', () => {
  it('does not render html or body tags in auth segment layout', () => {
    const authTree = AuthLayout({
      children: <div data-testid="auth-content">Auth content</div>,
    });

    expect(countTagNodes(authTree, 'html')).toBe(0);
    expect(countTagNodes(authTree, 'body')).toBe(0);
  });

  it('keeps a single body in root + auth layout composition', () => {
    const authTree = AuthLayout({
      children: <div data-testid="auth-content">Auth content</div>,
    });

    const tree = RootLayout({
      children: authTree,
    });

    expect(countTagNodes(tree, 'html')).toBe(1);
    expect(countTagNodes(tree, 'body')).toBe(1);
  });
});
