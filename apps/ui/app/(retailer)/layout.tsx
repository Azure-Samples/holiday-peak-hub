import type { ReactNode } from 'react';

import { LaneSwitch } from '@/components/shared/LaneSwitch';
import { SectionShell } from '@/components/shared/SectionShell';

/**
 * (retailer) route group layout.
 *
 * Wraps every page under `/retailers/...` in the shared SectionShell.
 * Section-specific chrome (heroes, calculators, comparators) lives in the
 * page-level components and follow-up issues #1040–#1045.
 *
 * Per ADR-034 every page in this group renders a LaneSwitch CTA so a builder
 * who lands on `/retailers/value` directly via SEO can switch lanes.
 */
export default function RetailerGroupLayout({
  children,
}: {
  children: ReactNode;
}) {
  return (
    <SectionShell
      variant="retailer"
      laneSwitch={<LaneSwitch from="retailer" to="builder" />}
    >
      {children}
    </SectionShell>
  );
}
