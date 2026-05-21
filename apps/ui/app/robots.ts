import type { MetadataRoute } from 'next';

import { SEO_CONFIG } from '@/lib/seo';

/**
 * robots.txt — points to the segmented sitemap per ADR-034 §6.
 */
export default function robots(): MetadataRoute.Robots {
  return {
    rules: [
      {
        userAgent: '*',
        allow: '/',
        disallow: ['/api/'],
      },
    ],
    sitemap: `${SEO_CONFIG.SITE_URL}/sitemap.xml`,
  };
}
