import React from 'react';
import { render, screen } from '@testing-library/react';

import HomePage from '../../app/page';
import { CategoryPageClient } from '../../app/category/CategoryPageClient';
import { ProductPageClient } from '../../app/product/ProductPageClient';
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

jest.mock('../../lib/hooks/useCategories', () => ({
  useCategories: () => ({
    data: [
      { id: 'electronics', name: 'Electronics', description: 'Electronic devices' },
      { id: 'fashion', name: 'Fashion', description: 'Fashion products' },
    ],
    isLoading: false,
    isError: false,
  }),
}));

jest.mock('../../lib/hooks/useSemanticSearch', () => ({
  useSemanticSearch: () => ({
    data: {
      source: 'agent',
      items: [
        {
          sku: 'seed-product-0001',
          title: 'Wireless Headphones',
          description: 'Headphones',
          brand: 'Holiday Peak',
          category: 'electronics',
          price: 199.99,
          currency: 'USD',
          images: ['/api/placeholder/300/300'],
          thumbnail: '/api/placeholder/300/300',
          inStock: true,
          rating: 4.8,
          reviewCount: 123,
        },
      ],
    },
    isLoading: false,
    isError: false,
  }),
}));

jest.mock('../../lib/hooks/useProducts', () => ({
  useProduct: () => ({
    data: {
      id: 'seed-product-0001',
      name: 'Wireless Headphones',
      description: 'Headphones',
      price: 199.99,
      category_id: 'electronics',
      image_url: '/api/placeholder/300/300',
      in_stock: true,
      rating: 4.8,
      review_count: 123,
      features: ['noise cancellation'],
    },
    isLoading: false,
    isError: false,
  }),
}));

jest.mock('../../contexts/AuthContext', () => ({
  useAuth: () => ({
    login: jest.fn(),
    isAuthenticated: false,
    isLoading: false,
    user: null,
    logout: jest.fn(),
  }),
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

  it('renders categories page heading', () => {
    render(<CategoriesPage />);
    expect(screen.getByText('Categories')).toBeInTheDocument();
  });

  it('redirects new arrivals page to query category route', () => {
    NewArrivalsPage();
    expect(redirect).toHaveBeenCalledWith('/category?slug=deals');
  });

  it('renders category page heading', () => {
    render(<CategoryPageClient slug="electronics" />);
    expect(screen.getByRole('heading', { name: 'Electronics' })).toBeInTheDocument();
  });

  it('renders product detail page', () => {
    render(<ProductPageClient productId="seed-product-0001" />);
    expect(
      screen.getByRole('heading', { name: 'Wireless Headphones' })
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
    expect(screen.getByText('Welcome to Holiday Peak Hub')).toBeInTheDocument();
  });

  it('renders signup page', () => {
    SignupPage();
    expect(redirect).toHaveBeenCalledWith('/auth/login');
  });
});
