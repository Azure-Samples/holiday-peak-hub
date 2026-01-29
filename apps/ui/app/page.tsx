'use client';

import React from 'react';
import Link from 'next/link';
import { MainLayout } from '@/components/templates/MainLayout';
import { Button } from '@/components/atoms/Button';
import { Badge } from '@/components/atoms/Badge';
import { Card } from '@/components/molecules/Card';
import { FiShoppingCart, FiTrendingUp, FiPackage, FiZap, FiArrowRight } from 'react-icons/fi';

export default function HomePage() {
  return (
    <MainLayout>
      {/* Hero Section */}
      <section className="relative bg-gradient-to-br from-ocean-500 via-cyan-500 to-ocean-600 dark:from-ocean-700 dark:via-cyan-700 dark:to-ocean-800 rounded-3xl overflow-hidden mb-12">
        <div className="relative z-10 px-8 py-16 md:py-24 lg:py-32">
          <div className="max-w-3xl">
            <Badge className="bg-lime-500 text-white mb-6 text-sm font-semibold px-4 py-2">
              🎉 Holiday Season Sale - Up to 40% Off
            </Badge>
            <h1 className="text-4xl md:text-5xl lg:text-6xl font-bold text-white mb-6 leading-tight">
              Discover Amazing Products for Your Lifestyle
            </h1>
            <p className="text-xl text-ocean-50 mb-8 leading-relaxed">
              Shop from thousands of premium products with intelligent recommendations, 
              real-time inventory, and fast delivery.
            </p>
            <div className="flex flex-col sm:flex-row gap-4">
              <Link href="/category/all">
                <Button 
                  size="lg" 
                  className="bg-white text-ocean-500 hover:bg-ocean-50 font-semibold px-8"
                >
                  <FiShoppingCart className="mr-2 w-5 h-5" />
                  Start Shopping
                </Button>
              </Link>
              <Link href="/category/deals">
                <Button 
                  size="lg" 
                  variant="outline" 
                  className="border-2 border-white text-white hover:bg-white/10 font-semibold px-8"
                >
                  View Deals
                  <FiArrowRight className="ml-2 w-5 h-5" />
                </Button>
              </Link>
            </div>
          </div>
        </div>
        
        {/* Decorative overlay */}
        <div className="absolute inset-0 bg-gradient-to-br from-transparent to-black/20" />
      </section>

      {/* Category Cards */}
      <section className="mb-16">
        <div className="flex items-center justify-between mb-8">
          <h2 className="text-3xl font-bold text-gray-900 dark:text-white">
            Shop by Category
          </h2>
          <Link href="/category/all" className="text-ocean-500 dark:text-ocean-300 hover:underline font-medium flex items-center">
            View All <FiArrowRight className="ml-1 w-4 h-4" />
          </Link>
        </div>
        
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
          <CategoryCard
            title="Electronics"
            image="/api/placeholder/400/300"
            href="/category/electronics"
            count="2,543 products"
          />
          <CategoryCard
            title="Fashion"
            image="/api/placeholder/400/300"
            href="/category/fashion"
            count="8,921 products"
          />
          <CategoryCard
            title="Home & Garden"
            image="/api/placeholder/400/300"
            href="/category/home-garden"
            count="1,234 products"
          />
          <CategoryCard
            title="Sports"
            image="/api/placeholder/400/300"
            href="/category/sports"
            count="3,456 products"
          />
        </div>
      </section>

      {/* Featured Products */}
      <section className="mb-16">
        <div className="flex items-center justify-between mb-8">
          <div>
            <h2 className="text-3xl font-bold text-gray-900 dark:text-white mb-2">
              Trending Now
            </h2>
            <p className="text-gray-600 dark:text-gray-400">
              Most popular products this week
            </p>
          </div>
          <Badge className="bg-lime-500 text-white">
            <FiTrendingUp className="w-4 h-4 mr-1 inline" />
            Hot
          </Badge>
        </div>
        
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
          <ProductCard
            title="Wireless Headphones"
            price="$199.99"
            originalPrice="$299.99"
            image="/api/placeholder/300/300"
            rating={4.5}
            reviews={234}
            href="/product/1"
          />
          <ProductCard
            title="Smart Watch Pro"
            price="$349.99"
            image="/api/placeholder/300/300"
            rating={4.8}
            reviews={567}
            href="/product/2"
          />
          <ProductCard
            title="Running Shoes"
            price="$89.99"
            originalPrice="$129.99"
            image="/api/placeholder/300/300"
            rating={4.6}
            reviews={890}
            href="/product/3"
          />
          <ProductCard
            title="Laptop Backpack"
            price="$49.99"
            image="/api/placeholder/300/300"
            rating={4.4}
            reviews={456}
            href="/product/4"
          />
        </div>
      </section>

      {/* Features Section */}
      <section className="mb-16">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <FeatureCard
            icon={<FiZap className="w-8 h-8" />}
            title="Fast Delivery"
            description="Get your orders delivered within 2-3 business days"
            color="ocean"
          />
          <FeatureCard
            icon={<FiPackage className="w-8 h-8" />}
            title="Easy Returns"
            description="30-day hassle-free return policy on all products"
            color="lime"
          />
          <FeatureCard
            icon={<FiTrendingUp className="w-8 h-8" />}
            title="Best Prices"
            description="Competitive pricing with regular discounts and deals"
            color="cyan"
          />
        </div>
      </section>
    </MainLayout>
  );
}

function CategoryCard({ title, image, href, count }: { title: string; image: string; href: string; count: string }) {
  return (
    <Link href={href}>
      <div className="group relative overflow-hidden rounded-xl bg-white dark:bg-gray-800 shadow-md hover:shadow-xl transition-all duration-300 transform hover:-translate-y-1">
        <div className="aspect-[4/3] overflow-hidden">
          <div className="w-full h-full bg-gradient-to-br from-ocean-100 to-cyan-100 dark:from-ocean-900 dark:to-cyan-900" />
        </div>
        <div className="p-4">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-1">
            {title}
          </h3>
          <p className="text-sm text-gray-600 dark:text-gray-400">{count}</p>
        </div>
        <div className="absolute inset-0 bg-ocean-500/10 dark:bg-ocean-300/10 opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
      </div>
    </Link>
  );
}

function ProductCard({ title, price, originalPrice, image, rating, reviews, href }: { 
  title: string; 
  price: string; 
  originalPrice?: string;
  image: string; 
  rating: number; 
  reviews: number;
  href: string;
}) {
  return (
    <Link href={href}>
      <Card className="group hover:shadow-xl transition-all duration-300 transform hover:-translate-y-1">
        <div className="aspect-square overflow-hidden rounded-t-lg">
          <div className="w-full h-full bg-gradient-to-br from-gray-100 to-gray-200 dark:from-gray-800 dark:to-gray-700" />
        </div>
        <div className="p-4">
          <h3 className="font-semibold text-gray-900 dark:text-white mb-2 line-clamp-2">
            {title}
          </h3>
          <div className="flex items-center mb-2">
            <div className="flex items-center text-yellow-400">
              {'★'.repeat(Math.floor(rating))}{'☆'.repeat(5 - Math.floor(rating))}
            </div>
            <span className="text-xs text-gray-500 dark:text-gray-400 ml-2">
              ({reviews})
            </span>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-xl font-bold text-ocean-500 dark:text-ocean-300">
              {price}
            </span>
            {originalPrice && (
              <span className="text-sm text-gray-500 dark:text-gray-400 line-through">
                {originalPrice}
              </span>
            )}
          </div>
        </div>
      </Card>
    </Link>
  );
}

function FeatureCard({ icon, title, description, color }: { 
  icon: React.ReactNode; 
  title: string; 
  description: string;
  color: 'ocean' | 'lime' | 'cyan';
}) {
  const colorClasses = {
    ocean: 'bg-ocean-100 dark:bg-ocean-900 text-ocean-500 dark:text-ocean-300',
    lime: 'bg-lime-100 dark:bg-lime-900 text-lime-500 dark:text-lime-300',
    cyan: 'bg-cyan-100 dark:bg-cyan-900 text-cyan-500 dark:text-cyan-300',
  };

  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-md border border-gray-200 dark:border-gray-700">
      <div className={`w-14 h-14 rounded-lg flex items-center justify-center mb-4 ${colorClasses[color]}`}>
        {icon}
      </div>
      <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
        {title}
      </h3>
      <p className="text-gray-600 dark:text-gray-400 text-sm">
        {description}
      </p>
    </div>
  );
}
