import type { ReactElement, ReactNode } from 'react';
import { SectionShell } from '../shared/SectionShell';

/**
 * HomeShell — the audience-router shell (ADR-035 §54 / Issue #1057).
 *
 * Wraps `SectionShell` with `variant="home"`. Owned slots:
 *   - `breadcrumb`  : optional breadcrumb element above the hero
 *   - `laneSwitch`  : the lane-switch persona toggle (filled by the
 *                     audience-IA persona switcher; never rendered on `/`
 *                     for the audience-router itself)
 *
 * Adding a fifth shell variant requires amending ADR-034.
 */
export type HomeShellProps = {
  children: ReactNode;
  breadcrumb?: ReactNode;
  laneSwitch?: ReactNode;
};

export function HomeShell({ children, breadcrumb, laneSwitch }: HomeShellProps): ReactElement {
  return (
    <SectionShell variant="home" breadcrumb={breadcrumb} laneSwitch={laneSwitch}>
      {children}
    </SectionShell>
  );
}
