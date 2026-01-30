/**
 * TypeScript types matching backend API models
 */

// User types
export interface User {
  user_id: string;
  email: string;
  name: string;
  roles: string[];
}

export interface UserProfile {
  id: string;
  email: string;
  name: string;
  phone?: string;
  created_at: string;
}

export interface UpdateProfileRequest {
  name?: string;
  phone?: string;
}

// Product types
export interface Product {
  id: string;
  name: string;
  description: string;
  price: number;
  category_id: string;
  image_url?: string;
  in_stock: boolean;
}

// Category types
export interface Category {
  id: string;
  name: string;
  description?: string;
  parent_id?: string;
  image_url?: string;
}

// Cart types
export interface CartItem {
  product_id: string;
  quantity: number;
  price: number;
}

export interface Cart {
  user_id: string;
  items: CartItem[];
  total: number;
}

export interface AddToCartRequest {
  product_id: string;
  quantity: number;
}

// Order types
export interface OrderItem {
  product_id: string;
  quantity: number;
  price: number;
}

export interface Order {
  id: string;
  user_id: string;
  items: OrderItem[];
  total: number;
  status: string;
  created_at: string;
}

export interface CreateOrderRequest {
  shipping_address_id: string;
  payment_method_id: string;
}

// Checkout types
export interface CheckoutValidationResponse {
  valid: boolean;
  errors: string[];
  warnings: string[];
  estimated_total: number;
  estimated_shipping: number;
  estimated_tax: number;
}

// Payment types
export interface ProcessPaymentRequest {
  order_id: string;
  payment_method_id: string;
  amount: number;
}

export interface Payment {
  id: string;
  order_id: string;
  amount: number;
  status: string;
  transaction_id?: string;
  created_at: string;
}

// Review types
export interface Review {
  id: string;
  product_id: string;
  user_id: string;
  rating: number;
  title: string;
  comment: string;
  created_at: string;
}

export interface CreateReviewRequest {
  product_id: string;
  rating: number;
  title: string;
  comment: string;
}

// Staff types
export interface SalesAnalytics {
  total_revenue: number;
  total_orders: number;
  average_order_value: number;
  top_products: any[];
}

export interface Ticket {
  id: string;
  user_id: string;
  subject: string;
  status: string;
  priority: string;
  created_at: string;
}

export interface Return {
  id: string;
  order_id: string;
  user_id: string;
  status: string;
  reason: string;
  created_at: string;
}

export interface Shipment {
  id: string;
  order_id: string;
  status: string;
  carrier: string;
  tracking_number: string;
  created_at: string;
}

// API Response wrappers
export interface ApiResponse<T> {
  data: T;
  status: number;
}

export interface ApiError {
  detail: string;
  status: number;
}
