import type { Metadata } from 'next';

/**
 * Audience lanes addressable by the SEO layer.
 *
 * Defined here (instead of imported from `@/components/shared/LaneSwitch`)
 * so the SEO contract stays independent of LaneSwitch's render layer. Once
 * #1012 lands, `LaneAudience` from LaneSwitch is structurally identical to
 * the `'retailer' | 'builder' | 'deploy'` arm of `Section` below.
 */
export type Section = 'retailer' | 'builder' | 'deploy' | 'home' | 'docs';

const SITE_NAME = 'Holiday Peak Hub';

/**
 * Canonical site URL. Set via NEXT_PUBLIC_SITE_URL at build time; falls back
 * to the GitHub Pages preview origin so local builds don't crash. The fallback
 * is a known string and is only used when the env var is missing — production
 * builds set it explicitly via the Static Web Apps deploy workflow.
 */
const SITE_URL =
  process.env.NEXT_PUBLIC_SITE_URL ?? 'https://holiday-peak-hub.example';

const OG_IMAGE_BY_SECTION: Record<Section, string> = {
  home: '/og/home.svg',
  retailer: '/og/retailer.svg',
  builder: '/og/builder.svg',
  deploy: '/og/deploy.svg',
  docs: '/og/docs.svg',
};

const TITLE_SUFFIX_BY_SECTION: Record<Section, string> = {
  home: SITE_NAME,
  retailer: `For Retailers — ${SITE_NAME}`,
  builder: `For Builders — ${SITE_NAME}`,
  deploy: `Deploy — ${SITE_NAME}`,
  docs: `Documentation — ${SITE_NAME}`,
};

export type BuildMetadataInput = {
  /** Audience section the page belongs to. */
  section: Section;
  /** Page title (without site suffix — buildMetadata appends it). */
  title?: string;
  /** Page description; should fit in ~150 chars to avoid truncation. */
  description: string;
  /** Path under the site root, e.g. `/retailers/value`. */
  path: string;
  /** Optional override for the OG image path. */
  ogImage?: string;
};

/**
 * Per-section metadata helper.
 *
 * Per ADR-034 every section page is a valid landing page from organic search
 * and must declare its own title, description, OG tags, and canonical URL.
 *
 * Section pages call this instead of hand-rolling Metadata so that:
 *   - Title suffix stays consistent across all pages in a section.
 *   - OG images stay matched to the audience tone.
 *   - Canonical URLs and og:url stay in sync with the path.
 *
 * The helper does not add `robots` or `alternates.languages` overrides —
 * those land in follow-up issues (i18n is out of scope for ADR-034 v1).
 */
export function buildMetadata({
  section,
  title,
  description,
  path,
  ogImage,
}: BuildMetadataInput): Metadata {
  const fullTitle = title
    ? `${title} — ${TITLE_SUFFIX_BY_SECTION[section]}`
    : TITLE_SUFFIX_BY_SECTION[section];
  const url = new URL(path, SITE_URL).toString();
  const image = ogImage ?? OG_IMAGE_BY_SECTION[section];

  return {
    title: fullTitle,
    description,
    alternates: {
      canonical: url,
    },
    openGraph: {
      title: fullTitle,
      description,
      url,
      siteName: SITE_NAME,
      images: [{ url: image, width: 1200, height: 630, alt: fullTitle }],
      type: 'website',
      locale: 'en_US',
    },
    twitter: {
      card: 'summary_large_image',
      title: fullTitle,
      description,
      images: [image],
    },
  };
}

export const SEO_CONFIG = {
  SITE_NAME,
  SITE_URL,
  OG_IMAGE_BY_SECTION,
} as const;
