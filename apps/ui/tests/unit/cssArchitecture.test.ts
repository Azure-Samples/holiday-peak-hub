import { existsSync, readFileSync, statSync } from 'node:fs';
import { join } from 'node:path';

/**
 * CSS architecture contract tests (ADR-035 §49 / Issue #1058).
 *
 * Pin the file map and the line-count discipline. The CI gate at
 * .github/workflows/ui-css-architecture-gate.yml enforces the same
 * line-count contract against the runner; this Jest test pins it
 * locally so the developer trips the gate before push.
 */

const ROOT = join(__dirname, '..', '..');

describe('CSS architecture (Issue #1058)', () => {
  it('globals.css ≤ 80 lines (hard ceiling)', () => {
    const css = readFileSync(join(ROOT, 'app', 'globals.css'), 'utf-8');
    const lines = css.split('\n').length;
    expect(lines).toBeLessThanOrEqual(80);
  });

  it('globals.css imports the three token-layer files', () => {
    const css = readFileSync(join(ROOT, 'app', 'globals.css'), 'utf-8');
    expect(css).toContain("@import 'tailwindcss';");
    expect(css).toContain("@import './styles/tokens.reference.css';");
    expect(css).toContain("@import './styles/tokens.system.css';");
  });

  it('globals.css declares the cascade-layer order', () => {
    const css = readFileSync(join(ROOT, 'app', 'globals.css'), 'utf-8');
    expect(css).toMatch(/@layer\s+reset,\s*theme,\s*base,\s*components,\s*utilities,\s*app\s*;/);
  });

  it('globals.css contains the prefers-reduced-motion override', () => {
    const css = readFileSync(join(ROOT, 'app', 'globals.css'), 'utf-8');
    expect(css).toContain('@media (prefers-reduced-motion: reduce)');
    expect(css).toMatch(/--motion-fast:\s*0\.01ms\s*!important/);
    expect(css).toMatch(/--motion-base:\s*0\.01ms\s*!important/);
    expect(css).toMatch(/--motion-emphasized:\s*0\.01ms\s*!important/);
  });

  it('globals.css contains the :focus-visible rule consuming --sys-focus-ring', () => {
    const css = readFileSync(join(ROOT, 'app', 'globals.css'), 'utf-8');
    expect(css).toContain('outline: 3px solid var(--sys-focus-ring);');
  });

  it('globals.css does NOT contain component classes (.btn-*, .card, .input, .link, .demo-*, .showcase-*)', () => {
    const css = readFileSync(join(ROOT, 'app', 'globals.css'), 'utf-8');
    expect(css).not.toMatch(/^\s*\.btn-primary\b/m);
    expect(css).not.toMatch(/^\s*\.card\b/m);
    expect(css).not.toMatch(/^\s*\.input\b/m);
    expect(css).not.toMatch(/^\s*\.link\b/m);
    expect(css).not.toMatch(/^\s*\.demo-stage\b/m);
    expect(css).not.toMatch(/^\s*\.showcase-shell\b/m);
  });

  it('globals.css does NOT contain the legacy .dark class override', () => {
    const css = readFileSync(join(ROOT, 'app', 'globals.css'), 'utf-8');
    expect(css).not.toMatch(/^\s*\.dark\s*\{/m);
  });

  it('tokens.reference.css contains the @theme block with motion tokens', () => {
    const path = join(ROOT, 'app', 'styles', 'tokens.reference.css');
    expect(existsSync(path)).toBe(true);
    const css = readFileSync(path, 'utf-8');
    expect(css).toContain('@theme {');
    expect(css).toMatch(/--motion-fast:\s*120ms/);
    expect(css).toMatch(/--motion-base:\s*200ms/);
    expect(css).toMatch(/--motion-emphasized:\s*320ms/);
  });

  it('tokens.legacy-decorations.css carries the --hp-* decoration tokens', () => {
    const path = join(ROOT, 'app', 'styles', 'tokens.legacy-decorations.css');
    expect(existsSync(path)).toBe(true);
    const css = readFileSync(path, 'utf-8');
    expect(css).toContain('--hp-glass-bg');
    expect(css).toContain('--hp-glow-primary');
    expect(css).toContain('--hp-stage-bg');
    expect(css).toContain('--hp-shadow-sm');
  });

  it('legacy-utilities.css carries the legacy .btn-*, .card, .input, .demo-*, .showcase-* classes', () => {
    const path = join(ROOT, 'app', 'styles', 'legacy-utilities.css');
    expect(existsSync(path)).toBe(true);
    const css = readFileSync(path, 'utf-8');
    expect(css).toMatch(/^\s*\.btn-primary\b/m);
    expect(css).toMatch(/^\s*\.btn-success\b/m);
    expect(css).toMatch(/^\s*\.card\b/m);
    expect(css).toMatch(/^\s*\.input\b/m);
    expect(css).toMatch(/^\s*\.link\b/m);
    expect(css).toMatch(/^\s*\.demo-stage\b/m);
    expect(css).toMatch(/^\s*\.demo-panel\b/m);
    expect(css).toMatch(/^\s*\.demo-telemetry\b/m);
    expect(css).toMatch(/^\s*\.showcase-shell\b/m);
    expect(css).toMatch(/^\s*\.showcase-enter\b/m);
    expect(css).toMatch(/^\s*\.showcase-rise\b/m);
    expect(css).toMatch(/^\s*\.text-balance\b/m);
  });

  it('legacy-utilities.css contains both showcase keyframes', () => {
    const css = readFileSync(join(ROOT, 'app', 'styles', 'legacy-utilities.css'), 'utf-8');
    expect(css).toContain('@keyframes showcase-enter');
    expect(css).toContain('@keyframes showcase-rise');
  });

  it('all referenced token files exist', () => {
    const files = [
      'app/styles/tokens.reference.css',
      'app/styles/tokens.system.css',
      'app/styles/tokens.legacy-decorations.css',
      'app/styles/legacy-utilities.css',
      'styles/tokens/brand.css',
      'styles/tokens/retailer.css',
      'styles/tokens/builder.css',
      'styles/tokens/deploy.css',
    ];
    for (const f of files) {
      const p = join(ROOT, f);
      expect(existsSync(p)).toBe(true);
      // Files must not be empty.
      expect(statSync(p).size).toBeGreaterThan(0);
    }
  });
});
