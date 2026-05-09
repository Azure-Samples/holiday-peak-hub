import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';

import { ReadTheDocsCta } from '../../components/molecules/ReadTheDocsCta';
import { TryThisInTheAppCta } from '../../components/molecules/TryThisInTheAppCta';

/**
 * Pin the docs ↔ app cross-link contract from Epic #1026.
 */

describe('ReadTheDocsCta (#1025)', () => {
  it('renders the link with the docs href', () => {
    render(
      <ReadTheDocsCta
        testId="rtd"
        docsHref="/docs/architecture/"
        label="Read the architecture overview"
        caption="Deep treatment with diagrams."
      />,
    );
    const cta = screen.getByTestId('rtd');
    const link = cta.querySelector('a[data-docs-href="/docs/architecture/"]');
    expect(link).toBeInTheDocument();
    expect(cta.textContent).toContain('Read the architecture overview');
    expect(cta.textContent).toContain('Deep treatment with diagrams.');
  });

  it('omits caption when not provided', () => {
    render(
      <ReadTheDocsCta testId="rtd" docsHref="/docs/" label="Docs" />,
    );
    const cta = screen.getByTestId('rtd');
    expect(cta.querySelector('p')).toBeNull();
  });
});

describe('TryThisInTheAppCta (#1024)', () => {
  it('renders the link with the app href', () => {
    render(
      <TryThisInTheAppCta
        testId="try"
        appHref="/deploy/configure"
        label="Try the deploy portal"
        caption="Preview-only path."
      />,
    );
    const cta = screen.getByTestId('try');
    const link = cta.querySelector('a[data-app-href="/deploy/configure"]');
    expect(link).toBeInTheDocument();
    expect(cta.textContent).toContain('Try the deploy portal');
    expect(cta.textContent).toContain('Preview-only path.');
  });
});
