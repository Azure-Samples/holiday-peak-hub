import type { MetadataRoute } from 'next';

import { SEO_CONFIG } from '@/lib/seo';

/**
 * Segmented sitemap per ADR-034 §6.
 *
 * Sections are grouped (retailer, builder, deploy, docs, home) so the lanes
 * do not compete for the same impressions in organic search. The mkdocs
 * subtree maintains its own `/docs/sitemap.xml`; the entry below references
 * that subtree without duplicating its URLs (cross-reference rule).
 *
 * `priority` and `changeFrequency` reflect the editorial cadence:
 *   - 1.0 / weekly for the home — always relevant.
 *   - 0.9 / weekly for top-level audience landings.
 *   - 0.7 / monthly for deeper section pages once they ship.
 *   - 0.5 / monthly for the docs subtree pointer.
 */
export default function sitemap(): MetadataRoute.Sitemap {
  const base = SEO_CONFIG.SITE_URL;
  const lastModified = new Date();

  const entries: MetadataRoute.Sitemap = [
    {
      url: `${base}/`,
      lastModified,
      changeFrequency: 'weekly',
      priority: 1.0,
    },
    {
      url: `${base}/retailers`,
      lastModified,
      changeFrequency: 'weekly',
      priority: 0.9,
    },
    {
      url: `${base}/retailers/value`,
      lastModified,
      changeFrequency: 'monthly',
      priority: 0.7,
    },
    {
      url: `${base}/retailers/agents`,
      lastModified,
      changeFrequency: 'monthly',
      priority: 0.7,
    },
    {
      url: `${base}/retailers/roi`,
      lastModified,
      changeFrequency: 'monthly',
      priority: 0.7,
    },
    {
      url: `${base}/retailers/comparators`,
      lastModified,
      changeFrequency: 'monthly',
      priority: 0.7,
    },
    {
      url: `${base}/retailers/case-studies`,
      lastModified,
      changeFrequency: 'monthly',
      priority: 0.6,
    },
    {
      url: `${base}/retailers/security`,
      lastModified,
      changeFrequency: 'monthly',
      priority: 0.7,
    },
    {
      url: `${base}/builders`,
      lastModified,
      changeFrequency: 'weekly',
      priority: 0.9,
    },
    {
      url: `${base}/builders/architecture`,
      lastModified,
      changeFrequency: 'monthly',
      priority: 0.7,
    },
    {
      url: `${base}/builders/adrs`,
      lastModified,
      changeFrequency: 'monthly',
      priority: 0.7,
    },
    {
      url: `${base}/builders/patterns`,
      lastModified,
      changeFrequency: 'monthly',
      priority: 0.7,
    },
    {
      url: `${base}/builders/telemetry`,
      lastModified,
      changeFrequency: 'monthly',
      priority: 0.6,
    },
    {
      url: `${base}/deploy`,
      lastModified,
      changeFrequency: 'monthly',
      priority: 0.8,
    },
    {
      url: `${base}/deploy/catalog`,
      lastModified,
      changeFrequency: 'monthly',
      priority: 0.7,
    },
    {
      url: `${base}/deploy/configure`,
      lastModified,
      changeFrequency: 'monthly',
      priority: 0.7,
    },
    {
      url: `${base}/deploy/preflight`,
      lastModified,
      changeFrequency: 'monthly',
      priority: 0.6,
    },
    {
      // Cross-reference to the mkdocs sitemap. Search engines follow nested
      // sitemap pointers; we don't duplicate the URLs.
      url: `${base}/docs/sitemap.xml`,
      lastModified,
      changeFrequency: 'monthly',
      priority: 0.5,
    },
  ];

  return entries;
}
