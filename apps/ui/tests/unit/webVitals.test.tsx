/**
 * Tests for the Web Vitals reporter (Issue #1060).
 *
 * apps/ui/app/web-vitals.tsx mounts in the root layout and reports
 * LCP / INP / CLS / TTFB / FCP via the Next.js `useReportWebVitals` hook.
 *
 * It must:
 *   1. Be a client component ("use client").
 *   2. Use Next's official `next/web-vitals` hook (NOT a custom listener).
 *   3. Forward to AppInsights when present, no-op otherwise.
 *   4. Render nothing visible (return null).
 *
 * The hook itself depends on the Next.js client runtime that jsdom does not
 * fully simulate — we cover the contract via source-level assertions.
 */

import { existsSync, readFileSync } from 'fs';
import { resolve } from 'path';

const APP_ROOT = resolve(__dirname, '..', '..');
const WEB_VITALS_PATH = resolve(APP_ROOT, 'app', 'web-vitals.tsx');

describe('WebVitalsReporter contract', () => {
  it('the file exists', () => {
    expect(existsSync(WEB_VITALS_PATH)).toBe(true);
  });

  it('declares "use client"', () => {
    const source = readFileSync(WEB_VITALS_PATH, 'utf-8');
    expect(source).toMatch(/^['"]use client['"]/);
  });

  it('uses the official next/web-vitals hook', () => {
    const source = readFileSync(WEB_VITALS_PATH, 'utf-8');
    expect(source).toMatch(/from ['"]next\/web-vitals['"]/);
    expect(source).toMatch(/useReportWebVitals/);
  });

  it('forwards to AppInsights when window.appInsights is available', () => {
    const source = readFileSync(WEB_VITALS_PATH, 'utf-8');
    expect(source).toMatch(/appInsights/);
    expect(source).toMatch(/trackEvent/);
    expect(source).toMatch(/metric\.name/);
    expect(source).toMatch(/metric\.value/);
  });

  it('returns null (renders nothing visible)', () => {
    const source = readFileSync(WEB_VITALS_PATH, 'utf-8');
    expect(source).toMatch(/return null/);
  });

  it('is mounted in the root layout', () => {
    const layout = readFileSync(resolve(APP_ROOT, 'app', 'layout.tsx'), 'utf-8');
    expect(layout).toMatch(/WebVitalsReporter/);
  });
});

