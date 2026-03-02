'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import Image from 'next/image';
import { Button } from '@/components/atoms/Button';
import { FiArrowRight, FiShoppingCart } from 'react-icons/fi';

const SLIDES = [
  {
    id: 1,
    title: 'Experience Pure Power',
    subtitle: 'New UltraSlate Pro 11" with M2 Chip',
    description: 'Perfect for digital artists and professionals. The ultimate tablet experience is here.',
    image: 'https://images.unsplash.com/photo-1544244015-0df4b3ffc6b0?auto=format&fit=crop&w=1600&q=80',
    ctaLink: '/shop?category=electronics',
    ctaText: 'Shop Tablets',
    bgClass: 'bg-gradient-to-r from-gray-900 via-gray-800 to-black',
  },
  {
    id: 2,
    title: 'Cinematic Experience at Home',
    subtitle: 'CinemaView OLED 65"',
    description: 'Perfect blacks, infinite contrast. Transform your living room today.',
    image: 'https://images.unsplash.com/photo-1593359677879-a4bb92f829d1?auto=format&fit=crop&w=1600&q=80',
    ctaLink: '/shop?category=electronics',
    ctaText: 'View TVs',
    bgClass: 'bg-gradient-to-r from-blue-900 via-indigo-900 to-black',
  },
  {
    id: 3,
    title: 'Style Meets Comfort',
    subtitle: 'Urban Explorer Collection',
    description: 'Discover the new season essentials designed for modern city living.',
    image: 'https://images.unsplash.com/photo-1483985988355-763728e1935b?auto=format&fit=crop&w=1600&q=80',
    ctaLink: '/shop?category=fashion',
    ctaText: 'Explore Fashion',
    bgClass: 'bg-gradient-to-r from-rose-900 via-purple-900 to-black',
  }
];

export const HeroSlider: React.FC = () => {
  const [currentSlide, setCurrentSlide] = useState(0);

  useEffect(() => {
    const timer = setInterval(() => {
      setCurrentSlide((prev) => (prev + 1) % SLIDES.length);
    }, 5000);
    return () => clearInterval(timer);
  }, []);

  const slide = SLIDES[currentSlide];

  return (
    <div className="relative h-[500px] w-full overflow-hidden rounded-3xl shadow-xl transition-all duration-700">
      {SLIDES.map((s, index) => (
         <div 
           key={s.id}
           className={`absolute inset-0 transition-opacity duration-1000 ease-in-out ${index === currentSlide ? 'opacity-100 z-10' : 'opacity-0 z-0'}`}
         >
            <div className="absolute inset-0 bg-black/40 z-10" /> 
            {/* Background Image */}
            <div className="absolute inset-0">
               <Image 
                 src={s.image} 
                 alt={s.title}
                 fill
                 className="object-cover"
                 priority={index === 0}
               />
            </div>
            
            {/* Content Overlay */}
            <div className={`absolute inset-0 z-20 flex flex-col justify-center px-8 md:px-16 lg:px-24 bg-gradient-to-r from-black/80 via-black/40 to-transparent`}>
              <div className="max-w-2xl text-white transform transition-transform duration-700 translate-y-0 opacity-100">
                <span className="inline-block py-1 px-3 rounded-full bg-prime-500/90 text-white text-sm font-semibold mb-4 backdrop-blur-sm">
                  {s.subtitle}
                </span>
                <h2 className="text-4xl md:text-6xl font-extrabold mb-4 leading-tight">
                  {s.title}
                </h2>
                <p className="text-lg md:text-xl text-gray-200 mb-8 max-w-lg">
                  {s.description}
                </p>
                <div className="flex gap-4">
                  <Link href={s.ctaLink}>
                    <Button size="lg" className="bg-white text-black hover:bg-gray-100 border-none font-bold px-8">
                       {s.ctaText} <FiArrowRight className="ml-2" />
                    </Button>
                  </Link>
                </div>
              </div>
            </div>
         </div>
      ))}

      {/* Dots */}
      <div className="absolute bottom-6 left-1/2 transform -translate-x-1/2 z-30 flex gap-2">
        {SLIDES.map((_, index) => (
          <button
            key={index}
            onClick={() => setCurrentSlide(index)}
            className={`w-3 h-3 rounded-full transition-all duration-300 ${
              index === currentSlide ? 'bg-white w-8' : 'bg-white/50 hover:bg-white/80'
            }`}
             aria-label={`Go to slide ${index + 1}`}
          />
        ))}
      </div>
    </div>
  );
};
