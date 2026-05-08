import type { ReactNode } from 'react';
import { SectionShell } from '@/components/shared/SectionShell';

/**
 * (deploy) route group layout.
 *
 * Wraps every page under `/deploy/...` in the shared SectionShell.
 * Section-specific chrome (catalog, configure, pre-flight, track) lives in
 * epic #1039.
 */
export default function DeployGroupLayout({
  children,
}: {
  children: ReactNode;
}) {
  return <SectionShell variant="deploy">{children}</SectionShell>;
}
