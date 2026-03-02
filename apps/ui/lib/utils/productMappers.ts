/**
 * Product mapping helpers for UI consumption.
 */

import type { Product as ApiProduct } from '../types/api';
import type { Product as UiProduct } from '../../components/types';

export interface AcpProduct {
  item_id: string;
  title: string;
  description?: string;
  image_url?: string;
  image?: string;
  category?: string;
  category_id?: string;
  brand?: string;
  price?: string;
  availability?: string;
}

const PLACEHOLDER_IMAGE = '/images/products/p1.jpg';

export const parsePriceString = (
  rawPrice?: string
): { amount: number; currency: string } => {
  if (!rawPrice) {
    return { amount: 0, currency: 'USD' };
  }

  const amountMatch = rawPrice.match(/([0-9]+(?:\.[0-9]+)?)/);
  const currencyMatch = rawPrice.match(/([A-Za-z]{3})/);

  return {
    amount: amountMatch ? Number(amountMatch[1]) : 0,
    currency: currencyMatch ? currencyMatch[1].toUpperCase() : 'USD',
  };
};

export const mapApiProductToUiProduct = (product: ApiProduct): UiProduct => {
  const mediaImage = product.media?.find((media) => Boolean(media.url))?.url;
  const thumbnail = product.image_url || mediaImage || PLACEHOLDER_IMAGE;
  return {
    sku: product.id,
    title: product.name,
    description: product.description,
    brand: 'Holiday Peak',
    category: product.category_id,
    price: product.price,
    currency: 'USD',
    images:
      product.media?.map((media) => String(media.url)).filter(Boolean) || [thumbnail],
    thumbnail,
    rating: product.rating,
    reviewCount: product.review_count,
    inStock: product.in_stock,
    tags: product.features,
  };
};

export const mapAcpProductToUiProduct = (product: AcpProduct): UiProduct => {
  const { amount, currency } = parsePriceString(product.price);
  const thumbnail = product.image_url || product.image || PLACEHOLDER_IMAGE;
  const availability = (product.availability || '').toLowerCase();
  return {
    sku: product.item_id,
    title: product.title,
    description: product.description || '',
    brand: product.brand || 'Holiday Peak',
    category: product.category_id || product.category || 'search',
    price: amount,
    currency,
    images: [thumbnail],
    thumbnail,
    inStock: availability !== 'out_of_stock',
  };
};

export const mapApiProductsToUi = (products: ApiProduct[]): UiProduct[] =>
  products.map(mapApiProductToUiProduct);

export const mapAcpProductsToUi = (products: AcpProduct[]): UiProduct[] =>
  products.map(mapAcpProductToUiProduct);
