/**
 * ui-axe-core — WCAG 2.2 AA gate on the audience-IA deep pages (Issue #1019).
 *
 * Sister suite to `audienceRouter.test.tsx`. The landings (home + retailer +
 * builder + deploy) are covered there. This suite extends the gate to the
 * deep pages that shipped in the audience-IA wave (PR #1076 retailers, PR
 * #1077 builders, PR #1078 deploy) so every audience-IA route group has
 * AA-grade chrome — including the AppSearchBox combobox added in PR #1081.
 *
 * The dynamic /deploy/track/[id] page requires route params and is covered
 * by `pagesRender.test.tsx` already; we exclude it here so the gate stays
 * deterministic and fast.
 */
import './jest-axe.d';

import '@testing-library/jest-dom';

import { render } from '@testing-library/react';
import { toHaveNoViolations } from 'jest-axe';

import RetailerLayout from '@/app/(retailer)/layout';
import RetailerValuePage from '@/app/(retailer)/retailers/value/page';
import RetailerAgentsPage from '@/app/(retailer)/retailers/agents/page';
import RetailerRoiPage from '@/app/(retailer)/retailers/roi/page';
import RetailerComparatorsPage from '@/app/(retailer)/retailers/comparators/page';
import RetailerCaseStudiesPage from '@/app/(retailer)/retailers/case-studies/page';
import RetailerSecurityPage from '@/app/(retailer)/retailers/security/page';

import BuilderLayout from '@/app/(builder)/layout';
import BuilderArchitecturePage from '@/app/(builder)/builders/architecture/page';
import BuilderAdrsPage from '@/app/(builder)/builders/adrs/page';
import BuilderPatternsPage from '@/app/(builder)/builders/patterns/page';
import BuilderTelemetryPage from '@/app/(builder)/builders/telemetry/page';
import BuilderEnablementPage from '@/app/(builder)/builders/enablement/page';

import DeployLayout from '@/app/(deploy)/layout';
import DeployCatalogPage from '@/app/(deploy)/deploy/catalog/page';
import DeployConfigurePage from '@/app/(deploy)/deploy/configure/page';
import DeployPreflightPage from '@/app/(deploy)/deploy/preflight/page';

import { axeAA } from './axeConfig';

expect.extend(toHaveNoViolations);

describe('ui-axe-core deep-page coverage — WCAG 2.2 AA gate (ADR-034 §7)', () => {
  describe('retailer (warm palette)', () => {
    it('/retailers/value has zero AA violations', async () => {
      const { container } = render(
        <RetailerLayout>
          <RetailerValuePage />
        </RetailerLayout>,
      );
      expect(await axeAA(container)).toHaveNoViolations();
    });

    it('/retailers/agents has zero AA violations', async () => {
      const { container } = render(
        <RetailerLayout>
          <RetailerAgentsPage />
        </RetailerLayout>,
      );
      expect(await axeAA(container)).toHaveNoViolations();
    });

    it('/retailers/roi has zero AA violations', async () => {
      const { container } = render(
        <RetailerLayout>
          <RetailerRoiPage />
        </RetailerLayout>,
      );
      expect(await axeAA(container)).toHaveNoViolations();
    });

    it('/retailers/comparators has zero AA violations', async () => {
      const { container } = render(
        <RetailerLayout>
          <RetailerComparatorsPage />
        </RetailerLayout>,
      );
      expect(await axeAA(container)).toHaveNoViolations();
    });

    it('/retailers/case-studies has zero AA violations', async () => {
      const { container } = render(
        <RetailerLayout>
          <RetailerCaseStudiesPage />
        </RetailerLayout>,
      );
      expect(await axeAA(container)).toHaveNoViolations();
    });

    it('/retailers/security has zero AA violations', async () => {
      const { container } = render(
        <RetailerLayout>
          <RetailerSecurityPage />
        </RetailerLayout>,
      );
      expect(await axeAA(container)).toHaveNoViolations();
    });
  });

  describe('builder (cool palette)', () => {
    it('/builders/architecture has zero AA violations', async () => {
      const { container } = render(
        <BuilderLayout>
          <BuilderArchitecturePage />
        </BuilderLayout>,
      );
      expect(await axeAA(container)).toHaveNoViolations();
    });

    it('/builders/adrs has zero AA violations', async () => {
      const { container } = render(
        <BuilderLayout>
          <BuilderAdrsPage />
        </BuilderLayout>,
      );
      expect(await axeAA(container)).toHaveNoViolations();
    });

    it('/builders/patterns has zero AA violations', async () => {
      const { container } = render(
        <BuilderLayout>
          <BuilderPatternsPage />
        </BuilderLayout>,
      );
      expect(await axeAA(container)).toHaveNoViolations();
    });

    it('/builders/telemetry has zero AA violations', async () => {
      const { container } = render(
        <BuilderLayout>
          <BuilderTelemetryPage />
        </BuilderLayout>,
      );
      expect(await axeAA(container)).toHaveNoViolations();
    });

    it('/builders/enablement has zero AA violations', async () => {
      const { container } = render(
        <BuilderLayout>
          <BuilderEnablementPage />
        </BuilderLayout>,
      );
      expect(await axeAA(container)).toHaveNoViolations();
    });
  });

  describe('deploy (neutral palette)', () => {
    it('/deploy/catalog has zero AA violations', async () => {
      const { container } = render(
        <DeployLayout>
          <DeployCatalogPage />
        </DeployLayout>,
      );
      expect(await axeAA(container)).toHaveNoViolations();
    });

    it('/deploy/configure has zero AA violations', async () => {
      const { container } = render(
        <DeployLayout>
          <DeployConfigurePage />
        </DeployLayout>,
      );
      expect(await axeAA(container)).toHaveNoViolations();
    });

    it('/deploy/preflight has zero AA violations', async () => {
      const { container } = render(
        <DeployLayout>
          <DeployPreflightPage />
        </DeployLayout>,
      );
      expect(await axeAA(container)).toHaveNoViolations();
    });
  });
});
