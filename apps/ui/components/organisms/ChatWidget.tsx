'use client';

import React, { useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import { usePathname, useSearchParams } from 'next/navigation';
import { Button } from '@/components/atoms/Button';
import { FiMessageSquare, FiSend, FiMinimize2, FiRefreshCw } from 'react-icons/fi';
import { Card } from '@/components/molecules/Card';
import { SearchComparisonScorecard } from '@/components/enrichment/SearchComparisonScorecard';
import { semanticSearchService } from '@/lib/services/semanticSearchService';

type ProductPreview = {
  sku: string;
  title: string;
  score?: number;
};

type ChatEntry = {
  id: string;
  role: 'user' | 'agent';
  text: string;
  comparison?: {
    intelligent: ProductPreview[];
    keyword: ProductPreview[];
  };
};

const DEFAULT_PROMPT = 'Find similar products to premium wireless noise-cancelling headphones under 300';

export const ChatWidget: React.FC = () => {
  const pathname = usePathname();
  const searchParams = useSearchParams();

  const shouldAutoOpen = useMemo(() => {
    if (searchParams.get('agentChat') === '1') {
      return true;
    }
    if (typeof window === 'undefined') {
      return false;
    }
    return window.location.hash === '#agent-chat';
  }, [searchParams]);

  const [isOpen, setIsOpen] = useState(shouldAutoOpen);
  const [messages, setMessages] = useState<ChatEntry[]>([
    {
      id: 'intro-agent-message',
      role: 'agent',
      text: 'Ask for similar products and I will compare intelligent agent retrieval with basic keyword search.',
    },
  ]);
  const [inputValue, setInputValue] = useState('');
  const [isSending, setIsSending] = useState(false);

  useEffect(() => {
    if (shouldAutoOpen) {
      setIsOpen(true);
    }
  }, [shouldAutoOpen]);

  if (pathname?.startsWith('/auth')) {
    return null;
  }

  const buildPreview = (items: Array<Record<string, unknown>>): ProductPreview[] => {
    return items.slice(0, 4).map((item, index) => {
      const sku = String(item.sku ?? item.id ?? `item-${index + 1}`);
      const title = String(item.title ?? item.name ?? sku);
      const scoreRaw = Number(item.score ?? item.relevanceScore ?? 0);
      const score = Number.isFinite(scoreRaw) && scoreRaw > 0 ? Number(scoreRaw.toFixed(2)) : undefined;
      return { sku, title, score };
    });
  };

  const handleSend = async () => {
    const trimmed = inputValue.trim();
    if (!trimmed || isSending) {
      return;
    }

    setIsSending(true);
    setMessages((prev) => [
      ...prev,
      {
        id: `${Date.now()}-user`,
        role: 'user',
        text: trimmed,
      },
    ]);
    setInputValue('');

    try {
      const [intelligentResult, keywordResult] = await Promise.allSettled([
        semanticSearchService.searchWithMode(trimmed, 'intelligent', 8),
        semanticSearchService.searchWithMode(trimmed, 'keyword', 8),
      ]);

      const intelligentPreview =
        intelligentResult.status === 'fulfilled'
          ? buildPreview(intelligentResult.value.items as unknown as Array<Record<string, unknown>>)
          : [];
      const keywordPreview =
        keywordResult.status === 'fulfilled'
          ? buildPreview(keywordResult.value.items as unknown as Array<Record<string, unknown>>)
          : [];

      if (intelligentPreview.length === 0 && keywordPreview.length === 0) {
        throw new Error('No usable comparison results');
      }

      setMessages((prev) => [
        ...prev,
        {
          id: `${Date.now()}-agent`,
          role: 'agent',
          text: 'Agent retrieval is tuned for intent and relevance context. Compare the two lists below.',
          comparison: {
            intelligent: intelligentPreview,
            keyword: keywordPreview,
          },
        },
      ]);
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          id: `${Date.now()}-agent-error`,
          role: 'agent',
          text: 'Search agent is temporarily unavailable. Retry in a few seconds or use /search directly.',
        },
      ]);
    } finally {
      setIsSending(false);
    }
  };

  const openWidget = () => {
    setIsOpen(true);
    if (typeof window !== 'undefined' && window.location.hash !== '#agent-chat') {
      window.history.replaceState(null, '', `${window.location.pathname}${window.location.search}#agent-chat`);
    }
  };

  if (!isOpen) {
    return (
      <button
        type="button"
        onClick={openWidget}
        className="fixed bottom-4 right-4 z-50 flex items-center gap-2 rounded-full bg-[var(--hp-primary)] px-4 py-3 text-white shadow-lg transition-transform hover:scale-105 hover:bg-[var(--hp-primary-hover)] sm:bottom-6 sm:right-6"
        aria-label="Open product enrichment chat"
      >
        <FiMessageSquare className="w-6 h-6" />
        <span className="hidden font-semibold md:inline">Ask Product Agent</span>
      </button>
    );
  }

  return (
    <section className="fixed bottom-4 right-4 z-50 w-[calc(100%-2rem)] max-w-sm sm:bottom-6 sm:right-6" aria-label="Agent chat widget">
      <Card className="flex h-[70dvh] max-h-[540px] min-h-[440px] flex-col overflow-hidden border-[var(--hp-border)] shadow-2xl">
        <div className="flex items-center justify-between bg-[var(--hp-primary)] p-4 text-white">
          <div className="flex items-center gap-2">
            <div className="h-2 w-2 animate-pulse rounded-full bg-green-300" />
            <h3 className="font-bold">Product Enrichment Agent</h3>
          </div>
          <div className="flex gap-3">
            <Link
              href="/search"
              className="hidden items-center text-xs font-semibold uppercase tracking-wide text-white/90 hover:text-white sm:inline-flex"
            >
              Open search page
            </Link>
            <button
              type="button"
              onClick={() => setIsOpen(false)}
              className="text-white/80 hover:text-white"
              aria-label="Minimize chat"
            >
              <FiMinimize2 className="h-5 w-5" />
            </button>
          </div>
        </div>

        <div className="border-b border-[var(--hp-border)] bg-[var(--hp-surface-strong)] px-4 py-2 text-xs text-[var(--hp-text-muted)]">
          Ask for similar products. We compare intelligent retrieval vs keyword fallback live.
        </div>

        <div className="flex-1 space-y-4 overflow-y-auto bg-[var(--hp-bg)] p-4" role="log" aria-live="polite" aria-relevant="additions text">
          {messages.map((m) => (
            <div key={m.id} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              <div
                className={`max-w-[84%] rounded-2xl p-3 text-sm ${
                  m.role === 'user'
                    ? 'rounded-br-none bg-[var(--hp-primary)] text-white'
                    : 'rounded-bl-none border border-[var(--hp-border)] bg-[var(--hp-surface)] text-[var(--hp-text)] shadow-sm'
                }`}
              >
                {m.text}

                {m.comparison ? (
                  <div className="mt-3 grid grid-cols-1 gap-3">
                    <SearchComparisonScorecard
                      intelligent={m.comparison.intelligent}
                      keyword={m.comparison.keyword}
                    />

                    <div>
                      <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-[var(--hp-primary)]">
                        Intelligent agent results
                      </p>
                      <ul className="space-y-1">
                        {m.comparison.intelligent.map((product) => (
                          <li key={`intelligent-${m.id}-${product.sku}`}>
                            <Link
                              href={`/product?id=${encodeURIComponent(product.sku)}`}
                              className="text-xs underline decoration-dotted underline-offset-2"
                            >
                              {product.title}
                              {product.score ? ` (score ${product.score})` : ''}
                            </Link>
                          </li>
                        ))}
                      </ul>
                    </div>

                    <div>
                      <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-[var(--hp-text-muted)]">
                        Keyword fallback results
                      </p>
                      <ul className="space-y-1">
                        {m.comparison.keyword.map((product) => (
                          <li key={`keyword-${m.id}-${product.sku}`}>
                            <Link
                              href={`/product?id=${encodeURIComponent(product.sku)}`}
                              className="text-xs underline decoration-dotted underline-offset-2"
                            >
                              {product.title}
                              {product.score ? ` (score ${product.score})` : ''}
                            </Link>
                          </li>
                        ))}
                      </ul>
                    </div>
                  </div>
                ) : null}
              </div>
            </div>
          ))}
        </div>

        <div className="border-t border-[var(--hp-border)] bg-[var(--hp-surface)] p-3">
          <form
            onSubmit={(e) => { e.preventDefault(); handleSend(); }}
            className="flex gap-2"
            aria-label="Send a message to the product enrichment agent"
          >
            <label htmlFor="widget-agent-input" className="sr-only">
              Ask the product enrichment agent
            </label>
            <input
              id="widget-agent-input"
              type="text"
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              placeholder={DEFAULT_PROMPT}
              className="flex-1 rounded-full border border-[var(--hp-border)] bg-[var(--hp-bg)] px-4 py-2 text-sm text-[var(--hp-text)]"
              autoFocus
            />
            <Button
              type="submit"
              size="sm"
              className="flex h-10 w-10 items-center justify-center rounded-full bg-[var(--hp-primary)] p-0 hover:bg-[var(--hp-primary-hover)]"
              ariaLabel="Send message"
              disabled={isSending}
            >
              {isSending ? <FiRefreshCw className="h-4 w-4 animate-spin" /> : <FiSend className="w-4 h-4" />}
            </Button>
          </form>
        </div>
      </Card>
    </section>
  );
};
