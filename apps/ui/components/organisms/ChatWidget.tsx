'use client';

import React, { useEffect, useMemo, useRef, useState } from 'react';
import Link from 'next/link';
import { usePathname, useSearchParams } from 'next/navigation';
import { Button } from '@/components/atoms/Button';
import { FiMessageSquare, FiSend, FiMinimize2, FiRefreshCw } from 'react-icons/fi';
import { Card } from '@/components/molecules/Card';
import { SearchComparisonScorecard } from '@/components/enrichment/SearchComparisonScorecard';
import { semanticSearchService } from '@/lib/services/semanticSearchService';
import type { StreamingSearchCallbacks } from '@/lib/services/semanticSearchService';

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
  trace?: {
    mode: string;
    timeMs: number;
    resultCount: number;
  };
};

const DEFAULT_PROMPT = 'Find similar products to premium wireless noise-cancelling headphones under 300';
const CHAT_WIDGET_PANEL_ID = 'agent-chat-widget-panel';
const CHAT_WIDGET_LOG_ID = 'agent-chat-widget-log';
const CHAT_WIDGET_INPUT_ID = 'widget-agent-input';
const QUICK_PROMPTS = [
  'Giftable kitchen tools under 80',
  'Office chairs with lumbar support under 300',
  'Compact smart speakers for small rooms',
];

const TraceDetail: React.FC<{ trace: NonNullable<ChatEntry['trace']> }> = ({ trace }) => {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <div className="mt-1.5">
      <button
        type="button"
        onClick={() => setIsOpen((prev) => !prev)}
        aria-expanded={isOpen}
        className="text-[10px] text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-300 underline decoration-dotted underline-offset-2 focus:outline-none focus-visible:ring-1 focus-visible:ring-blue-500 rounded"
      >
        {isOpen ? 'Hide trace' : 'Show trace'}
      </button>
      {isOpen && (
        <dl className="mt-1 grid grid-cols-3 gap-x-3 text-[10px] text-gray-400 dark:text-gray-500">
          <div>
            <dt className="font-semibold">Mode</dt>
            <dd className="font-mono">{trace.mode}</dd>
          </div>
          <div>
            <dt className="font-semibold">Time</dt>
            <dd className="font-mono">{trace.timeMs}ms</dd>
          </div>
          <div>
            <dt className="font-semibold">Results</dt>
            <dd className="font-mono">{trace.resultCount}</dd>
          </div>
        </dl>
      )}
    </div>
  );
};

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
  const [statusMessage, setStatusMessage] = useState('Ready. Ask for similar products to compare retrieval modes.');
  const launcherButtonRef = useRef<HTMLButtonElement>(null);
  const transcriptRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const focusLauncherButton = () => {
    window.setTimeout(() => {
      launcherButtonRef.current?.focus();
    }, 0);
  };

  useEffect(() => {
    if (shouldAutoOpen) {
      setIsOpen(true);
    }
  }, [shouldAutoOpen]);

  useEffect(() => {
    if (!isOpen) {
      return;
    }

    inputRef.current?.focus();

    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        event.preventDefault();
        setIsOpen(false);
        setStatusMessage('Chat minimized.');
        focusLauncherButton();
      }
    };

    window.addEventListener('keydown', handleEscape);
    return () => window.removeEventListener('keydown', handleEscape);
  }, [isOpen]);

  useEffect(() => {
    const transcriptElement = transcriptRef.current;
    if (!transcriptElement || typeof transcriptElement.scrollTo !== 'function') {
      return;
    }

    transcriptElement.scrollTo({ top: transcriptElement.scrollHeight, behavior: 'smooth' });
  }, [messages, isSending]);

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
    setStatusMessage('Streaming intelligent results and comparing with keyword retrieval.');
    setInputValue('');

    const agentMessageId = `${Date.now()}-agent`;
    let intelligentPreview: ProductPreview[] = [];
    let streamedAnswer = '';
    const searchStartTime = performance.now();

    try {
      // Start keyword search (non-streaming) and intelligent search (streaming) in parallel
      const keywordPromise = semanticSearchService.searchWithMode(trimmed, 'keyword', 8);

      const intelligentStreamDone = new Promise<void>((resolve, reject) => {
        const callbacks: StreamingSearchCallbacks = {
          onResults: (response) => {
            intelligentPreview = buildPreview(
              response.items as unknown as Array<Record<string, unknown>>,
            );
          },
          onToken: (text) => {
            streamedAnswer += text;
            // Progressively update the agent message with the streaming answer
            setMessages((prev) => {
              const existing = prev.find((m) => m.id === agentMessageId);
              if (existing) {
                return prev.map((m) =>
                  m.id === agentMessageId ? { ...m, text: streamedAnswer } : m,
                );
              }
              return [
                ...prev,
                { id: agentMessageId, role: 'agent' as const, text: streamedAnswer },
              ];
            });
          },
          onDone: () => resolve(),
          onError: (error) => reject(error),
        };
        semanticSearchService.searchStream(
          { query: trimmed, limit: 8, mode: 'intelligent' },
          callbacks,
        );
      });

      const [keywordResult] = await Promise.allSettled([keywordPromise, intelligentStreamDone]);

      const keywordPreview =
        keywordResult.status === 'fulfilled'
          ? buildPreview(keywordResult.value.items as unknown as Array<Record<string, unknown>>)
          : [];

      if (intelligentPreview.length === 0 && keywordPreview.length === 0) {
        throw new Error('No usable comparison results');
      }

      const finalText = streamedAnswer
        || 'Agent retrieval is tuned for intent and relevance context. Compare the two lists below.';

      const elapsedMs = Math.round(performance.now() - searchStartTime);
      const totalResults = intelligentPreview.length + keywordPreview.length;
      const searchMode = intelligentPreview.length > 0 ? 'hybrid' : 'keyword';

      setMessages((prev) => {
        const filtered = prev.filter((m) => m.id !== agentMessageId);
        return [
          ...filtered,
          {
            id: agentMessageId,
            role: 'agent' as const,
            text: finalText,
            comparison: {
              intelligent: intelligentPreview,
              keyword: keywordPreview,
            },
            trace: {
              mode: searchMode,
              timeMs: elapsedMs,
              resultCount: totalResults,
            },
          },
        ];
      });
      setStatusMessage('Comparison ready. Review intelligent and keyword results below.');
    } catch {
      setMessages((prev) => [
        ...prev.filter((m) => m.id !== agentMessageId),
        {
          id: `${Date.now()}-agent-error`,
          role: 'agent',
          text: 'Search agent is temporarily unavailable. Retry in a few seconds or use /search directly.',
        },
      ]);
      setStatusMessage('Comparison failed. Search agent is temporarily unavailable.');
    } finally {
      setIsSending(false);
    }
  };

  const openWidget = () => {
    setIsOpen(true);
    setStatusMessage('Chat opened. Type your product request to start a comparison.');
    if (typeof window !== 'undefined' && window.location.hash !== '#agent-chat') {
      window.history.replaceState(null, '', `${window.location.pathname}${window.location.search}#agent-chat`);
    }
  };

  const handleQuickPrompt = (prompt: string) => {
    setInputValue(prompt);
    setStatusMessage('Quick prompt selected. Press send to run comparison.');
    inputRef.current?.focus();
  };

  if (!isOpen) {
    return (
      <button
        type="button"
        ref={launcherButtonRef}
        onClick={openWidget}
        className="fixed bottom-4 right-4 z-50 flex items-center gap-2 rounded-full bg-[var(--hp-primary)] px-4 py-3 text-white shadow-lg transition-transform hover:scale-105 hover:bg-[var(--hp-primary-hover)] sm:bottom-6 sm:right-6"
        aria-label="Open product enrichment chat"
        aria-expanded={false}
        aria-controls={CHAT_WIDGET_PANEL_ID}
      >
        <FiMessageSquare className="w-6 h-6" />
        <span className="hidden font-semibold md:inline">Ask Product Agent</span>
      </button>
    );
  }

  return (
    <section
      id={CHAT_WIDGET_PANEL_ID}
      role="dialog"
      aria-modal="false"
      aria-labelledby="agent-chat-widget-title"
      className="fixed bottom-4 right-4 z-50 w-[calc(100%-2rem)] max-w-md sm:bottom-6 sm:right-6"
      aria-label="Agent chat widget"
    >
      <Card className="flex h-[70dvh] max-h-[540px] min-h-[440px] flex-col overflow-hidden border-[var(--hp-border)] shadow-2xl">
        <div className="flex items-center justify-between bg-[var(--hp-primary)] p-4 text-white">
          <div className="flex items-center gap-2">
            <div className="h-2 w-2 animate-pulse rounded-full bg-green-300" />
            <h3 id="agent-chat-widget-title" className="font-bold">Product Enrichment Agent</h3>
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
              onClick={() => {
                setIsOpen(false);
                setStatusMessage('Chat minimized.');
                focusLauncherButton();
              }}
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

        <div className="grid grid-cols-1 gap-2 border-b border-[var(--hp-border)] bg-[var(--hp-surface)] px-4 py-3 sm:grid-cols-3" aria-label="Quick prompts">
          {QUICK_PROMPTS.map((prompt) => (
            <button
              key={prompt}
              type="button"
              onClick={() => handleQuickPrompt(prompt)}
              className="rounded-lg border border-[var(--hp-border)] bg-[var(--hp-surface-strong)] px-2 py-1.5 text-left text-xs font-semibold text-[var(--hp-text)] hover:bg-[var(--hp-surface)]"
            >
              {prompt}
            </button>
          ))}
        </div>

        <div className="sr-only" role="status" aria-live="polite">{statusMessage}</div>

        <div
          id={CHAT_WIDGET_LOG_ID}
          ref={transcriptRef}
          className="flex-1 space-y-4 overflow-y-auto bg-[var(--hp-bg)] p-4"
          role="log"
          aria-live="polite"
          aria-relevant="additions text"
        >
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

                {m.role === 'agent' && m.trace ? <TraceDetail trace={m.trace} /> : null}
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
              id={CHAT_WIDGET_INPUT_ID}
              ref={inputRef}
              type="text"
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              placeholder={DEFAULT_PROMPT}
              className="flex-1 rounded-full border border-[var(--hp-border)] bg-[var(--hp-bg)] px-4 py-2 text-sm text-[var(--hp-text)]"
              aria-controls={CHAT_WIDGET_LOG_ID}
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
