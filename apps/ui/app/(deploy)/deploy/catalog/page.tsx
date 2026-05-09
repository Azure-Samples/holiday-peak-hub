import type { Metadata } from 'next';

import { AgentPicker } from '@/components/molecules/AgentPicker';
import { CallToAction } from '@/components/molecules/CallToAction';
import { DeployPreviewBanner } from '@/components/molecules/DeployPreviewBanner';
import { Hero } from '@/components/molecules/Hero';
import { buildMetadata } from '@/lib/seo';

export const metadata: Metadata = buildMetadata({
  section: 'deploy',
  description:
    'Pick the agents you want to deploy. Live cost band per agent. No GitHub account required to launch.',
  path: '/deploy/catalog',
});

const DOMAINS = [
  {
    key: 'crm',
    label: 'Customer relationship — CRM (4 agents)',
    agents: [
      { slug: 'crm-campaign-intelligence', name: 'Campaign intelligence', oneLine: 'Build, test, and revise email/SMS campaigns from segment definitions.', costLower: '0.18', costUpper: '0.26', maturity: 'design-partner' as const },
      { slug: 'crm-profile-aggregation', name: 'Profile aggregation', oneLine: 'Roll up customer profile signals across CRM, e-commerce, and support.', costLower: '0.10', costUpper: '0.16', maturity: 'design-partner' as const },
      { slug: 'crm-segmentation-personalization', name: 'Segmentation & personalization', oneLine: 'Compute segments and per-customer personalization tokens.', costLower: '0.18', costUpper: '0.28', maturity: 'design-partner' as const },
      { slug: 'crm-support-assistance', name: 'Support assistance', oneLine: 'Drafts to Tier-1 / Tier-2 reps with policy-citation guardrails.', costLower: '0.22', costUpper: '0.34', maturity: 'preview' as const },
    ],
  },
  {
    key: 'ecommerce',
    label: 'E-commerce (5 agents)',
    agents: [
      { slug: 'ecommerce-cart-intelligence', name: 'Cart intelligence', oneLine: 'Bundle suggestions, ETA hints, and abandonment recovery prompts.', costLower: '0.20', costUpper: '0.30', maturity: 'preview' as const },
      { slug: 'ecommerce-catalog-search', name: 'Catalog search', oneLine: 'Semantic search over the product catalog with trust-tier guardrails.', costLower: '0.14', costUpper: '0.22', maturity: 'design-partner' as const },
      { slug: 'ecommerce-checkout-support', name: 'Checkout support', oneLine: 'Drafts and remediations for checkout-time disputes.', costLower: '0.18', costUpper: '0.28', maturity: 'preview' as const },
      { slug: 'ecommerce-order-status', name: 'Order status', oneLine: 'Order status, ETA, and tracking link rolled up across systems.', costLower: '0.12', costUpper: '0.18', maturity: 'design-partner' as const },
      { slug: 'ecommerce-product-detail-enrichment', name: 'Product-detail enrichment', oneLine: 'Augment product detail with synonyms, attributes, and trust signals.', costLower: '0.18', costUpper: '0.26', maturity: 'design-partner' as const },
    ],
  },
  {
    key: 'inventory',
    label: 'Inventory (4 agents)',
    agents: [
      { slug: 'inventory-alerts-triggers', name: 'Alerts & triggers', oneLine: 'Watch inventory levels and surface alert conditions.', costLower: '0.10', costUpper: '0.18', maturity: 'design-partner' as const },
      { slug: 'inventory-health-check', name: 'Health check', oneLine: 'Continuously evaluate inventory health and surface anomalies.', costLower: '0.10', costUpper: '0.16', maturity: 'design-partner' as const },
      { slug: 'inventory-jit-replenishment', name: 'JIT replenishment', oneLine: 'Just-in-time replenishment recommendations.', costLower: '0.20', costUpper: '0.30', maturity: 'preview' as const },
      { slug: 'inventory-reservation-validation', name: 'Reservation validation', oneLine: 'Validate inventory reservations against current stock.', costLower: '0.10', costUpper: '0.18', maturity: 'design-partner' as const },
    ],
  },
  {
    key: 'logistics',
    label: 'Logistics (4 agents)',
    agents: [
      { slug: 'logistics-carrier-selection', name: 'Carrier selection', oneLine: 'Pick the right carrier per order and region.', costLower: '0.14', costUpper: '0.22', maturity: 'design-partner' as const },
      { slug: 'logistics-eta-computation', name: 'ETA computation', oneLine: 'Compute and refine ETA across regions and carriers.', costLower: '0.16', costUpper: '0.26', maturity: 'design-partner' as const },
      { slug: 'logistics-returns-support', name: 'Returns support', oneLine: 'Returns triage with policy citation.', costLower: '0.18', costUpper: '0.28', maturity: 'preview' as const },
      { slug: 'logistics-route-issue-detection', name: 'Route-issue detection', oneLine: 'Detect route exceptions and surface remediations.', costLower: '0.14', costUpper: '0.24', maturity: 'design-partner' as const },
    ],
  },
  {
    key: 'product-management',
    label: 'Product management (4 agents)',
    agents: [
      { slug: 'product-management-acp-transformation', name: 'ACP transformation', oneLine: 'Transform vendor ACP feeds into normalized product records.', costLower: '0.14', costUpper: '0.22', maturity: 'design-partner' as const },
      { slug: 'product-management-assortment-optimization', name: 'Assortment optimization', oneLine: 'Recommend assortment adjustments based on demand signals.', costLower: '0.20', costUpper: '0.30', maturity: 'preview' as const },
      { slug: 'product-management-consistency-validation', name: 'Consistency validation', oneLine: 'Validate product attribute consistency across catalogs.', costLower: '0.12', costUpper: '0.20', maturity: 'design-partner' as const },
      { slug: 'product-management-normalization-classification', name: 'Normalization & classification', oneLine: 'Normalize and classify products against retailer taxonomies.', costLower: '0.18', costUpper: '0.28', maturity: 'design-partner' as const },
    ],
  },
  {
    key: 'search',
    label: 'Search (1 agent)',
    agents: [
      { slug: 'search-enrichment-agent', name: 'Search enrichment', oneLine: 'Enrich search queries with synonyms, intent, and rerank signals.', costLower: '0.16', costUpper: '0.24', maturity: 'design-partner' as const },
    ],
  },
  {
    key: 'truth',
    label: 'Truth (4 agents)',
    agents: [
      { slug: 'truth-enrichment', name: 'Truth enrichment', oneLine: 'Enrich product data with verified sources.', costLower: '0.20', costUpper: '0.30', maturity: 'design-partner' as const },
      { slug: 'truth-export', name: 'Truth export', oneLine: 'Export truth records to downstream systems on demand.', costLower: '0.10', costUpper: '0.16', maturity: 'design-partner' as const },
      { slug: 'truth-hitl', name: 'Truth HITL', oneLine: 'Human-in-the-loop reviewer for truth boundary cases.', costLower: '0.14', costUpper: '0.22', maturity: 'preview' as const },
      { slug: 'truth-ingestion', name: 'Truth ingestion', oneLine: 'Ingest truth signals from authoritative sources.', costLower: '0.12', costUpper: '0.20', maturity: 'design-partner' as const },
    ],
  },
];

/**
 * `/deploy/catalog` — agent picker + cost preview (Issue #1028 / Epic #1039).
 *
 * v1: server-rendered selectable list with per-agent cost band. The actual
 * cost roll-up + Azure Retail Prices live recompute lands with #1038 once
 * the configure flow (#1029) provides region context.
 */
export default function DeployCatalogPage() {
  return (
    <>
      <DeployPreviewBanner testId="deploy-catalog-preview-banner" maturity="preview" />
      <Hero
        kind="audience-page"
        headline="Pick the agents you want to deploy."
        sub="26 agents across 7 domains. Cost bands shown per agent. Final cost depends on region — selected on the next step."
        primaryCta={{ label: 'Continue → Configure', href: '/deploy/configure' }}
        secondaryCta={{ label: 'See cost methodology', href: '/docs/methodology/retailer-roi' }}
        testId="deploy-catalog-hero"
      />
      <AgentPicker
        testId="deploy-catalog-picker"
        headline="Catalog"
        description="All agents are pre-selected; uncheck any you do not want. The cost band assumes design-partner traffic mix; your spend depends on tenant traffic."
        domains={DOMAINS}
      />
      <CallToAction
        tone="single"
        headline="Ready to configure?"
        primary={{ label: 'Configure deployment →', href: '/deploy/configure' }}
        caption="Sign in with the Microsoft Entra tenant that owns the target subscription. No GitHub account required."
        testId="deploy-catalog-cta"
      />
    </>
  );
}
