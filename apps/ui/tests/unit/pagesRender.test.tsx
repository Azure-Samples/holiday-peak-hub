import React from 'react';
import { act, render, screen } from '@testing-library/react';

import HomePage from '../../app/page';
import CategoryPage from '../../app/category/[slug]/page';
import ProductPage from '../../app/product/[id]/page';
import CheckoutPage from '../../app/checkout/page';
import OrderTrackingPage from '../../app/order/[id]/page';
import ProfilePage from '../../app/profile/page';
import DashboardPage from '../../app/dashboard/page';
import AdminPortalPage from '../../app/admin/page';
import RequestsPage from '../../app/staff/requests/page';
import LogisticsTrackingPage from '../../app/staff/logistics/page';
import SalesAnalyticsPage from '../../app/staff/sales/page';
import LoginPage from '../../app/auth/login/page';
import SignupPage from '../../app/auth/signup/page';
import CategoriesPage from '../../app/categories/page';
import NewArrivalsPage from '../../app/new/page';

const redirect = jest.fn();

jest.mock('next/navigation', () => ({
  redirect: (path: string) => redirect(path),
}));

jest.mock('@/components/templates/MainLayout', () => ({
  MainLayout: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="main-layout">{children}</div>
  ),
}));

jest.mock('@/components/templates/ShopLayout', () => ({
  ShopLayout: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="shop-layout">{children}</div>
  ),
}));

jest.mock('@/components/templates/CheckoutLayout', () => ({
  CheckoutLayout: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="checkout-layout">{children}</div>
  ),
}));

describe('Page rendering smoke tests', () => {
  it('renders the home page hero', () => {
    render(<HomePage />);
    expect(
      screen.getByText('Discover Amazing Products for Your Lifestyle')
    ).toBeInTheDocument();
  });

  it('redirects categories page to /category/all', () => {
    CategoriesPage();
    expect(redirect).toHaveBeenCalledWith('/category/all');
  });

  it('redirects new arrivals page to /category/deals', () => {
    NewArrivalsPage();
    expect(redirect).toHaveBeenCalledWith('/category/deals');
  });

  it('renders category page heading', async () => {
    await act(async () => {
      render(<CategoryPage params={Promise.resolve({ slug: 'electronics' })} />);
    });
    expect(screen.getByText('Electronics Products')).toBeInTheDocument();
  });

  it('renders product detail page', () => {
    render(<ProductPage params={{ id: '1' }} />);
    expect(
      screen.getByRole('heading', { name: 'Premium Wireless Headphones' })
    ).toBeInTheDocument();
  });

  it('renders checkout summary', () => {
    render(<CheckoutPage />);
    expect(screen.getByText('Order Summary')).toBeInTheDocument();
  });

  it('renders order tracking form', () => {
    render(<OrderTrackingPage />);
    expect(screen.getByText('Track Your Order')).toBeInTheDocument();
  });

  it('renders profile page', () => {
    render(<ProfilePage />);
    expect(screen.getByText('My Profile')).toBeInTheDocument();
  });

  it('renders dashboard page', () => {
    render(<DashboardPage />);
    expect(screen.getByText('My Dashboard')).toBeInTheDocument();
  });

  it('renders admin portal page', () => {
    render(<AdminPortalPage />);
    expect(screen.getByText('Admin Portal')).toBeInTheDocument();
  });

  it('renders staff requests page', () => {
    render(<RequestsPage />);
    expect(screen.getByText('Customer Requests')).toBeInTheDocument();
  });

  it('renders staff logistics page', () => {
    render(<LogisticsTrackingPage />);
    expect(screen.getByText('Logistics Tracking')).toBeInTheDocument();
  });

  it('renders staff sales page', () => {
    render(<SalesAnalyticsPage />);
    expect(screen.getByText('Sales Analytics')).toBeInTheDocument();
  });

  it('renders login page', () => {
    render(<LoginPage />);
    expect(screen.getByText('Welcome Back')).toBeInTheDocument();
  });

  it('renders signup page', () => {
    render(<SignupPage />);
    expect(screen.getByText('Create Your Account')).toBeInTheDocument();
  });
});
