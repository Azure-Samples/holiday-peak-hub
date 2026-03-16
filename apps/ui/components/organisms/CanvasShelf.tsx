'use client';

import React, { useEffect, useMemo, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import { trackEcommerceEvent } from '@/lib/utils/telemetry';

type CanvasShelfItem = {
  id: string;
  title: string;
  subtitle?: string;
  meta?: string;
  href: string;
};

export interface CanvasShelfProps {
  title: string;
  items: CanvasShelfItem[];
  ariaLabel: string;
  height?: number;
}

type CardBox = {
  x: number;
  y: number;
  width: number;
  height: number;
  item: CanvasShelfItem;
};

const CARD_WIDTH = 240;
const CARD_HEIGHT = 154;
const CARD_GAP = 16;
const PAD_X = 12;
const PAD_Y = 12;
const DRAG_CLICK_THRESHOLD_PX = 8;
const KEYBOARD_STEP = CARD_WIDTH * 0.65;

const clamp = (value: number, min: number, max: number): number =>
  Math.min(max, Math.max(min, value));

const truncate = (value: string, maxLen: number): string =>
  value.length > maxLen ? `${value.slice(0, maxLen - 1)}…` : value;

export const CanvasShelf: React.FC<CanvasShelfProps> = ({
  title,
  items,
  ariaLabel,
  height = 188,
}) => {
  const router = useRouter();
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const frameRef = useRef<number | null>(null);
  const draggingRef = useRef(false);
  const draggedRef = useRef(false);
  const dragStartXRef = useRef(0);
  const scrollStartRef = useRef(0);
  const scrollRef = useRef(0);
  const targetScrollRef = useRef(0);
  const hitboxesRef = useRef<CardBox[]>([]);
  const reducedMotionRef = useRef(false);
  const [containerWidth, setContainerWidth] = useState(0);
  const [activeIndex, setActiveIndex] = useState(0);

  const trackShelfScroll = (
    interaction: 'wheel' | 'button' | 'keyboard' | 'drag',
    delta: number,
  ) => {
    if (delta === 0) {
      return;
    }

    trackEcommerceEvent('shelf_scrolled', {
      shelf_title: title,
      interaction,
      item_count: items.length,
      delta,
    });
  };

  const trackOpen = (item: CanvasShelfItem, index: number) => {
    trackEcommerceEvent('shelf_item_opened', {
      shelf_title: title,
      item_id: item.id,
      item_href: item.href,
      item_position: index,
    });

    try {
      const parsedUrl = new URL(item.href, 'https://holiday-peak-hub.local');
      const categorySlug = parsedUrl.searchParams.get('slug');
      const productSku = parsedUrl.searchParams.get('id');

      if (parsedUrl.pathname === '/category' && categorySlug) {
        trackEcommerceEvent('category_opened', {
          slug: categorySlug,
          source: 'canvas_shelf',
        });
      }

      if (parsedUrl.pathname === '/product' && productSku) {
        trackEcommerceEvent('product_opened', {
          sku: productSku,
          source: 'canvas_shelf',
        });
      }
    } catch {
      return;
    }
  };

  const maxScroll = useMemo(() => {
    const contentWidth = items.length * (CARD_WIDTH + CARD_GAP) - CARD_GAP + PAD_X * 2;
    return Math.max(0, contentWidth - containerWidth);
  }, [items.length, containerWidth]);

  useEffect(() => {
    targetScrollRef.current = clamp(targetScrollRef.current, 0, maxScroll);
    scrollRef.current = clamp(scrollRef.current, 0, maxScroll);
  }, [maxScroll]);

  useEffect(() => {
    if (typeof window === 'undefined') {
      return;
    }

    const mediaQuery = window.matchMedia('(prefers-reduced-motion: reduce)');
    const applyMotionPreference = () => {
      reducedMotionRef.current = mediaQuery.matches;
    };

    applyMotionPreference();
    mediaQuery.addEventListener('change', applyMotionPreference);
    return () => mediaQuery.removeEventListener('change', applyMotionPreference);
  }, []);

  useEffect(() => {
    if (items.length === 0) {
      setActiveIndex(0);
      return;
    }

    setActiveIndex((current) => clamp(current, 0, items.length - 1));
  }, [items.length]);

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

    const ctx = canvas.getContext('2d');
    if (!ctx) {
      return;
    }

    const dpr = window.devicePixelRatio || 1;
    const drawWidth = Math.floor(containerWidth);
    const drawHeight = height;
    canvas.width = Math.floor(drawWidth * dpr);
    canvas.height = Math.floor(drawHeight * dpr);
    canvas.style.height = `${drawHeight}px`;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

    const render = () => {
      const current = scrollRef.current;
      const target = targetScrollRef.current;
      const next =
        reducedMotionRef.current || Math.abs(target - current) < 0.4
          ? target
          : current + (target - current) * 0.16;
      scrollRef.current = next;

      ctx.clearRect(0, 0, drawWidth, drawHeight);
      ctx.fillStyle = 'rgba(255, 255, 255, 0.01)';
      ctx.fillRect(0, 0, drawWidth, drawHeight);

      const hitboxes: CardBox[] = [];
      const y = PAD_Y;

      items.forEach((item, index) => {
        const x = Math.round(PAD_X + index * (CARD_WIDTH + CARD_GAP) - next);
        const cardRight = x + CARD_WIDTH;

        if (cardRight < 0 || x > drawWidth) {
          return;
        }

        const radius = 16;
        ctx.beginPath();
        ctx.moveTo(x + radius, y);
        ctx.arcTo(x + CARD_WIDTH, y, x + CARD_WIDTH, y + CARD_HEIGHT, radius);
        ctx.arcTo(x + CARD_WIDTH, y + CARD_HEIGHT, x, y + CARD_HEIGHT, radius);
        ctx.arcTo(x, y + CARD_HEIGHT, x, y, radius);
        ctx.arcTo(x, y, x + CARD_WIDTH, y, radius);
        ctx.closePath();

        const gradient = ctx.createLinearGradient(x, y, x + CARD_WIDTH, y + CARD_HEIGHT);
        gradient.addColorStop(0, '#fff8ec');
        gradient.addColorStop(1, '#f6f8ff');
        ctx.fillStyle = gradient;
        ctx.fill();

        ctx.lineWidth = 1;
        ctx.strokeStyle = '#eadfcc';
        ctx.stroke();

        ctx.fillStyle = '#b33a24';
        ctx.font = '600 12px ui-sans-serif, system-ui, sans-serif';
        ctx.fillText(truncate(item.meta || 'Agentic Catalog', 30), x + 14, y + 24);

        ctx.fillStyle = '#1d1a16';
        ctx.font = '700 16px ui-sans-serif, system-ui, sans-serif';
        ctx.fillText(truncate(item.title, 42), x + 14, y + 52);

        if (item.subtitle) {
          ctx.fillStyle = '#5e5649';
          ctx.font = '400 13px ui-sans-serif, system-ui, sans-serif';
          ctx.fillText(truncate(item.subtitle, 60), x + 14, y + 76);
        }

        ctx.fillStyle = '#0b6e66';
        ctx.font = '600 12px ui-sans-serif, system-ui, sans-serif';
        ctx.fillText('Open →', x + 14, y + CARD_HEIGHT - 16);

        hitboxes.push({
          x,
          y,
          width: CARD_WIDTH,
          height: CARD_HEIGHT,
          item,
        });
      });

      hitboxesRef.current = hitboxes;
      frameRef.current = window.requestAnimationFrame(render);
    };

    frameRef.current = window.requestAnimationFrame(render);
    return () => {
      if (frameRef.current) {
        window.cancelAnimationFrame(frameRef.current);
      }
    };
  }, [containerWidth, height, items]);

  const updateTargetScroll = (
    delta: number,
    interaction: 'wheel' | 'button' | 'keyboard' | 'drag',
  ) => {
    targetScrollRef.current = clamp(targetScrollRef.current + delta, 0, maxScroll);
    trackShelfScroll(interaction, delta);
  };

  const focusIndex = (index: number) => {
    if (items.length === 0) {
      return;
    }

    const nextIndex = clamp(index, 0, items.length - 1);
    setActiveIndex(nextIndex);

    const cardLeft = PAD_X + nextIndex * (CARD_WIDTH + CARD_GAP);
    const cardRight = cardLeft + CARD_WIDTH;
    const viewportLeft = targetScrollRef.current;
    const viewportRight = viewportLeft + containerWidth;

    if (cardLeft < viewportLeft) {
      targetScrollRef.current = clamp(cardLeft - PAD_X, 0, maxScroll);
      return;
    }

    if (cardRight > viewportRight) {
      targetScrollRef.current = clamp(cardRight - containerWidth + PAD_X, 0, maxScroll);
    }
  };

  const openItemByIndex = (index: number) => {
    const item = items[index];
    if (item?.href) {
      trackOpen(item, index);
      router.push(item.href);
    }
  };

  const scrollByWheel = (event: React.WheelEvent<HTMLCanvasElement>) => {
    event.preventDefault();
    const dominantDelta = Math.abs(event.deltaX) > Math.abs(event.deltaY) ? event.deltaX : event.deltaY;
    const modeMultiplier = event.deltaMode === 1 ? 16 : 1;
    updateTargetScroll(dominantDelta * modeMultiplier, 'wheel');
  };

  const onPointerDown = (event: React.PointerEvent<HTMLCanvasElement>) => {
    draggingRef.current = true;
    draggedRef.current = false;
    dragStartXRef.current = event.clientX;
    scrollStartRef.current = targetScrollRef.current;
    event.currentTarget.setPointerCapture(event.pointerId);
  };

  const onPointerMove = (event: React.PointerEvent<HTMLCanvasElement>) => {
    if (!draggingRef.current) {
      return;
    }

    const delta = event.clientX - dragStartXRef.current;
    if (Math.abs(delta) >= DRAG_CLICK_THRESHOLD_PX) {
      draggedRef.current = true;
    }
    targetScrollRef.current = clamp(scrollStartRef.current - delta, 0, maxScroll);
  };

  const onPointerUp = (event: React.PointerEvent<HTMLCanvasElement>) => {
    if (!draggingRef.current) {
      return;
    }

    event.currentTarget.releasePointerCapture(event.pointerId);
    const delta = Math.abs(event.clientX - dragStartXRef.current);
    draggingRef.current = false;
    if (delta >= DRAG_CLICK_THRESHOLD_PX) {
      draggedRef.current = true;
    }

    if (draggedRef.current) {
      trackShelfScroll('drag', scrollStartRef.current - targetScrollRef.current);
      return;
    }

    const rect = event.currentTarget.getBoundingClientRect();
    const clickX = event.clientX - rect.left;
    const clickY = event.clientY - rect.top;

    const clicked = hitboxesRef.current.find(
      (box) =>
        clickX >= box.x &&
        clickX <= box.x + box.width &&
        clickY >= box.y &&
        clickY <= box.y + box.height,
    );

    if (clicked?.item.href) {
      const clickedIndex = items.findIndex((item) => item.id === clicked.item.id);
      if (clickedIndex >= 0) {
        setActiveIndex(clickedIndex);
        openItemByIndex(clickedIndex);
        return;
      }
      router.push(clicked.item.href);
    }
  };

  const onPointerCancel = (event: React.PointerEvent<HTMLCanvasElement>) => {
    if (!draggingRef.current) {
      return;
    }

    draggingRef.current = false;
    draggedRef.current = false;
    event.currentTarget.releasePointerCapture(event.pointerId);
  };

  const onKeyDown = (event: React.KeyboardEvent<HTMLCanvasElement>) => {
    if (event.key === 'ArrowRight') {
      event.preventDefault();
      focusIndex(activeIndex + 1);
      updateTargetScroll(KEYBOARD_STEP, 'keyboard');
      return;
    }

    if (event.key === 'ArrowLeft') {
      event.preventDefault();
      focusIndex(activeIndex - 1);
      updateTargetScroll(-KEYBOARD_STEP, 'keyboard');
      return;
    }

    if (event.key === 'Home') {
      event.preventDefault();
      focusIndex(0);
      trackShelfScroll('keyboard', -targetScrollRef.current);
      targetScrollRef.current = 0;
      return;
    }

    if (event.key === 'End') {
      event.preventDefault();
      focusIndex(items.length - 1);
      trackShelfScroll('keyboard', maxScroll - targetScrollRef.current);
      targetScrollRef.current = maxScroll;
      return;
    }

    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault();
      openItemByIndex(activeIndex);
    }
  };

  return (
    <section className="space-y-3" aria-label={ariaLabel}>
      <div className="flex items-center justify-between">
        <h3 className="text-xl font-black text-[var(--hp-text)]">{title}</h3>
        <div className="hidden gap-2 sm:flex">
          <button
            type="button"
            onClick={() => updateTargetScroll(-CARD_WIDTH * 0.85, 'button')}
            className="rounded-full border border-[var(--hp-border)] bg-[var(--hp-surface)] px-3 py-1 text-xs font-semibold text-[var(--hp-text-muted)]"
            aria-label={`Scroll ${title} left`}
          >
            ←
          </button>
          <button
            type="button"
            onClick={() => updateTargetScroll(CARD_WIDTH * 0.85, 'button')}
            className="rounded-full border border-[var(--hp-border)] bg-[var(--hp-surface)] px-3 py-1 text-xs font-semibold text-[var(--hp-text-muted)]"
            aria-label={`Scroll ${title} right`}
          >
            →
          </button>
        </div>
      </div>

      <canvas
        ref={canvasRef}
        role="region"
        aria-label={ariaLabel}
        aria-describedby={`${ariaLabel.replace(/\s+/g, '-').toLowerCase()}-instructions`}
        tabIndex={0}
        aria-keyshortcuts="ArrowLeft ArrowRight Home End Enter Space"
        className="w-full cursor-grab rounded-2xl border border-[var(--hp-border)] bg-[var(--hp-surface)] outline-none focus-visible:ring-2 focus-visible:ring-[var(--hp-primary)] focus-visible:ring-offset-2 focus-visible:ring-offset-[var(--hp-bg)] active:cursor-grabbing touch-pan-y"
        onWheel={scrollByWheel}
        onKeyDown={onKeyDown}
        onPointerDown={onPointerDown}
        onPointerMove={onPointerMove}
        onPointerUp={onPointerUp}
        onPointerCancel={onPointerCancel}
      >
        Interactive catalog shelf. Use arrow keys or mouse wheel to scroll cards.
      </canvas>

      <p id={`${ariaLabel.replace(/\s+/g, '-').toLowerCase()}-instructions`} className="sr-only">
        Use left and right arrow keys to move between cards. Press Enter or Space to open the active card. Drag horizontally with mouse or touch to scroll.
      </p>

      <ul className="sr-only" aria-label={`${title} fallback list`}>
        {items.map((item) => (
          <li key={item.id}>
            <a href={item.href}>{item.title}</a>
          </li>
        ))}
      </ul>
    </section>
  );
};

export default CanvasShelf;
