import type { ReactNode } from 'react';

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
 * arrival path); a builder seeing this can use the footer audience nav.
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
    >
      {children}
    </SectionShell>
  );
}
