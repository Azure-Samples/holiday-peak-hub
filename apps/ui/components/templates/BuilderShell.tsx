import type { ReactElement, ReactNode } from 'react';
import { SectionShell } from '../shared/SectionShell';

/**
 * BuilderShell — the cool-cognitive-model shell (ADR-035 §54 / Issue #1057).
 *
 * Wraps `SectionShell` with `variant="builder"`. The `data-audience` attribute
 * emitted by `SectionShell` re-binds system tokens to the cool palette
 * (`--color-cool-500` etc.). Composites inside this shell consume system
 * tokens and pick up the cool palette automatically.
 */
export type BuilderShellProps = {
  children: ReactNode;
  breadcrumb?: ReactNode;
  laneSwitch?: ReactNode;
};

export function BuilderShell({ children, breadcrumb, laneSwitch }: BuilderShellProps): ReactElement {
  return (
    <SectionShell variant="builder" breadcrumb={breadcrumb} laneSwitch={laneSwitch}>
      {children}
    </SectionShell>
  );
}
