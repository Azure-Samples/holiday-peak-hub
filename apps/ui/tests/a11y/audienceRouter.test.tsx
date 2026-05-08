/**
 * ui-axe-core CI gate — WCAG 2.2 AA on the audience-router pages.
 *
 * Per ADR-034 §7 every audience landing must pass `axe-core` against both
 * the warm/retailer palette and the cool/builder palette. This suite renders
 * representative pages inside their actual route-group layouts (so the
 * `[data-section="…"]` token scoping is in effect) and asserts zero
 * AA violations.
 *
 * The CI job `ui-axe-core` (.github/workflows/ui-axe-core.yml) executes only
 * the tests under `tests/a11y/` so a flake here is an a11y signal, not a
 * generic test-suite failure.
 */
import './jest-axe.d';

import '@testing-library/jest-dom';

import { render } from '@testing-library/react';
import { toHaveNoViolations } from 'jest-axe';

import RetailerLayout from '@/app/(retailer)/layout';
import RetailersIndexPage from '@/app/(retailer)/retailers/page';
import BuilderLayout from '@/app/(builder)/layout';
import BuildersIndexPage from '@/app/(builder)/builders/page';
import DeployLayout from '@/app/(deploy)/layout';
import DeployIndexPage from '@/app/(deploy)/deploy/page';
import { HomeSplitHero } from '@/components/shared/HomeSplitHero';

import { axeAA } from './axeConfig';

expect.extend(toHaveNoViolations);

describe('ui-axe-core — WCAG 2.2 AA gate (ADR-034 §7)', () => {
  it('home audience-router has zero AA violations', async () => {
    // HomePage is async (resolves persona from cookies/searchParams). Axe
    // exercises the actually-interactive payload, which is HomeSplitHero
    // — the rest of the home is static wrapper copy.
    const { container } = render(<HomeSplitHero persona={null} />);
    const results = await axeAA(container);
    expect(results).toHaveNoViolations();
  });

  it('retailer landing (warm palette) has zero AA violations', async () => {
    const { container } = render(
      <RetailerLayout>
        <RetailersIndexPage />
      </RetailerLayout>,
    );
    const results = await axeAA(container);
    expect(results).toHaveNoViolations();
  });

  it('builder landing (cool palette) has zero AA violations', async () => {
    const { container } = render(
      <BuilderLayout>
        <BuildersIndexPage />
      </BuilderLayout>,
    );
    const results = await axeAA(container);
    expect(results).toHaveNoViolations();
  });

  it('deploy landing (neutral palette) has zero AA violations', async () => {
    const { container } = render(
      <DeployLayout>
        <DeployIndexPage />
      </DeployLayout>,
    );
    const results = await axeAA(container);
    expect(results).toHaveNoViolations();
  });
});
