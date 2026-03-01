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
  useParams: () => ({ id: 'ORD-2026-0123' }),
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

jest.mock('../../lib/hooks/useProducts', () => ({
  useProducts: () => ({
    data: [
      {
        id: 'seed-product-0001',
        name: 'Wireless Headphones',
        description: 'Headphones',
        price: 199.99,
        category_id: 'electronics',
        image_url: '/images/products/p1.jpg',
        in_stock: true,
      },
    ],
    isLoading: false,
    isError: false,
  }),
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

jest.mock('../../lib/hooks/useOrders', () => ({
  useOrder: () => ({
    data: {
      id: 'ORD-2026-0123',
      user_id: 'user-1',
      items: [
        {
          product_id: 'seed-product-0001',
          quantity: 1,
          price: 199.99,
        },
      ],
      total: 199.99,
      status: 'pending',
      created_at: '2026-01-27T10:00:00Z',
      tracking: { state: 'processing' },
      eta: { date: '2026-01-31' },
      carrier: { name: 'FedEx' },
    },
    isLoading: false,
    isError: false,
  }),
}));

jest.mock('../../lib/hooks/useStaff', () => ({
  useStaffTickets: () => ({
    data: [
      {
        id: 'ticket-1',
        user_id: 'user-1',
        subject: 'Need help',
        status: 'open',
        priority: 'high',
        created_at: '2026-01-27T10:00:00Z',
      },
    ],
    isLoading: false,
    isError: false,
  }),
  useStaffReturns: () => ({
    data: [
      {
        id: 'ret-1',
        order_id: 'ORD-2026-0123',
        user_id: 'user-1',
        status: 'pending',
        reason: 'Damaged',
        created_at: '2026-01-27T10:00:00Z',
      },
    ],
    isLoading: false,
    isError: false,
  }),
  useStaffShipments: () => ({
    data: [
      {
        id: 'ship-1',
        order_id: 'ORD-2026-0123',
        status: 'in_transit',
        carrier: 'FedEx',
        tracking_number: 'FDX123',
        created_at: '2026-01-27T10:00:00Z',
      },
    ],
    isLoading: false,
    isError: false,
  }),
  useStaffAnalyticsSummary: () => ({
    data: {
      total_revenue: 1200,
      total_orders: 12,
      average_order_value: 100,
      top_products: [{ name: 'Wireless Headphones' }],
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
    expect(redirect).toHaveBeenCalledWith('/deals');
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

  it('renders order details page', () => {
    render(<OrderTrackingPage />);
    expect(screen.getByText('Order Details')).toBeInTheDocument();
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
