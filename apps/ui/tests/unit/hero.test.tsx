import '@testing-library/jest-dom';
import { render, screen } from '@testing-library/react';
import { Hero } from '@/components/molecules/Hero';

/**
 * Hero contract tests (ADR-035 §54 / Issue #1057).
 *
 * Pin the discriminated-union behaviour:
 *   - audience-router : two equally-weighted CTAs always render
 *   - audience-page   : single primary CTA, optional secondary
 *   - docs            : no CTA cluster
 */
describe('Hero', () => {
  it('renders both audience-router CTAs as primary', () => {
    render(
      <Hero
        kind="audience-router"
        headline="Pick your lane"
        sub="Retailers see outcomes; builders see architecture."
        primaryCta={{ label: "I'm a retailer", href: '/retailers' }}
        secondaryCta={{ label: "I'm a builder", href: '/builders' }}
        testId="hero"
      />,
    );
    const hero = screen.getByTestId('hero');
    expect(hero).toHaveAttribute('data-hero-kind', 'audience-router');
    expect(screen.getByRole('link', { name: /retailer/i })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /builder/i })).toBeInTheDocument();
    expect(screen.getAllByRole('link')).toHaveLength(2);
  });

  it('renders audience-page hero with single primary when no secondary', () => {
    render(
      <Hero
        kind="audience-page"
        headline="See it on your data"
        sub="Outcome-led headline."
        primaryCta={{ label: 'See it on your data', href: '/retailers/value' }}
        testId="hero"
      />,
    );
    expect(screen.getByTestId('hero')).toHaveAttribute('data-hero-kind', 'audience-page');
    expect(screen.getAllByRole('link')).toHaveLength(1);
  });

  it('renders audience-page hero with both ctas when secondary provided', () => {
    render(
      <Hero
        kind="audience-page"
        headline="See architecture"
        sub="Capability-led headline."
        primaryCta={{ label: 'See architecture →', href: '/builders/architecture' }}
        secondaryCta={{ label: 'Browse agent catalog →', href: '/builders/agents' }}
        testId="hero"
      />,
    );
    expect(screen.getAllByRole('link')).toHaveLength(2);
  });

  it('docs hero has no CTA cluster', () => {
    render(<Hero kind="docs" headline="Documentation" sub="Architecture, governance, ops." testId="hero" />);
    expect(screen.getByTestId('hero')).toHaveAttribute('data-hero-kind', 'docs');
    expect(screen.queryAllByRole('link')).toHaveLength(0);
  });
});
