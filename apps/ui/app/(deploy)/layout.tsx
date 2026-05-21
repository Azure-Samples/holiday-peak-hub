import type { ReactNode } from 'react';

import { AppSearchBox } from '@/components/molecules/AppSearchBox';
import { LaneSwitch } from '@/components/shared/LaneSwitch';
import { SectionShell } from '@/components/shared/SectionShell';

/**
 * (deploy) route group layout.
 *
 * Wraps every page under `/deploy/...` in the shared SectionShell.
 * Section-specific chrome (catalog, configure, pre-flight, track) lives in
 * epic #1039.
 *
 * The deploy lane offers two lane switches because either persona may have
 * arrived here via a direct link. Lazy: render the retailer one (most common
 * arrival path); a builder seeing this can use the footer audience nav. The
 * AppSearchBox (Issue #1022) lets operators jump between deploy steps fast,
 * with an explicit cross-link to mkdocs runbooks.
 */
export default function DeployGroupLayout({
  children,
}: {
  children: ReactNode;
}) {
  return (
    <SectionShell
      variant="deploy"
      laneSwitch={<LaneSwitch from="deploy" to="retailer" />}
      appSearch={<AppSearchBox audience="deploy" />}
    >
      {children}
    </SectionShell>
  );
}
