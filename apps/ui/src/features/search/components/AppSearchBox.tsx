'use client';

import Link from 'next/link';
import {
  type CSSProperties,
  type KeyboardEvent,
  useCallback,
  useEffect,
  useId,
  useMemo,
  useRef,
  useState,
} from 'react';

import { type AppAudience, AUDIENCE_FILTER } from '../internal/appPages';
import { buildDocsSearchUrl, searchAppPages, type SearchHit } from '../internal/matcher';

/**
 * AppSearchBox — lightweight in-app search (Issue #1022).
 *
 * Per ADR-034 + capability 42 the platform ships TWO search boxes, not one:
 *   - mkdocs Material's built-in search serves `/docs/*`.
 *   - This component serves `/retailers/*`, `/builders/*`, `/deploy/*`, and
 *     home, indexing the audience-IA page manifest in `features/search/internal/appPages.ts`.
 *
 * Cross-discovery is achieved by an explicit "Search the docs instead →"
 * footer link inside this dropdown (and a reciprocal link injected into the
 * mkdocs Material search results page — follow-up to this issue).
 *
 * Telemetry contract:
 *   - Result clicks emit `data-telemetry="app-search-result-click"` with
 *     `data-telemetry-url` so App Insights custom events can correlate.
 *   - Cross-link clicks emit `data-telemetry="app-search-cross-link-click"`
 *     so the two-box decision can be revisited if usage diverges.
 */

export type AppSearchBoxProps = {
  /** Audience bucket of the host SectionShell. Filters which pages appear. */
  audience: AppAudience;
  /**
   * Optional placeholder override. Defaults to scope-clarifying copy
   * ("Search retailers + builders + deploy") so users distinguish this
   * from the mkdocs Material box on `/docs/*`.
   */
  placeholder?: string;
  /** Optional max number of result rows. Defaults to 6. */
  limit?: number;
  /** Test hook. */
  testId?: string;
};

const ROOT_STYLE: CSSProperties = {
  position: 'relative',
  width: '100%',
  maxWidth: '24rem',
};

const INPUT_STYLE: CSSProperties = {
  width: '100%',
  padding: '0.5rem 0.75rem',
  borderRadius: 'var(--radius-md, 0.5rem)',
  border: '1px solid var(--sys-border, var(--hp-border, #d1d5db))',
  background: 'var(--sys-surface, var(--hp-surface, #ffffff))',
  color: 'var(--sys-text, var(--hp-text, #111827))',
  fontSize: '0.875rem',
  lineHeight: 1.4,
};

const POPOVER_STYLE: CSSProperties = {
  position: 'absolute',
  left: 0,
  right: 0,
  top: 'calc(100% + 0.25rem)',
  background: 'var(--sys-surface, var(--hp-surface, #ffffff))',
  border: '1px solid var(--sys-border, var(--hp-border, #e5e7eb))',
  borderRadius: 'var(--radius-md, 0.5rem)',
  boxShadow: '0 8px 24px rgba(0, 0, 0, 0.08)',
  padding: '0.5rem',
  zIndex: 50,
  maxHeight: '24rem',
  overflowY: 'auto',
};

const RESULT_BUTTON_STYLE: CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  gap: '0.125rem',
  padding: '0.5rem 0.625rem',
  borderRadius: 'var(--radius-sm, 0.375rem)',
  textDecoration: 'none',
  color: 'inherit',
  background: 'transparent',
};

const RESULT_BUTTON_ACTIVE_STYLE: CSSProperties = {
  ...RESULT_BUTTON_STYLE,
  background: 'var(--sys-surface-base, var(--hp-bg, #f9fafb))',
};

const RESULT_TITLE_STYLE: CSSProperties = {
  fontWeight: 600,
  fontSize: '0.875rem',
  color: 'var(--sys-text, var(--hp-text, #111827))',
};

const RESULT_DESC_STYLE: CSSProperties = {
  fontSize: '0.8125rem',
  color: 'var(--sys-muted, var(--hp-muted, #6b7280))',
  lineHeight: 1.4,
};

const FOOTER_STYLE: CSSProperties = {
  marginTop: '0.5rem',
  paddingTop: '0.5rem',
  borderTop: '1px solid var(--sys-border, var(--hp-border, #e5e7eb))',
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'center',
  gap: '0.5rem',
  fontSize: '0.8125rem',
};

const EMPTY_STYLE: CSSProperties = {
  padding: '0.75rem 0.625rem',
  fontSize: '0.8125rem',
  color: 'var(--sys-muted, var(--hp-muted, #6b7280))',
};

export function AppSearchBox({
  audience,
  placeholder,
  limit = 6,
  testId,
}: AppSearchBoxProps) {
  const inputId = useId();
  const listboxId = `${inputId}-listbox`;
  const containerRef = useRef<HTMLDivElement | null>(null);

  const [query, setQuery] = useState('');
  const [open, setOpen] = useState(false);
  const [activeIndex, setActiveIndex] = useState(-1);

  // Seed the query from the `?q=` URL parameter (Issue #1022 cross-link
  // contract). When the mkdocs Material search results page links to
  // `/?q=<term>`, the home AppSearchBox should pre-populate so the user
  // continues their search seamlessly. Only runs once on mount; we never
  // overwrite user typing.
  useEffect(() => {
    if (typeof window === 'undefined') {
      return;
    }
    const params = new URLSearchParams(window.location.search);
    const incoming = params.get('q');
    if (incoming && incoming.length > 0) {
      setQuery(incoming);
      setOpen(true);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps -- mount only
  }, []);

  const allowedAudiences = AUDIENCE_FILTER[audience];

  const hits: SearchHit[] = useMemo(
    () => searchAppPages(query, allowedAudiences, limit),
    [query, allowedAudiences, limit],
  );

  const docsHref = buildDocsSearchUrl(query);

  const resolvedPlaceholder = useMemo(() => {
    if (placeholder) {
      return placeholder;
    }
    if (audience === 'home') {
      return 'Search retailers + builders + deploy';
    }
    if (audience === 'retailer') {
      return 'Search retailer pages';
    }
    if (audience === 'builder') {
      return 'Search builder pages';
    }
    return 'Search deploy pages';
  }, [audience, placeholder]);

  // Close popover on outside click.
  useEffect(() => {
    if (!open) {
      return undefined;
    }
    const onDocClick = (event: MouseEvent) => {
      if (!containerRef.current) {
        return;
      }
      if (event.target instanceof Node && containerRef.current.contains(event.target)) {
        return;
      }
      setOpen(false);
      setActiveIndex(-1);
    };
    document.addEventListener('mousedown', onDocClick);
    return () => document.removeEventListener('mousedown', onDocClick);
  }, [open]);

  const handleKeyDown = useCallback(
    (event: KeyboardEvent<HTMLInputElement>) => {
      if (event.key === 'ArrowDown') {
        event.preventDefault();
        setOpen(true);
        setActiveIndex((prev) => Math.min(prev + 1, hits.length - 1));
        return;
      }
      if (event.key === 'ArrowUp') {
        event.preventDefault();
        setActiveIndex((prev) => Math.max(prev - 1, -1));
        return;
      }
      if (event.key === 'Escape') {
        setOpen(false);
        setActiveIndex(-1);
        return;
      }
      if (event.key === 'Enter' && activeIndex >= 0 && hits[activeIndex]) {
        event.preventDefault();
        window.location.href = hits[activeIndex].page.url;
      }
    },
    [activeIndex, hits],
  );

  return (
    <div
      ref={containerRef}
      style={ROOT_STYLE}
      data-testid={testId ?? 'app-search-box'}
      data-audience={audience}
    >
      <label htmlFor={inputId} className="sr-only">
        {resolvedPlaceholder}
      </label>
      <input
        id={inputId}
        type="search"
        role="combobox"
        aria-expanded={open}
        aria-controls={listboxId}
        aria-autocomplete="list"
        aria-activedescendant={
          activeIndex >= 0 && hits[activeIndex]
            ? `${listboxId}-option-${activeIndex}`
            : undefined
        }
        autoComplete="off"
        value={query}
        placeholder={resolvedPlaceholder}
        onChange={(event) => {
          setQuery(event.target.value);
          setOpen(true);
          setActiveIndex(-1);
        }}
        onFocus={() => setOpen(true)}
        onKeyDown={handleKeyDown}
        style={INPUT_STYLE}
      />
      {open ? (
        <div
          id={listboxId}
          role="listbox"
          aria-label="Search results"
          style={POPOVER_STYLE}
        >
          {hits.length === 0 ? (
            <p style={EMPTY_STYLE}>
              No app pages match. Try{' '}
              <Link
                href={docsHref}
                data-telemetry="app-search-cross-link-click"
                data-telemetry-source={audience}
              >
                searching the docs instead →
              </Link>
            </p>
          ) : (
            <ul role="presentation" style={{ listStyle: 'none', margin: 0, padding: 0 }}>
              {hits.map((hit, index) => {
                const isActive = index === activeIndex;
                return (
                  <li key={hit.page.url} role="presentation">
                    <Link
                      id={`${listboxId}-option-${index}`}
                      role="option"
                      aria-selected={isActive}
                      href={hit.page.url}
                      style={isActive ? RESULT_BUTTON_ACTIVE_STYLE : RESULT_BUTTON_STYLE}
                      onMouseEnter={() => setActiveIndex(index)}
                      data-telemetry="app-search-result-click"
                      data-telemetry-url={hit.page.url}
                      data-telemetry-audience={hit.page.audience}
                    >
                      <span style={RESULT_TITLE_STYLE}>{hit.page.title}</span>
                      <span style={RESULT_DESC_STYLE}>{hit.page.description}</span>
                    </Link>
                  </li>
                );
              })}
            </ul>
          )}
          <div style={FOOTER_STYLE}>
            <span style={{ color: 'var(--sys-muted, var(--hp-muted, #6b7280))' }}>
              Looking for ADRs, runbooks, or deep guides?
            </span>
            <Link
              href={docsHref}
              data-telemetry="app-search-cross-link-click"
              data-telemetry-source={audience}
              style={{ fontWeight: 600 }}
            >
              Search the docs →
            </Link>
          </div>
        </div>
      ) : null}
    </div>
  );
}

export default AppSearchBox;
