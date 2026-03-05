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
import { FiTrendingUp, FiArrowRight, FiList, FiMessageSquare } from 'react-icons/fi';

export default function HomePage() {
  const { data: categories = [] } = useCategories();
  const { data: products = [], isLoading } = useProducts({ limit: 8 });

  const featuredProducts = mapApiProductsToUi(products);
  const featuredCategories = categories.slice(0, 4);

  return (
    <MainLayout>
      <section className="mb-8 sm:mb-10">
        <HeroSlider />
      </section>

      <section className="showcase-shell mb-8 p-4 sm:mb-10 sm:p-5">
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
          <h2 className="text-2xl font-black showcase-gradient-text sm:text-3xl">
            Explore Catalog Departments
          </h2>
          <Link
            href="/category?slug=all"
            className="inline-flex items-center text-sm font-semibold text-[var(--hp-primary)] transition-colors hover:text-[var(--hp-primary-hover)]"
          >
            Open full catalog
            <FiArrowRight className="ml-1 h-4 w-4" />
          </Link>
        </div>

        <p className="mb-4 text-sm text-[var(--hp-text-muted)]">
          Catalog path: start by category, then open product detail pages for exact attributes and pricing.
        </p>

        <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
          {featuredCategories.length > 0 ? (
            featuredCategories.map((category) => (
              <Link
                key={category.id}
                href={`/category?slug=${encodeURIComponent(category.id)}`}
                className="group relative block aspect-[4/3] overflow-hidden rounded-2xl border border-[var(--hp-border)] shadow-sm transition-all duration-300 hover:-translate-y-1 hover:shadow-xl"
              >
                {category.image_url ? (
                  <Image
                    src={category.image_url}
                    alt={category.name}
                    fill
                    className="object-cover transition-transform duration-500 group-hover:scale-110"
                  />
                ) : (
                  <div className="absolute inset-0 animate-pulse bg-[var(--hp-surface-strong)]" />
                )}
                <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-black/20 to-transparent" />
                <div className="absolute bottom-4 left-4 text-white z-10">
                  <h3 className="mb-1 text-lg font-bold sm:text-xl">{category.name}</h3>
                  <p className="translate-y-2 text-xs text-gray-200 opacity-0 transition-all duration-300 group-hover:translate-y-0 group-hover:opacity-100 sm:text-sm">
                    {category.description || 'Browse products'}
                  </p>
                </div>
              </Link>
            ))
          ) : (
            Array(4).fill(0).map((_, i) => (
              <div key={i} className="aspect-[4/3] animate-pulse rounded-2xl bg-[var(--hp-surface-strong)]" />
            ))
          )}
        </div>
      </section>

      <section className="mb-8 sm:mb-10">
        <div className="mb-5 flex flex-wrap items-center gap-3">
          <Badge className="bg-[var(--hp-surface-strong)] px-3 py-1 text-[var(--hp-primary)]">
            <FiTrendingUp className="mr-1 inline" /> Trending Now
          </Badge>
          <h2 className="text-2xl font-black text-[var(--hp-text)] sm:text-3xl">
            Product Discovery Grid
          </h2>
        </div>

        <ProductGrid
          products={featuredProducts}
          loading={isLoading}
          gridColumns={4}
          ariaLabel="Featured product catalog"
        />

        <div className="mt-6 text-center">
          <Link href="/category?slug=all">
            <Button
              size="lg"
              variant="secondary"
              className="rounded-full border border-[var(--hp-border)] px-8 text-[var(--hp-text)]"
            >
              Browse All Catalog Products
            </Button>
          </Link>
        </div>
      </section>

      <section className="showcase-shell relative mb-10 overflow-hidden p-5 sm:p-8">
        <div className="absolute inset-0">
          <Image
            src="https://images.unsplash.com/photo-1556742049-0cfed4f7a07d?auto=format&fit=crop&w=1600&q=80"
            alt="Data and AI support"
            fill
            className="object-cover opacity-10"
          />
        </div>

        <div className="relative z-10 grid gap-4 md:grid-cols-2">
          <article className="rounded-2xl border border-[var(--hp-border)] bg-[var(--hp-surface)]/90 p-4">
            <div className="mb-2 inline-flex items-center text-sm font-semibold text-[var(--hp-accent)]">
              <FiList className="mr-2 h-4 w-4" />
              Catalog Interpretation Layer
            </div>
            <h3 className="text-xl font-black text-[var(--hp-text)]">Use Product Cards For Facts</h3>
            <p className="mt-2 text-sm text-[var(--hp-text-muted)]">
              Price, stock, and category details come from catalog data shown in the grid and product pages.
            </p>
          </article>

          <article className="rounded-2xl border border-[var(--hp-border)] bg-[var(--hp-surface)]/90 p-4">
            <div className="mb-2 inline-flex items-center text-sm font-semibold text-[var(--hp-primary)]">
              <FiMessageSquare className="mr-2 h-4 w-4" />
              Agent Interaction Layer
            </div>
            <h3 className="text-xl font-black text-[var(--hp-text)]">Use Agent For Enrichment</h3>
            <p className="mt-2 text-sm text-[var(--hp-text-muted)]">
              Ask the Product Enrichment Agent for comparisons and interpretation beyond raw catalog fields.
            </p>
            <div className="mt-4">
              <Link href="/agents/product-enrichment-chat">
                <Button className="bg-[var(--hp-primary)] hover:bg-[var(--hp-primary-hover)]">
                  Open Agent Chat
                </Button>
              </Link>
            </div>
          </article>
        </div>
      </section>

      <ChatWidget />
    </MainLayout>
  );
}
