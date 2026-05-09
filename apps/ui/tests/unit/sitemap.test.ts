import sitemap from '@/app/sitemap';
import robots from '@/app/robots';
import { SEO_CONFIG } from '@/lib/seo/buildMetadata';

describe('app/sitemap.ts', () => {
  const entries = sitemap();

  it('emits the home, three audience landings, deep audience pages, plus the docs cross-reference', () => {
    const urls = entries.map((entry) => entry.url);
    expect(urls).toEqual(
      expect.arrayContaining([
        `${SEO_CONFIG.SITE_URL}/`,
        `${SEO_CONFIG.SITE_URL}/retailers`,
        `${SEO_CONFIG.SITE_URL}/retailers/value`,
        `${SEO_CONFIG.SITE_URL}/retailers/agents`,
        `${SEO_CONFIG.SITE_URL}/retailers/roi`,
        `${SEO_CONFIG.SITE_URL}/retailers/comparators`,
        `${SEO_CONFIG.SITE_URL}/retailers/case-studies`,
        `${SEO_CONFIG.SITE_URL}/retailers/security`,
        `${SEO_CONFIG.SITE_URL}/builders`,
        `${SEO_CONFIG.SITE_URL}/builders/architecture`,
        `${SEO_CONFIG.SITE_URL}/builders/adrs`,
        `${SEO_CONFIG.SITE_URL}/builders/patterns`,
        `${SEO_CONFIG.SITE_URL}/builders/telemetry`,
        `${SEO_CONFIG.SITE_URL}/deploy`,
        `${SEO_CONFIG.SITE_URL}/deploy/catalog`,
        `${SEO_CONFIG.SITE_URL}/deploy/configure`,
        `${SEO_CONFIG.SITE_URL}/deploy/preflight`,
        `${SEO_CONFIG.SITE_URL}/docs/sitemap.xml`,
      ]),
    );
    expect(urls.length).toBeGreaterThanOrEqual(18);
  });

  it('home has the highest priority', () => {
    const home = entries.find(
      (entry) => entry.url === `${SEO_CONFIG.SITE_URL}/`,
    );
    expect(home?.priority).toBe(1.0);
  });

  it('audience landings sit between home and docs in priority', () => {
    const retailer = entries.find(
      (entry) => entry.url === `${SEO_CONFIG.SITE_URL}/retailers`,
    );
    const builder = entries.find(
      (entry) => entry.url === `${SEO_CONFIG.SITE_URL}/builders`,
    );
    const docs = entries.find((entry) =>
      entry.url.endsWith('/docs/sitemap.xml'),
    );
    expect(retailer?.priority).toBe(0.9);
    expect(builder?.priority).toBe(0.9);
    expect(docs?.priority).toBe(0.5);
  });

  it('every entry has a lastModified timestamp', () => {
    entries.forEach((entry) => {
      expect(entry.lastModified).toBeInstanceOf(Date);
    });
  });
});

describe('app/robots.ts', () => {
  it('points to the segmented sitemap', () => {
    const result = robots();
    expect(result.sitemap).toBe(`${SEO_CONFIG.SITE_URL}/sitemap.xml`);
  });

  it('disallows /api/ and allows everything else', () => {
    const result = robots();
    const rules = Array.isArray(result.rules) ? result.rules : [result.rules];
    const wildcard = rules.find(
      (rule) => rule && (rule.userAgent === '*' || (Array.isArray(rule.userAgent) && rule.userAgent.includes('*'))),
    );
    expect(wildcard).toBeDefined();
    expect(wildcard?.allow).toBe('/');
    expect(wildcard?.disallow).toEqual(['/api/']);
  });
});
