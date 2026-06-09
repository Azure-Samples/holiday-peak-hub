/**
 * Search Feature - Public Facade
 *
 * This is the single public entry point for the search bounded context UI.
 * App routes, components, and tests should import search capabilities from here
 * instead of deep-linking into feature internals.
 */

// ===== TYPES =====
export type {
  AppAudience,
  AppPage,
  AppSearchBoxProps,
  IntentPanelProps,
  IntelligentSearchOptions,
  IntelligentSearchPreference,
  IntelligentSearchStage,
  SearchComparisonItem,
  SearchDegradedReason,
  SearchHit,
  SearchModeIndicatorProps,
  SearchModePreference,
  SearchModeToggleProps,
  SearchResultCardProps,
  SearchResultType,
  SemanticSearchContext,
  SemanticSearchIntent,
  SemanticSearchRequest,
  SemanticSearchResponse,
  StreamingSearchCallbacks,
} from './types';

// ===== COMPONENTS =====
export { AppSearchBox } from './components/AppSearchBox';
export { IntentPanel } from './components/IntentPanel';
export { SearchComparisonScorecard } from './components/SearchComparisonScorecard';
export { SearchModeIndicator } from './components/SearchModeIndicator';
export { SearchModeToggle } from './components/SearchModeToggle';
export { SearchPage } from './components/SearchPage';
export { SearchResultCard } from './components/SearchResultCard';

// ===== HOOKS =====
export { useIntelligentSearch } from './hooks/useIntelligentSearch';
export { useSemanticSearch } from './hooks/useSemanticSearch';
export { useStreamingSearch } from './hooks/useStreamingSearch';

// ===== SERVICES =====
export { semanticSearchService } from './services/semanticSearchService';

// ===== INTERNAL HELPERS EXPOSED FOR TESTED APP-SEARCH CONTRACTS =====
export { APP_PAGES, AUDIENCE_FILTER } from './internal/appPages';
export { buildDocsSearchUrl, searchAppPages } from './internal/matcher';