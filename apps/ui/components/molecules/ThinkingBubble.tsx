'use client';

import React, { useEffect, useRef, useState } from 'react';
import { cn } from '@/components/utils';

export interface ThinkingBubbleProps {
  content: string;
  isStreaming?: boolean;
  maxHeight?: number;
  maxWidth?: number;
  className?: string;
}

// No GoF pattern applies — simple presentational component with local scroll state.
function renderInlineMarkdown(text: string): React.ReactNode[] {
  const nodes: React.ReactNode[] = [];
  const pattern = /(\*\*[^*]+\*\*|`[^`]+`|\*[^*]+\*)/g;
  let lastIndex = 0;
  let match: RegExpExecArray | null;

  while ((match = pattern.exec(text)) !== null) {
    if (match.index > lastIndex) {
      nodes.push(text.slice(lastIndex, match.index));
    }

    const token = match[0];
    if (token.startsWith('**') && token.endsWith('**')) {
      nodes.push(
        <strong key={match.index} className="font-semibold">
          {token.slice(2, -2)}
        </strong>,
      );
    } else if (token.startsWith('`') && token.endsWith('`')) {
      nodes.push(
        <code
          key={match.index}
          className="rounded bg-[var(--hp-surface-strong)] px-1 py-0.5 font-mono text-[0.85em]"
        >
          {token.slice(1, -1)}
        </code>,
      );
    } else if (token.startsWith('*') && token.endsWith('*')) {
      nodes.push(<em key={match.index}>{token.slice(1, -1)}</em>);
    }

    lastIndex = match.index + token.length;
  }

  if (lastIndex < text.length) {
    nodes.push(text.slice(lastIndex));
  }

  return nodes;
}

function StreamingDots() {
  return (
    <span className="inline-flex items-center gap-0.5" aria-label="Loading">
      <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-current [animation-delay:0ms]" />
      <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-current [animation-delay:150ms]" />
      <span className="h-1.5 w-1.5 animate-bounce rounded-full bg-current [animation-delay:300ms]" />
    </span>
  );
}

export function ThinkingBubble({
  content,
  isStreaming = false,
  maxHeight = 128,
  maxWidth = 240,
  className,
}: ThinkingBubbleProps) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const [autoScroll, setAutoScroll] = useState(true);

  useEffect(() => {
    if (autoScroll && scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [content, autoScroll]);

  const handleScroll = () => {
    if (!scrollRef.current) {
      return;
    }

    const { scrollTop, scrollHeight, clientHeight } = scrollRef.current;
    setAutoScroll(scrollHeight - scrollTop - clientHeight < 16);
  };

  const lines = content.split('\n');

  return (
    <div
      className={cn(
        'relative rounded-2xl border border-[var(--hp-border)] bg-[var(--hp-surface)] px-3 py-2 text-xs text-[var(--hp-text)] shadow-[var(--hp-shadow-lg)]',
        className,
      )}
      style={{ maxWidth, width: 'max-content' }}
    >
      <div
        ref={scrollRef}
        className="overflow-y-auto leading-relaxed"
        style={{ maxHeight }}
        onScroll={handleScroll}
      >
        {content ? (
          lines.map((line, index) => (
            <React.Fragment key={index}>
              {index > 0 && <br />}
              {renderInlineMarkdown(line)}
            </React.Fragment>
          ))
        ) : isStreaming ? (
          <StreamingDots />
        ) : null}
        {isStreaming && content && (
          <span className="ml-1 inline-block">
            <StreamingDots />
          </span>
        )}
      </div>

      <div className="absolute -bottom-2 left-1/2 -translate-x-1/2">
        <span className="block h-2 w-2 rounded-full bg-[var(--hp-border)]" />
      </div>
      <div className="absolute -bottom-5 left-1/2 translate-x-0.5">
        <span className="block h-1.5 w-1.5 rounded-full bg-[var(--hp-border)]" />
      </div>
    </div>
  );
}
