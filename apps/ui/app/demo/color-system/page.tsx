'use client';

import React from 'react';
import { MainLayout } from '@/components/templates/MainLayout';
import { Button } from '@/components/atoms/Button';
import { Badge } from '@/components/atoms/Badge';
import { FiShoppingCart, FiTrendingUp, FiPackage, FiClock } from 'react-icons/fi';

export default function ColorSystemDemo() {
  return (
    <MainLayout>
      <div className="space-y-12">
        {/* Hero Section */}
        <section className="bg-gradient-to-r from-ocean-500 to-cyan-500 dark:from-ocean-700 dark:to-cyan-700 rounded-2xl p-12 text-white">
          <div className="max-w-3xl">
            <Badge className="bg-lime-500 text-white mb-4">New Color System</Badge>
            <h1 className="text-5xl font-bold mb-4">
              Welcome to Holiday Peak Hub
            </h1>
            <p className="text-xl text-ocean-50 mb-8">
              Experience our new Ocean Blue, Lime Green, and Cyan color palette designed for modern retail excellence.
            </p>
            <div className="flex gap-4">
              <Button size="lg" className="bg-white text-ocean-500 hover:bg-ocean-50">
                <FiShoppingCart className="mr-2" />
                Start Shopping
              </Button>
              <Button size="lg" variant="outline" className="border-white text-white hover:bg-white/10">
                Learn More
              </Button>
            </div>
          </div>
        </section>

        {/* Color Palette Showcase */}
        <section>
          <h2 className="text-3xl font-bold text-gray-900 dark:text-white mb-8">Color Palette</h2>
          
          {/* Ocean Blue */}
          <div className="mb-8">
            <h3 className="text-xl font-semibold text-gray-900 dark:text-white mb-4">Ocean Blue - Primary</h3>
            <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
              <ColorSwatch color="ocean-50" label="50" />
              <ColorSwatch color="ocean-100" label="100" />
              <ColorSwatch color="ocean-200" label="200" />
              <ColorSwatch color="ocean-300" label="300" />
              <ColorSwatch color="ocean-400" label="400" />
              <ColorSwatch color="ocean-500" label="500" primary />
              <ColorSwatch color="ocean-600" label="600" />
              <ColorSwatch color="ocean-700" label="700" />
              <ColorSwatch color="ocean-800" label="800" />
              <ColorSwatch color="ocean-900" label="900" />
            </div>
          </div>

          {/* Lime Green */}
          <div className="mb-8">
            <h3 className="text-xl font-semibold text-gray-900 dark:text-white mb-4">Lime Green - Success</h3>
            <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
              <ColorSwatch color="lime-50" label="50" />
              <ColorSwatch color="lime-100" label="100" />
              <ColorSwatch color="lime-200" label="200" />
              <ColorSwatch color="lime-300" label="300" />
              <ColorSwatch color="lime-400" label="400" />
              <ColorSwatch color="lime-500" label="500" primary />
              <ColorSwatch color="lime-600" label="600" />
              <ColorSwatch color="lime-700" label="700" />
              <ColorSwatch color="lime-800" label="800" />
              <ColorSwatch color="lime-900" label="900" />
            </div>
          </div>

          {/* Cyan */}
          <div className="mb-8">
            <h3 className="text-xl font-semibold text-gray-900 dark:text-white mb-4">Cyan - Accent</h3>
            <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
              <ColorSwatch color="cyan-50" label="50" />
              <ColorSwatch color="cyan-100" label="100" />
              <ColorSwatch color="cyan-200" label="200" />
              <ColorSwatch color="cyan-300" label="300" />
              <ColorSwatch color="cyan-400" label="400" />
              <ColorSwatch color="cyan-500" label="500" primary />
              <ColorSwatch color="cyan-600" label="600" />
              <ColorSwatch color="cyan-700" label="700" />
              <ColorSwatch color="cyan-800" label="800" />
              <ColorSwatch color="cyan-900" label="900" />
            </div>
          </div>
        </section>

        {/* Component Showcase */}
        <section>
          <h2 className="text-3xl font-bold text-gray-900 dark:text-white mb-8">Components with New Colors</h2>
          
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {/* Feature Card 1 */}
            <div className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-md border border-gray-200 dark:border-gray-700">
              <div className="w-12 h-12 bg-ocean-100 dark:bg-ocean-900 rounded-lg flex items-center justify-center mb-4">
                <FiTrendingUp className="w-6 h-6 text-ocean-500 dark:text-ocean-300" />
              </div>
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
                Real-time Analytics
              </h3>
              <p className="text-gray-600 dark:text-gray-400 mb-4">
                Track your sales and customer behavior with powerful insights.
              </p>
              <Button variant="outline" className="w-full border-ocean-500 text-ocean-500 hover:bg-ocean-50 dark:border-ocean-300 dark:text-ocean-300">
                Learn More
              </Button>
            </div>

            {/* Feature Card 2 */}
            <div className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-md border border-gray-200 dark:border-gray-700">
              <div className="w-12 h-12 bg-lime-100 dark:bg-lime-900 rounded-lg flex items-center justify-center mb-4">
                <FiPackage className="w-6 h-6 text-lime-500 dark:text-lime-300" />
              </div>
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
                Inventory Management
              </h3>
              <p className="text-gray-600 dark:text-gray-400 mb-4">
                Keep your stock levels optimized with intelligent predictions.
              </p>
              <Button className="w-full bg-lime-500 hover:bg-lime-600 text-white">
                Get Started
              </Button>
            </div>

            {/* Feature Card 3 */}
            <div className="bg-white dark:bg-gray-800 rounded-xl p-6 shadow-md border border-gray-200 dark:border-gray-700">
              <div className="w-12 h-12 bg-cyan-100 dark:bg-cyan-900 rounded-lg flex items-center justify-center mb-4">
                <FiClock className="w-6 h-6 text-cyan-500 dark:text-cyan-300" />
              </div>
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
                Fast Delivery
              </h3>
              <p className="text-gray-600 dark:text-gray-400 mb-4">
                Optimize routes and reduce delivery times with AI.
              </p>
              <Button className="w-full bg-cyan-500 hover:bg-cyan-600 text-white">
                Track Orders
              </Button>
            </div>
          </div>
        </section>

        {/* Button Variants */}
        <section>
          <h2 className="text-3xl font-bold text-gray-900 dark:text-white mb-8">Button Variants</h2>
          
          <div className="space-y-6">
            <div>
              <h3 className="text-lg font-semibold text-gray-700 dark:text-gray-300 mb-4">Primary (Ocean Blue)</h3>
              <div className="flex flex-wrap gap-4">
                <Button size="sm" className="bg-ocean-500 hover:bg-ocean-600 dark:bg-ocean-300 dark:hover:bg-ocean-400">
                  Small
                </Button>
                <Button className="bg-ocean-500 hover:bg-ocean-600 dark:bg-ocean-300 dark:hover:bg-ocean-400">
                  Medium
                </Button>
                <Button size="lg" className="bg-ocean-500 hover:bg-ocean-600 dark:bg-ocean-300 dark:hover:bg-ocean-400">
                  Large
                </Button>
              </div>
            </div>

            <div>
              <h3 className="text-lg font-semibold text-gray-700 dark:text-gray-300 mb-4">Success (Lime Green)</h3>
              <div className="flex flex-wrap gap-4">
                <Button size="sm" className="bg-lime-500 hover:bg-lime-600 dark:bg-lime-400 dark:hover:bg-lime-500">
                  Small
                </Button>
                <Button className="bg-lime-500 hover:bg-lime-600 dark:bg-lime-400 dark:hover:bg-lime-500">
                  Medium
                </Button>
                <Button size="lg" className="bg-lime-500 hover:bg-lime-600 dark:bg-lime-400 dark:hover:bg-lime-500">
                  Large
                </Button>
              </div>
            </div>

            <div>
              <h3 className="text-lg font-semibold text-gray-700 dark:text-gray-300 mb-4">Accent (Cyan)</h3>
              <div className="flex flex-wrap gap-4">
                <Button size="sm" className="bg-cyan-500 hover:bg-cyan-600 dark:bg-cyan-400 dark:hover:bg-cyan-500">
                  Small
                </Button>
                <Button className="bg-cyan-500 hover:bg-cyan-600 dark:bg-cyan-400 dark:hover:bg-cyan-500">
                  Medium
                </Button>
                <Button size="lg" className="bg-cyan-500 hover:bg-cyan-600 dark:bg-cyan-400 dark:hover:bg-cyan-500">
                  Large
                </Button>
              </div>
            </div>
          </div>
        </section>

        {/* Badges */}
        <section>
          <h2 className="text-3xl font-bold text-gray-900 dark:text-white mb-8">Badges</h2>
          
          <div className="flex flex-wrap gap-4">
            <Badge className="bg-ocean-500 text-white">Ocean Blue</Badge>
            <Badge className="bg-lime-500 text-white">Lime Green</Badge>
            <Badge className="bg-cyan-500 text-white">Cyan</Badge>
            <Badge className="bg-ocean-100 text-ocean-700 dark:bg-ocean-900 dark:text-ocean-300">Ocean Light</Badge>
            <Badge className="bg-lime-100 text-lime-700 dark:bg-lime-900 dark:text-lime-300">Lime Light</Badge>
            <Badge className="bg-cyan-100 text-cyan-700 dark:bg-cyan-900 dark:text-cyan-300">Cyan Light</Badge>
          </div>
        </section>
      </div>
    </MainLayout>
  );
}

function ColorSwatch({ color, label, primary }: { color: string; label: string; primary?: boolean }) {
  return (
    <div className="group cursor-pointer">
      <div className={`h-24 rounded-lg bg-${color} border-2 ${primary ? 'border-gray-900 dark:border-white' : 'border-transparent'} transition-transform group-hover:scale-105`} />
      <div className="mt-2 text-center">
        <div className="text-sm font-medium text-gray-900 dark:text-white">{label}</div>
        {primary && <div className="text-xs text-gray-500 dark:text-gray-400">Primary</div>}
      </div>
    </div>
  );
}
