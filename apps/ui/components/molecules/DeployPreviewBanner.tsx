import type { ReactElement } from 'react';
import { MaturityBadge, type MaturityLevel } from '../atoms/MaturityBadge';

/**
 * DeployPreviewBanner — banner shown above every /deploy/* sub-page
 * (Epic #1039 / Issue #1027).
 *
 * The deploy portal is preview / design-partner only at v1. The banner
 * makes that unmissable and links to the canonical `azd up` instructions
 * for users who want a production path today.
 *
 * Hard rules from Epic #1039:
 *   - "No GitHub account required" is a v1 promise; until the OBO + ARM
 *     kickoff lands (#1031), the deploy portal is read-only.
 *   - The banner ships on every sub-page; do not bury this disclosure.
 */

export type DeployPreviewBannerProps = {
  maturity: MaturityLevel;
  fallbackHref?: string;
  testId?: string;
};

const STYLE = {
  display: 'flex',
  flexWrap: 'wrap' as const,
  alignItems: 'center',
  gap: '0.75rem',
  padding: '0.75rem 1rem',
  borderRadius: 'var(--radius-md, 0.5rem)',
  border: '1px solid var(--sys-warning-border, var(--hp-warning-border))',
  background: 'var(--sys-warning-bg, var(--hp-warning-bg))',
  color: 'var(--sys-warning-text, var(--hp-warning-text))',
  fontSize: '0.875rem',
  marginBottom: '1rem',
};

export function DeployPreviewBanner({
  maturity,
  fallbackHref = 'https://github.com/Azure-Samples/holiday-peak-hub/blob/main/docs/deploy/azd-up.md',
  testId,
}: DeployPreviewBannerProps): ReactElement {
  return (
    <aside
      role="status"
      data-testid={testId}
      data-deploy-preview-banner
      data-maturity={maturity}
      style={STYLE}
    >
      <strong>Preview only.</strong>
      <span>
        The one-click deploy flow is design-partner-gated. For the production path today,
        use{' '}
        <a href={fallbackHref} style={{ color: 'inherit', fontWeight: 600 }}>
          azd up
        </a>
        .
      </span>
      <MaturityBadge level={maturity} />
    </aside>
  );
}
