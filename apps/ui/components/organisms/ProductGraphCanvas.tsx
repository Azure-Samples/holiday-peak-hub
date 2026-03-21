'use client';

import React, { useEffect, useMemo, useRef, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { FiArrowRight, FiMessageSquare, FiSearch } from 'react-icons/fi';
import { Button } from '@/components/atoms/Button';
import type { Product } from '@/components/types';
import agentApiClient from '@/lib/api/agentClient';
import { formatAgentResponse } from '@/lib/utils/agentResponseCards';
import { trackEcommerceEvent } from '@/lib/utils/telemetry';

type Viewport = {
  x: number;
  y: number;
};

type ProductNode = {
  id: string;
  x: number;
  y: number;
  width: number;
  height: number;
  product: Product;
  summary: string;
  href: string;
};

export interface ProductGraphCanvasProps {
  products: Product[];
  title?: string;
  ariaLabel?: string;
  height?: number;
}

const CARD_WIDTH = 312;
const CARD_HEIGHT = 256;
const GAP_X = 44;
const GAP_Y = 40;
const PAD_X = 72;
const PAD_Y = 72;
const MAX_PRODUCTS = 120;
const WORLD_SCALE_FACTOR = 3;
const CLICK_DRAG_THRESHOLD = 8;
const INERTIA_FRICTION = 0.9;
const MIN_VELOCITY = 0.15;
const HOVER_SCALE_MAX = 0.045;
const CATEGORY_EDGE_PALETTE = [
  '#5a8cff',
  '#42b883',
  '#f59e0b',
  '#ef4444',
  '#8b5cf6',
  '#14b8a6',
  '#ec4899',
  '#0ea5e9',
  '#84cc16',
  '#f97316',
];

const clamp = (value: number, min: number, max: number): number =>
  Math.min(max, Math.max(min, value));

const toDisplayPrice = (product: Product): string => {
  return `${product.currency} ${product.price.toFixed(2)}`;
};

const toImageSource = (product: Product): string => {
  return product.thumbnail || product.images[0] || '';
};

const resolveGridColumns = (count: number): number => {
  const basis = Math.max(1, count);
  return Math.max(10, Math.min(16, Math.ceil(Math.sqrt(basis * 1.6))));
};

const normalizeCategoryKey = (category: string | undefined): string => {
  if (!category) {
    return 'uncategorized';
  }
  return category.trim().toLowerCase() || 'uncategorized';
};

const categoryHash = (value: string): number => {
  let hash = 0;
  for (let index = 0; index < value.length; index += 1) {
    hash = (hash * 31 + value.charCodeAt(index)) >>> 0;
  }
  return hash;
};

const categoryEdgeColor = (category: string): string => {
  const index = categoryHash(category) % CATEGORY_EDGE_PALETTE.length;
  return CATEGORY_EDGE_PALETTE[index];
};

const wrapCanvasLines = (
  context: CanvasRenderingContext2D,
  text: string,
  maxWidth: number,
  maxLines: number,
): string[] => {
  const words = text.split(/\s+/).filter(Boolean);
  if (words.length === 0) {
    return [];
  }

  const measureWidth = (value: string): number => {
    if (typeof context.measureText === 'function') {
      return context.measureText(value).width;
    }
    return value.length * 7;
  };

  const lines: string[] = [];
  let current = words[0];

  for (let index = 1; index < words.length; index += 1) {
    const next = `${current} ${words[index]}`;
    if (measureWidth(next) <= maxWidth) {
      current = next;
      continue;
    }

    lines.push(current);
    current = words[index];

    if (lines.length === maxLines - 1) {
      break;
    }
  }

  if (lines.length < maxLines && current) {
    lines.push(current);
  }

  if (lines.length > maxLines) {
    lines.length = maxLines;
  }

  if (lines.length === maxLines && words.join(' ') !== lines.join(' ')) {
    const lastIndex = maxLines - 1;
    let lastLine = lines[lastIndex] ?? '';
    while (lastLine.length > 0 && measureWidth(`${lastLine}…`) > maxWidth) {
      lastLine = lastLine.slice(0, -1);
    }
    lines[lastIndex] = `${lastLine}…`;
  }

  return lines;
};

const toNodes = (
  products: Product[],
  summaries: Record<string, string>,
  columns: number,
  worldWidth: number,
  worldHeight: number,
): ProductNode[] => {
  const limited = products.slice(0, MAX_PRODUCTS);
  const rows = Math.max(1, Math.ceil(limited.length / columns));
  const contentWidth = columns * CARD_WIDTH + Math.max(columns - 1, 0) * GAP_X;
  const contentHeight = rows * CARD_HEIGHT + Math.max(rows - 1, 0) * GAP_Y;
  const originX = Math.floor((worldWidth - contentWidth) / 2);
  const originY = Math.floor((worldHeight - contentHeight) / 2);

  return limited.map((product, index) => {
    const col = index % columns;
    const row = Math.floor(index / columns);

    return {
      id: product.sku,
      x: originX + col * (CARD_WIDTH + GAP_X),
      y: originY + row * (CARD_HEIGHT + GAP_Y),
      width: CARD_WIDTH,
      height: CARD_HEIGHT,
      product,
      summary:
        summaries[product.sku] ||
        product.description ||
        `${product.category} product enriched by the agent.`,
      href: `/product?id=${encodeURIComponent(product.sku)}`,
    };
  });
};

export const ProductGraphCanvas: React.FC<ProductGraphCanvasProps> = ({
  products,
  title = 'Product Graph Surface',
  ariaLabel = 'Draggable product graph',
  height,
}) => {
  const router = useRouter();
  const rootRef = useRef<HTMLElement | null>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const pointerStartRef = useRef<{ x: number; y: number } | null>(null);
  const viewportStartRef = useRef<Viewport>({ x: 0, y: 0 });
  const lastPointerRef = useRef<{ x: number; y: number; ts: number } | null>(null);
  const draggedRef = useRef(false);
  const velocityRef = useRef<{ vx: number; vy: number }>({ vx: 0, vy: 0 });
  const inertiaFrameRef = useRef<number | null>(null);
  const hoverFrameRef = useRef<number | null>(null);
  const didCenterViewportRef = useRef(false);
  const imageCacheRef = useRef<Map<string, HTMLImageElement | false>>(new Map());

  const [containerWidth, setContainerWidth] = useState(0);
  const [containerHeight, setContainerHeight] = useState(height || 680);
  const [summariesBySku, setSummariesBySku] = useState<Record<string, string>>({});
  const [summariesLoading, setSummariesLoading] = useState(false);
  const [imageVersion, setImageVersion] = useState(0);
  const [hoveredNodeId, setHoveredNodeId] = useState<string | null>(null);
  const [hoverTick, setHoverTick] = useState(0);
  const [themeVersion, setThemeVersion] = useState(0);

  const gridColumns = useMemo(() => resolveGridColumns(products.length), [products.length]);

  const minWorldWidth = useMemo(() => {
    return PAD_X * 2 + gridColumns * CARD_WIDTH + Math.max(gridColumns - 1, 0) * GAP_X;
  }, [gridColumns]);

  const minWorldHeight = useMemo(() => {
    const rowCount = Math.max(1, Math.ceil(Math.min(products.length, MAX_PRODUCTS) / gridColumns));
    return PAD_Y * 2 + rowCount * CARD_HEIGHT + Math.max(rowCount - 1, 0) * GAP_Y;
  }, [gridColumns, products.length]);

  const worldWidth = useMemo(() => {
    return Math.max(minWorldWidth, Math.floor(containerWidth * WORLD_SCALE_FACTOR));
  }, [containerWidth, minWorldWidth]);

  const worldHeight = useMemo(() => {
    return Math.max(minWorldHeight, Math.floor(containerHeight * WORLD_SCALE_FACTOR));
  }, [containerHeight, minWorldHeight]);

  const nodes = useMemo(
    () => toNodes(products, summariesBySku, gridColumns, worldWidth, worldHeight),
    [gridColumns, products, summariesBySku, worldHeight, worldWidth],
  );

  const [viewport, setViewport] = useState<Viewport>({
    x: 0,
    y: 0,
  });

  const stopInertia = () => {
    if (inertiaFrameRef.current) {
      window.cancelAnimationFrame(inertiaFrameRef.current);
      inertiaFrameRef.current = null;
    }
  };

  useEffect(() => {
    const nextWidth = Math.max(0, worldWidth - containerWidth);
    const nextHeight = Math.max(0, worldHeight - containerHeight);

    setViewport((current) => ({
      x:
        !didCenterViewportRef.current && nextWidth > 0
          ? Math.floor(nextWidth / 2)
          : clamp(current.x, 0, nextWidth),
      y:
        !didCenterViewportRef.current && nextHeight > 0
          ? Math.floor(nextHeight / 2)
          : clamp(current.y, 0, nextHeight),
    }));

    if (!didCenterViewportRef.current && (nextWidth > 0 || nextHeight > 0)) {
      didCenterViewportRef.current = true;
    }
  }, [containerHeight, containerWidth, worldHeight, worldWidth]);

  useEffect(() => {
    return () => {
      stopInertia();
      if (hoverFrameRef.current) {
        window.cancelAnimationFrame(hoverFrameRef.current);
        hoverFrameRef.current = null;
      }
    };
  }, []);

  useEffect(() => {
    if (!hoveredNodeId) {
      if (hoverFrameRef.current) {
        window.cancelAnimationFrame(hoverFrameRef.current);
        hoverFrameRef.current = null;
      }
      setHoverTick(0);
      return;
    }

    let cancelled = false;
    const animateHover = () => {
      if (cancelled) {
        return;
      }
      setHoverTick(performance.now());
      hoverFrameRef.current = window.requestAnimationFrame(animateHover);
    };

    hoverFrameRef.current = window.requestAnimationFrame(animateHover);
    return () => {
      cancelled = true;
      if (hoverFrameRef.current) {
        window.cancelAnimationFrame(hoverFrameRef.current);
        hoverFrameRef.current = null;
      }
    };
  }, [hoveredNodeId]);

  useEffect(() => {
    const root = rootRef.current;
    if (!root) {
      return;
    }

    const observer = new ResizeObserver((entries) => {
      const nextWidth = entries[0]?.contentRect.width ?? 0;
      const nextHeight = entries[0]?.contentRect.height ?? 0;
      setContainerWidth(nextWidth);
      setContainerHeight(height ?? nextHeight);
    });

    observer.observe(root);
    return () => observer.disconnect();
  }, [height]);

  useEffect(() => {
    if (typeof window === 'undefined') {
      return;
    }

    const rootElement = document.documentElement;
    if (!rootElement || typeof MutationObserver === 'undefined') {
      return;
    }

    const observer = new MutationObserver(() => {
      setThemeVersion((current) => current + 1);
    });

    observer.observe(rootElement, {
      attributes: true,
      attributeFilter: ['class', 'style'],
    });

    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    let cancelled = false;

    const loadSummaries = async () => {
      if (products.length === 0) {
        return;
      }

      setSummariesLoading(true);

      const entries = await Promise.all(
        products.slice(0, 40).map(async (product) => {
          try {
            const response = await agentApiClient.post('/ecommerce-product-detail-enrichment/invoke', {
              sku: product.sku,
              message:
                `Summarize this product in up to 16 words for a graph card. ` +
                `Category: ${product.category}. Title: ${product.title}.`,
            });
            const view = formatAgentResponse(response.data);
            return [product.sku, view.text] as const;
          } catch {
            return [product.sku, product.description || product.category + ' product'] as const;
          }
        }),
      );

      if (!cancelled) {
        setSummariesBySku((current) => {
          const next = { ...current };
          entries.forEach(([sku, summary]) => {
            next[sku] = summary;
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
  }, [products]);

  useEffect(() => {
    let cancelled = false;

    nodes.forEach((node) => {
      const imageSource = toImageSource(node.product);
      if (!imageSource || imageCacheRef.current.has(imageSource)) {
        return;
      }

      imageCacheRef.current.set(imageSource, false);
      const image = new window.Image();
      image.decoding = 'async';
      image.onload = () => {
        if (cancelled) {
          return;
        }
        imageCacheRef.current.set(imageSource, image);
        setImageVersion((current) => current + 1);
      };
      image.onerror = () => {
        if (!cancelled) {
          imageCacheRef.current.set(imageSource, false);
        }
      };
      image.src = imageSource;
    });

    return () => {
      cancelled = true;
    };
  }, [nodes]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || containerWidth === 0 || containerHeight === 0) {
      return;
    }

    const context = canvas.getContext('2d');
    if (!context) {
      return;
    }

    const dpr = window.devicePixelRatio || 1;
    canvas.width = Math.floor(containerWidth * dpr);
    canvas.height = Math.floor(containerHeight * dpr);
    canvas.style.height = `${containerHeight}px`;
    context.setTransform(dpr, 0, 0, dpr, 0, 0);

    const rootStyles = getComputedStyle(document.documentElement);
    const token = (name: string, fallback: string) => {
      const value = rootStyles.getPropertyValue(name).trim();
      return value || fallback;
    };

    const isDark = document.documentElement.classList.contains('dark');
    const colorBg = token('--hp-bg', '#f8f6ef');
    const colorSurface = token('--hp-surface', '#fffcf7');
    const colorSurfaceStrong = token('--hp-surface-strong', '#fff5df');
    const colorBorder = token('--hp-border', '#eadfcc');
    const colorPrimary = token('--hp-primary', '#b33a24');
    const colorAccent = token('--hp-accent', '#0b6e66');

    context.clearRect(0, 0, containerWidth, containerHeight);

    const backgroundGradient = context.createLinearGradient(0, 0, containerWidth, containerHeight);
    backgroundGradient.addColorStop(0, colorSurface);
    backgroundGradient.addColorStop(1, colorBg);
    context.fillStyle = backgroundGradient;
    context.fillRect(0, 0, containerWidth, containerHeight);

    const projected = nodes.map((node) => ({
      ...node,
      left: node.x - viewport.x,
      top: node.y - viewport.y,
    }));

    const nodesByCategory = new Map<string, Array<(typeof projected)[number]>>();
    projected.forEach((node) => {
      const categoryKey = normalizeCategoryKey(node.product.category);
      const current = nodesByCategory.get(categoryKey) || [];
      current.push(node);
      nodesByCategory.set(categoryKey, current);
    });

    context.lineWidth = 1.2;
    nodesByCategory.forEach((categoryNodes) => {
      if (categoryNodes.length < 2) {
        return;
      }

      const categoryKey = normalizeCategoryKey(categoryNodes[0]?.product.category);
      context.strokeStyle = categoryEdgeColor(categoryKey);

      const ordered = [...categoryNodes].sort((a, b) => {
        if (a.top === b.top) {
          return a.left - b.left;
        }
        return a.top - b.top;
      });

      for (let index = 0; index < ordered.length - 1; index += 1) {
        const source = ordered[index];
        const target = ordered[index + 1];
        context.beginPath();
        context.moveTo(source.left + source.width / 2, source.top + source.height / 2);
        context.lineTo(target.left + target.width / 2, target.top + target.height / 2);
        context.stroke();
      }
    });

    const drawCard = (left: number, top: number, widthValue: number, heightValue: number) => {
      const radius = 14;
      context.beginPath();
      context.moveTo(left + radius, top);
      context.arcTo(left + widthValue, top, left + widthValue, top + heightValue, radius);
      context.arcTo(left + widthValue, top + heightValue, left, top + heightValue, radius);
      context.arcTo(left, top + heightValue, left, top, radius);
      context.arcTo(left, top, left + widthValue, top, radius);
      context.closePath();
    };

    const orderedNodes =
      hoveredNodeId && projected.some((node) => node.id === hoveredNodeId)
        ? [
            ...projected.filter((node) => node.id !== hoveredNodeId),
            ...projected.filter((node) => node.id === hoveredNodeId),
          ]
        : projected;

    orderedNodes.forEach((node, index) => {
      const isHovered = node.id === hoveredNodeId;
      const hoverScale = isHovered
        ? 1 + HOVER_SCALE_MAX * (0.62 + 0.38 * Math.sin(hoverTick / 160))
        : 1;
      const drawWidth = node.width * hoverScale;
      const drawHeight = node.height * hoverScale;
      const drawLeft = node.left - (drawWidth - node.width) / 2;
      const drawTop = node.top - (drawHeight - node.height) / 2 - (isHovered ? 4 : 0);

      if (
        drawLeft < -drawWidth ||
        drawLeft > containerWidth + drawWidth ||
        drawTop < -drawHeight ||
        drawTop > containerHeight + drawHeight
      ) {
        return;
      }

      const gradient = context.createLinearGradient(drawLeft, drawTop, drawLeft + drawWidth, drawTop + drawHeight);
      gradient.addColorStop(0, index % 2 === 0 ? colorSurfaceStrong : colorSurface);
      gradient.addColorStop(1, colorSurface);

      context.save();
      if (isHovered) {
        context.shadowColor = isDark ? 'rgba(8, 13, 22, 0.55)' : 'rgba(46, 64, 101, 0.28)';
        context.shadowBlur = 18;
        context.shadowOffsetY = 8;
      }

      drawCard(drawLeft, drawTop, drawWidth, drawHeight);
      context.fillStyle = gradient;
      context.fill();
      context.strokeStyle = colorBorder;
      context.stroke();
      context.restore();

      const imageSource = toImageSource(node.product);
      const cachedImage = imageSource ? imageCacheRef.current.get(imageSource) : undefined;
      if (cachedImage instanceof HTMLImageElement) {
        context.save();
        drawCard(drawLeft, drawTop, drawWidth, drawHeight);
        context.clip();
        context.drawImage(cachedImage, drawLeft, drawTop, drawWidth, drawHeight);
        context.restore();
      } else {
        const imageGradient = context.createLinearGradient(
          drawLeft,
          drawTop,
          drawLeft + drawWidth,
          drawTop + drawHeight,
        );
        imageGradient.addColorStop(0, isDark ? '#213047' : '#edf4ff');
        imageGradient.addColorStop(1, isDark ? '#233c3a' : '#e9f7f4');
        context.fillStyle = imageGradient;
        context.fillRect(drawLeft + 1, drawTop + 1, drawWidth - 2, drawHeight - 2);
      }

      const textOverlayHeight = Math.max(118, drawHeight * 0.47);
      const textOverlayTop = drawTop + drawHeight - textOverlayHeight;
      const textGradient = context.createLinearGradient(
        drawLeft,
        textOverlayTop - 24,
        drawLeft,
        drawTop + drawHeight,
      );
      textGradient.addColorStop(0, isDark ? 'rgba(4, 7, 11, 0.16)' : 'rgba(28, 39, 64, 0.08)');
      textGradient.addColorStop(1, isDark ? 'rgba(7, 12, 22, 0.86)' : 'rgba(24, 34, 57, 0.78)');
      context.fillStyle = textGradient;
      context.fillRect(drawLeft + 1, textOverlayTop, drawWidth - 2, textOverlayHeight - 1);

      context.fillStyle = isDark ? 'rgba(10, 18, 31, 0.82)' : 'rgba(39, 51, 79, 0.82)';
      context.fillRect(drawLeft + 12, drawTop + 12, Math.min(drawWidth - 24, 126), 22);

      context.textAlign = 'left';
      context.fillStyle = '#fefefe';
      context.font = '700 11px ui-sans-serif, system-ui, sans-serif';
      context.fillText(node.product.category.slice(0, 18), drawLeft + 18, drawTop + 27);

      const textMaxWidth = drawWidth - 28;

      context.fillStyle = '#f7fbff';
      context.font = '700 21px ui-sans-serif, system-ui, sans-serif';
      const titleLines = wrapCanvasLines(context, node.product.title, textMaxWidth, 2);
      titleLines.forEach((line, lineIndex) => {
        context.fillText(line, drawLeft + 14, textOverlayTop + 26 + lineIndex * 24);
      });

      context.fillStyle = isDark ? '#d7dfef' : '#d8e2f4';
      context.font = '600 12px ui-sans-serif, system-ui, sans-serif';
      const brandY = textOverlayTop + 26 + Math.max(1, titleLines.length) * 24;
      context.fillText(node.product.brand.slice(0, 24), drawLeft + 14, brandY);

      context.fillStyle = isDark ? '#c8d5ed' : '#c7d4ec';
      context.font = '500 12px ui-sans-serif, system-ui, sans-serif';
      const summaryLines = wrapCanvasLines(context, node.summary, textMaxWidth, 2);
      summaryLines.forEach((line, lineIndex) => {
        context.fillText(line, drawLeft + 14, brandY + 20 + lineIndex * 17);
      });

      context.fillStyle = isDark ? '#f3ecff' : '#f8f2ff';
      context.font = '700 14px ui-sans-serif, system-ui, sans-serif';
      context.textAlign = 'left';
      context.fillText(toDisplayPrice(node.product), drawLeft + 14, drawTop + drawHeight - 16);

      context.fillStyle = node.product.inStock ? colorAccent : colorPrimary;
      context.font = '600 12px ui-sans-serif, system-ui, sans-serif';
      context.textAlign = 'right';
      context.fillText(
        node.product.inStock ? 'In stock' : 'Out of stock',
        drawLeft + drawWidth - 14,
        drawTop + drawHeight - 16,
      );
      context.textAlign = 'left';
    });
  }, [
    containerHeight,
    containerWidth,
    gridColumns,
    hoveredNodeId,
    hoverTick,
    imageVersion,
    nodes,
    themeVersion,
    viewport,
  ]);

  const maxOffsetX = Math.max(0, worldWidth - containerWidth);
  const maxOffsetY = Math.max(0, worldHeight - containerHeight);

  const getNodeAtPoint = (x: number, y: number): ProductNode | undefined => {
    return nodes.find((node) => {
      const left = node.x - viewport.x;
      const top = node.y - viewport.y;
      return x >= left && x <= left + node.width && y >= top && y <= top + node.height;
    });
  };

  const onPointerDown = (event: React.PointerEvent<HTMLCanvasElement>) => {
    stopInertia();
    setHoveredNodeId(null);
    pointerStartRef.current = { x: event.clientX, y: event.clientY };
    viewportStartRef.current = viewport;
    lastPointerRef.current = { x: event.clientX, y: event.clientY, ts: performance.now() };
    velocityRef.current = { vx: 0, vy: 0 };
    draggedRef.current = false;
    event.currentTarget.setPointerCapture(event.pointerId);
  };

  const onPointerMove = (event: React.PointerEvent<HTMLCanvasElement>) => {
    if (!pointerStartRef.current) {
      const rect = event.currentTarget.getBoundingClientRect();
      const hovered = getNodeAtPoint(event.clientX - rect.left, event.clientY - rect.top);
      setHoveredNodeId((current) => (current === (hovered?.id || null) ? current : hovered?.id || null));
      return;
    }

    const deltaX = event.clientX - pointerStartRef.current.x;
    const deltaY = event.clientY - pointerStartRef.current.y;

    if (Math.abs(deltaX) >= CLICK_DRAG_THRESHOLD || Math.abs(deltaY) >= CLICK_DRAG_THRESHOLD) {
      draggedRef.current = true;
    }

    const now = performance.now();
    if (lastPointerRef.current) {
      const dt = Math.max(1, now - lastPointerRef.current.ts);
      velocityRef.current = {
        vx: (event.clientX - lastPointerRef.current.x) / dt,
        vy: (event.clientY - lastPointerRef.current.y) / dt,
      };
    }
    lastPointerRef.current = { x: event.clientX, y: event.clientY, ts: now };

    setViewport({
      x: clamp(viewportStartRef.current.x - deltaX, 0, maxOffsetX),
      y: clamp(viewportStartRef.current.y - deltaY, 0, maxOffsetY),
    });
  };

  const onPointerLeave = () => {
    if (!pointerStartRef.current) {
      setHoveredNodeId(null);
    }
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
        shelf_title: 'home_product_graph_grid',
        interaction: 'drag',
        item_count: nodes.length,
        delta: Math.round(movement),
      });

      const animateInertia = () => {
        const { vx, vy } = velocityRef.current;

        if (Math.abs(vx) < MIN_VELOCITY && Math.abs(vy) < MIN_VELOCITY) {
          stopInertia();
          return;
        }

        setViewport((current) => {
          const nextX = clamp(current.x - vx * 18, 0, maxOffsetX);
          const nextY = clamp(current.y - vy * 18, 0, maxOffsetY);
          return { x: nextX, y: nextY };
        });

        velocityRef.current = {
          vx: vx * INERTIA_FRICTION,
          vy: vy * INERTIA_FRICTION,
        };

        inertiaFrameRef.current = window.requestAnimationFrame(animateInertia);
      };

      stopInertia();
      inertiaFrameRef.current = window.requestAnimationFrame(animateInertia);
      pointerStartRef.current = null;
      lastPointerRef.current = null;
      return;
    }

    const rect = event.currentTarget.getBoundingClientRect();
    const node = getNodeAtPoint(event.clientX - rect.left, event.clientY - rect.top);
    if (node) {
      trackEcommerceEvent('shelf_item_opened', {
        shelf_title: 'home_product_graph_grid',
        item_id: node.id,
        item_href: node.href,
        item_position: nodes.findIndex((candidate) => candidate.id === node.id),
      });

      trackEcommerceEvent('product_opened', {
        sku: node.product.sku,
        source: 'canvas_shelf',
      });

      router.push(node.href);
    }

    pointerStartRef.current = null;
    lastPointerRef.current = null;
  };

  const onWheel = (event: React.WheelEvent<HTMLCanvasElement>) => {
    event.preventDefault();
    stopInertia();

    const deltaX = event.deltaX + (event.shiftKey ? event.deltaY : 0);
    const deltaY = event.shiftKey ? 0 : event.deltaY;
    const movement = Math.sqrt(deltaX * deltaX + deltaY * deltaY);

    setViewport((current) => ({
      x: clamp(current.x + deltaX, 0, maxOffsetX),
      y: clamp(current.y + deltaY, 0, maxOffsetY),
    }));

    trackEcommerceEvent('shelf_scrolled', {
      shelf_title: 'home_product_graph_grid',
      interaction: 'wheel',
      item_count: nodes.length,
      delta: Math.round(movement),
    });
  };

  return (
    <section ref={rootRef} className="relative h-full" aria-label={ariaLabel}>
      <canvas
        ref={canvasRef}
        role="img"
        aria-label={ariaLabel}
        tabIndex={0}
        className="h-full w-full touch-none cursor-grab bg-[var(--hp-surface)] active:cursor-grabbing"
        onPointerDown={onPointerDown}
        onPointerMove={onPointerMove}
        onPointerUp={onPointerUp}
        onPointerLeave={onPointerLeave}
        onWheel={onWheel}
      >
        Draggable product graph grid that extends beyond the page. Drag or wheel to pan in all directions and click cards to open products.
      </canvas>

      <div
        className="pointer-events-none absolute left-4 top-4 z-20 rounded-xl border border-[var(--hp-border)] px-3 py-2"
        style={{
          backgroundColor: 'var(--hp-surface)',
          boxShadow: '0 8px 24px rgba(0, 0, 0, 0.18)',
          opacity: 0.97,
        }}
      >
        <p className="text-xs font-semibold uppercase tracking-wide text-[var(--hp-text-muted)]">{title}</p>
        <p className="text-xs text-[var(--hp-text-muted)]">
          Drag or wheel across a 3x oversized product graph inspired by the reference container drag surface.
        </p>
        {summariesLoading ? (
          <p className="mt-1 text-[11px] font-medium text-[var(--hp-primary)]">Refreshing agent summaries...</p>
        ) : null}
      </div>

      <div className="absolute right-4 top-4 z-20 flex flex-col gap-2">
        <Link href="/search" className="inline-flex">
          <Button
            size="sm"
            className="rounded-full border border-[var(--hp-primary)] bg-[var(--hp-primary)] text-white hover:bg-[var(--hp-primary-hover)]"
          >
            <FiSearch className="mr-1 h-4 w-4" /> Search
            <FiArrowRight className="ml-1 h-4 w-4" />
          </Button>
        </Link>
        <Link href="/agents/product-enrichment-chat" className="inline-flex">
          <Button
            size="sm"
            className="rounded-full border border-[var(--hp-accent)] bg-[var(--hp-accent)] text-white hover:brightness-110"
          >
            <FiMessageSquare className="mr-1 h-4 w-4" /> Agent Chat
          </Button>
        </Link>
      </div>

      <ul className="sr-only" aria-label="Graph products fallback list">
        {nodes.map((node) => (
          <li key={node.id}>
            <a href={node.href}>{node.product.title}</a>
          </li>
        ))}
      </ul>
    </section>
  );
};

export default ProductGraphCanvas;
