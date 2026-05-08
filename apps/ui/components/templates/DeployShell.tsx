import type { ReactElement, ReactNode } from 'react';
import { SectionShell } from '../shared/SectionShell';

/**
 * DeployShell — the deploy-funnel shell (ADR-035 §54 / Issue #1057).
 *
 * Wraps `SectionShell` with `variant="deploy"`. The deploy lane shares the
 * cool palette with builder per ADR-034 (deploy is the procedural funnel
 * for both audiences); the visual continuity is intentional.
 */
export type DeployShellProps = {
  children: ReactNode;
  breadcrumb?: ReactNode;
  laneSwitch?: ReactNode;
};

export function DeployShell({ children, breadcrumb, laneSwitch }: DeployShellProps): ReactElement {
  return (
    <SectionShell variant="deploy" breadcrumb={breadcrumb} laneSwitch={laneSwitch}>
      {children}
    </SectionShell>
  );
}
