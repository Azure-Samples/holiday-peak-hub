/**
 * Enablement asset registry loader (Issue #1052 / Epic #1053).
 *
 * Front-matter contract for assets under `docs/enablement/**`:
 *
 *     ---
 *     title: ...
 *     kind: battle-card | demo-script | win-loss | customer-quote
 *     owner: <github-handle>
 *     last_reviewed: 2025-11-04
 *     attribution_status: approved | pending | unknown   # only for quotes
 *     ---
 *
 * Currency contract:
 *   - battle-card     → 90 day expiry
 *   - demo-script     → 180 day expiry
 *   - win-loss        → never expires
 *   - customer-quote  → never expires; renders only when
 *                       `attribution_status === 'approved'`.
 *
 * Expired or non-approved assets are HIDDEN — never rendered. The expired
 * count is surfaced in the index banner so the GTM lead knows the
 * graveyard size without it leaking onto the surface.
 */

import fs from 'node:fs';
import path from 'node:path';

export type EnablementKind =
  | 'battle-card'
  | 'demo-script'
  | 'win-loss'
  | 'customer-quote';

export type EnablementAsset = {
  slug: string;
  title: string;
  kind: EnablementKind;
  owner: string;
  lastReviewed: string;
  attributionStatus?: 'approved' | 'pending' | 'unknown';
  href: string;
  /** Days until the asset expires (negative for expired). */
  daysToExpiry: number;
};

export type EnablementIndex = {
  generatedAt: string;
  assets: EnablementAsset[];
  expiredCount: number;
};

const SOURCE_DIR_CANDIDATES = [
  path.join(process.cwd(), '..', '..', 'docs', 'enablement'),
  path.join(process.cwd(), 'docs', 'enablement'),
];

const EXPIRY_DAYS: Record<EnablementKind, number | null> = {
  'battle-card': 90,
  'demo-script': 180,
  'win-loss': null,
  'customer-quote': null,
};

const FRONT_MATTER_RE = /^---\r?\n([\s\S]*?)\r?\n---/;

function parseFrontMatter(text: string): Record<string, string> {
  const m = text.match(FRONT_MATTER_RE);
  if (!m) return {};
  const out: Record<string, string> = {};
  for (const line of m[1].split(/\r?\n/)) {
    const idx = line.indexOf(':');
    if (idx === -1) continue;
    const key = line.slice(0, idx).trim();
    const value = line.slice(idx + 1).trim().replace(/^"(.*)"$/, '$1');
    out[key] = value;
  }
  return out;
}

function findSourceDir(): string | null {
  for (const candidate of SOURCE_DIR_CANDIDATES) {
    if (fs.existsSync(candidate) && fs.statSync(candidate).isDirectory()) {
      return candidate;
    }
  }
  return null;
}

function listMarkdown(dir: string): string[] {
  const out: string[] = [];
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      out.push(...listMarkdown(full));
    } else if (entry.isFile() && entry.name.endsWith('.md')) {
      out.push(full);
    }
  }
  return out;
}

export function loadEnablementIndex(now: Date = new Date()): EnablementIndex {
  const sourceDir = findSourceDir();
  if (!sourceDir) {
    return {
      generatedAt: now.toISOString(),
      assets: [],
      expiredCount: 0,
    };
  }

  let expiredCount = 0;
  const assets: EnablementAsset[] = [];

  for (const file of listMarkdown(sourceDir)) {
    let text: string;
    try {
      text = fs.readFileSync(file, 'utf-8');
    } catch {
      continue;
    }
    const fm = parseFrontMatter(text);
    if (!fm.title || !fm.kind || !fm.owner || !fm.last_reviewed) continue;

    const kind = fm.kind as EnablementKind;
    const expiry = EXPIRY_DAYS[kind];
    if (expiry === undefined) continue;

    const reviewedAt = new Date(fm.last_reviewed);
    if (Number.isNaN(reviewedAt.getTime())) continue;

    const ageDays =
      (now.getTime() - reviewedAt.getTime()) / (1000 * 60 * 60 * 24);
    const daysToExpiry =
      expiry === null ? Number.POSITIVE_INFINITY : expiry - ageDays;

    if (kind === 'customer-quote') {
      const attribution = fm.attribution_status as
        | 'approved'
        | 'pending'
        | 'unknown'
        | undefined;
      if (attribution !== 'approved') {
        // Quote without approved attribution is hidden, period.
        expiredCount += 1;
        continue;
      }
    }

    if (daysToExpiry < 0) {
      expiredCount += 1;
      continue;
    }

    const slug = path.basename(file, '.md');
    const githubHref = `https://github.com/Azure-Samples/holiday-peak-hub/blob/main/${path
      .relative(process.cwd(), file)
      .replace(/\\/g, '/')}`;

    assets.push({
      slug,
      title: fm.title,
      kind,
      owner: fm.owner,
      lastReviewed: fm.last_reviewed,
      attributionStatus:
        kind === 'customer-quote'
          ? (fm.attribution_status as EnablementAsset['attributionStatus'])
          : undefined,
      href: githubHref,
      daysToExpiry: Number.isFinite(daysToExpiry)
        ? Math.round(daysToExpiry)
        : Number.POSITIVE_INFINITY,
    });
  }

  // Stable sort: live assets soonest-to-expire first, immutable last.
  assets.sort((a, b) => {
    if (a.daysToExpiry === Infinity && b.daysToExpiry === Infinity) {
      return a.title.localeCompare(b.title);
    }
    if (a.daysToExpiry === Infinity) return 1;
    if (b.daysToExpiry === Infinity) return -1;
    return a.daysToExpiry - b.daysToExpiry;
  });

  return {
    generatedAt: now.toISOString(),
    assets,
    expiredCount,
  };
}
