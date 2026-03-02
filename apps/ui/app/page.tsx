'use client';

import React from 'react';
import Link from 'next/link';
import Image from 'next/image';
import { MainLayout } from '@/components/templates/MainLayout';
import { Button } from '@/components/atoms/Button';
import { Badge } from '@/components/atoms/Badge';
import { ProductGrid } from '@/components/organisms/ProductGrid';
import { HeroSlider } from '@/components/organisms/HeroSlider';
import { ChatWidget } from '@/components/organisms/ChatWidget';
import { useCategories } from '@/lib/hooks/useCategories';
import { useProducts } from '@/lib/hooks/useProducts';
import { mapApiProductsToUi } from '@/lib/utils/productMappers';
import { FiTrendingUp, FiArrowRight } from 'react-icons/fi';

export default function HomePage() {
  const { data: categories = [] } = useCategories();
  const { data: products = [], isLoading } = useProducts({ limit: 8 });

  const featuredProducts = mapApiProductsToUi(products);
  const featuredCategories = categories.slice(0, 4);

  return (
    <MainLayout>
      {/* Hero Section with Slider */}
      <section className="mb-12">
        <HeroSlider />
      </section>

      {/* Categories Grid - Google Shopping Style */}
      <section className="mb-16">
        <div className="flex items-center justify-between mb-8">
          <h2 className="text-3xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-gray-900 to-gray-600 dark:from-white dark:to-gray-300">
            Shop by Department
          </h2>
          <Link href="/category?slug=all" className="text-prime-600 hover:text-prime-700 font-medium flex items-center transition-colors">
            View All <FiArrowRight className="ml-1 w-4 h-4" />
          </Link>
        </div>
        
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {featuredCategories.length > 0 ? (
            featuredCategories.map((category) => (
              <Link 
                key={category.id} 
                href={`/category?slug=${encodeURIComponent(category.id)}`}
                className="group relative overflow-hidden rounded-2xl aspect-[4/3] shadow-md hover:shadow-xl transition-all duration-300 transform hover:-translate-y-1 block"
              >
                {category.image_url ? (
                  <Image
                    src={category.image_url}
                    alt={category.name}
                    fill
                    className="object-cover transition-transform duration-500 group-hover:scale-110"
                  />
                ) : (
                  <div className="absolute inset-0 bg-gray-200 dark:bg-gray-800 animate-pulse" />
                )}
                <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-black/20 to-transparent" />
                <div className="absolute bottom-4 left-4 text-white z-10">
                  <h3 className="text-xl font-bold mb-1">{category.name}</h3>
                  <p className="text-sm text-gray-200 opacity-0 group-hover:opacity-100 transition-opacity duration-300 transform translate-y-2 group-hover:translate-y-0">
                    {category.description || 'Shop Now'}
                  </p>
                </div>
              </Link>
            ))
          ) : (
             Array(4).fill(0).map((_, i) => (
               <div key={i} className="rounded-2xl aspect-[4/3] bg-gray-100 dark:bg-gray-800 animate-pulse" />
             ))
          )}
        </div>
      </section>

      {/* Featured Products - Innovative Grid */}
      <section className="mb-16">
        <div className="flex items-center gap-3 mb-8">
          <Badge className="bg-prime-100 text-prime-700 dark:bg-prime-900/30 dark:text-prime-300 px-3 py-1">
             <FiTrendingUp className="mr-1 inline" /> Trending Now
          </Badge>
          <h2 className="text-3xl font-bold text-gray-900 dark:text-white">
            Daily Discoveries
          </h2>
        </div>
        
        <ProductGrid 
          products={featuredProducts} 
          loading={isLoading} 
          columns={4}
        />

        <div className="mt-12 text-center">
           <Link href="/shop">
             <Button size="lg" variant="outline" className="rounded-full px-8 border-gray-300 hover:bg-gray-50 dark:border-gray-700 dark:hover:bg-gray-800">
               Load More Products
             </Button>
           </Link>
        </div>
      </section>

      {/* Innovative CTA Section */}
      <section className="relative rounded-3xl overflow-hidden bg-gray-900 text-white mb-16 shadow-2xl">
         <div className="absolute inset-0">
            <Image 
              src="https://images.unsplash.com/photo-1556742049-0cfed4f7a07d?auto=format&fit=crop&w=1600&q=80" 
              alt="Customer Support" 
              fill
              className="object-cover opacity-20"
            />
         </div>
         <div className="relative z-10 p-12 md:p-16 text-center max-w-2xl mx-auto">
            <h2 className="text-3xl md:text-5xl font-bold mb-6">Need Help Choosing?</h2>
            <p className="text-xl text-gray-300 mb-8 font-light">
              Our AI-powered agents are ready to help you compare products, check stock, and find exactly what you need in seconds.
            </p>
            <div className="flex justify-center gap-4">
               {/* Trigger Chat Widget via event or context would be better, but this visual CTA directs user to the widget */}
               <Button 
                 size="lg" 
                 className="bg-white text-gray-900 hover:bg-gray-100 font-bold px-8 py-4 h-auto text-lg rounded-full shadow-lg hover:shadow-xl transform hover:-translate-y-1 transition-all"
                 onClick={() => {
                    const chatBtn = document.querySelector('button[aria-label="Open chat"]') as HTMLButtonElement;
                    if(chatBtn) chatBtn.click();
                 }}
               >
                 Start Chatting
               </Button>
            </div>
         </div>
      </section>

      {/* Floating Chat Widget */}
      <ChatWidget />
    </MainLayout>
  );
}
