import type { ReactNode } from 'react';
import { SectionShell } from '@/components/shared/SectionShell';

/**
 * (retailer) route group layout.
 *
 * Wraps every page under `/retailers/...` in the shared SectionShell.
 * Section-specific chrome (heroes, calculators, comparators) lives in the
 * page-level components and follow-up issues #1040–#1045.
 */
export default function RetailerGroupLayout({
  children,
}: {
  children: ReactNode;
}) {
  return <SectionShell variant="retailer">{children}</SectionShell>;
}
