import type { MaturityLevel } from '@/components/atoms/MaturityBadge';

export type AgentCatalogAgent = {
  slug: string;
  name: string;
  oneLine: string;
  costLower: string;
  costUpper: string;
  maturity: MaturityLevel;
};

export type AgentCatalogDomain = {
  key: string;
  label: string;
  blurb: string;
  agents: readonly AgentCatalogAgent[];
};

export const AGENT_CATALOG_DOMAINS: readonly AgentCatalogDomain[] = [
  {
    key: 'crm',
    label: 'CRM',
    blurb: 'Customer profiles, segmentation, campaign drafting, and support assistance.',
    agents: [
      { slug: 'crm-campaign-intelligence', name: 'Campaign Intelligence', oneLine: 'Drafts campaign briefs from segment + recent product activity.', costLower: '0.18', costUpper: '0.26', maturity: 'design-partner' },
      { slug: 'crm-profile-aggregation', name: 'Profile Aggregation', oneLine: 'Composes a single customer profile from CRM, web, and order signals.', costLower: '0.04', costUpper: '0.08', maturity: 'design-partner' },
      { slug: 'crm-segmentation-personalization', name: 'Segmentation & Personalization', oneLine: 'Emits readable customer-segment briefs with RFV / channel-mix rationale.', costLower: '0.09', costUpper: '0.14', maturity: 'design-partner' },
      { slug: 'crm-support-assistance', name: 'Support Assistance', oneLine: 'Triages support tickets against policy and order history.', costLower: '0.10', costUpper: '0.16', maturity: 'design-partner' },
    ],
  },
  {
    key: 'ecommerce',
    label: 'E-commerce',
    blurb: 'Cart, search, checkout, order status, and product detail enrichment.',
    agents: [
      { slug: 'ecommerce-cart-intelligence', name: 'Cart Intelligence', oneLine: 'Recommends cart additions and recovery offers from session and history.', costLower: '0.05', costUpper: '0.09', maturity: 'design-partner' },
      { slug: 'ecommerce-catalog-search', name: 'Catalog Search', oneLine: 'Semantic search over the catalog with re-ranking and intent routing.', costLower: '0.03', costUpper: '0.06', maturity: 'design-partner' },
      { slug: 'ecommerce-checkout-support', name: 'Checkout Support', oneLine: 'Resolves cart-to-payment errors and explains pricing differences.', costLower: '0.07', costUpper: '0.12', maturity: 'preview' },
      { slug: 'ecommerce-order-status', name: 'Order Status', oneLine: 'Composes a current-state answer from CRUD, logistics, and CRM context.', costLower: '0.02', costUpper: '0.04', maturity: 'design-partner' },
      { slug: 'ecommerce-product-detail-enrichment', name: 'Product Detail Enrichment', oneLine: 'Backfills attributes from supplier feeds + image evidence; agent-led, human-reviewed.', costLower: '0.12', costUpper: '0.20', maturity: 'design-partner' },
    ],
  },
  {
    key: 'inventory',
    label: 'Inventory',
    blurb: 'Replenishment, alerts, health checks, reservation validation.',
    agents: [
      { slug: 'inventory-alerts-triggers', name: 'Alerts & Triggers', oneLine: 'Composes operational alerts from sell-through and inbound signals.', costLower: '0.03', costUpper: '0.06', maturity: 'design-partner' },
      { slug: 'inventory-health-check', name: 'Health Check', oneLine: 'Surveys inventory state per SKU group and flags anomalies.', costLower: '0.04', costUpper: '0.07', maturity: 'design-partner' },
      { slug: 'inventory-jit-replenishment', name: 'JIT Replenishment', oneLine: 'Proposes vendor orders from sell-through, on-hand, and inbound - surfaced for buyer approval.', costLower: '0.14', costUpper: '0.22', maturity: 'design-partner' },
      { slug: 'inventory-reservation-validation', name: 'Reservation Validation', oneLine: 'Holds inventory across cart, checkout, and fulfillment; rolls back ghost holds.', costLower: '0.02', costUpper: '0.04', maturity: 'design-partner' },
    ],
  },
  {
    key: 'logistics',
    label: 'Logistics',
    blurb: 'Carrier selection, ETA computation, returns, route issue detection.',
    agents: [
      { slug: 'logistics-carrier-selection', name: 'Carrier Selection', oneLine: 'Proposes the best carrier per shipment from cost, ETA, and reliability signals.', costLower: '0.04', costUpper: '0.08', maturity: 'design-partner' },
      { slug: 'logistics-eta-computation', name: 'ETA Computation', oneLine: 'Composes carrier and route signals into a confidence-banded ETA per order.', costLower: '0.03', costUpper: '0.05', maturity: 'design-partner' },
      { slug: 'logistics-returns-support', name: 'Returns Support', oneLine: 'Triages returns against policy, drafts response, escalates exceptions.', costLower: '0.10', costUpper: '0.16', maturity: 'preview' },
      { slug: 'logistics-route-issue-detection', name: 'Route Issue Detection', oneLine: 'Detects in-transit anomalies and triggers proactive customer comms.', costLower: '0.05', costUpper: '0.09', maturity: 'preview' },
    ],
  },
  {
    key: 'product-management',
    label: 'Product Management',
    blurb: 'Assortment, normalization, ACP transformation, consistency validation.',
    agents: [
      { slug: 'product-management-acp-transformation', name: 'ACP Transformation', oneLine: 'Maps supplier ACP feeds into the canonical catalog shape with provenance.', costLower: '0.06', costUpper: '0.10', maturity: 'design-partner' },
      { slug: 'product-management-assortment-optimization', name: 'Assortment Optimization', oneLine: 'Proposes assortment moves from sell-through, margin, and category share.', costLower: '0.18', costUpper: '0.28', maturity: 'design-partner' },
      { slug: 'product-management-consistency-validation', name: 'Consistency Validation', oneLine: 'Audits catalog rows for cross-attribute and cross-channel inconsistencies.', costLower: '0.05', costUpper: '0.09', maturity: 'design-partner' },
      { slug: 'product-management-normalization-classification', name: 'Normalization & Classification', oneLine: 'Normalizes attributes and re-classifies into the canonical taxonomy.', costLower: '0.07', costUpper: '0.12', maturity: 'design-partner' },
    ],
  },
  {
    key: 'search',
    label: 'Search',
    blurb: 'Search-side enrichment that lifts recall on long-tail queries.',
    agents: [
      { slug: 'search-enrichment-agent', name: 'Search Enrichment', oneLine: 'Enriches the index with synonyms, attribute hints, and intent signals.', costLower: '0.02', costUpper: '0.04', maturity: 'design-partner' },
    ],
  },
  {
    key: 'truth',
    label: 'Truth',
    blurb: 'Provenance, ingestion, human-in-the-loop curation, export, exit-and-portability.',
    agents: [
      { slug: 'truth-enrichment', name: 'Truth Enrichment', oneLine: 'Layers provenance + confidence onto canonical product / customer rows.', costLower: '0.06', costUpper: '0.10', maturity: 'design-partner' },
      { slug: 'truth-export', name: 'Truth Export', oneLine: 'Exports curated rows back to source systems on a configurable cadence.', costLower: '0.02', costUpper: '0.04', maturity: 'design-partner' },
      { slug: 'truth-hitl', name: 'Truth HITL', oneLine: 'Routes low-confidence rows to a human reviewer with full context.', costLower: '0.04', costUpper: '0.08', maturity: 'design-partner' },
      { slug: 'truth-ingestion', name: 'Truth Ingestion', oneLine: 'Ingests source-system rows with provenance and conflict resolution.', costLower: '0.03', costUpper: '0.06', maturity: 'design-partner' },
    ],
  },
];

export const AGENT_CATALOG_AGENTS: readonly AgentCatalogAgent[] = AGENT_CATALOG_DOMAINS.flatMap(
  (domain) => domain.agents,
);

const AGENT_CATALOG_AGENT_BY_SLUG: ReadonlyMap<string, AgentCatalogAgent> = new Map(
  AGENT_CATALOG_AGENTS.map((agent): [string, AgentCatalogAgent] => [agent.slug, agent]),
);

export function getAgentCatalogAgent(slug: string): AgentCatalogAgent | undefined {
  return AGENT_CATALOG_AGENT_BY_SLUG.get(slug);
}