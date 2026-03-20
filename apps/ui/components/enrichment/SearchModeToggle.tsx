import React from 'react';
import { Badge } from '../atoms/Badge';
import type { IntelligentSearchPreference } from '@/lib/hooks/useIntelligentSearch';

export interface SearchModeToggleProps {
  preference: IntelligentSearchPreference;
  resolvedMode: 'keyword' | 'intelligent';
  onChange: (preference: IntelligentSearchPreference) => void;
}

const OPTIONS: Array<{ value: IntelligentSearchPreference; label: string }> = [
  { value: 'auto', label: 'Auto' },
  { value: 'keyword', label: 'Keyword' },
  { value: 'intelligent', label: 'Intelligent' },
];

export const SearchModeToggle: React.FC<SearchModeToggleProps> = ({
  preference,
  resolvedMode,
  onChange,
}) => {
  const modeLabel = resolvedMode === 'intelligent' ? 'Intelligent Search' : 'Keyword Search';

  return (
    <section
      className="rounded-2xl border border-[var(--hp-border)] bg-[var(--hp-surface)] p-3"
      aria-label="Search mode controls"
    >
      <div className="mb-2 flex flex-wrap items-center gap-2">
        <span className="text-sm font-semibold text-[var(--hp-text)]">Search mode</span>
        <Badge
          className={
            resolvedMode === 'intelligent'
              ? 'bg-gradient-to-r from-[var(--hp-primary)] to-[var(--hp-accent)] text-white'
              : 'bg-[var(--hp-surface-strong)] text-[var(--hp-text-muted)]'
          }
        >
          {modeLabel}
        </Badge>
      </div>

      <div className="flex flex-wrap gap-2" role="radiogroup" aria-label="Select search mode preference">
        {OPTIONS.map((option) => {
          const checked = option.value === preference;
          return (
            <button
              key={option.value}
              type="button"
              className={`min-w-[88px] rounded-lg px-3 py-1.5 text-sm font-bold uppercase transition-colors duration-200 focus:outline-none focus:ring-2 focus:ring-offset-2 ${
                checked
                  ? 'bg-[var(--hp-primary)] text-white hover:bg-[var(--hp-primary-hover)]'
                  : 'border border-[var(--hp-border)] bg-transparent text-[var(--hp-text)] hover:bg-[var(--hp-surface-strong)]'
              }`}
              aria-label={`Search mode ${option.label}`}
              role="radio"
              aria-checked={checked}
              onClick={() => onChange(option.value)}
            >
              {option.label}
            </button>
          );
        })}
      </div>
    </section>
  );
};

SearchModeToggle.displayName = 'SearchModeToggle';
