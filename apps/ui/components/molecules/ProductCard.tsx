/**
 * ProductCard Molecule Component
 * Product display card for e-commerce catalog
 */

import React from 'react';
import Image from 'next/image';
import Link from 'next/link';
import { FiHeart, FiShoppingCart } from 'react-icons/fi';
import { cn } from '../utils';
import { Badge } from '../atoms/Badge';
import { Button } from '../atoms/Button';
import { PriceDisplay } from './PriceDisplay';
import type { Product, BaseComponentProps } from '../types';

export interface ProductCardProps extends BaseComponentProps {
  /** Product data */
  product: Product;
  /** Card layout */
  layout?: 'grid' | 'list';
  /** Whether to show add to cart button */
  showAddToCart?: boolean;
  /** Whether to show wishlist button */
  showWishlist?: boolean;
  /** Whether to show quick view button */
  showQuickView?: boolean;
  /** Add to cart handler */
  onAddToCart?: (product: Product) => void;
  /** Wishlist handler */
  onWishlist?: (product: Product) => void;
  /** Quick view handler */
  onQuickView?: (product: Product) => void;
  /** Whether product is in wishlist */
  inWishlist?: boolean;
  /** Image priority (for LCP optimization) */
  imagePriority?: boolean;
}

export const ProductCard: React.FC<ProductCardProps> = ({
  product,
  layout = 'grid',
  showAddToCart = true,
  showWishlist = true,
  showQuickView = false,
  onAddToCart,
  onWishlist,
  onQuickView,
  inWishlist = false,
  imagePriority = false,
  className,
  testId,
  ariaLabel,
}) => {
  const {
    sku,
    title,
    description,
    brand,
    category,
    price,
    msrp,
    salePrice,
    currency,
    thumbnail,
    rating,
    reviewCount,
    inStock,
    tags,
  } = product;

  const finalPrice = salePrice || price;
  const isOnSale = msrp && finalPrice < msrp;

  if (layout === 'list') {
    return (
      <div
        data-testid={testId}
        aria-label={ariaLabel || title}
        className={cn(
          'flex items-center gap-4 p-4',
          'bg-white dark:bg-gray-800',
          'border border-gray-200 dark:border-gray-700',
          'rounded-lg hover:shadow-md transition-shadow duration-200',
          className
        )}
      >
        {/* Image */}
        <Link
          href={`/products/${sku}`}
          className="shrink-0 w-24 h-24 relative overflow-hidden rounded-md"
        >
          <Image
            src={thumbnail}
            alt={title}
            fill
            className="object-cover"
            priority={imagePriority}
          />
          {!inStock && (
            <div className="absolute inset-0 bg-black/50 flex items-center justify-center">
              <Badge variant="error">Out of Stock</Badge>
            </div>
          )}
        </Link>

        {/* Content */}
        <div className="flex-1 min-w-0">
          <div className="flex items-start justify-between gap-2">
            <div className="flex-1 min-w-0">
              {brand && (
                <p className="text-xs text-gray-500 dark:text-gray-400 uppercase">
                  {brand}
                </p>
              )}
              <Link
                href={`/products/${sku}`}
                className="block font-semibold text-gray-900 dark:text-white hover:text-blue-600 dark:hover:text-blue-400 truncate"
              >
                {title}
              </Link>
              {category && (
                <p className="text-sm text-gray-500 dark:text-gray-400">
                  {category}
                </p>
              )}
              <p className="text-sm text-gray-600 dark:text-gray-300 line-clamp-2 mt-1">
                {description}
              </p>
            </div>

            {/* Price */}
            <PriceDisplay
              price={finalPrice}
              msrp={msrp}
              currency={currency}
              size="md"
            />
          </div>

          {/* Rating & Actions */}
          <div className="flex items-center gap-2 mt-2">
            {rating && (
              <div className="flex items-center gap-1">
                <span className="text-yellow-500">★</span>
                <span className="text-sm text-gray-600 dark:text-gray-400">
                  {rating.toFixed(1)}
                  {reviewCount && ` (${reviewCount})`}
                </span>
              </div>
            )}

            <div className="ml-auto flex items-center gap-2">
              {showWishlist && (
                <Button
                  variant="ghost"
                  size="sm"
                  iconOnly
                  onClick={() => onWishlist?.(product)}
                  ariaLabel="Add to wishlist"
                >
                  <FiHeart
                    className={cn(
                      'w-4 h-4',
                      inWishlist && 'fill-current text-red-500'
                    )}
                  />
                </Button>
              )}

              {showAddToCart && (
                <Button
                  variant="primary"
                  size="sm"
                  onClick={() => onAddToCart?.(product)}
                  disabled={!inStock}
                  iconLeft={<FiShoppingCart className="w-4 h-4" />}
                >
                  Add to Cart
                </Button>
              )}
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Grid layout
  return (
    <div
      data-testid={testId}
      aria-label={ariaLabel || title}
      className={cn(
        'group relative flex flex-col',
        'bg-white dark:bg-gray-800',
        'border border-gray-200 dark:border-gray-700',
        'rounded-lg overflow-hidden',
        'hover:shadow-lg transition-shadow duration-200',
        className
      )}
    >
      {/* Badges */}
      <div className="absolute top-2 left-2 z-10 flex flex-col gap-1">
        {isOnSale && <Badge variant="error" size="sm">Sale</Badge>}
        {!inStock && <Badge variant="secondary" size="sm">Out of Stock</Badge>}
        {tags?.map((tag) => (
          <Badge key={tag} variant="primary" size="sm">
            {tag}
          </Badge>
        ))}
      </div>

      {/* Wishlist Button */}
      {showWishlist && (
        <button
          type="button"
          onClick={() => onWishlist?.(product)}
          className={cn(
            'absolute top-2 right-2 z-10',
            'p-2 rounded-full bg-white/90 dark:bg-gray-800/90',
            'hover:bg-white dark:hover:bg-gray-800',
            'transition-colors duration-200',
            'opacity-0 group-hover:opacity-100'
          )}
          aria-label="Add to wishlist"
        >
          <FiHeart
            className={cn(
              'w-5 h-5',
              inWishlist ? 'fill-current text-red-500' : 'text-gray-600 dark:text-gray-400'
            )}
          />
        </button>
      )}

      {/* Image */}
      <Link
        href={`/products/${sku}`}
        className="relative aspect-square overflow-hidden bg-gray-100 dark:bg-gray-900"
      >
        <Image
          src={thumbnail}
          alt={title}
          fill
          className="object-cover group-hover:scale-105 transition-transform duration-300"
          priority={imagePriority}
        />
      </Link>

      {/* Content */}
      <div className="flex-1 flex flex-col p-4">
        {brand && (
          <p className="text-xs text-gray-500 dark:text-gray-400 uppercase mb-1">
            {brand}
          </p>
        )}
        
        <Link
          href={`/products/${sku}`}
          className="font-semibold text-gray-900 dark:text-white hover:text-blue-600 dark:hover:text-blue-400 line-clamp-2 mb-2"
        >
          {title}
        </Link>

        {/* Rating */}
        {rating && (
          <div className="flex items-center gap-1 mb-2">
            <span className="text-yellow-500 text-sm">★</span>
            <span className="text-sm text-gray-600 dark:text-gray-400">
              {rating.toFixed(1)}
              {reviewCount && ` (${reviewCount})`}
            </span>
          </div>
        )}

        {/* Price */}
        <PriceDisplay
          price={finalPrice}
          msrp={msrp}
          currency={currency}
          size="md"
          className="mb-3"
        />

        {/* Actions */}
        <div className="mt-auto flex gap-2">
          {showAddToCart && (
            <Button
              variant="primary"
              size="sm"
              fullWidth
              onClick={() => onAddToCart?.(product)}
              disabled={!inStock}
              iconLeft={<FiShoppingCart className="w-4 h-4" />}
            >
              {inStock ? 'Add to Cart' : 'Out of Stock'}
            </Button>
          )}
          
          {showQuickView && (
            <Button
              variant="secondary"
              size="sm"
              onClick={() => onQuickView?.(product)}
            >
              Quick View
            </Button>
          )}
        </div>
      </div>
    </div>
  );
};

ProductCard.displayName = 'ProductCard';
