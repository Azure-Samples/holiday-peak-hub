import { fireEvent, render, screen, within } from '@testing-library/react';

import { AppSearchBox } from '@/components/molecules/AppSearchBox';

describe('AppSearchBox', () => {
  it('renders the audience-scoped placeholder', () => {
    render(<AppSearchBox audience="builder" />);
    const input = screen.getByPlaceholderText('Search builder pages');
    expect(input).toBeInTheDocument();
    expect(input).toHaveAttribute('role', 'combobox');
    expect(input).toHaveAttribute('aria-expanded', 'false');
  });

  it('falls back to scope-clarifying copy on home', () => {
    render(<AppSearchBox audience="home" />);
    expect(
      screen.getByPlaceholderText('Search retailers + builders + deploy'),
    ).toBeInTheDocument();
  });

  it('opens the dropdown on focus and shows audience-scoped suggestions', () => {
    render(<AppSearchBox audience="retailer" />);
    const input = screen.getByPlaceholderText('Search retailer pages');
    fireEvent.focus(input);

    const listbox = screen.getByRole('listbox');
    expect(listbox).toBeInTheDocument();
    expect(within(listbox).queryByText('Architecture registry')).not.toBeInTheDocument();
    expect(within(listbox).getByText('For Retailers')).toBeInTheDocument();
  });

  it('filters results by query text and ranks title matches first', () => {
    render(<AppSearchBox audience="home" />);
    const input = screen.getByPlaceholderText('Search retailers + builders + deploy');
    fireEvent.focus(input);
    fireEvent.change(input, { target: { value: 'roi' } });

    const listbox = screen.getByRole('listbox');
    const options = within(listbox).getAllByRole('option');
    expect(options.length).toBeGreaterThan(0);
    expect(options[0]).toHaveTextContent('ROI calculator');
  });

  it('renders the cross-link to the mkdocs Material search results page', () => {
    render(<AppSearchBox audience="builder" />);
    const input = screen.getByPlaceholderText('Search builder pages');
    fireEvent.focus(input);
    fireEvent.change(input, { target: { value: 'adr' } });

    const link = screen.getByRole('link', { name: /search the docs/i });
    expect(link).toHaveAttribute('href', '/docs/search/?q=adr');
    expect(link).toHaveAttribute(
      'data-telemetry',
      'app-search-cross-link-click',
    );
  });

  it('closes when Escape is pressed', () => {
    render(<AppSearchBox audience="deploy" />);
    const input = screen.getByPlaceholderText('Search deploy pages');
    fireEvent.focus(input);
    expect(screen.getByRole('listbox')).toBeInTheDocument();
    fireEvent.keyDown(input, { key: 'Escape' });
    expect(screen.queryByRole('listbox')).not.toBeInTheDocument();
  });

  it('shows the empty-state copy with the docs cross-link when nothing matches', () => {
    render(<AppSearchBox audience="retailer" />);
    const input = screen.getByPlaceholderText('Search retailer pages');
    fireEvent.focus(input);
    fireEvent.change(input, { target: { value: 'zzzzzzzz' } });

    const empty = screen.getByText(/no app pages match/i);
    expect(empty).toBeInTheDocument();
    const link = empty.querySelector('a');
    expect(link).not.toBeNull();
    expect(link?.getAttribute('href')).toBe('/docs/search/?q=zzzzzzzz');
  });
});
