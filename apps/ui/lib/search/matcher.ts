import { APP_PAGES, type AppPage } from './appPages';

/**
 * Lightweight in-memory search matcher (Issue #1022).
 *
 * The audience-IA corpus is ~20 pages — too small to justify a Pagefind
 * binary postbuild step in v1, but big enough that a deterministic
 * substring + token matcher produces stable, useful suggestions on first
 * paint. The Pagefind Node-API integration remains a v1.5 follow-up that
 * uses the same `APP_PAGES` manifest as `addCustomRecord` input.
 *
 * Scoring (higher is better):
 *   +10 — query token matches `title` (case-insensitive substring).
 *   +5  — query token matches any `keywords` entry.
 *   +2  — query token matches `description`.
 *   +1  — query token matches `url`.
 *
 * Multi-token queries score additively per token and per page. Empty queries
 * return the first 6 pages from the audience-filtered manifest as a static
 * suggestion list.
 *
 * Audience filtering follows `AUDIENCE_FILTER`: a builder-shell search
 * surfaces builder + home pages, and the cross-link CTA opens the docs
 * search instead of crossing into the retailer lane silently.
 */

export type SearchHit = {
  page: AppPage;
  score: number;
};

const TOKEN_SPLIT = /\s+/u;

function tokenize(value: string): string[] {
  return value
    .toLowerCase()
    .trim()
    .split(TOKEN_SPLIT)
    .filter(Boolean);
}

function scorePage(page: AppPage, queryTokens: string[]): number {
  if (queryTokens.length === 0) {
    return 0;
  }
  const titleLower = page.title.toLowerCase();
  const descriptionLower = page.description.toLowerCase();
  const urlLower = page.url.toLowerCase();
  const keywordsLower = page.keywords.map((kw) => kw.toLowerCase());

  let score = 0;
  for (const token of queryTokens) {
    if (titleLower.includes(token)) {
      score += 10;
    }
    if (keywordsLower.some((kw) => kw.includes(token))) {
      score += 5;
    }
    if (descriptionLower.includes(token)) {
      score += 2;
    }
    if (urlLower.includes(token)) {
      score += 1;
    }
  }
  return score;
}

/**
 * Search the audience-IA corpus.
 *
 * @param query - Free-text query. Empty string returns first-paint suggestions.
 * @param audiences - Allowed audience buckets. Use `AUDIENCE_FILTER[variant]`.
 * @param limit - Maximum hits returned. Defaults to 6.
 */
export function searchAppPages(
  query: string,
  audiences: readonly AppPage['audience'][],
  limit = 6,
): SearchHit[] {
  const allowed = APP_PAGES.filter((page) => audiences.includes(page.audience));
  const queryTokens = tokenize(query);

  if (queryTokens.length === 0) {
    return allowed.slice(0, limit).map((page) => ({ page, score: 0 }));
  }

  const scored = allowed
    .map((page) => ({ page, score: scorePage(page, queryTokens) }))
    .filter((hit) => hit.score > 0)
    .sort((a, b) => {
      if (b.score !== a.score) {
        return b.score - a.score;
      }
      return a.page.title.localeCompare(b.page.title);
    });

  return scored.slice(0, limit);
}

/**
 * Build a docs-search URL for the cross-link CTA.
 *
 * The mkdocs Material search results page accepts `?q=<term>` and renders
 * matches inline. When the query is empty we link to `/docs/search/` so
 * users land on the docs search page even before typing.
 */
export function buildDocsSearchUrl(query: string): string {
  const trimmed = query.trim();
  if (trimmed.length === 0) {
    return '/docs/search/';
  }
  return `/docs/search/?q=${encodeURIComponent(trimmed)}`;
}
