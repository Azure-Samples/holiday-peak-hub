import React from 'react';
import { Badge } from '../atoms/Badge';

export interface UseCaseTagsProps {
  useCases?: string[];
  label?: string;
  className?: string;
}

export const UseCaseTags: React.FC<UseCaseTagsProps> = ({
  useCases = [],
  label = 'Use cases',
  className,
}) => {
  if (useCases.length === 0) {
    return null;
  }

  return (
    <section className={className} aria-label={label}>
      <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-[var(--hp-text-muted)]">{label}</p>
      <div className="flex flex-wrap gap-2">
        {useCases.map((useCase) => (
          <Badge key={useCase} className="bg-[var(--hp-accent)]/20 text-[var(--hp-accent)]">
            {useCase}
          </Badge>
        ))}
      </div>
    </section>
  );
};

UseCaseTags.displayName = 'UseCaseTags';
