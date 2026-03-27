import React from 'react';
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { Navigation } from '../../components/organisms/Navigation';

const usePathnameMock = jest.fn();
const useAuthMock = jest.fn();
const useAgentGlobalHealthMock = jest.fn();

jest.mock('next/navigation', () => ({
  usePathname: () => usePathnameMock(),
}));

jest.mock('../../contexts/AuthContext', () => ({
  useAuth: () => useAuthMock(),
}));

jest.mock('../../lib/hooks/useAgentMonitor', () => ({
  useAgentGlobalHealth: () => useAgentGlobalHealthMock(),
}));

function ControlledNavigation({
  navLinks,
}: {
  navLinks: Array<{ label: string; href: string }>;
}) {
  const [mobileMenuOpen, setMobileMenuOpen] = React.useState(false);

  return (
    <Navigation
      navLinks={navLinks}
      mobileMenuOpen={mobileMenuOpen}
      onMobileMenuToggle={() => setMobileMenuOpen((current) => !current)}
    />
  );
}

describe('Navigation', () => {
  beforeEach(() => {
    usePathnameMock.mockReturnValue('/');
    useAuthMock.mockReturnValue({
      isAuthenticated: false,
      loginAsMockRole: jest.fn(),
      user: null,
    });
    useAgentGlobalHealthMock.mockReturnValue({
      data: 'healthy',
    });
  });

  it('renders the same primary links in mobile menu as desktop navigation', () => {
    const navLinks = [
      { label: 'Catalog', href: '/category?slug=all' },
      { label: 'Dashboard', href: '/dashboard' },
      { label: 'Admin', href: '/admin' },
    ];

    render(<ControlledNavigation navLinks={navLinks} />);

    fireEvent.click(screen.getByRole('button', { name: 'Open menu' }));

    const mobileMenu = screen.getByRole('dialog', { name: 'Mobile navigation menu' });

    for (const link of navLinks) {
      expect(within(mobileMenu).getByRole('link', { name: link.label })).toBeInTheDocument();
    }

    expect(within(mobileMenu).getByRole('link', { name: 'Pipeline status' })).toBeInTheDocument();
    expect(within(mobileMenu).getByRole('link', { name: 'Open Agent Popup' })).toBeInTheDocument();
  });

  it('closes the mobile menu on Escape and returns focus to the trigger', async () => {
    render(
      <ControlledNavigation
        navLinks={[
          { label: 'Catalog', href: '/category?slug=all' },
          { label: 'Admin', href: '/admin' },
        ]}
      />
    );

    const menuTrigger = screen.getByRole('button', { name: 'Open menu' });
    fireEvent.click(menuTrigger);

    expect(screen.getByRole('dialog', { name: 'Mobile navigation menu' })).toBeInTheDocument();

    fireEvent.keyDown(window, { key: 'Escape' });

    await waitFor(() => {
      expect(screen.queryByRole('dialog', { name: 'Mobile navigation menu' })).not.toBeInTheDocument();
    });

    expect(menuTrigger).toHaveFocus();
  });

  it('marks the current route link with aria-current', () => {
    usePathnameMock.mockReturnValue('/admin');

    render(
      <ControlledNavigation
        navLinks={[
          { label: 'Catalog', href: '/category?slug=all' },
          { label: 'Admin', href: '/admin' },
        ]}
      />
    );

    const adminLinks = screen.getAllByRole('link', { name: 'Admin' });
    expect(adminLinks.some((link) => link.getAttribute('aria-current') === 'page')).toBe(true);
  });
});
