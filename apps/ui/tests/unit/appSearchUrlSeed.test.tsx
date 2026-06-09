/**
 * Cross-link contract tests (Issue #1022).
 *
 * Validates that the reciprocal half of the two-search-box contract is in
 * place: a `?q=<term>` URL param landing on the home page seeds the
 * AppSearchBox so the user continues their search seamlessly. The forward
 * direction (AppSearchBox results → /docs/search/?q=...) is covered by
 * `appSearchMatcher.test.ts` and `AppSearchBox.test.tsx`.
 */
import { fireEvent, render, screen } from '@testing-library/react';

import { AppSearchBox } from '@/src/features/search';

describe('AppSearchBox URL ?q= seed (Issue #1022 reciprocal cross-link)', () => {
  beforeEach(() => {
    // Reset URL between cases so each test owns its query state.
    window.history.replaceState({}, '', '/');
  });

  it('seeds the input when ?q= is present in the URL', () => {
    window.history.replaceState({}, '', '/?q=architecture');
    render(<AppSearchBox audience="home" />);
    const input = screen.getByPlaceholderText(
      'Search retailers + builders + deploy',
    ) as HTMLInputElement;
    expect(input.value).toBe('architecture');
    // Auto-opens so the user sees results immediately.
    expect(screen.getByRole('listbox')).toBeInTheDocument();
  });

  it('does not seed when ?q= is empty', () => {
    window.history.replaceState({}, '', '/?q=');
    render(<AppSearchBox audience="home" />);
    const input = screen.getByPlaceholderText(
      'Search retailers + builders + deploy',
    ) as HTMLInputElement;
    expect(input.value).toBe('');
    expect(screen.queryByRole('listbox')).not.toBeInTheDocument();
  });

  it('does not seed when ?q= is absent', () => {
    window.history.replaceState({}, '', '/');
    render(<AppSearchBox audience="retailer" />);
    const input = screen.getByPlaceholderText('Search retailer pages') as HTMLInputElement;
    expect(input.value).toBe('');
  });

  it('user typing overrides the seeded value', () => {
    window.history.replaceState({}, '', '/?q=initial');
    render(<AppSearchBox audience="home" />);
    const input = screen.getByPlaceholderText(
      'Search retailers + builders + deploy',
    ) as HTMLInputElement;
    expect(input.value).toBe('initial');
    fireEvent.change(input, { target: { value: 'overridden' } });
    expect(input.value).toBe('overridden');
  });
});
