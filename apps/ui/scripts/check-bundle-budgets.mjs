#!/usr/bin/env node
/**
 * Route-segment JS bundle-budget gate (Issue #1060).
 *
 * Runs AFTER `yarn build`. For each audience route, sums the gzipped JS sizes
 * of the chunks that route loads, then compares against the per-route limits
 * in `apps/ui/budgets.json`.
 *
 * Measurement strategy (Next 16):
 * - For each prerendered route, parse the static `.next/server/app/<seg>.html`
 *   for `/_next/static/chunks/*.js` references and sum gzipped sizes.
 * - For dynamic routes (e.g. `/` until home reaches static rendering), fall
 *   back to `rootMainFiles + polyfillFiles` from `.next/build-manifest.json`,
 *   which is the floor any route loads. The report flags the route as
 *   measured-as-floor.
 *
 * Demo / admin / legacy routes are un-budgeted at v1 (separate route groups).
 *
 * Modes:
 *   default (advisory, --mode=advisory): always exits 0; OVER rows printed
 *     but do not fail the gate. Used at v1 while F1 cleanup completes.
 *   strict (--mode=strict, or BUDGETS_STRICT=1): exits 1 if any audience route
 *     exceeds budget. Activated after the dependency-trim follow-up lands.
 */

import { readFileSync, existsSync } from 'node:fs';
import { gzipSync } from 'node:zlib';
import { join, dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const APP_DIR = resolve(__dirname, '..');

const BUDGETS_PATH = join(APP_DIR, 'budgets.json');
const NEXT_DIR = join(APP_DIR, '.next');
const APP_DIR_SERVER = join(NEXT_DIR, 'server', 'app');
const BUILD_MANIFEST = join(NEXT_DIR, 'build-manifest.json');
const STATIC_PREFIX = '/_next/';
const KB = 1024;

const MODE = (() => {
  const cli = process.argv.find((a) => a.startsWith('--mode='));
  if (cli) return cli.slice('--mode='.length);
  if (process.env.BUDGETS_STRICT === '1') return 'strict';
  return 'advisory';
})();

function fail(msg) {
  console.error(`bundle-budgets: ${msg}`);
  process.exit(1);
}

if (!existsSync(BUDGETS_PATH)) fail(`missing ${BUDGETS_PATH}`);
if (!existsSync(BUILD_MANIFEST)) {
  fail(`missing ${BUILD_MANIFEST} — run \`yarn build\` first.`);
}

const budgets = JSON.parse(readFileSync(BUDGETS_PATH, 'utf-8'));
const buildManifest = JSON.parse(readFileSync(BUILD_MANIFEST, 'utf-8'));

function gzippedSize(absPath) {
  const buf = readFileSync(absPath);
  return gzipSync(buf, { level: 9 }).length;
}

function chunkAbsPath(refPath) {
  let rel = refPath;
  if (rel.startsWith(STATIC_PREFIX)) rel = rel.slice(STATIC_PREFIX.length);
  return join(NEXT_DIR, rel);
}

function totalGzippedBytes(chunks) {
  let bytes = 0;
  for (const ref of chunks) {
    if (!ref.endsWith('.js')) continue;
    const abs = chunkAbsPath(ref);
    if (!existsSync(abs)) continue;
    bytes += gzippedSize(abs);
  }
  return bytes;
}

const ROOT_CHUNKS = new Set([
  ...(buildManifest.rootMainFiles ?? []),
  ...(buildManifest.polyfillFiles ?? []),
]);

const AUDIENCE_ROUTES = [
  { route: '/', htmlSegment: null }, // dynamic; floor only
  { route: '/retailers', htmlSegment: 'retailers' },
  { route: '/builders', htmlSegment: 'builders' },
  { route: '/deploy', htmlSegment: 'deploy' },
];

function chunksForRoute({ htmlSegment }) {
  if (htmlSegment === null) {
    return { chunks: new Set(ROOT_CHUNKS), source: 'floor (root+polyfill)' };
  }
  const htmlPath = join(APP_DIR_SERVER, `${htmlSegment}.html`);
  if (!existsSync(htmlPath)) {
    return { chunks: new Set(ROOT_CHUNKS), source: `floor (no ${htmlSegment}.html)` };
  }
  const html = readFileSync(htmlPath, 'utf-8');
  const matches = html.matchAll(/\/_next\/static\/chunks\/[A-Za-z0-9._~-]+\.js/g);
  const chunks = new Set();
  for (const m of matches) chunks.add(m[0]);
  for (const c of ROOT_CHUNKS) chunks.add(c);
  return { chunks, source: `${htmlSegment}.html` };
}

const RESULTS = [];
let failures = 0;

for (const r of AUDIENCE_ROUTES) {
  const { chunks, source } = chunksForRoute(r);
  const sizeBytes = totalGzippedBytes([...chunks]);
  const sizeKb = sizeBytes / KB;
  const limitKb = budgets.limits[r.route];
  const ok = sizeKb <= limitKb;
  RESULTS.push({ route: r.route, sizeKb: Number(sizeKb.toFixed(1)), limitKb, ok, source });
  if (!ok) failures += 1;
}

const colW = (s, n) => String(s).padEnd(n, ' ');
console.log('');
console.log('UI route-segment bundle-budget report (gzipped JS, kilobytes):');
console.log('');
console.log(`${colW('route', 16)}${colW('size', 10)}${colW('limit', 10)}${colW('source', 28)}status`);
console.log('-'.repeat(80));
for (const r of RESULTS) {
  const status = r.ok ? 'OK' : 'OVER';
  console.log(
    `${colW(r.route, 16)}${colW(`${r.sizeKb}`, 10)}${colW(`${r.limitKb}`, 10)}${colW(r.source, 28)}${status}`,
  );
}
console.log('');

if (failures > 0) {
  if (MODE === 'strict') {
    console.error(`bundle-budgets: ${failures} route(s) over budget (strict mode).`);
    process.exit(1);
  }
  console.error(
    `bundle-budgets: ADVISORY — ${failures} route(s) over budget. ` +
      'Gate runs in advisory mode at v1; flips to strict after the F1 cleanup follow-up lands. ' +
      'See docs/ui/a11y-perf.md.',
  );
  process.exit(0);
}
console.log('bundle-budgets: all audience routes within budget.');
