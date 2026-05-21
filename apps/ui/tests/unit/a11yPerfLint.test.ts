/**
 * Tests for the a11y/perf ESLint contract (Issue #1060).
 *
 * The audience-route override in apps/ui/.eslintrc.json carries five
 * no-restricted-syntax rules:
 *   1. raw hex colors            (#1056)
 *   2. cubic-bezier in className (#1058)
 *   3. dark: in className        (#1058)
 *   4. outline-none in className (#1060) ← THIS
 *   5. style={{}} props          (#1058, react/forbid-dom-props)
 *
 * The CSS contract from #1058 already pinned the `:focus-visible` rule and
 * the prefers-reduced-motion zeroing. This test pins the new outline-none
 * lint rule.
 */

import { existsSync, readFileSync } from 'fs';
import { resolve } from 'path';

const APP_ROOT = resolve(__dirname, '..', '..');

describe('a11y/perf ESLint contract (Issue #1060)', () => {
  const config = (() => {
    const path = resolve(APP_ROOT, '.eslintrc.json');
    expect(existsSync(path)).toBe(true);
    return JSON.parse(readFileSync(path, 'utf-8')) as {
      overrides: Array<{
        files?: string[];
        rules?: Record<string, unknown>;
      }>;
    };
  })();

  const audienceOverride = config.overrides.find(
    (o) =>
      Array.isArray(o.files) &&
      o.files.some((f: string) => f.includes('(retailer)')) &&
      o.files.some((f: string) => f.includes('(builder)')) &&
      o.files.some((f: string) => f.includes('(deploy)')),
  );

  it('the audience-route override exists', () => {
    expect(audienceOverride).toBeDefined();
  });

  it('forbids `outline-none` in className literals', () => {
    expect(audienceOverride).toBeDefined();
    const rule = (audienceOverride!.rules as { 'no-restricted-syntax': unknown[] })[
      'no-restricted-syntax'
    ];
    expect(Array.isArray(rule)).toBe(true);
    const serialized = JSON.stringify(rule);
    expect(serialized).toMatch(/outline-none/);
    expect(serialized).toMatch(/WCAG 2\.4\.7/);
    expect(serialized).toMatch(/Issue #1060/);
  });

  it('forbids `outline-none` in template literals', () => {
    expect(audienceOverride).toBeDefined();
    const rule = (audienceOverride!.rules as { 'no-restricted-syntax': unknown[] })[
      'no-restricted-syntax'
    ];
    const serialized = JSON.stringify(rule);
    // Two selectors total: Literal + TemplateElement.
    const matches = serialized.match(/outline-none/g) ?? [];
    expect(matches.length).toBeGreaterThanOrEqual(2);
  });
});
