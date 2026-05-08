/**
 * axe-core configuration for the ui-axe-core CI job.
 *
 * Per ADR-034 §7 / Issue #1014:
 *   - WCAG 2.2 AA violations FAIL the build.
 *   - Non-AA findings (best-practice, AAA) emit a warning but do not fail.
 *
 * jest-axe maps the `runOnly` option to axe-core's runner; we constrain it to
 * the AA-relevant tag set so AAA / best-practice rules don't accidentally
 * become merge gates.
 */
import { configureAxe } from 'jest-axe';

export const axeAA = configureAxe({
  runOnly: {
    type: 'tag',
    values: ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa'],
  },
});
