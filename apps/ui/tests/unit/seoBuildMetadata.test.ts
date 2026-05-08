import { buildMetadata, SEO_CONFIG } from '@/lib/seo/buildMetadata';

describe('lib/seo/buildMetadata', () => {
  it('appends section title suffix when title is provided', () => {
    const meta = buildMetadata({
      section: 'retailer',
      title: 'ROI Calculator',
      description: 'Estimate the value.',
      path: '/retailers/roi',
    });
    expect(meta.title).toBe(
      'ROI Calculator — For Retailers — Holiday Peak Hub',
    );
    expect(meta.description).toBe('Estimate the value.');
  });

  it('uses the section title suffix as the full title when no title is provided', () => {
    const meta = buildMetadata({
      section: 'home',
      description: 'Pick your lane.',
      path: '/',
    });
    expect(meta.title).toBe('Holiday Peak Hub');
  });

  it('produces canonical and og:url that match the path', () => {
    const meta = buildMetadata({
      section: 'builder',
      title: 'Architecture',
      description: 'See the architecture.',
      path: '/builders/architecture',
    });
    const expected = `${SEO_CONFIG.SITE_URL}/builders/architecture`;
    expect(meta.alternates?.canonical).toBe(expected);
    expect(meta.openGraph?.url).toBe(expected);
  });

  it('selects the per-section OG image by default', () => {
    const meta = buildMetadata({
      section: 'deploy',
      description: 'Spin up your own.',
      path: '/deploy',
    });
    const images = meta.openGraph?.images as Array<{ url: string }> | undefined;
    expect(images?.[0]?.url).toBe('/og/deploy.svg');
  });

  it('honours an explicit ogImage override', () => {
    const meta = buildMetadata({
      section: 'retailer',
      title: 'Case study',
      description: 'A retailer story.',
      path: '/retailers/case-studies/contoso',
      ogImage: '/og/cases/contoso.svg',
    });
    const images = meta.openGraph?.images as Array<{ url: string }> | undefined;
    expect(images?.[0]?.url).toBe('/og/cases/contoso.svg');
    const twitterImages = meta.twitter?.images as string[] | undefined;
    expect(twitterImages?.[0]).toBe('/og/cases/contoso.svg');
  });

  it('emits Twitter summary_large_image card', () => {
    const meta = buildMetadata({
      section: 'home',
      description: 'Pick your lane.',
      path: '/',
    });
    expect(meta.twitter?.card).toBe('summary_large_image');
  });

  it('uses en_US locale and website type for OG', () => {
    const meta = buildMetadata({
      section: 'builder',
      description: 'Architecture.',
      path: '/builders',
    });
    expect(meta.openGraph?.locale).toBe('en_US');
    expect(meta.openGraph?.type).toBe('website');
  });
});
