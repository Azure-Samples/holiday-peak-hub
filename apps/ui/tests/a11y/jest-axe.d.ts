/**
 * Type augmentation for jest-axe so we can assert `toHaveNoViolations`.
 *
 * Vendored locally instead of relying on the published @types/jest-axe alone,
 * because some TS configurations don't auto-pick up its `expect.extend` shape.
 */
import 'jest-axe';

declare global {
  // eslint-disable-next-line @typescript-eslint/no-namespace
  namespace jest {
    interface Matchers<R> {
      toHaveNoViolations(): R;
    }
  }
}

export {};
