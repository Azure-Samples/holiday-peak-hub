/**
 * API Endpoints
 * 
 * Centralized definition of all backend API endpoints
 */

export const API_ENDPOINTS = {
  // Health
  health: '/health',
  ready: '/ready',

  // Authentication
  auth: {
    me: '/api/auth/me',
    register: '/api/auth/register',
    logout: '/api/auth/logout',
  },

  // Users
  users: {
    me: '/api/users/me',
    update: '/api/users/me',
  },

  // Products
  products: {
    list: '/api/products',
    get: (id: string) => `/api/products/${id}`,
    search: (query: string) => `/api/products?search=${encodeURIComponent(query)}`,
    byCategory: (categoryId: string) => `/api/products?category=${categoryId}`,
  },

  // Brand Shopping Personalization
  brandShopping: {
    catalogProduct: (sku: string) => `/api/catalog/products/${sku}`,
    customerProfile: (customerId: string) => `/api/customers/${customerId}/profile`,
    pricingOffers: '/api/pricing/offers',
    rankRecommendations: '/api/recommendations/rank',
    composeRecommendations: '/api/recommendations/compose',
  },

  // Categories
  categories: {
    list: '/api/categories',
    get: (id: string) => `/api/categories/${id}`,
    children: (parentId: string) => `/api/categories?parent_id=${parentId}`,
  },

  // Cart
  cart: {
    get: '/api/cart',
    addItem: '/api/cart/items',
    removeItem: (productId: string) => `/api/cart/items/${productId}`,
    clear: '/api/cart',
  },

  // Orders
  orders: {
    list: '/api/orders',
    get: (id: string) => `/api/orders/${id}`,
    create: '/api/orders',
    cancel: (id: string) => `/api/orders/${id}/cancel`,
  },

  // Returns / Refund progression
  returns: {
    list: '/api/returns',
    create: '/api/returns',
    get: (id: string) => `/api/returns/${id}`,
    refund: (id: string) => `/api/returns/${id}/refund`,
  },

  // Checkout
  checkout: {
    validate: '/api/checkout/validate',
  },

  // Inventory / Reservations
  inventory: {
    health: '/api/inventory/health',
    reservations: {
      create: '/api/inventory/reservations',
      get: (reservationId: string) => `/api/inventory/reservations/${reservationId}`,
      confirm: (reservationId: string) => `/api/inventory/reservations/${reservationId}/confirm`,
      release: (reservationId: string) => `/api/inventory/reservations/${reservationId}/release`,
    },
  },

  // Payments
  payments: {
    intent: '/api/payments/intent',
    confirmIntent: '/api/payments/confirm-intent',
    process: '/api/payments',
    get: (id: string) => `/api/payments/${id}`,
  },

  // Reviews
  reviews: {
    list: (productId: string) => `/api/reviews?product_id=${productId}`,
    create: '/api/reviews',
    delete: (id: string) => `/api/reviews/${id}`,
  },

  // Staff - Analytics
  staff: {
    analytics: {
      summary: '/api/staff/analytics/summary',
    },
    tickets: {
      list: '/api/staff/tickets',
      create: '/api/staff/tickets',
      get: (id: string) => `/api/staff/tickets/${id}`,
      update: (id: string) => `/api/staff/tickets/${id}`,
      resolve: (id: string) => `/api/staff/tickets/${id}/resolve`,
      escalate: (id: string) => `/api/staff/tickets/${id}/escalate`,
    },
    returns: {
      list: '/api/staff/returns',
      get: (id: string) => `/api/staff/returns/${id}`,
      approve: (id: string) => `/api/staff/returns/${id}/approve`,
      reject: (id: string) => `/api/staff/returns/${id}/reject`,
      receive: (id: string) => `/api/staff/returns/${id}/receive`,
      restock: (id: string) => `/api/staff/returns/${id}/restock`,
      refund: (id: string) => `/api/staff/returns/${id}/refund`,
      refundProgress: (id: string) => `/api/staff/returns/${id}/refund`,
    },
    shipments: {
      list: '/api/staff/shipments',
      get: (id: string) => `/api/staff/shipments/${id}`,
    },
    review: {
      queue: '/api/staff/review',
      stats: '/api/staff/review/stats',
      product: (entityId: string) => `/api/staff/review/${entityId}`,
      audit: (entityId: string) => `/api/staff/review/${entityId}/audit`,
      action: (id: string) => `/api/staff/review/proposals/${id}`,
    },
  },

  // Truth Layer Admin
  truth: {
    schemas: {
      list: '/api/truth/schemas',
      get: (id: string) => `/api/truth/schemas/${id}`,
      create: '/api/truth/schemas',
      update: (id: string) => `/api/truth/schemas/${id}`,
      delete: (id: string) => `/api/truth/schemas/${id}`,
    },
    config: {
      get: '/api/truth/config',
      update: '/api/truth/config',
    },
    analytics: {
      summary: '/api/truth/analytics/summary',
      completeness: '/api/truth/analytics/completeness',
      throughput: '/api/truth/analytics/throughput',
    },
  },
} as const;

export default API_ENDPOINTS;
