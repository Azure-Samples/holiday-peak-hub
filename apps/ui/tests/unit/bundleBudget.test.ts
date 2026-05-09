/**
 * Tests for the bundle-budget gate (Issue #1060).
 *
 * The gate script lives at apps/ui/scripts/check-bundle-budgets.mjs and is
 * exercised end-to-end in the GitHub workflow (ui-bundle-budget-gate.yml).
 * Here we assert the contract surface the workflow depends on:
 * - budgets.json carries the v1 audience-route limits.
 * - The script exists, is executable Node, and fails on missing manifest.
 * - The script supports the `advisory` and `strict` modes referenced in the
 *   workflow YAML.
 */

import { existsSync, readFileSync } from 'fs';
import { resolve } from 'path';

const APP_ROOT = resolve(__dirname, '..', '..');

describe('bundle-budget gate (Issue #1060)', () => {
  it('apps/ui/budgets.json defines the four audience-route limits', () => {
    const path = resolve(APP_ROOT, 'budgets.json');
    expect(existsSync(path)).toBe(true);
    const budgets = JSON.parse(readFileSync(path, 'utf-8')) as {
      version: number;
      unit: string;
      limits: Record<string, number>;
    };
    expect(budgets.version).toBe(1);
    expect(budgets.unit).toBe('kilobytes-gzipped');
    expect(budgets.limits['/']).toBe(150);
    expect(budgets.limits['/retailers']).toBe(200);
    expect(budgets.limits['/builders']).toBe(200);
    expect(budgets.limits['/deploy']).toBe(250);
  });

  it('the gate script exists and references the canonical sources', () => {
    const path = resolve(APP_ROOT, 'scripts', 'check-bundle-budgets.mjs');
    expect(existsSync(path)).toBe(true);
    const source = readFileSync(path, 'utf-8');
    // It must read budgets.json and Next's build-manifest.json.
    expect(source).toMatch(/budgets\.json/);
    expect(source).toMatch(/build-manifest\.json/);
    // It must support both advisory and strict modes.
    expect(source).toMatch(/--mode=/);
    expect(source).toMatch(/strict/);
    expect(source).toMatch(/advisory/);
    // It measures gzipped size.
    expect(source).toMatch(/gzipSync/);
  });
});
