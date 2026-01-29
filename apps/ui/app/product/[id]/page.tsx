'use client';

import React, { useState } from 'react';
import { MainLayout } from '@/components/templates/MainLayout';
import { Button } from '@/components/atoms/Button';
import { Badge } from '@/components/atoms/Badge';
import { Card } from '@/components/molecules/Card';
import { Select } from '@/components/atoms/Select';
import { Tabs } from '@/components/molecules/Tabs';
import Link from 'next/link';
import { 
  FiShoppingCart, FiHeart, FiTruck, FiShield, 
  FiRotateCcw, FiStar, FiCheck, FiMinus, FiPlus 
} from 'react-icons/fi';

export default function ProductPage({ params }: { params: { id: string } }) {
  const [quantity, setQuantity] = useState(1);
  const [selectedSize, setSelectedSize] = useState('M');
  const [selectedColor, setSelectedColor] = useState('Blue');

  // Mock product data - will be replaced with API call
  const product = {
    id: params.id,
    title: 'Premium Wireless Headphones',
    description: 'Experience crystal-clear audio with our premium wireless headphones featuring active noise cancellation, 30-hour battery life, and comfort-fit design.',
    price: 199.99,
    originalPrice: 299.99,
    rating: 4.8,
    reviews: 1234,
    inStock: true,
    stockCount: 47,
    brand: 'AudioTech',
    sku: 'WH-1000XM5',
    category: 'Electronics',
  };

  const discount = Math.round(((product.originalPrice - product.price) / product.originalPrice) * 100);

  return (
    <MainLayout>
      {/* Breadcrumb */}
      <nav className="text-sm text-gray-600 dark:text-gray-400 mb-6 flex items-center gap-2">
        <Link href="/" className="hover:text-ocean-500 dark:hover:text-ocean-300">Home</Link>
        <span>/</span>
        <Link href="/category/electronics" className="hover:text-ocean-500 dark:hover:text-ocean-300">Electronics</Link>
        <span>/</span>
        <span className="text-gray-900 dark:text-white">{product.title}</span>
      </nav>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 mb-16">
        {/* Product Images */}
        <div>
          {/* Main Image */}
          <div className="aspect-square bg-gradient-to-br from-gray-100 to-gray-200 dark:from-gray-800 dark:to-gray-700 rounded-2xl mb-4" />
          
          {/* Thumbnail Gallery */}
          <div className="grid grid-cols-4 gap-4">
            {[1, 2, 3, 4].map((i) => (
              <button
                key={i}
                className="aspect-square bg-gradient-to-br from-gray-100 to-gray-200 dark:from-gray-800 dark:to-gray-700 rounded-lg border-2 border-transparent hover:border-ocean-500 transition-colors"
              />
            ))}
          </div>
        </div>

        {/* Product Info */}
        <div>
          {/* Brand & Title */}
          <p className="text-sm text-gray-600 dark:text-gray-400 mb-2">{product.brand}</p>
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-4">
            {product.title}
          </h1>

          {/* Rating */}
          <div className="flex items-center gap-4 mb-6">
            <div className="flex items-center">
              <div className="flex text-yellow-400 text-lg">
                {'★'.repeat(Math.floor(product.rating))}{'☆'.repeat(5 - Math.floor(product.rating))}
              </div>
              <span className="ml-2 text-gray-900 dark:text-white font-semibold">
                {product.rating}
              </span>
            </div>
            <Link href="#reviews" className="text-ocean-500 dark:text-ocean-300 hover:underline">
              {product.reviews} reviews
            </Link>
          </div>

          {/* Price */}
          <div className="flex items-center gap-4 mb-6">
            <span className="text-4xl font-bold text-ocean-500 dark:text-ocean-300">
              ${product.price}
            </span>
            <span className="text-xl text-gray-500 dark:text-gray-400 line-through">
              ${product.originalPrice}
            </span>
            <Badge className="bg-lime-500 text-white text-lg px-3 py-1">
              {discount}% OFF
            </Badge>
          </div>

          {/* Stock Status */}
          {product.inStock ? (
            <div className="flex items-center gap-2 text-lime-600 dark:text-lime-400 mb-6">
              <FiCheck className="w-5 h-5" />
              <span className="font-semibold">In Stock ({product.stockCount} available)</span>
            </div>
          ) : (
            <div className="text-red-600 dark:text-red-400 mb-6">
              <span className="font-semibold">Out of Stock</span>
            </div>
          )}

          {/* Description */}
          <p className="text-gray-600 dark:text-gray-400 mb-8 leading-relaxed">
            {product.description}
          </p>

          {/* Variants */}
          <div className="space-y-6 mb-8">
            {/* Color */}
            <div>
              <label className="block text-sm font-semibold text-gray-900 dark:text-white mb-3">
                Color: {selectedColor}
              </label>
              <div className="flex gap-3">
                {['Blue', 'Black', 'White', 'Red'].map((color) => (
                  <button
                    key={color}
                    onClick={() => setSelectedColor(color)}
                    className={`w-12 h-12 rounded-lg border-2 ${
                      selectedColor === color
                        ? 'border-ocean-500 dark:border-ocean-300'
                        : 'border-gray-300 dark:border-gray-600'
                    }`}
                    style={{
                      backgroundColor: color.toLowerCase(),
                    }}
                  />
                ))}
              </div>
            </div>

            {/* Size */}
            <div>
              <label className="block text-sm font-semibold text-gray-900 dark:text-white mb-3">
                Size: {selectedSize}
              </label>
              <div className="flex gap-3">
                {['S', 'M', 'L', 'XL'].map((size) => (
                  <button
                    key={size}
                    onClick={() => setSelectedSize(size)}
                    className={`px-6 py-3 rounded-lg border-2 font-semibold ${
                      selectedSize === size
                        ? 'border-ocean-500 bg-ocean-50 text-ocean-500 dark:border-ocean-300 dark:bg-ocean-900 dark:text-ocean-300'
                        : 'border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300'
                    }`}
                  >
                    {size}
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* Quantity */}
          <div className="mb-8">
            <label className="block text-sm font-semibold text-gray-900 dark:text-white mb-3">
              Quantity
            </label>
            <div className="flex items-center gap-4">
              <div className="flex items-center border-2 border-gray-300 dark:border-gray-600 rounded-lg">
                <button
                  onClick={() => setQuantity(Math.max(1, quantity - 1))}
                  className="p-3 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-l-lg"
                >
                  <FiMinus className="w-5 h-5" />
                </button>
                <span className="px-6 py-3 font-semibold text-gray-900 dark:text-white">
                  {quantity}
                </span>
                <button
                  onClick={() => setQuantity(Math.min(product.stockCount, quantity + 1))}
                  className="p-3 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-r-lg"
                >
                  <FiPlus className="w-5 h-5" />
                </button>
              </div>
              <span className="text-sm text-gray-600 dark:text-gray-400">
                Maximum {product.stockCount} items
              </span>
            </div>
          </div>

          {/* Actions */}
          <div className="flex gap-4 mb-8">
            <Button
              size="lg"
              className="flex-1 bg-ocean-500 hover:bg-ocean-600 dark:bg-ocean-300 dark:hover:bg-ocean-400 text-white dark:text-gray-900 font-semibold"
            >
              <FiShoppingCart className="mr-2 w-5 h-5" />
              Add to Cart
            </Button>
            <Button
              size="lg"
              variant="outline"
              className="border-2 border-ocean-500 text-ocean-500 hover:bg-ocean-50 dark:border-ocean-300 dark:text-ocean-300"
            >
              <FiHeart className="w-5 h-5" />
            </Button>
          </div>

          {/* Features */}
          <Card className="p-6">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <Feature
                icon={<FiTruck className="w-6 h-6" />}
                title="Free Shipping"
                description="On orders over $50"
              />
              <Feature
                icon={<FiRotateCcw className="w-6 h-6" />}
                title="30-Day Returns"
                description="Hassle-free returns"
              />
              <Feature
                icon={<FiShield className="w-6 h-6" />}
                title="1-Year Warranty"
                description="Full protection"
              />
            </div>
          </Card>
        </div>
      </div>

      {/* Product Details Tabs */}
      <div className="mb-16">
        <Tabs
          tabs={[
            {
              id: 'description',
              label: 'Description',
              content: (
                <div className="prose dark:prose-invert max-w-none">
                  <h3>Product Description</h3>
                  <p>{product.description}</p>
                  <h4>Key Features</h4>
                  <ul>
                    <li>Active Noise Cancellation (ANC)</li>
                    <li>30-hour battery life</li>
                    <li>Bluetooth 5.0 connectivity</li>
                    <li>Comfort-fit cushioned ear cups</li>
                    <li>Built-in microphone for calls</li>
                  </ul>
                </div>
              ),
            },
            {
              id: 'specifications',
              label: 'Specifications',
              content: (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <SpecRow label="Brand" value={product.brand} />
                  <SpecRow label="Model" value={product.sku} />
                  <SpecRow label="Category" value={product.category} />
                  <SpecRow label="Weight" value="250g" />
                  <SpecRow label="Battery Life" value="30 hours" />
                  <SpecRow label="Connectivity" value="Bluetooth 5.0" />
                </div>
              ),
            },
            {
              id: 'reviews',
              label: `Reviews (${product.reviews})`,
              content: (
                <div className="space-y-6">
                  <ReviewCard
                    author="John Doe"
                    rating={5}
                    date="2 days ago"
                    comment="Excellent sound quality and very comfortable for long listening sessions!"
                  />
                  <ReviewCard
                    author="Jane Smith"
                    rating={4}
                    date="1 week ago"
                    comment="Great headphones, but a bit pricey. Worth it for the ANC feature though."
                  />
                  <ReviewCard
                    author="Mike Johnson"
                    rating={5}
                    date="2 weeks ago"
                    comment="Best headphones I've ever owned. The battery life is amazing!"
                  />
                </div>
              ),
            },
          ]}
        />
      </div>

      {/* Related Products */}
      <section>
        <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-6">
          You May Also Like
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
          {[1, 2, 3, 4].map((i) => (
            <RelatedProductCard key={i} id={i} />
          ))}
        </div>
      </section>
    </MainLayout>
  );
}

function Feature({ icon, title, description }: { icon: React.ReactNode; title: string; description: string }) {
  return (
    <div className="text-center">
      <div className="text-ocean-500 dark:text-ocean-300 mb-2 flex justify-center">
        {icon}
      </div>
      <h4 className="font-semibold text-gray-900 dark:text-white text-sm mb-1">
        {title}
      </h4>
      <p className="text-xs text-gray-600 dark:text-gray-400">
        {description}
      </p>
    </div>
  );
}

function SpecRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between py-3 border-b border-gray-200 dark:border-gray-700">
      <span className="font-medium text-gray-600 dark:text-gray-400">{label}</span>
      <span className="text-gray-900 dark:text-white">{value}</span>
    </div>
  );
}

function ReviewCard({ author, rating, date, comment }: { 
  author: string; 
  rating: number; 
  date: string; 
  comment: string;
}) {
  return (
    <Card className="p-6">
      <div className="flex items-start gap-4">
        <div className="w-12 h-12 rounded-full bg-ocean-500 dark:bg-ocean-300 flex items-center justify-center text-white dark:text-gray-900 font-bold">
          {author.charAt(0)}
        </div>
        <div className="flex-1">
          <div className="flex items-center justify-between mb-2">
            <h4 className="font-semibold text-gray-900 dark:text-white">{author}</h4>
            <span className="text-sm text-gray-500 dark:text-gray-400">{date}</span>
          </div>
          <div className="flex text-yellow-400 mb-2">
            {'★'.repeat(rating)}{'☆'.repeat(5 - rating)}
          </div>
          <p className="text-gray-600 dark:text-gray-400">{comment}</p>
        </div>
      </div>
    </Card>
  );
}

function RelatedProductCard({ id }: { id: number }) {
  return (
    <Link href={`/product/${id}`}>
      <Card className="group hover:shadow-xl transition-all duration-300 transform hover:-translate-y-1">
        <div className="aspect-square bg-gradient-to-br from-gray-100 to-gray-200 dark:from-gray-800 dark:to-gray-700 rounded-t-lg" />
        <div className="p-4">
          <h3 className="font-semibold text-gray-900 dark:text-white mb-2">
            Related Product {id}
          </h3>
          <div className="flex items-center gap-2">
            <span className="text-xl font-bold text-ocean-500 dark:text-ocean-300">
              ${(id * 89.99).toFixed(2)}
            </span>
            <div className="flex text-yellow-400 text-sm">
              ★★★★☆
            </div>
          </div>
        </div>
      </Card>
    </Link>
  );
}
