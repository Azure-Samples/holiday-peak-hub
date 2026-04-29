import type { AgentProfileSlug } from '@/lib/agents/profiles';

export interface ScenarioConfig {
  id: 'discovery' | 'customer-360' | 'truth' | 'checkout';
  title: string;
  eyebrow: string;
  summary: string;
  metric: string;
  outcome: string;
  liveSurfaceHref: string;
  operatorHref: string;
  leadAgent: AgentProfileSlug;
  supportingAgents: AgentProfileSlug[];
  storyBeats: string[];
}

export const SCENARIO_OPTIONS = [
  {
    id: 'discovery',
    title: 'Product discovery and enrichment',
    eyebrow: 'Discovery scenario',
    summary:
      'Grounded search, semantic enrichment, and product detail storytelling work as one motion so discovery feels faster and more trustworthy.',
    metric: '+35% search-to-product CTR',
    outcome: 'Higher intent product views without sacrificing grounding or latency discipline.',
    liveSurfaceHref: '/search?agentChat=1',
    operatorHref: '/admin/agent-activity',
    leadAgent: 'ecommerce-catalog-search',
    supportingAgents: ['search-enrichment-agent', 'ecommerce-product-detail-enrichment'],
    storyBeats: [
      'Catalog search grounds the query in live products instead of generic semantic text.',
      'Search enrichment adds explanation, use-cases, and facets that make the answer actionable.',
      'Product detail enrichment carries the same signal onto the PDP so trust does not reset after the click.',
    ],
  },
  {
    id: 'customer-360',
    title: 'Customer 360 personalization',
    eyebrow: 'CRM ensemble',
    summary:
      'Identity, segment, campaign, and support robots compose a single customer brief so each team starts from the same signal.',
    metric: '4 agents in 1.4 s',
    outcome: 'Faster personalization and support recovery because the customer context is assembled once, then reused.',
    liveSurfaceHref: '/admin/crm/profiles',
    operatorHref: '/admin/agent-activity',
    leadAgent: 'crm-profile-aggregation',
    supportingAgents: [
      'crm-segmentation-personalization',
      'crm-campaign-intelligence',
      'crm-support-assistance',
    ],
    storyBeats: [
      'Profile aggregation builds the identity spine and recent behavior snapshot.',
      'Segmentation personalization classifies the shopper into an actionable cohort.',
      'Campaign intelligence and support assistance turn the same brief into next-best action and risk handling.',
    ],
  },
  {
    id: 'truth',
    title: 'Product truth layer',
    eyebrow: 'Truth pipeline',
    summary:
      'Ingestion, enrichment, HITL review, and export make product readiness visible as a governed pipeline instead of a manual spreadsheet project.',
    metric: '>98% catalog quality',
    outcome: 'Faster publish readiness with lower manual review burden and clearer operator evidence.',
    liveSurfaceHref: '/admin/truth-analytics',
    operatorHref: '/staff/review',
    leadAgent: 'truth-enrichment',
    supportingAgents: ['truth-ingestion', 'truth-hitl', 'truth-export'],
    storyBeats: [
      'Truth ingestion admits raw product payloads with traceable provenance.',
      'Truth enrichment fills the highest-value gaps and exposes confidence on the record.',
      'HITL review and truth export package ambiguous fields and approved outputs for downstream channels.',
    ],
  },
  {
    id: 'checkout',
    title: 'Cart and checkout intelligence',
    eyebrow: 'Conversion guardrail',
    summary:
      'Cart scoring, checkout support, and downstream logistics signals reduce abandonment by catching friction before the shopper feels it.',
    metric: '-25% abandonment',
    outcome: 'Higher conversion and more credible delivery promises because validation moves ahead of failure.',
    liveSurfaceHref: '/checkout',
    operatorHref: '/cart',
    leadAgent: 'ecommerce-checkout-support',
    supportingAgents: [
      'ecommerce-cart-intelligence',
      'inventory-reservation-validation',
      'logistics-eta-computation',
    ],
    storyBeats: [
      'Cart intelligence scores abandonment risk and picks the one revenue move worth showing.',
      'Checkout support validates address, payment, and fulfillment signals before submit.',
      'Reservation validation and ETA computation keep the downstream promise aligned with what the UI says.',
    ],
  },
] as const satisfies readonly ScenarioConfig[];

export type ScenarioId = (typeof SCENARIO_OPTIONS)[number]['id'];

export const SCENARIO_BY_ID: Record<ScenarioId, ScenarioConfig> = SCENARIO_OPTIONS.reduce(
  (accumulator, scenario) => {
    accumulator[scenario.id] = scenario;
    return accumulator;
  },
  {} as Record<ScenarioId, ScenarioConfig>,
);

export function isScenarioId(value: string): value is ScenarioId {
  return value in SCENARIO_BY_ID;
}