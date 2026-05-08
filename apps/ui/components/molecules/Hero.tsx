import type { ReactElement, ReactNode } from 'react';
import Link from 'next/link';

/**
 * Hero — the audience-router and audience-page hero (ADR-035 §54 / Issue #1057).
 *
 * Discriminated by `kind`:
 *   - `audience-router` : `/` only. Two equally-weighted CTAs by contract.
 *   - `audience-page`   : section index pages. One primary CTA, optional
 *                          secondary outline link.
 *   - `docs`            : docs landing. Headline + breadcrumb-style sub.
 *
 * Composites have no `className` escape hatch. Density / tone are
 * audience-bound through the parent shell's `data-audience` attribute.
 */
export type HeroAudienceRouterProps = {
  kind: 'audience-router';
  headline: string;
  sub: string;
  primaryCta: { label: string; href: string };
  secondaryCta: { label: string; href: string };
  testId?: string;
};

export type HeroAudiencePageProps = {
  kind: 'audience-page';
  headline: string;
  sub: string;
  primaryCta: { label: string; href: string };
  secondaryCta?: { label: string; href: string };
  testId?: string;
};

export type HeroDocsProps = {
  kind: 'docs';
  headline: string;
  sub: string;
  testId?: string;
};

export type HeroProps = HeroAudienceRouterProps | HeroAudiencePageProps | HeroDocsProps;

const SECTION_STYLE = {
  display: 'flex',
  flexDirection: 'column' as const,
  alignItems: 'center',
  textAlign: 'center' as const,
  padding: 'clamp(3rem, 6vw, 5rem) 1.5rem',
  gap: '1.5rem',
  background: 'var(--sys-surface, var(--hp-surface))',
  color: 'var(--sys-text, var(--hp-text))',
};

const HEADING_STYLE = {
  fontSize: 'clamp(1.875rem, 4vw, 3rem)',
  fontWeight: 700,
  lineHeight: 1.15,
  letterSpacing: '-0.02em',
  maxWidth: '52rem',
};

const SUB_STYLE = {
  fontSize: 'clamp(1rem, 1.6vw, 1.125rem)',
  lineHeight: 1.55,
  color: 'var(--sys-text-muted, var(--hp-text-muted))',
  maxWidth: '40rem',
};

const PRIMARY_CTA_STYLE = {
  display: 'inline-flex',
  alignItems: 'center',
  gap: '0.5rem',
  padding: '0.75rem 1.25rem',
  borderRadius: 'var(--radius-md, 0.75rem)',
  background: 'var(--sys-action-primary, var(--hp-primary))',
  color: 'var(--sys-action-primary-foreground, white)',
  fontWeight: 600,
  textDecoration: 'none' as const,
};

const SECONDARY_CTA_STYLE = {
  display: 'inline-flex',
  alignItems: 'center',
  gap: '0.5rem',
  padding: '0.75rem 1.25rem',
  borderRadius: 'var(--radius-md, 0.75rem)',
  border: '1px solid var(--sys-border, var(--hp-border))',
  color: 'var(--sys-text, var(--hp-text))',
  fontWeight: 600,
  textDecoration: 'none' as const,
};

function CtaCluster({ ctas }: { ctas: Array<{ label: string; href: string; primary?: boolean }> }): ReactElement {
  return (
    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.75rem', justifyContent: 'center' }}>
      {ctas.map((cta) => (
        <Link
          key={cta.href}
          href={cta.href}
          style={cta.primary ? PRIMARY_CTA_STYLE : SECONDARY_CTA_STYLE}
        >
          {cta.label}
        </Link>
      ))}
    </div>
  );
}

/**
 * Render the audience-router hero with two equally-weighted CTAs (ADR-034 §1).
 */
function AudienceRouterHero({
  headline,
  sub,
  primaryCta,
  secondaryCta,
  testId,
}: HeroAudienceRouterProps): ReactElement {
  return (
    <section data-testid={testId} data-hero-kind="audience-router" style={SECTION_STYLE}>
      <h1 style={HEADING_STYLE}>{headline}</h1>
      <p style={SUB_STYLE}>{sub}</p>
      <CtaCluster
        ctas={[
          { label: primaryCta.label, href: primaryCta.href, primary: true },
          { label: secondaryCta.label, href: secondaryCta.href, primary: true },
        ]}
      />
    </section>
  );
}

function AudiencePageHero({
  headline,
  sub,
  primaryCta,
  secondaryCta,
  testId,
}: HeroAudiencePageProps): ReactElement {
  const ctas: Array<{ label: string; href: string; primary?: boolean }> = [
    { label: primaryCta.label, href: primaryCta.href, primary: true },
  ];
  if (secondaryCta) {
    ctas.push({ label: secondaryCta.label, href: secondaryCta.href });
  }
  return (
    <section data-testid={testId} data-hero-kind="audience-page" style={SECTION_STYLE}>
      <h1 style={HEADING_STYLE}>{headline}</h1>
      <p style={SUB_STYLE}>{sub}</p>
      <CtaCluster ctas={ctas} />
    </section>
  );
}

function DocsHero({ headline, sub, testId }: HeroDocsProps): ReactElement {
  return (
    <section data-testid={testId} data-hero-kind="docs" style={SECTION_STYLE}>
      <h1 style={HEADING_STYLE}>{headline}</h1>
      <p style={SUB_STYLE}>{sub}</p>
    </section>
  );
}

export function Hero(props: HeroProps): ReactElement {
  if (props.kind === 'audience-router') {
    return <AudienceRouterHero {...props} />;
  }
  if (props.kind === 'audience-page') {
    return <AudiencePageHero {...props} />;
  }
  // docs
  return <DocsHero {...props} />;
}

export type HeroSlot = ReactNode;
