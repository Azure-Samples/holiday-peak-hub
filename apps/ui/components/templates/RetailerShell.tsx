import type { ReactElement, ReactNode } from 'react';
import { SectionShell } from '../shared/SectionShell';

/**
 * RetailerShell — the warm-cognitive-model shell (ADR-035 §54 / Issue #1057).
 *
 * Wraps `SectionShell` with `variant="retailer"`. The `data-audience` attribute
 * emitted by `SectionShell` re-binds system tokens to the warm palette
 * (`--color-warm-500` etc.). Composites inside this shell consume system
 * tokens and pick up the warm palette automatically.
 */
export type RetailerShellProps = {
  children: ReactNode;
  breadcrumb?: ReactNode;
  laneSwitch?: ReactNode;
};

export function RetailerShell({ children, breadcrumb, laneSwitch }: RetailerShellProps): ReactElement {
  return (
    <SectionShell variant="retailer" breadcrumb={breadcrumb} laneSwitch={laneSwitch}>
      {children}
    </SectionShell>
  );
}
