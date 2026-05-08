import type { ReactNode } from 'react';
import { SectionShell } from '@/components/shared/SectionShell';

/**
 * (builder) route group layout.
 *
 * Wraps every page under `/builders/...` in the shared SectionShell.
 * Section-specific chrome (architecture diagrams, ADR registry, telemetry,
 * enablement) lives in epic #1053.
 */
export default function BuilderGroupLayout({
  children,
}: {
  children: ReactNode;
}) {
  return <SectionShell variant="builder">{children}</SectionShell>;
}
