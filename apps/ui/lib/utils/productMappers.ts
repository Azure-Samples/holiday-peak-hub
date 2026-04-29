/**
 * Product mapping helpers for UI consumption.
 */

import type { Product as ApiProduct } from '../types/api';
import type { Product as UiProduct } from '../../components/types';

export interface AcpProduct {
  item_id: string;
  title: string;
  description?: string;
  enriched_description?: string;
  use_cases?: string[];
  complementary_products?: string[];
  substitute_products?: string[];
  extended_attributes?: {
    use_cases?: string[];
    complementary_products?: string[];
    substitute_products?: string[];
    enriched_description?: string;
  };
  image_url?: string;
  image?: string;
  category?: string;
  category_id?: string;
  brand?: string;
  price?: string;
  availability?: string;
}

const PLACEHOLDER_IMAGES = [
  '/images/products/p1.jpg',
  '/images/products/p2.jpg',
  '/images/products/p3.jpg',
  '/images/products/p4.jpg',
  '/images/products/p5.jpg',
];

function getPlaceholderImage(productId?: string): string {
  if (!productId) {
    return PLACEHOLDER_IMAGES[0];
  }

  let hash = 0;
  for (let index = 0; index < productId.length; index += 1) {
    hash = ((hash << 5) - hash + productId.charCodeAt(index)) | 0;
  }

  return PLACEHOLDER_IMAGES[Math.abs(hash) % PLACEHOLDER_IMAGES.length];
}

const INVALID_IMAGE_HOSTS = new Set([
  'example.com',
  'www.example.com',
  'via.placeholder.com',
  'placeholder.com',
]);

const INVALID_IMAGE_HOST_SUFFIXES = ['unsplash.com'];

export const sanitizeProductImageUrl = (rawUrl?: string, productId?: string): string => {
  const placeholder = getPlaceholderImage(productId);

  if (!rawUrl) {
    return placeholder;
  }

  const candidate = rawUrl.trim();
  if (!candidate) {
    return placeholder;
  }

  if (candidate.startsWith('/')) {
    return candidate;
  }

  if (candidate.startsWith('http://') || candidate.startsWith('https://')) {
    try {
      const parsed = new URL(candidate);
      const hostname = parsed.hostname.toLowerCase();
      const hasBlockedSuffix = INVALID_IMAGE_HOST_SUFFIXES.some(
        (suffix) => hostname === suffix || hostname.endsWith(`.${suffix}`),
      );
      if (INVALID_IMAGE_HOSTS.has(hostname) || hasBlockedSuffix) {
        return placeholder;
      }
      return candidate;
    } catch {
      return placeholder;
    }
  }

  return placeholder;
};

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
  const thumbnail = sanitizeProductImageUrl(product.image_url || mediaImage, product.id);
  const placeholder = getPlaceholderImage(product.id);
  const mappedImages =
    product.media
      ?.map((media) => sanitizeProductImageUrl(String(media.url), product.id))
      .filter((url) => url !== placeholder) || [];
  return {
    sku: product.id,
    title: product.name,
    description: product.description,
    brand: 'Holiday Peak',
    category: product.category_id,
    price: product.price,
    currency: 'USD',
    images: mappedImages.length > 0 ? mappedImages : [thumbnail],
    thumbnail,
    rating: product.rating,
    reviewCount: product.review_count,
    inStock: product.in_stock,
    tags: product.features,
    useCases: product.use_cases,
    complementaryProducts: product.complementary_products,
    substituteProducts: product.substitute_products,
    enrichedDescription: product.enriched_description,
  };
};

export const mapAcpProductToUiProduct = (product: AcpProduct): UiProduct => {
  const { amount, currency } = parsePriceString(product.price);
  const thumbnail = sanitizeProductImageUrl(product.image_url || product.image, product.item_id);
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
    useCases: product.use_cases || product.extended_attributes?.use_cases || [],
    complementaryProducts:
      product.complementary_products || product.extended_attributes?.complementary_products || [],
    substituteProducts:
      product.substitute_products || product.extended_attributes?.substitute_products || [],
    enrichedDescription:
      product.enriched_description || product.extended_attributes?.enriched_description || undefined,
  };
};

export const mapApiProductsToUi = (products: ApiProduct[]): UiProduct[] =>
  products.map(mapApiProductToUiProduct);

export const mapAcpProductsToUi = (products: AcpProduct[]): UiProduct[] =>
  products.map(mapAcpProductToUiProduct);
