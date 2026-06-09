/**
 * Tests for the feature-isolation ESLint contract (Issue #991).
 *
 * No GoF runtime pattern applies; this is a governance contract test that
 * pins ESLint configuration data for ADR-033's modular-monolith boundary.
 */

import { existsSync, readFileSync } from 'fs';
import { resolve } from 'path';
import { deserialize, serialize } from 'v8';
import { ESLint } from 'eslint';

const APP_ROOT = resolve(__dirname, '..', '..');
const SYNTHETIC_FILE_PATH = resolve(APP_ROOT, 'src', 'app', 'synthetic-feature-isolation.tsx');
const FEATURE_ISOLATION_MESSAGE =
  'Cross-feature deep imports are rejected. Import features only via their public index.ts.';

interface RestrictedImportPattern {
  group?: string[];
  message?: string;
}

interface EslintConfig {
  rules?: Record<string, unknown>;
}

const isRestrictedImportPattern = (value: unknown): value is RestrictedImportPattern => {
  if (typeof value !== 'object' || value === null) {
    return false;
  }

  const candidate = value as { group?: unknown; message?: unknown };
  return Array.isArray(candidate.group) && typeof candidate.message === 'string';
};

const ensureStructuredClone = () => {
  if (typeof globalThis.structuredClone === 'function') {
    return;
  }

  Object.defineProperty(globalThis, 'structuredClone', {
    configurable: true,
    value: <Value>(value: Value): Value => deserialize(serialize(value)) as Value,
  });
};

const lintSyntheticSource = async (source: string) => {
  ensureStructuredClone();

  const eslint = new ESLint({
    cwd: APP_ROOT,
    overrideConfigFile: resolve(APP_ROOT, '.eslintrc.json'),
  });

  const [result] = await eslint.lintText(source, {
    filePath: SYNTHETIC_FILE_PATH,
    warnIgnored: false,
  });

  return result.messages;
};

describe('feature-isolation ESLint contract (Issue #991)', () => {
  const config = (() => {
    const path = resolve(APP_ROOT, '.eslintrc.json');
    expect(existsSync(path)).toBe(true);
    return JSON.parse(readFileSync(path, 'utf-8')) as EslintConfig;
  })();

  const rule = config.rules?.['no-restricted-imports'];

  it('defines a root no-restricted-imports rule', () => {
    expect(Array.isArray(rule)).toBe(true);
    expect((rule as unknown[])[0]).toBe('error');
  });

  it('rejects cross-feature deep imports while allowing public index surfaces', () => {
    expect(Array.isArray(rule)).toBe(true);

    const [, options] = rule as [string, { patterns?: unknown[] }];
    const featurePattern = options.patterns?.find(isRestrictedImportPattern);

    expect(featurePattern).toBeDefined();
    expect(featurePattern?.group).toEqual(
      expect.arrayContaining([
        '../features/*/*',
        '!../features/*/index',
        '!../features/*/index.ts',
        '!../features/*/index.tsx',
        '@/src/features/*/*',
        '!@/src/features/*/index',
        '!@/src/features/*/index.ts',
        '!@/src/features/*/index.tsx',
        '../features/*/internal/*',
        '@/src/features/*/internal/*',
      ]),
    );
  });

  it('explains that features must be imported through public index.ts', () => {
    expect(Array.isArray(rule)).toBe(true);

    const [, options] = rule as [string, { patterns?: unknown[] }];
    const featurePattern = options.patterns?.find(isRestrictedImportPattern);

    expect(featurePattern?.message).toContain('Cross-feature deep imports are rejected');
    expect(featurePattern?.message).toContain('public index.ts');
  });

  it('reports the feature-isolation rule for synthetic cross-feature deep imports', async () => {
    const messages = await lintSyntheticSource(`
      import { calculateInventoryRisk } from '@/src/features/inventory/internal/risk';

      export const selectedRiskCalculator = calculateInventoryRisk;
    `);

    expect(messages).toEqual(
      expect.arrayContaining([
        expect.objectContaining({
          ruleId: 'no-restricted-imports',
          message: expect.stringContaining(FEATURE_ISOLATION_MESSAGE),
        }),
      ]),
    );
  });

  it('allows synthetic public feature index imports', async () => {
    const messages = await lintSyntheticSource(`
      import { InventoryFeature } from '@/src/features/inventory/index';

      export const selectedFeature = InventoryFeature;
    `);

    expect(messages).not.toEqual(
      expect.arrayContaining([
        expect.objectContaining({
          ruleId: 'no-restricted-imports',
        }),
      ]),
    );
  });
});