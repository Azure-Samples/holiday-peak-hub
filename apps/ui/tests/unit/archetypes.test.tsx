import { render, screen } from '@testing-library/react';

import HomePage from '@/app/page';
import RetailerLayout from '@/app/(retailer)/layout';
import RetailersIndexPage from '@/app/(retailer)/retailers/page';
import BuilderLayout from '@/app/(builder)/layout';
import BuildersIndexPage from '@/app/(builder)/builders/page';
import DeployLayout from '@/app/(deploy)/layout';
import DeployIndexPage from '@/app/(deploy)/deploy/page';

/**
 * UX-pattern archetype contract tests (Issue #1059).
 *
 * Pin the locked composition order at v1 per `docs/ui/ux-patterns.md`.
 * A future PR re-ordering an archetype trips these tests.
 */

describe('Archetype A: `/` (audience router, neutral)', () => {
  it('renders the audience-router hero with two equally-weighted CTAs', () => {
    render(<HomePage />);
    const hero = screen.getByTestId('home-hero');
    expect(hero).toHaveAttribute('data-hero-kind', 'audience-router');
    expect(screen.getByText("I'm a retailer")).toBeInTheDocument();
    expect(screen.getByText("I'm a builder")).toBeInTheDocument();
  });

  it('renders the cardinality-locked three-card value-prop grid', () => {
    render(<HomePage />);
    const grid = screen.getByTestId('home-value-props');
    expect(grid).toHaveAttribute('data-valueprop-grid', 'three');
    expect(grid.querySelectorAll('[data-valueprop-kind]').length).toBe(3);
  });

  it('renders the audience-pair second-pass CTA', () => {
    render(<HomePage />);
    expect(screen.getByTestId('home-cta-pair')).toBeInTheDocument();
  });

  it('does NOT render a third hero CTA (Hick\'s-Law lock)', () => {
    render(<HomePage />);
    const hero = screen.getByTestId('home-hero');
    // Two anchor children inside the hero CTA cluster.
    expect(hero.querySelectorAll('a').length).toBe(2);
  });
});

describe('Archetype B: `/retailers` (warm)', () => {
  function renderRetailers() {
    return render(
      <RetailerLayout>
        <RetailersIndexPage />
      </RetailerLayout>,
    );
  }

  it('renders the audience-page hero', () => {
    renderRetailers();
    expect(screen.getByTestId('retailers-hero')).toHaveAttribute(
      'data-hero-kind',
      'audience-page',
    );
  });

  it('renders the value-prop grid in the 3-to-5 cardinality', () => {
    renderRetailers();
    const grid = screen.getByTestId('retailers-value-props');
    expect(grid).toHaveAttribute('data-valueprop-grid', 'three-to-five');
  });

  it('renders the before/after comparator with maturity', () => {
    renderRetailers();
    const cmp = screen.getByTestId('retailers-comparator');
    expect(cmp).toHaveAttribute('data-comparator', 'before-after');
    expect(cmp).toHaveAttribute('data-maturity');
  });

  it('renders the agent cluster', () => {
    renderRetailers();
    expect(screen.getByTestId('retailers-agents')).toBeInTheDocument();
  });

  it('renders both the walkthrough CTA and the procurement CTA', () => {
    renderRetailers();
    expect(screen.getByTestId('retailers-cta-walkthrough')).toBeInTheDocument();
    expect(screen.getByTestId('retailers-cta-procurement')).toBeInTheDocument();
  });
});

describe('Archetype C: `/builders` (cool)', () => {
  function renderBuilders() {
    return render(
      <BuilderLayout>
        <BuildersIndexPage />
      </BuilderLayout>,
    );
  }

  it('renders the audience-page hero with dual CTAs', () => {
    renderBuilders();
    expect(screen.getByTestId('builders-hero')).toHaveAttribute(
      'data-hero-kind',
      'audience-page',
    );
  });

  it('renders the technical value-prop grid (3-to-5)', () => {
    renderBuilders();
    const grid = screen.getByTestId('builders-value-props');
    expect(grid).toHaveAttribute('data-valueprop-grid', 'three-to-five');
  });

  it('renders the code-block cluster', () => {
    renderBuilders();
    expect(screen.getByTestId('builders-code-blocks')).toBeInTheDocument();
  });

  it('renders the feature matrix', () => {
    renderBuilders();
    expect(screen.getByTestId('builders-feature-matrix')).toBeInTheDocument();
  });

  it('renders the docs cluster', () => {
    renderBuilders();
    expect(screen.getByTestId('builders-docs')).toBeInTheDocument();
  });

  it('renders the audience-pair CTA at the bottom', () => {
    renderBuilders();
    expect(screen.getByTestId('builders-cta-pair')).toBeInTheDocument();
  });
});

describe('Archetype D: `/deploy` (cool, slate)', () => {
  function renderDeploy() {
    return render(
      <DeployLayout>
        <DeployIndexPage />
      </DeployLayout>,
    );
  }

  it('renders the audience-page hero', () => {
    renderDeploy();
    expect(screen.getByTestId('deploy-hero')).toHaveAttribute(
      'data-hero-kind',
      'audience-page',
    );
  });

  it('renders the 5-step deploy cluster', () => {
    renderDeploy();
    const cluster = screen.getByTestId('deploy-steps');
    expect(cluster).toBeInTheDocument();
    expect(cluster.querySelectorAll('[data-deploy-step]').length).toBe(5);
  });

  it('renders the feature matrix with a Region column', () => {
    renderDeploy();
    const fm = screen.getByTestId('deploy-feature-matrix');
    expect(fm).toBeInTheDocument();
    // Region header is present because showRegion=true.
    expect(fm.textContent).toContain('Region');
  });

  it('renders the post-deploy docs cluster', () => {
    renderDeploy();
    expect(screen.getByTestId('deploy-docs')).toBeInTheDocument();
  });

  it('renders the start CTA at the bottom', () => {
    renderDeploy();
    expect(screen.getByTestId('deploy-cta-start')).toBeInTheDocument();
  });
});
