'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import Image from 'next/image';
import { Button } from '@/components/atoms/Button';
import { FiArrowRight, FiMessageSquare } from 'react-icons/fi';

const SLIDES = [
  {
    id: 1,
    title: 'Plan Your Peak Weekend Cart',
    subtitle: 'Catalog Signal: New electronics in stock',
    description: 'Explore high-demand items in the live catalog and move directly to product details.',
    image: 'https://images.unsplash.com/photo-1544244015-0df4b3ffc6b0?auto=format&fit=crop&w=1600&q=80',
    ctaLink: '/category?slug=electronics',
    ctaText: 'Open Catalog',
  },
  {
    id: 2,
    title: 'Move From Discovery To Decision',
    subtitle: 'Catalog + Agent workflow',
    description: 'Compare options in the catalog, then use the Product Enrichment Agent for deeper guidance.',
    image: 'https://images.unsplash.com/photo-1593359677879-a4bb92f829d1?auto=format&fit=crop&w=1600&q=80',
    ctaLink: '/agents/product-enrichment-chat',
    ctaText: 'Ask Product Agent',
  },
  {
    id: 3,
    title: 'Trace Product Context Fast',
    subtitle: 'Data interpretation ready',
    description: 'Go from category view to product insights with a route-safe demo flow for stakeholders.',
    image: 'https://images.unsplash.com/photo-1483985988355-763728e1935b?auto=format&fit=crop&w=1600&q=80',
    ctaLink: '/category?slug=fashion',
    ctaText: 'View Category',
  },
];

export const HeroSlider: React.FC = () => {
  const [currentSlide, setCurrentSlide] = useState(0);
  const [reducedMotion, setReducedMotion] = useState(false);
  const [announceSlide, setAnnounceSlide] = useState(false);

  useEffect(() => {
    const media = window.matchMedia('(prefers-reduced-motion: reduce)');
    const update = () => setReducedMotion(media.matches);
    update();
    media.addEventListener('change', update);
    return () => media.removeEventListener('change', update);
  }, []);

  useEffect(() => {
    if (reducedMotion) {
      return undefined;
    }

    const timer = setInterval(() => {
      setCurrentSlide((prev) => (prev + 1) % SLIDES.length);
    }, 5500);

    return () => clearInterval(timer);
  }, [reducedMotion]);

  useEffect(() => {
    setAnnounceSlide(true);
  }, [currentSlide]);

  const goToPreviousSlide = () => {
    setCurrentSlide((prev) => (prev - 1 + SLIDES.length) % SLIDES.length);
  };

  const goToNextSlide = () => {
    setCurrentSlide((prev) => (prev + 1) % SLIDES.length);
  };

  const handleCarouselKeyDown: React.KeyboardEventHandler<HTMLElement> = (event) => {
    if (event.key === 'ArrowLeft') {
      event.preventDefault();
      goToPreviousSlide();
      return;
    }

    if (event.key === 'ArrowRight') {
      event.preventDefault();
      goToNextSlide();
    }
  };

  const active = SLIDES[currentSlide];

  return (
    <section
      role="region"
      aria-roledescription="carousel"
      aria-label="Holiday Peak showcase"
      tabIndex={0}
      onKeyDown={handleCarouselKeyDown}
      className="showcase-shell relative isolate w-full overflow-hidden"
    >
      <div className="absolute inset-0 bg-gradient-to-br from-[var(--hp-primary)]/15 via-transparent to-[var(--hp-accent)]/20" aria-hidden="true" />

      {SLIDES.map((s, index) => (
        <div
          key={s.id}
          className={`absolute inset-0 transition-opacity duration-700 ease-out ${index === currentSlide ? 'opacity-100 z-10' : 'opacity-0 z-0'}`}
          aria-hidden={index !== currentSlide}
        >
          <div className="absolute inset-0">
            <Image
              src={s.image}
              alt={s.title}
              fill
              className="object-cover"
              priority={index === 0}
            />
          </div>
          <div className="absolute inset-0 bg-gradient-to-r from-hp-hero-overlay/85 via-hp-hero-overlay/55 to-hp-hero-overlay/20" />
        </div>
      ))}

      <div className="relative z-20 flex min-h-80 flex-col justify-end p-5 sm:min-h-96 sm:p-7 lg:p-10">
        <div className="max-w-2xl text-white showcase-enter">
          <span className="mb-3 inline-flex rounded-full border border-white/25 bg-white/15 px-3 py-1 text-xs font-semibold uppercase tracking-[0.16em]">
            {active.subtitle}
          </span>
          <h1 className="text-balance text-3xl font-black leading-tight sm:text-4xl lg:text-5xl">{active.title}</h1>
          <p className="mt-3 max-w-xl text-sm text-white/85 sm:text-base">{active.description}</p>
          <div className="mt-5 flex flex-col gap-3 sm:flex-row">
            <Link href={active.ctaLink}>
              <Button size="lg" className="bg-[var(--hp-primary)] px-6 py-3 text-sm hover:bg-[var(--hp-primary-hover)]">
                {active.ctaText}
                <FiArrowRight className="ml-1" />
              </Button>
            </Link>

            <Link href="/agents/product-enrichment-chat">
              <Button size="lg" variant="secondary" className="border border-white/20 bg-white/10 px-6 py-3 text-sm text-white hover:bg-white/20">
                <FiMessageSquare className="mr-1" />
                Agent Product Enrichment Chat
              </Button>
            </Link>
          </div>
        </div>

        <div className="mt-5 flex items-center gap-2" role="tablist" aria-label="Showcase slides">
          {SLIDES.map((slide, index) => (
            <button
              key={slide.id}
              onClick={() => setCurrentSlide(index)}
              className={`h-2.5 rounded-full transition-all ${index === currentSlide ? 'w-9 bg-white' : 'w-3 bg-white/50 hover:bg-white/80'}`}
              aria-label={`Go to slide ${index + 1}`}
              aria-selected={index === currentSlide}
              role="tab"
            />
          ))}
        </div>

        <p className="sr-only" aria-live="polite" aria-atomic="true">
          {announceSlide ? `Slide ${currentSlide + 1} of ${SLIDES.length}: ${active.title}` : ''}
        </p>
      </div>

      {reducedMotion && (
        <p className="absolute right-4 top-4 z-30 rounded-full bg-black/45 px-3 py-1 text-xs text-white">
          Reduced motion enabled
        </p>
      )}
    </section>
  );
};
