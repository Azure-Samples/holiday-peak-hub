'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { Button } from '@/components/atoms/Button';
import { FiMessageSquare, FiSend, FiMinimize2, FiArrowRight } from 'react-icons/fi';
import { Card } from '@/components/molecules/Card';

export const ChatWidget: React.FC = () => {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState<{ role: 'user' | 'agent'; text: string }[]>([
    {
      role: 'agent',
      text: 'I can interpret product data and help compare options. Catalog browsing is available in-page, and this chat is the agent layer.',
    },
  ]);
  const [inputValue, setInputValue] = useState('');

  const handleSend = () => {
    if (!inputValue.trim()) return;

    setMessages((prev) => [...prev, { role: 'user', text: inputValue }]);

    setTimeout(() => {
      setMessages((prev) => [
        ...prev,
        {
          role: 'agent',
          text: 'Demo response: use this thread to ask for enrichment, stock interpretation, and comparison support.',
        },
      ]);
    }, 1000);

    setInputValue('');
  };

  if (!isOpen) {
    return (
      <button
        type="button"
        onClick={() => setIsOpen(true)}
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
              href="/agents/product-enrichment-chat"
              className="hidden items-center text-xs font-semibold uppercase tracking-wide text-white/90 hover:text-white sm:inline-flex"
            >
              <FiArrowRight className="mr-1 h-4 w-4" />
              Full Screen
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
          Catalog actions remain on page cards. Agent actions happen in this chat.
        </div>

        <div className="flex-1 space-y-4 overflow-y-auto bg-[var(--hp-bg)] p-4" role="log" aria-live="polite" aria-relevant="additions text">
          {messages.map((m, idx) => (
            <div key={idx} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              <div
                className={`max-w-[84%] rounded-2xl p-3 text-sm ${
                  m.role === 'user'
                    ? 'rounded-br-none bg-[var(--hp-primary)] text-white'
                    : 'rounded-bl-none border border-[var(--hp-border)] bg-[var(--hp-surface)] text-[var(--hp-text)] shadow-sm'
                }`}
              >
                {m.text}
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
              placeholder="Ask for product insights"
              className="flex-1 rounded-full border border-[var(--hp-border)] bg-[var(--hp-bg)] px-4 py-2 text-sm text-[var(--hp-text)]"
              autoFocus
            />
            <Button
              type="submit"
              size="sm"
              className="flex h-10 w-10 items-center justify-center rounded-full bg-[var(--hp-primary)] p-0 hover:bg-[var(--hp-primary-hover)]"
              ariaLabel="Send message"
            >
              <FiSend className="w-4 h-4" />
            </Button>
          </form>
        </div>
      </Card>
    </section>
  );
};
