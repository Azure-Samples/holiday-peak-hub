import React from 'react';
import { fireEvent, render, screen } from '@testing-library/react';

import HomePage from '../../app/page';
import { CategoryPageClient } from '../../app/category/CategoryPageClient';
import { ProductPageClient } from '../../app/product/ProductPageClient';
import CheckoutPage from '../../app/checkout/page';
import OrdersPage from '../../app/orders/page';
import OrderTrackingPage from '../../app/order/[id]/page';
import ProfilePage from '../../app/profile/page';
import DashboardPage from '../../app/dashboard/page';
import AdminPortalPage from '../../app/admin/page';
import SchemasPage from '../../app/admin/schemas/page';
import ConfigPage from '../../app/admin/config/page';
import TruthAnalyticsPage from '../../app/admin/truth-analytics/page';
import RequestsPage from '../../app/staff/requests/page';
import LogisticsTrackingPage from '../../app/staff/logistics/page';
import SalesAnalyticsPage from '../../app/staff/sales/page';
import StaffReviewQueuePage from '../../app/staff/review/page';
import LoginPage from '../../app/auth/login/page';
import SignupPage from '../../app/auth/signup/page';
import CategoriesPage from '../../app/categories/page';
import NewArrivalsPage from '../../app/new/page';

const redirect = jest.fn();
const useSearchParamsMock = jest.fn(() => ({
  get: (_key: string) => null as string | null,
}));

jest.mock('next/navigation', () => ({
  redirect: (path: string) => redirect(path),
  useParams: () => ({ id: 'ORD-2026-0123', entityId: 'prod-001' }),
  useRouter: () => ({ push: jest.fn() }),
  useSearchParams: () => useSearchParamsMock(),
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
  useOrders: () => ({
    data: [
      {
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
        status: 'processing',
        created_at: '2026-01-27T10:00:00Z',
      },
    ],
    isLoading: false,
    isError: false,
  }),
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

jest.mock('../../lib/hooks/useReturns', () => ({
  useReturns: () => ({
    data: [
      {
        id: 'ret-1',
        order_id: 'ORD-2026-0123',
        user_id: 'user-1',
        status: 'requested',
        reason: 'Damaged item',
        items: [{ product_id: 'seed-product-0001', quantity: 1 }],
        created_at: '2026-01-27T10:00:00Z',
        updated_at: '2026-01-27T10:00:00Z',
        requested_at: '2026-01-27T10:00:00Z',
        approved_at: null,
        rejected_at: null,
        received_at: null,
        restocked_at: null,
        refunded_at: null,
        last_transition_at: '2026-01-27T10:00:00Z',
        status_history: [],
        audit_log: [],
        refund: null,
      },
    ],
    isLoading: false,
    isError: false,
  }),
  useCreateReturn: () => ({
    mutateAsync: jest.fn(),
    isPending: false,
    isError: false,
  }),
}));

jest.mock('../../lib/hooks/usePersonalization', () => ({
  useBrandShoppingFlow: () => ({
    mutate: jest.fn(),
    data: {
      product: {
        sku: 'seed-product-0001',
        name: 'Wireless Headphones',
        description: 'Headphones',
        category_id: 'electronics',
        price: 199.99,
        currency: 'usd',
        in_stock: true,
      },
      profile: {
        customer_id: 'user-1',
        email: 'demo@example.com',
        name: 'Demo User',
        tier: 'standard',
      },
      offers: {
        customer_id: 'user-1',
        sku: 'seed-product-0001',
        quantity: 1,
        currency: 'usd',
        base_price: 199.99,
        offers: [],
        final_price: 199.99,
      },
      ranked: {
        customer_id: 'user-1',
        ranked: [{ sku: 'seed-product-0001', score: 0.75, reason_codes: ['input_score'] }],
      },
      composed: {
        customer_id: 'user-1',
        headline: 'Top picks for user-1',
        recommendations: [
          {
            sku: 'seed-product-0001',
            title: 'Wireless Headphones',
            score: 0.75,
            message: 'Recommended for user-1 based on shopping intent',
          },
        ],
      },
    },
    error: null,
    isPending: false,
    isError: false,
  }),
}));

jest.mock('../../lib/hooks/useCart', () => ({
  useCart: () => ({
    data: {
      user_id: 'user-1',
      items: [
        {
          product_id: 'seed-product-0001',
          quantity: 1,
          price: 199.99,
        },
      ],
      total: 199.99,
    },
    isLoading: false,
    isError: false,
  }),
}));

jest.mock('../../lib/hooks/useInventory', () => ({
  useInventoryHealth: () => ({
    data: {
      total_skus: 1,
      healthy: 1,
      low_stock: 0,
      out_of_stock: 0,
      items: [],
    },
    isLoading: false,
    isError: false,
    isFetching: false,
    refetch: jest.fn(),
  }),
  useReservationOutcomeQueries: () => [],
}));

jest.mock('../../lib/hooks/useUser', () => ({
  useUserProfile: () => ({
    data: {
      name: 'Demo User',
      email: 'demo@example.com',
      phone: '555-0101',
      created_at: '2026-01-01T00:00:00Z',
    },
    isLoading: false,
    isError: false,
  }),
  useUpdateProfile: () => ({
    mutate: jest.fn(),
    isPending: false,
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
        status: 'requested',
        reason: 'Damaged',
        created_at: '2026-01-27T10:00:00Z',
        updated_at: '2026-01-27T10:00:00Z',
        requested_at: '2026-01-27T10:00:00Z',
        approved_at: null,
        rejected_at: null,
        received_at: null,
        restocked_at: null,
        refunded_at: null,
        last_transition_at: '2026-01-27T10:00:00Z',
        status_history: [],
        audit_log: [],
        refund: null,
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
  useCreateStaffTicket: () => ({
    mutate: jest.fn(),
    isPending: false,
  }),
  useUpdateStaffTicket: () => ({
    mutate: jest.fn(),
    isPending: false,
  }),
  useResolveStaffTicket: () => ({
    mutate: jest.fn(),
    isPending: false,
  }),
  useEscalateStaffTicket: () => ({
    mutate: jest.fn(),
    isPending: false,
  }),
  useApproveStaffReturn: () => ({
    mutateAsync: jest.fn(),
    isPending: false,
    error: null,
  }),
  useRejectStaffReturn: () => ({
    mutateAsync: jest.fn(),
    isPending: false,
    error: null,
  }),
  useReceiveStaffReturn: () => ({
    mutateAsync: jest.fn(),
    isPending: false,
    error: null,
  }),
  useRestockStaffReturn: () => ({
    mutateAsync: jest.fn(),
    isPending: false,
    error: null,
  }),
  useRefundStaffReturn: () => ({
    mutateAsync: jest.fn(),
    isPending: false,
    error: null,
  }),
}));

jest.mock('../../lib/hooks/useTruthAdmin', () => ({
  useTruthSchemas: () => ({
    data: [
      {
        id: 'schema-1',
        category: 'electronics',
        version: '1.0.0',
        fields: [{ name: 'brand', type: 'string', required: true }],
        created_at: '2026-01-01T00:00:00Z',
        updated_at: '2026-01-01T00:00:00Z',
      },
    ],
    isLoading: false,
    isError: false,
  }),
  useCreateTruthSchema: () => ({ mutate: jest.fn(), isPending: false }),
  useUpdateTruthSchema: () => ({ mutate: jest.fn(), isPending: false }),
  useDeleteTruthSchema: () => ({ mutate: jest.fn(), isPending: false }),
  useTruthConfig: () => ({
    data: {
      tenant_id: 'tenant-1',
      auto_approve_threshold: 0.95,
      enrichment_enabled: true,
      hitl_enabled: true,
      writeback_enabled: false,
      writeback_dry_run: false,
      feature_flags: { new_dashboard: true },
      updated_at: '2026-01-01T00:00:00Z',
    },
    isLoading: false,
    isError: false,
  }),
  useUpdateTruthConfig: () => ({ mutate: jest.fn(), isPending: false, isSuccess: false, isError: false }),
  useTruthAnalyticsSummary: () => ({
    data: {
      overall_completeness: 0.82,
      total_products: 500,
      enrichment_jobs_processed: 1200,
      auto_approved: 980,
      sent_to_hitl: 220,
      queue_pending: 45,
      queue_approved: 155,
      queue_rejected: 20,
      avg_review_time_minutes: 8.5,
      acp_exports: 800,
      ucp_exports: 300,
    },
    isLoading: false,
    isError: false,
  }),
  useTruthCompletenessBreakdown: () => ({
    data: [
      { category: 'electronics', completeness: 0.9, product_count: 120 },
      { category: 'fashion', completeness: 0.75, product_count: 200 },
    ],
    isLoading: false,
  }),
  useTruthPipelineThroughput: () => ({
    data: [
      { timestamp: '2026-01-01T00:00:00Z', ingested: 100, enriched: 95, approved: 80, rejected: 5 },
    ],
    isLoading: false,
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

jest.mock('../../lib/hooks/useTruth', () => ({
  useReviewQueue: () => ({
    data: {
      items: [
        {
          id: 'proposal-1',
          entity_id: 'prod-001',
          product_title: 'Wireless Headphones',
          category: 'Electronics',
          field_name: 'color',
          current_value: null,
          proposed_value: 'Midnight Black',
          confidence: 0.92,
          source: 'gpt-4o',
          proposed_at: '2026-03-01T10:00:00Z',
          status: 'pending',
        },
      ],
      total: 1,
      page: 1,
      page_size: 20,
    },
    isLoading: false,
    isError: false,
  }),
  useReviewStats: () => ({
    data: {
      pending: 1,
      approved_today: 5,
      rejected_today: 2,
      avg_confidence: 0.87,
    },
    isLoading: false,
    isError: false,
  }),
  useProductReviewDetail: () => ({ data: undefined, isLoading: false, isError: false }),
  useAuditHistory: () => ({ data: [], isLoading: false, isError: false }),
  useReviewAction: () => ({ mutate: jest.fn(), isPending: false }),
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
  beforeEach(() => {
    useSearchParamsMock.mockReturnValue({
      get: (_key: string) => null,
    });
  });

  it('renders the home page hero', () => {
    render(<HomePage />);
    expect(
      screen.getByText('Plan Your Peak Weekend Cart')
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

  it('renders orders page with return lifecycle action state', () => {
    render(<OrdersPage />);
    expect(screen.getByText('Orders')).toBeInTheDocument();
    expect(screen.getByText('Request Return')).toBeInTheDocument();
    expect(screen.getByText('Return lifecycle in progress: requested')).toBeInTheDocument();
  });

  it('renders order details page', () => {
    render(<OrderTrackingPage />);
    expect(screen.getByText('Order Details')).toBeInTheDocument();
  });

  it('renders profile page', () => {
    render(<ProfilePage />);
    expect(screen.getByText('My Profile')).toBeInTheDocument();
    expect(screen.getByText('Demo User')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('tab', { name: 'Addresses' }));
    expect(screen.getByText('Addresses are not available in the current API contract.')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('tab', { name: 'Payment Methods' }));
    expect(screen.getByText('Payment methods are not available in the current API contract.')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('tab', { name: 'Security' }));
    expect(screen.getByText('Security settings are not available in the current API contract.')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('tab', { name: 'Preferences' }));
    expect(screen.getByText('Preferences are not available in the current API contract.')).toBeInTheDocument();

    expect(screen.queryByText('123 Main St')).not.toBeInTheDocument();
    expect(screen.queryByText('456 Office Plaza')).not.toBeInTheDocument();
    expect(screen.queryByText('Add New Address')).not.toBeInTheDocument();
    expect(screen.queryByText('Add Payment Method')).not.toBeInTheDocument();
  });

  it('renders dashboard page', () => {
    render(<DashboardPage />);
    expect(screen.getByText('My Dashboard')).toBeInTheDocument();
    expect(screen.getByText('Total Orders')).toBeInTheDocument();
    expect(screen.getAllByText('Unavailable').length).toBeGreaterThan(0);
    expect(screen.getByText('Rewards data is not available in the current API contract.')).toBeInTheDocument();
    expect(screen.queryByText('1,250 points')).not.toBeInTheDocument();
    expect(screen.queryByText("You're 750 points away from your next reward!")).not.toBeInTheDocument();
  });

  it('renders admin portal page', () => {
    render(<AdminPortalPage />);
    expect(screen.getByText('Admin Portal')).toBeInTheDocument();
  });

  it('renders admin schemas page', () => {
    render(<SchemasPage />);
    expect(screen.getByText('Schema Management')).toBeInTheDocument();
  });

  it('renders admin config page', () => {
    render(<ConfigPage />);
    expect(screen.getAllByText('Tenant Configuration').length).toBeGreaterThan(0);
  });

  it('renders truth analytics page', () => {
    render(<TruthAnalyticsPage />);
    expect(screen.getByText('Truth Layer Analytics')).toBeInTheDocument();
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

  it('renders route-protection login message when redirect is present', () => {
    useSearchParamsMock.mockReturnValue({
      get: (key: string) => (key === 'redirect' ? '/checkout' : null),
    });

    render(<LoginPage />);
    expect(screen.getByText('Sign in to continue to the page you requested.')).toBeInTheDocument();
  });

  it('renders signup page', () => {
    SignupPage();
    expect(redirect).toHaveBeenCalledWith('/auth/login');
  });

  it('renders staff review queue page', () => {
    render(<StaffReviewQueuePage />);
    expect(screen.getByText('AI Review Queue')).toBeInTheDocument();
  });
});
