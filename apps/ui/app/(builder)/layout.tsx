import type { ReactNode } from 'react';

import { AppSearchBox } from '@/components/molecules/AppSearchBox';
import { LaneSwitch } from '@/components/shared/LaneSwitch';
import { SectionShell } from '@/components/shared/SectionShell';

/**
 * (builder) route group layout.
 *
 * Wraps every page under `/builders/...` in the shared SectionShell.
 * Section-specific chrome (architecture diagrams, ADR registry, telemetry,
 * enablement) lives in epic #1053.
 *
 * Per ADR-034 every page in this group renders a LaneSwitch CTA so a retailer
 * who lands on `/builders/architecture` directly via SEO can switch lanes,
 * and an AppSearchBox (Issue #1022) so engineers can navigate the builder
 * pages and cross-link into the mkdocs Material search.
 */
export default function BuilderGroupLayout({
  children,
}: {
  children: ReactNode;
}) {
  return (
    <SectionShell
      variant="builder"
      laneSwitch={<LaneSwitch from="builder" to="retailer" />}
      appSearch={<AppSearchBox audience="builder" />}
    >
      {children}
    </SectionShell>
  );
}
