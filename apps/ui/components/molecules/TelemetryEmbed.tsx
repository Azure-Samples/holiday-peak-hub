import type { ReactElement } from 'react';

/**
 * TelemetryEmbed — App Insights workbook iframe with demo-data banner
 * (Issue #1050 / Epic #1053).
 *
 * Hard rules from Epic #1053:
 *   - Banner: "This is the public demo deployment, not customer data.
 *     Refreshes hourly. Latency to truth ≤ 1 h." UNMISSABLE.
 *   - App Insights ingestion cap configured server-side (workflow-level).
 *   - Workbook URL is configured via NEXT_PUBLIC_TELEMETRY_WORKBOOK_URL;
 *     if absent, the embed renders a placeholder explaining how to wire it.
 *   - No customer data is rendered here. Period.
 *
 * The banner is the FIRST element in source order so screen readers
 * announce the demo-only context before the iframe.
 */

export type TelemetryEmbedProps = {
  /** App Insights workbook embed URL. */
  workbookUrl?: string;
  /** Hourly refresh footer caption. */
  caption?: string;
  testId?: string;
};

const SECTION_STYLE = {
  display: 'flex',
  flexDirection: 'column' as const,
  gap: '0.75rem',
  padding: 'clamp(2rem, 5vw, 3rem) 1.5rem',
  background: 'var(--sys-surface, var(--hp-surface))',
  borderRadius: 'var(--radius-lg, 1rem)',
  maxWidth: '78rem',
  margin: '0 auto',
  width: '100%',
};

const BANNER_STYLE = {
  padding: '0.75rem 1rem',
  borderRadius: 'var(--radius-md, 0.5rem)',
  border: '1px solid var(--sys-warning-border, var(--hp-warning-border))',
  background: 'var(--sys-warning-bg, var(--hp-warning-bg))',
  color: 'var(--sys-warning-text, var(--hp-warning-text))',
  fontSize: '0.875rem',
  fontWeight: 600,
};

const IFRAME_WRAP_STYLE = {
  position: 'relative' as const,
  width: '100%',
  paddingTop: '62%',
  background: 'var(--sys-surface-base, var(--hp-bg))',
  borderRadius: 'var(--radius-md, 0.5rem)',
  overflow: 'hidden' as const,
  border: '1px solid var(--sys-border, var(--hp-border))',
};

const IFRAME_STYLE = {
  position: 'absolute' as const,
  inset: 0,
  width: '100%',
  height: '100%',
  border: 0,
};

const PLACEHOLDER_STYLE = {
  display: 'flex',
  flexDirection: 'column' as const,
  gap: '0.75rem',
  padding: '2.5rem 1.5rem',
  textAlign: 'center' as const,
  background: 'var(--sys-surface-base, var(--hp-bg))',
  borderRadius: 'var(--radius-md, 0.5rem)',
  border: '1px dashed var(--sys-border, var(--hp-border))',
  color: 'var(--sys-text-muted, var(--hp-text-muted))',
  fontSize: '0.9375rem',
  lineHeight: 1.6,
};

const CAPTION_STYLE = {
  fontSize: '0.8125rem',
  color: 'var(--sys-text-muted, var(--hp-text-muted))',
};

export function TelemetryEmbed({
  workbookUrl,
  caption,
  testId,
}: TelemetryEmbedProps): ReactElement {
  return (
    <section
      data-testid={testId}
      data-telemetry-embed
      data-has-workbook={Boolean(workbookUrl).toString()}
      style={SECTION_STYLE}
    >
      <p
        role="status"
        data-demo-banner
        style={BANNER_STYLE}
      >
        PUBLIC DEMO ONLY. This is the public demo deployment, not customer data.
        Refreshes hourly. Latency to truth ≤ 1 h.
      </p>
      {workbookUrl ? (
        <div style={IFRAME_WRAP_STYLE}>
          <iframe
            src={workbookUrl}
            title="App Insights — public demo workbook"
            loading="lazy"
            referrerPolicy="no-referrer"
            sandbox="allow-scripts allow-same-origin allow-forms"
            style={IFRAME_STYLE}
          />
        </div>
      ) : (
        <div style={PLACEHOLDER_STYLE} data-placeholder>
          <p>
            <strong>Workbook URL not configured.</strong>
          </p>
          <p>
            Set the <code>NEXT_PUBLIC_TELEMETRY_WORKBOOK_URL</code> environment
            variable to embed the App Insights workbook here. The workbook is
            shipped under{' '}
            <code>infra/observability/workbooks/public-demo.bicep</code> and
            limited by an ingestion cap to control cost.
          </p>
        </div>
      )}
      {caption ? <p style={CAPTION_STYLE}>{caption}</p> : null}
    </section>
  );
}
