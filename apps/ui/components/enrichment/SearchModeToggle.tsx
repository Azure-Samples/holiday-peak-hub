import React from 'react';
import { Button } from '../atoms/Button';
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
              ? 'bg-[var(--hp-accent)]/20 text-[var(--hp-accent)]'
              : 'bg-[var(--hp-surface-strong)] text-[var(--hp-text-muted)]'
          }
        >
          {resolvedMode}
        </Badge>
      </div>

      <div className="flex flex-wrap gap-2" role="radiogroup" aria-label="Select search mode preference">
        {OPTIONS.map((option) => {
          const checked = option.value === preference;
          return (
            <Button
              key={option.value}
              type="button"
              size="sm"
              variant={checked ? 'primary' : 'outline'}
              className="min-w-[88px]"
              ariaLabel={`Search mode ${option.label}`}
              onClick={() => onChange(option.value)}
            >
              {option.label}
            </Button>
          );
        })}
      </div>
    </section>
  );
};

SearchModeToggle.displayName = 'SearchModeToggle';
