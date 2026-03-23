import React from 'react';
import { Badge } from '../atoms/Badge';

export interface SearchModeIndicatorProps {
  source: 'agent' | 'crud' | 'fallback';
}

export const SearchModeIndicator: React.FC<SearchModeIndicatorProps> = ({ source }) => {
  const label =
    source === 'agent'
      ? 'Search mode: Agent enrichment'
      : source === 'crud'
        ? 'Search mode: CRUD catalog'
      : 'Search mode: Fallback catalog';

  return (
    <div role="status" aria-live="polite" aria-atomic="true">
      <Badge className="bg-ocean-500 text-white">{label}</Badge>
    </div>
  );
};

SearchModeIndicator.displayName = 'SearchModeIndicator';
