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
      <p className="mb-2 text-[10px] font-semibold uppercase tracking-widest text-gray-400">{label}</p>
      <div className="flex flex-wrap gap-1.5" role="list" aria-label={`${label} tags`}>
        {useCases.map((useCase) => (
          <Badge key={useCase} size="sm" className="bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 border border-gray-200 dark:border-gray-700 text-[11px] font-medium px-2.5 py-0.5" testId={`use-case-${useCase}`}>
            <span aria-label={`Use case ${useCase}`}>{useCase}</span>
          </Badge>
        ))}
      </div>
    </section>
  );
};

UseCaseTags.displayName = 'UseCaseTags';
