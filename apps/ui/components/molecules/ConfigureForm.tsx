import type { ReactElement } from 'react';
import { MaturityBadge, type MaturityLevel } from '../atoms/MaturityBadge';

/**
 * ConfigureForm — sub/RG/location/Foundry-endpoint form (Issue #1029 /
 * Epic #1039).
 *
 * v1: pure server-rendered HTML form. The Entra sign-in handshake + the
 * subscription dropdown population happen in a follow-up that wires the
 * deploy-portal API. At v1 the form posts to `/deploy/preflight` and the
 * preflight page renders the static green/red panel.
 */

export type ConfigureFormProps = {
  maturity: MaturityLevel;
  /** ISO 3166-1 + Azure region codes, e.g. westeurope. */
  regions: { code: string; label: string }[];
  /** Where the form posts to. */
  action: string;
  testId?: string;
};

const SECTION_STYLE = {
  display: 'flex',
  flexDirection: 'column' as const,
  gap: '1rem',
  padding: 'clamp(2rem, 5vw, 3rem) 1.5rem',
  background: 'var(--sys-surface, var(--hp-surface))',
  borderRadius: 'var(--radius-lg, 1rem)',
  maxWidth: '52rem',
  margin: '0 auto',
  width: '100%',
};

const HEADLINE_STYLE = {
  fontSize: 'clamp(1.25rem, 2.4vw, 1.75rem)',
  fontWeight: 700,
  color: 'var(--sys-text, var(--hp-text))',
};

const FIELD_GROUP_STYLE = {
  display: 'flex',
  flexDirection: 'column' as const,
  gap: '0.25rem',
};

const LABEL_STYLE = {
  fontSize: '0.8125rem',
  fontWeight: 600,
  color: 'var(--sys-text, var(--hp-text))',
};

const HINT_STYLE = {
  fontSize: '0.75rem',
  color: 'var(--sys-text-muted, var(--hp-text-muted))',
};

const INPUT_STYLE = {
  padding: '0.625rem 0.75rem',
  borderRadius: 'var(--radius-md, 0.5rem)',
  border: '1px solid var(--sys-border, var(--hp-border))',
  background: 'var(--sys-surface-base, var(--hp-bg))',
  color: 'var(--sys-text, var(--hp-text))',
  fontSize: '0.875rem',
};

const BUTTON_STYLE = {
  alignSelf: 'flex-start',
  padding: '0.625rem 1.25rem',
  borderRadius: 'var(--radius-md, 0.5rem)',
  border: 'none',
  background: 'var(--sys-primary, var(--hp-primary))',
  color: 'var(--sys-on-primary, var(--hp-on-primary))',
  fontWeight: 600,
  fontSize: '0.9375rem',
  cursor: 'pointer',
};

export function ConfigureForm({
  maturity,
  regions,
  action,
  testId,
}: ConfigureFormProps): ReactElement {
  return (
    <section data-testid={testId} data-configure-form style={SECTION_STYLE}>
      <header style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: '0.75rem' }}>
        <h2 style={HEADLINE_STYLE}>Configure your deployment</h2>
        <MaturityBadge level={maturity} />
      </header>
      <p style={HINT_STYLE}>
        Sign in to surface the subscriptions you have <code>Owner</code> or{' '}
        <code>Contributor</code> on. We never see your credentials. The deploy-portal
        service has zero standing RBAC on your subscription.
      </p>
      <form action={action} method="POST" style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
        <div style={FIELD_GROUP_STYLE}>
          <label htmlFor="cfg-tenant" style={LABEL_STYLE}>
            Microsoft Entra tenant
          </label>
          <input
            id="cfg-tenant"
            name="tenantId"
            placeholder="contoso.onmicrosoft.com or tenant id"
            required
            style={INPUT_STYLE}
          />
          <span style={HINT_STYLE}>
            We use OBO consent narrowed to the chosen subscription only.
          </span>
        </div>
        <div style={FIELD_GROUP_STYLE}>
          <label htmlFor="cfg-subscription" style={LABEL_STYLE}>
            Subscription id
          </label>
          <input
            id="cfg-subscription"
            name="subscriptionId"
            placeholder="00000000-0000-0000-0000-000000000000"
            pattern="[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
            required
            style={INPUT_STYLE}
          />
        </div>
        <div style={FIELD_GROUP_STYLE}>
          <label htmlFor="cfg-rg" style={LABEL_STYLE}>
            Resource group name
          </label>
          <input
            id="cfg-rg"
            name="resourceGroup"
            placeholder="rg-hph-mytest"
            pattern="^[a-z0-9][a-z0-9-]{2,38}[a-z0-9]$"
            required
            style={INPUT_STYLE}
          />
          <span style={HINT_STYLE}>3–40 chars, lowercase, hyphens allowed.</span>
        </div>
        <div style={FIELD_GROUP_STYLE}>
          <label htmlFor="cfg-region" style={LABEL_STYLE}>
            Region
          </label>
          <select id="cfg-region" name="location" defaultValue={regions[0]?.code} style={INPUT_STYLE}>
            {regions.map((r) => (
              <option key={r.code} value={r.code}>
                {r.label}
              </option>
            ))}
          </select>
        </div>
        <div style={FIELD_GROUP_STYLE}>
          <label htmlFor="cfg-foundry" style={LABEL_STYLE}>
            Azure AI Foundry endpoint (optional)
          </label>
          <input
            id="cfg-foundry"
            name="foundryEndpoint"
            placeholder="https://<project>.<region>.api.azure.com"
            style={INPUT_STYLE}
          />
          <span style={HINT_STYLE}>
            Leave blank to provision a new project under the same subscription.
          </span>
        </div>
        <button type="submit" style={BUTTON_STYLE}>
          Run pre-flight checks →
        </button>
      </form>
    </section>
  );
}
