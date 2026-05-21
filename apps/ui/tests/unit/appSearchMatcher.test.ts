import {
  buildDocsSearchUrl,
  searchAppPages,
} from '@/lib/search/matcher';
import { AUDIENCE_FILTER } from '@/lib/search/appPages';

describe('searchAppPages', () => {
  it('returns first-paint suggestions when query is empty', () => {
    const hits = searchAppPages('', AUDIENCE_FILTER.home, 4);
    expect(hits).toHaveLength(4);
    expect(hits.every((hit) => hit.score === 0)).toBe(true);
    // Home variant exposes pages from every audience, so the leading suggestion
    // should be the homepage entry.
    expect(hits[0].page.url).toBe('/');
  });

  it('honors audience filter so a builder shell does not surface retailer pages', () => {
    const hits = searchAppPages('', AUDIENCE_FILTER.builder, 20);
    const audiences = new Set(hits.map((hit) => hit.page.audience));
    expect(audiences).toEqual(new Set(['home', 'builder']));
  });

  it('surfaces builder agent detail pages from the shared profile manifest', () => {
    const hits = searchAppPages('product detail enrichment', AUDIENCE_FILTER.builder, 10);
    expect(hits[0].page.url).toBe('/builders/agents/ecommerce-product-detail-enrichment');
  });

  it('scores title matches above description-only matches', () => {
    const hits = searchAppPages('roi', AUDIENCE_FILTER.retailer, 10);
    expect(hits.length).toBeGreaterThan(0);
    expect(hits[0].page.url).toBe('/retailers/roi');
    // Retailer value also contains "roi" in keywords/description but not title,
    // so it must not outrank /retailers/roi.
    const valuePosition = hits.findIndex((hit) => hit.page.url === '/retailers/value');
    if (valuePosition >= 0) {
      expect(hits[0].score).toBeGreaterThan(hits[valuePosition].score);
    }
  });

  it('combines tokens additively for multi-word queries', () => {
    const hits = searchAppPages('preflight checks', AUDIENCE_FILTER.deploy, 5);
    expect(hits[0].page.url).toBe('/deploy/preflight');
  });

  it('returns no hits for queries that match nothing', () => {
    const hits = searchAppPages('zzzzz-no-match-at-all', AUDIENCE_FILTER.home, 6);
    expect(hits).toHaveLength(0);
  });

  it('respects the limit', () => {
    const hits = searchAppPages('', AUDIENCE_FILTER.home, 2);
    expect(hits).toHaveLength(2);
  });
});

describe('buildDocsSearchUrl', () => {
  it('returns the docs search root when query is empty', () => {
    expect(buildDocsSearchUrl('')).toBe('/docs/search/');
    expect(buildDocsSearchUrl('   ')).toBe('/docs/search/');
  });

  it('encodes the query for /docs/search/?q=...', () => {
    expect(buildDocsSearchUrl('hello world')).toBe('/docs/search/?q=hello%20world');
  });

  it('encodes special characters', () => {
    expect(buildDocsSearchUrl('a&b=c')).toBe('/docs/search/?q=a%26b%3Dc');
  });
});
