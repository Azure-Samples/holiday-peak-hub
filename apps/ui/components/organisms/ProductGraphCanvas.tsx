'use client';

import React, { useEffect, useMemo, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import type { Product } from '@/components/types';
import type { Category } from '@/lib/types/api';
import agentApiClient from '@/lib/api/agentClient';
import { formatAgentResponse } from '@/lib/utils/agentResponseCards';
import { trackEcommerceEvent } from '@/lib/utils/telemetry';

type GraphNode = {
  id: Category['id'];
  x: number;
  y: number;
  width: number;
  height: number;
  categoryName: string;
  summary: string;
  href: string;
  productCount: number;
};

type Viewport = {
  x: number;
  y: number;
};

export interface ProductGraphCanvasProps {
  categories: Category[];
  products: Product[];
  title?: string;
  ariaLabel?: string;
  height?: number;
}

const NODE_WIDTH = 248;
const NODE_HEIGHT = 132;
const CLICK_DRAG_THRESHOLD = 8;
const WORLD_WIDTH = 1500;
const WORLD_HEIGHT = 900;

const clamp = (value: number, min: number, max: number): number =>
  Math.min(max, Math.max(min, value));

const seededJitter = (seed: string): number => {
  let hash = 0;
  for (let index = 0; index < seed.length; index += 1) {
    hash = (hash * 31 + seed.charCodeAt(index)) >>> 0;
  }
  return (hash % 23) - 11;
};

const toGraphNodes = (params: {
  categories: Category[];
  summaries: Record<string, string>;
  productBuckets: Record<string, Product[]>;
}): GraphNode[] => {
  const { categories, summaries, productBuckets } = params;
  if (categories.length === 0) {
    return [];
  }

  const centerX = WORLD_WIDTH / 2;
  const centerY = WORLD_HEIGHT / 2;
  const radiusX = categories.length < 5 ? WORLD_WIDTH * 0.24 : WORLD_WIDTH * 0.34;
  const radiusY = categories.length < 5 ? WORLD_HEIGHT * 0.24 : WORLD_HEIGHT * 0.3;

  return categories.map((category, index) => {
    const angle = (index / Math.max(categories.length, 1)) * Math.PI * 2;
    const jitterX = seededJitter(`${category.id}-x`);
    const jitterY = seededJitter(`${category.id}-y`);
    const productsForCategory = productBuckets[category.id] || [];

    return {
      id: category.id,
      x: Math.round(centerX + Math.cos(angle) * radiusX + jitterX * 4),
      y: Math.round(centerY + Math.sin(angle) * radiusY + jitterY * 4),
      width: NODE_WIDTH,
      height: NODE_HEIGHT,
      categoryName: category.name,
      summary:
        summaries[category.id] ||
        category.description ||
        `Explore ${category.name} products with AI-enriched recommendations.`,
      href: `/category?slug=${encodeURIComponent(category.id)}`,
      productCount: productsForCategory.length,
    };
  });
};

export const ProductGraphCanvas: React.FC<ProductGraphCanvasProps> = ({
  categories,
  products,
  title = 'Category Intelligence Graph',
  ariaLabel = 'Draggable category graph with AI summaries',
  height = 620,
}) => {
  const router = useRouter();
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const pointerStartRef = useRef<{ x: number; y: number } | null>(null);
  const viewportStartRef = useRef<Viewport>({ x: 0, y: 0 });
  const draggedRef = useRef(false);
  const [containerWidth, setContainerWidth] = useState(0);
  const [summariesByCategory, setSummariesByCategory] = useState<Record<string, string>>({});
  const [summariesLoading, setSummariesLoading] = useState(false);
  const [viewport, setViewport] = useState<Viewport>({
    x: (WORLD_WIDTH - 900) / 2,
    y: (WORLD_HEIGHT - 600) / 2,
  });

  const productBuckets = useMemo(() => {
    const buckets: Record<string, Product[]> = {};
    products.forEach((product) => {
      const key = product.category;
      if (!buckets[key]) {
        buckets[key] = [];
      }
      buckets[key].push(product);
    });
    return buckets;
  }, [products]);

  const graphCategories = useMemo(() => categories.slice(0, 10), [categories]);

  const nodes = useMemo(
    () =>
      toGraphNodes({
        categories: graphCategories,
        summaries: summariesByCategory,
        productBuckets,
      }),
    [graphCategories, productBuckets, summariesByCategory],
  );

  useEffect(() => {
    let cancelled = false;

    const loadSummaries = async () => {
      if (graphCategories.length === 0) {
        return;
      }

      setSummariesLoading(true);

      const entries = await Promise.all(
        graphCategories.map(async (category) => {
          const existing = summariesByCategory[category.id];
          if (existing) {
            return [category.id, existing] as const;
          }

          const samples = (productBuckets[category.id] || [])
            .slice(0, 4)
            .map((product) => product.title)
            .join(', ');

          try {
            const response = await agentApiClient.post('/ecommerce-product-detail-enrichment/invoke', {
              sku: category.id,
              message:
                `Create a concise retail category summary (max 20 words) for ${category.name}. ` +
                `Use these sample products as context: ${samples || 'general assortment'}.`,
            });
            const view = formatAgentResponse(response.data);
            return [category.id, view.text] as const;
          } catch {
            return [
              category.id,
              category.description || `AI summary unavailable right now for ${category.name}.`,
            ] as const;
          }
        }),
      );

      if (!cancelled) {
        setSummariesByCategory((current) => {
          const next = { ...current };
          entries.forEach(([id, summary]) => {
            next[id] = summary;
          });
          return next;
        });
        setSummariesLoading(false);
      }
    };

    void loadSummaries();

    return () => {
      cancelled = true;
    };
  }, [graphCategories, productBuckets, summariesByCategory]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) {
      return;
    }

    const observer = new ResizeObserver((entries) => {
      const nextWidth = entries[0]?.contentRect.width ?? 0;
      setContainerWidth(nextWidth);
    });

    observer.observe(canvas);
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || containerWidth === 0) {
      return;
    }

    const context = canvas.getContext('2d');
    if (!context) {
      return;
    }

    const dpr = window.devicePixelRatio || 1;
    canvas.width = Math.floor(containerWidth * dpr);
    canvas.height = Math.floor(height * dpr);
    canvas.style.height = `${height}px`;
    context.setTransform(dpr, 0, 0, dpr, 0, 0);

    context.clearRect(0, 0, containerWidth, height);

    const projectedNodes = nodes.map((node) => ({
      ...node,
      left: node.x - viewport.x,
      top: node.y - viewport.y,
    }));

    context.lineWidth = 1.4;
    context.strokeStyle = '#d7deef';
    for (let index = 0; index < projectedNodes.length; index += 1) {
      const source = projectedNodes[index];
      const target = projectedNodes[(index + 1) % projectedNodes.length];
      if (!target) {
        continue;
      }
      context.beginPath();
      context.moveTo(source.left + source.width / 2, source.top + source.height / 2);
      context.lineTo(target.left + target.width / 2, target.top + target.height / 2);
      context.stroke();
    }

    const drawRoundedRect = (
      left: number,
      top: number,
      width: number,
      cardHeight: number,
      radius: number,
    ) => {
      context.beginPath();
      context.moveTo(left + radius, top);
      context.arcTo(left + width, top, left + width, top + cardHeight, radius);
      context.arcTo(left + width, top + cardHeight, left, top + cardHeight, radius);
      context.arcTo(left, top + cardHeight, left, top, radius);
      context.arcTo(left, top, left + width, top, radius);
      context.closePath();
    };

    projectedNodes.forEach((node, index) => {
      if (
        node.left < -node.width ||
        node.left > containerWidth + node.width ||
        node.top < -node.height ||
        node.top > height + node.height
      ) {
        return;
      }

      const gradient = context.createLinearGradient(node.left, node.top, node.left + node.width, node.top + node.height);
      gradient.addColorStop(0, index % 2 === 0 ? '#f7fbff' : '#fff8ed');
      gradient.addColorStop(1, '#ffffff');

      drawRoundedRect(node.left, node.top, node.width, node.height, 16);
      context.fillStyle = gradient;
      context.fill();
      context.strokeStyle = '#c8d1e6';
      context.stroke();

      context.fillStyle = '#b33a24';
      context.font = '700 11px ui-sans-serif, system-ui, sans-serif';
      context.textAlign = 'left';
      context.fillText(`${node.productCount} products`, node.left + 12, node.top + 18);

      context.fillStyle = '#27334f';
      context.font = '700 14px ui-sans-serif, system-ui, sans-serif';
      context.fillText(node.categoryName.slice(0, 26), node.left + 12, node.top + 42);

      context.fillStyle = '#4f5d7b';
      context.font = '500 12px ui-sans-serif, system-ui, sans-serif';
      const summary = node.summary.slice(0, 72);
      context.fillText(summary, node.left + 12, node.top + 64);

      context.fillStyle = '#0b6e66';
      context.font = '600 11px ui-sans-serif, system-ui, sans-serif';
      context.fillText('Open category →', node.left + 12, node.top + node.height - 12);
    });
  }, [containerWidth, height, nodes, viewport]);

  const maxOffsetX = Math.max(0, WORLD_WIDTH - containerWidth);
  const maxOffsetY = Math.max(0, WORLD_HEIGHT - height);

  const getNodeAtPoint = (x: number, y: number): GraphNode | undefined => {
    return nodes.find((node) => {
      const left = node.x - viewport.x;
      const top = node.y - viewport.y;
      return x >= left && x <= left + node.width && y >= top && y <= top + node.height;
    });
  };

  const onPointerDown = (event: React.PointerEvent<HTMLCanvasElement>) => {
    pointerStartRef.current = { x: event.clientX, y: event.clientY };
    viewportStartRef.current = viewport;
    draggedRef.current = false;
    event.currentTarget.setPointerCapture(event.pointerId);
  };

  const onPointerMove = (event: React.PointerEvent<HTMLCanvasElement>) => {
    if (!pointerStartRef.current) {
      return;
    }

    const deltaX = event.clientX - pointerStartRef.current.x;
    const deltaY = event.clientY - pointerStartRef.current.y;

    if (Math.abs(deltaX) >= CLICK_DRAG_THRESHOLD || Math.abs(deltaY) >= CLICK_DRAG_THRESHOLD) {
      draggedRef.current = true;
    }

    setViewport({
      x: clamp(viewportStartRef.current.x - deltaX, 0, maxOffsetX),
      y: clamp(viewportStartRef.current.y - deltaY, 0, maxOffsetY),
    });
  };

  const onPointerUp = (event: React.PointerEvent<HTMLCanvasElement>) => {
    if (!pointerStartRef.current) {
      return;
    }

    event.currentTarget.releasePointerCapture(event.pointerId);
    const deltaX = event.clientX - pointerStartRef.current.x;
    const deltaY = event.clientY - pointerStartRef.current.y;
    const movement = Math.sqrt(deltaX * deltaX + deltaY * deltaY);

    if (draggedRef.current || movement >= CLICK_DRAG_THRESHOLD) {
      trackEcommerceEvent('shelf_scrolled', {
        shelf_title: 'home_category_graph',
        interaction: 'drag',
        item_count: nodes.length,
        delta: Math.round(movement),
      });
      pointerStartRef.current = null;
      return;
    }

    const rect = event.currentTarget.getBoundingClientRect();
    const node = getNodeAtPoint(event.clientX - rect.left, event.clientY - rect.top);
    if (node) {
      trackEcommerceEvent('shelf_item_opened', {
        shelf_title: 'home_category_graph',
        item_id: node.id,
        item_href: node.href,
        item_position: nodes.findIndex((candidate) => candidate.id === node.id),
      });

      trackEcommerceEvent('category_opened', {
        slug: node.id,
        source: 'canvas_shelf',
      });

      trackEcommerceEvent('product_opened', {
        sku: node.id,
        source: 'canvas_shelf',
      });
      router.push(node.href);
    }

    pointerStartRef.current = null;
  };

  return (
    <section className="showcase-shell relative p-5 sm:p-6" aria-label={ariaLabel}>
      <h2 className="mb-2 text-2xl font-black text-[var(--hp-text)] sm:text-3xl">{title}</h2>
      <p className="mb-4 text-sm text-[var(--hp-text-muted)]">
        Drag to navigate the category map. Each node is an AI-generated category card from the enrichment agent.
      </p>

      {summariesLoading ? (
        <p className="mb-3 text-xs font-medium text-[var(--hp-text-muted)]">Refreshing agent summaries...</p>
      ) : null}

      <canvas
        ref={canvasRef}
        role="img"
        aria-label={ariaLabel}
        tabIndex={0}
        className="min-h-[65dvh] w-full cursor-grab rounded-2xl border border-[var(--hp-border)] bg-[var(--hp-surface)] active:cursor-grabbing"
        onPointerDown={onPointerDown}
        onPointerMove={onPointerMove}
        onPointerUp={onPointerUp}
      >
        Draggable category graph. Drag to pan, click a category card to open that category.
      </canvas>

      <ul className="sr-only" aria-label="Graph categories fallback list">
        {nodes.map((node) => (
          <li key={node.id}>
            <a href={node.href}>{node.categoryName}</a>
          </li>
        ))}
      </ul>
    </section>
  );
};

export default ProductGraphCanvas;