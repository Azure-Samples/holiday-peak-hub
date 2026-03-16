'use client';

import React, { useState } from 'react';
import { FiBookmark, FiCheck, FiCopy } from 'react-icons/fi';
import type { AgentCard, AgentMessageView } from '@/lib/utils/agentResponseCards';

export interface AgentMessageDisplayProps {
  view: AgentMessageView;
  compact?: boolean;
  onPinCard?: (card: AgentCard) => void;
}

const AgentCardBlock: React.FC<{
  card: AgentCard;
  compact: boolean;
  onPinCard?: (card: AgentCard) => void;
}> = ({ card, compact, onPinCard }) => {
  return (
    <div className="rounded-xl border border-[var(--hp-border)] bg-[var(--hp-surface)] p-3">
      <div className="flex items-start justify-between gap-2">
        <p className="text-xs font-semibold uppercase tracking-wide text-[var(--hp-text-muted)]">{card.title}</p>
        {onPinCard ? (
          <button
            type="button"
            onClick={() => onPinCard(card)}
            className="inline-flex items-center gap-1 rounded-md border border-[var(--hp-border)] px-1.5 py-0.5 text-[10px] font-semibold text-[var(--hp-text-muted)] hover:text-[var(--hp-primary)]"
            aria-label={`Pin ${card.title}`}
          >
            <FiBookmark className="h-3 w-3" />
            Pin
          </button>
        ) : null}
      </div>
      {card.value ? <p className="mt-1 text-sm text-[var(--hp-text)]">{card.value}</p> : null}
      {card.items && card.items.length > 0 ? (
        <ul className={compact ? 'mt-2 space-y-1 text-xs text-[var(--hp-text-muted)]' : 'mt-2 space-y-1.5 text-sm text-[var(--hp-text-muted)]'}>
          {card.items.map((item, index) => (
            <li key={`${card.id}-${index}`} className="rounded-md bg-[var(--hp-bg)] px-2 py-1">{item}</li>
          ))}
        </ul>
      ) : null}
    </div>
  );
};

export const AgentMessageDisplay: React.FC<AgentMessageDisplayProps> = ({ view, compact = false, onPinCard }) => {
  const [copied, setCopied] = useState(false);

  const copyContent = async () => {
    const sections: string[] = [view.text];
    view.cards.forEach((card) => {
      sections.push(`\n${card.title}`);
      if (card.value) {
        sections.push(card.value);
      }
      if (card.items?.length) {
        sections.push(...card.items.map((item) => `- ${item}`));
      }
    });

    if (view.rawJson) {
      sections.push('\nRaw payload');
      sections.push(view.rawJson);
    }

    await navigator.clipboard.writeText(sections.join('\n'));
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1500);
  };

  return (
    <div className="space-y-3">
      <div className="flex items-start justify-between gap-2">
        <p className={compact ? 'text-sm text-[var(--hp-text)]' : 'text-sm text-[var(--hp-text)]'}>{view.text}</p>
        <button
          type="button"
          onClick={copyContent}
          className="inline-flex items-center gap-1 rounded-md border border-[var(--hp-border)] bg-[var(--hp-surface)] px-2 py-1 text-xs font-semibold text-[var(--hp-text-muted)] hover:text-[var(--hp-primary)]"
          aria-label="Copy agent response"
        >
          {copied ? <FiCheck className="h-3.5 w-3.5" /> : <FiCopy className="h-3.5 w-3.5" />}
          {copied ? 'Copied' : 'Copy'}
        </button>
      </div>

      {view.cards.length > 0 ? (
        <div className={compact ? 'grid gap-2' : 'grid gap-2 sm:grid-cols-2'}>
          {view.cards.map((card) => (
            <AgentCardBlock key={card.id} card={card} compact={compact} onPinCard={onPinCard} />
          ))}
        </div>
      ) : null}

      {view.rawJson ? (
        <pre className="max-h-44 overflow-auto rounded-lg bg-[var(--hp-bg)] p-2 text-xs text-[var(--hp-text-muted)]">
          {view.rawJson}
        </pre>
      ) : null}
    </div>
  );
};

export default AgentMessageDisplay;
