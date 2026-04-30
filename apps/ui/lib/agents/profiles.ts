export type AgentProfileDomain =
  | 'crm'
  | 'ecommerce'
  | 'inventory'
  | 'logistics'
  | 'product-management'
  | 'search'
  | 'truth-layer';

export type AgentPrimaryMode = 'sync' | 'async';

export type AgentProfileSlug = (typeof ALL_AGENT_SLUGS)[number];

export interface AgentProductivityGain {
  latency: string;
  quality: string;
  cost: string;
  revenueImpact?: string;
}

export interface AgentKpiDefinition {
  id: string;
  label: string;
  why: string;
  target: string;
  source: string;
}

export interface AgentJsonSchema {
  type: 'object';
  description: string;
  required?: string[];
  properties: Record<string, {
    type: string;
    description: string;
  }>;
  additionalProperties?: boolean;
}

export interface AgentProfile {
  slug: AgentProfileSlug;
  displayName: string;
  domain: AgentProfileDomain;
  domainLabel: string;
  primaryMode: AgentPrimaryMode;
  oneLiner: string;
  fitFor: string[];
  retailProblem: string;
  productivityGain: AgentProductivityGain;
  kpisToTrack: AgentKpiDefinition[];
  inputSchema: AgentJsonSchema;
  outputSchema: AgentJsonSchema;
  sampleInput: Record<string, unknown>;
  traceExplorerHref: string;
  collaborates: string[];
  accentColor: string;
}

type AgentProfileOverride = Partial<
  Pick<
  AgentProfile,
  | 'displayName'
  | 'oneLiner'
  | 'fitFor'
  | 'retailProblem'
  | 'productivityGain'
  | 'collaborates'
  >
>;

const ALL_AGENT_SLUGS = [
  'crm-campaign-intelligence',
  'crm-profile-aggregation',
  'crm-segmentation-personalization',
  'crm-support-assistance',
  'ecommerce-catalog-search',
  'ecommerce-cart-intelligence',
  'ecommerce-checkout-support',
  'ecommerce-order-status',
  'ecommerce-product-detail-enrichment',
  'inventory-health-check',
  'inventory-alerts-triggers',
  'inventory-jit-replenishment',
  'inventory-reservation-validation',
  'logistics-carrier-selection',
  'logistics-eta-computation',
  'logistics-returns-support',
  'logistics-route-issue-detection',
  'product-management-acp-transformation',
  'product-management-assortment-optimization',
  'product-management-consistency-validation',
  'product-management-normalization-classification',
  'search-enrichment-agent',
  'truth-ingestion',
  'truth-enrichment',
  'truth-hitl',
  'truth-export',
] as const;

const DOMAIN_GROUPS: Record<AgentProfileDomain, readonly string[]> = {
  crm: [
    'crm-campaign-intelligence',
    'crm-profile-aggregation',
    'crm-segmentation-personalization',
    'crm-support-assistance',
  ],
  ecommerce: [
    'ecommerce-catalog-search',
    'ecommerce-cart-intelligence',
    'ecommerce-checkout-support',
    'ecommerce-order-status',
    'ecommerce-product-detail-enrichment',
  ],
  inventory: [
    'inventory-health-check',
    'inventory-alerts-triggers',
    'inventory-jit-replenishment',
    'inventory-reservation-validation',
  ],
  logistics: [
    'logistics-carrier-selection',
    'logistics-eta-computation',
    'logistics-returns-support',
    'logistics-route-issue-detection',
  ],
  'product-management': [
    'product-management-acp-transformation',
    'product-management-assortment-optimization',
    'product-management-consistency-validation',
    'product-management-normalization-classification',
  ],
  search: ['search-enrichment-agent'],
  'truth-layer': ['truth-ingestion', 'truth-enrichment', 'truth-hitl', 'truth-export'],
};

const TRACE_EXPLORER_HREF_BY_SLUG: Record<AgentProfileSlug, string> = {
  'crm-campaign-intelligence': '/admin/crm/campaigns',
  'crm-profile-aggregation': '/admin/crm/profiles',
  'crm-segmentation-personalization': '/admin/crm/segmentation',
  'crm-support-assistance': '/admin/crm/support',
  'ecommerce-catalog-search': '/admin/ecommerce/catalog',
  'ecommerce-cart-intelligence': '/admin/ecommerce/cart',
  'ecommerce-checkout-support': '/admin/ecommerce/checkout',
  'ecommerce-order-status': '/admin/ecommerce/orders',
  'ecommerce-product-detail-enrichment': '/admin/ecommerce/products',
  'inventory-health-check': '/admin/inventory/health',
  'inventory-alerts-triggers': '/admin/inventory/alerts',
  'inventory-jit-replenishment': '/admin/inventory/replenishment',
  'inventory-reservation-validation': '/admin/inventory/reservation',
  'logistics-carrier-selection': '/admin/logistics/carriers',
  'logistics-eta-computation': '/admin/logistics/eta',
  'logistics-returns-support': '/admin/logistics/returns',
  'logistics-route-issue-detection': '/admin/logistics/routes',
  'product-management-acp-transformation': '/admin/products/acp',
  'product-management-assortment-optimization': '/admin/products/assortment',
  'product-management-consistency-validation': '/admin/products/validation',
  'product-management-normalization-classification': '/admin/products/normalization',
  'search-enrichment-agent': '/admin/ecommerce/catalog',
  'truth-ingestion': '/admin/enrichment-monitor',
  'truth-enrichment': '/admin/truth-analytics',
  'truth-hitl': '/staff/review',
  'truth-export': '/admin/workflows',
};

/**
 * Agent primary mode classification per ADR-024 Part 4.
 * Sync agents serve real-time user-facing requests; async agents process
 * background event-driven workloads.
 */
const PRIMARY_MODE_BY_SLUG: Record<AgentProfileSlug, AgentPrimaryMode> = {
  'crm-campaign-intelligence': 'async',
  'crm-profile-aggregation': 'sync',
  'crm-segmentation-personalization': 'async',
  'crm-support-assistance': 'sync',
  'ecommerce-catalog-search': 'sync',
  'ecommerce-cart-intelligence': 'sync',
  'ecommerce-checkout-support': 'sync',
  'ecommerce-order-status': 'sync',
  'ecommerce-product-detail-enrichment': 'sync',
  'inventory-health-check': 'async',
  'inventory-alerts-triggers': 'async',
  'inventory-jit-replenishment': 'async',
  'inventory-reservation-validation': 'sync',
  'logistics-carrier-selection': 'sync',
  'logistics-eta-computation': 'sync',
  'logistics-returns-support': 'sync',
  'logistics-route-issue-detection': 'async',
  'product-management-acp-transformation': 'async',
  'product-management-assortment-optimization': 'async',
  'product-management-consistency-validation': 'async',
  'product-management-normalization-classification': 'async',
  'search-enrichment-agent': 'async',
  'truth-ingestion': 'async',
  'truth-enrichment': 'async',
  'truth-hitl': 'async',
  'truth-export': 'async',
};

type DomainPreset = Pick<
  AgentProfile,
  'domain' | 'domainLabel' | 'fitFor' | 'retailProblem' | 'productivityGain' | 'kpisToTrack' | 'accentColor'
>;

const DOMAIN_PRESETS: Record<AgentProfileDomain, DomainPreset> = {
  crm: {
    domain: 'crm',
    domainLabel: 'CRM Concierge Desk',
    fitFor: [
      'Customer 360 personalization',
      'Campaign orchestration',
      'Support triage and retention',
    ],
    retailProblem:
      'Customer signals are fragmented across profiles, segments, support queues, and campaign systems.',
    productivityGain: {
      latency: '1.4 s to compose a profile brief',
      quality: 'Unified customer view with live cohort, funnel, and risk context',
      cost: '$0.003 per assembled briefing',
      revenueImpact: 'Faster personalization and better service recovery',
    },
    kpisToTrack: [
      {
        id: 'outcome-kpi',
        label: 'Personalization conversion lift',
        why: 'Measures whether coordinated customer context turns into revenue, not just nicer copy.',
        target: '>12% lift',
        source: 'customer-360.outcome',
      },
      {
        id: 'quality-kpi',
        label: 'Profile merge confidence',
        why: 'Signals whether identity stitching is precise enough to trust downstream automation.',
        target: '>0.90',
        source: 'customer-360.quality',
      },
      {
        id: 'ops-kpi',
        label: 'Briefing p95 latency',
        why: 'Executives care about how quickly the system can support a live customer decision.',
        target: '<2.0 s',
        source: 'agent-monitor.latency',
      },
      {
        id: 'adoption-kpi',
        label: 'Distinct teams using the brief',
        why: 'Cross-functional usage is the signal that the orchestration is becoming operationally real.',
        target: '>4 teams',
        source: 'agent-monitor.adoption',
      },
    ],
    accentColor: '#8b5cf6',
  },
  ecommerce: {
    domain: 'ecommerce',
    domainLabel: 'Storefront Operations',
    fitFor: [
      'Product discovery and search',
      'Cart recovery and checkout',
      'Order transparency and conversion',
    ],
    retailProblem:
      'Shoppers drop when relevance, confidence, or checkout validation is slow or inconsistent.',
    productivityGain: {
      latency: '<1.2 s p95 customer response',
      quality: '+35% search-to-product CTR',
      cost: '$0.0007 to $0.004 per customer turn',
      revenueImpact: '+8-12% AOV and lower abandonment',
    },
    kpisToTrack: [
      {
        id: 'outcome-kpi',
        label: 'Search-to-product CTR',
        why: 'Shows whether discovery guidance actually moves shoppers toward product detail intent.',
        target: '>35%',
        source: 'commerce.discovery',
      },
      {
        id: 'quality-kpi',
        label: 'Guidance acceptance rate',
        why: 'Tracks whether recommendations and explanations are convincing enough to act on.',
        target: '>55%',
        source: 'commerce.quality',
      },
      {
        id: 'ops-kpi',
        label: 'Experience p95 latency',
        why: 'Retail interactions need to feel instantaneous on the critical path to checkout.',
        target: '<1.5 s',
        source: 'agent-monitor.latency',
      },
      {
        id: 'adoption-kpi',
        label: 'Assisted journeys per hour',
        why: 'Volume tells you if the agent layer is materially participating in the shopping flow.',
        target: '>150 / h',
        source: 'agent-monitor.throughput',
      },
    ],
    accentColor: '#f07858',
  },
  inventory: {
    domain: 'inventory',
    domainLabel: 'Back-of-House Operations',
    fitFor: [
      'Stock health monitoring',
      'Anomaly detection and replenishment',
      'Reservation assurance',
    ],
    retailProblem:
      'Teams react too late to demand spikes, low stock, and reservation failures during peak periods.',
    productivityGain: {
      latency: '<5 min from signal to recommendation',
      quality: '-70% stockouts on priority SKUs',
      cost: '$0.02 per remediation decision',
      revenueImpact: '+10% working-capital efficiency',
    },
    kpisToTrack: [
      {
        id: 'outcome-kpi',
        label: 'Stockout rate on priority SKUs',
        why: 'This is the business outcome leadership actually feels during peak demand.',
        target: '<2%',
        source: 'inventory.outcome',
      },
      {
        id: 'quality-kpi',
        label: 'Alert precision',
        why: 'Too many false alerts destroy trust in the replenishment loop.',
        target: '>85%',
        source: 'inventory.quality',
      },
      {
        id: 'ops-kpi',
        label: 'Signal-to-action latency',
        why: 'Peak operations depend on how fast a detected issue becomes an action.',
        target: '<5 min',
        source: 'inventory.ops',
      },
      {
        id: 'adoption-kpi',
        label: 'Automated remediation coverage',
        why: 'Coverage indicates whether the system is reducing manual supervision.',
        target: '>60%',
        source: 'inventory.adoption',
      },
    ],
    accentColor: '#14b8a6',
  },
  logistics: {
    domain: 'logistics',
    domainLabel: 'Shipping Desk',
    fitFor: [
      'ETA prediction',
      'Route issue detection',
      'Returns automation and carrier selection',
    ],
    retailProblem:
      'Customers and operators lose confidence when deliveries slip, routes change, or returns are opaque.',
    productivityGain: {
      latency: 'Live ETA recomputation in under 2 s',
      quality: '>92% ETA accuracy and 60-80% automated return resolution',
      cost: '8-15% carrier savings and lower cost per ticket',
      revenueImpact: 'Fewer WISMO tickets and better post-purchase trust',
    },
    kpisToTrack: [
      {
        id: 'outcome-kpi',
        label: 'ETA accuracy',
        why: 'Reliable promise dates reduce service load and improve confidence in the brand.',
        target: '>92%',
        source: 'logistics.outcome',
      },
      {
        id: 'quality-kpi',
        label: 'Return eligibility precision',
        why: 'Eligibility mistakes become customer frustration or margin leakage.',
        target: '>90%',
        source: 'logistics.quality',
      },
      {
        id: 'ops-kpi',
        label: 'Resolution turnaround',
        why: 'A logistics agent must keep pace with live route changes and support requests.',
        target: '<10 min',
        source: 'logistics.ops',
      },
      {
        id: 'adoption-kpi',
        label: 'Automated shipment interventions',
        why: 'Tells you whether the control tower is actually handling live operations.',
        target: '>50 / day',
        source: 'logistics.adoption',
      },
    ],
    accentColor: '#10b981',
  },
  'product-management': {
    domain: 'product-management',
    domainLabel: 'Merchandising Studio',
    fitFor: [
      'Normalization and classification',
      'Consistency validation',
      'Assortment optimization and ACP transformation',
    ],
    retailProblem:
      'Merch teams spend too much time repairing inconsistent product structure before they can optimize assortment.',
    productivityGain: {
      latency: 'Structured product decisioning in seconds',
      quality: '>98% schema readiness for downstream search and truth workflows',
      cost: '$0.04 per product decision',
      revenueImpact: 'Faster launch readiness for new catalog drops',
    },
    kpisToTrack: [
      {
        id: 'outcome-kpi',
        label: 'Launch-ready assortment coverage',
        why: 'Measures how much of the catalog is actually publishable on time.',
        target: '>95%',
        source: 'merch.outcome',
      },
      {
        id: 'quality-kpi',
        label: 'Schema and classification accuracy',
        why: 'Poor structure bleeds into search quality, truth layer quality, and reporting.',
        target: '>0.92',
        source: 'merch.quality',
      },
      {
        id: 'ops-kpi',
        label: 'Review queue latency',
        why: 'Merch teams need to know whether ambiguous cases are piling up.',
        target: '<15 min',
        source: 'merch.ops',
      },
      {
        id: 'adoption-kpi',
        label: 'Automated product transformations',
        why: 'The signal that data prep is shifting from manual effort to governed automation.',
        target: '>500 / day',
        source: 'merch.adoption',
      },
    ],
    accentColor: '#ec4899',
  },
  search: {
    domain: 'search',
    domainLabel: 'Relevance Amplifier',
    fitFor: ['Search enrichment', 'Semantic retrieval', 'Cross-agent discovery narratives'],
    retailProblem:
      'Structured search results alone rarely explain why a shopper should trust or act on a result.',
    productivityGain: {
      latency: 'Streams in the same turn as discovery',
      quality: 'Higher answer richness without sacrificing relevance',
      cost: '$0.001 to enrich a turn',
      revenueImpact: 'More confident discovery sessions',
    },
    kpisToTrack: [
      {
        id: 'outcome-kpi',
        label: 'Enriched-answer engagement',
        why: 'Shows whether added context is valuable enough to earn more interaction.',
        target: '>40%',
        source: 'search.outcome',
      },
      {
        id: 'quality-kpi',
        label: 'Relevant facet precision',
        why: 'Facet and explanation quality determine whether search feels guided or noisy.',
        target: '>0.9',
        source: 'search.quality',
      },
      {
        id: 'ops-kpi',
        label: 'Incremental latency overhead',
        why: 'Extra intelligence must not destroy the speed advantage of search.',
        target: '<300 ms',
        source: 'search.ops',
      },
      {
        id: 'adoption-kpi',
        label: 'Enriched turns per session',
        why: 'Tracks whether the enrichment layer keeps getting used within the same journey.',
        target: '>2.5',
        source: 'search.adoption',
      },
    ],
    accentColor: '#f97316',
  },
  'truth-layer': {
    domain: 'truth-layer',
    domainLabel: 'Product Truth Layer',
    fitFor: [
      'Catalog onboarding',
      'Schema-governed enrichment',
      'Human-in-the-loop review and export',
    ],
    retailProblem:
      'Catalog readiness breaks when raw product data arrives incomplete, inconsistent, and without review context.',
    productivityGain: {
      latency: '<30 min end-to-end onboarding cycle',
      quality: '>98% data quality with <20% manual review rate',
      cost: '$0.04 per product through the pipeline',
      revenueImpact: 'Faster channel activation and fewer bad publishes',
    },
    kpisToTrack: [
      {
        id: 'outcome-kpi',
        label: 'Catalog completeness',
        why: 'Executives want to know how much of the catalog is actually ready to sell.',
        target: '>98%',
        source: 'truth.summary',
      },
      {
        id: 'quality-kpi',
        label: 'HITL approval rate',
        why: 'Approval rate is the fastest signal of trust drift in the pipeline.',
        target: '>80%',
        source: 'truth.quality',
      },
      {
        id: 'ops-kpi',
        label: 'Pipeline throughput',
        why: 'Peak catalog operations need a visible measure of whether work is flowing.',
        target: '>100 items / 10m',
        source: 'truth.ops',
      },
      {
        id: 'adoption-kpi',
        label: 'Auto-approved share',
        why: 'Shows whether teams are earning back manual time while maintaining guardrails.',
        target: '>70%',
        source: 'truth.adoption',
      },
    ],
    accentColor: '#6366f1',
  },
};

const OVERRIDES: Partial<Record<(typeof ALL_AGENT_SLUGS)[number], AgentProfileOverride>> = {
  'crm-campaign-intelligence': {
    displayName: 'CRM Campaign Intelligence',
    oneLiner: 'Turns live customer context into a campaign action plan with measurable uplift hypotheses.',
  },
  'crm-profile-aggregation': {
    displayName: 'CRM Profile Aggregation',
    oneLiner: 'Builds the identity spine for every downstream customer-facing decision.',
    collaborates: ['crm-segmentation-personalization', 'crm-support-assistance', 'crm-campaign-intelligence'],
  },
  'crm-segmentation-personalization': {
    displayName: 'CRM Segmentation & Personalization',
    oneLiner: 'Maps customers into actionable cohorts and turns those cohorts into next-best experiences.',
  },
  'crm-support-assistance': {
    displayName: 'CRM Support Assistance',
    oneLiner: 'Compresses ticket history, customer context, and policy into a faster first response.',
  },
  'ecommerce-catalog-search': {
    displayName: 'eCommerce Catalog Search',
    oneLiner: 'Makes the storefront queryable in natural language while keeping deterministic product grounding.',
    fitFor: ['Executive demo hero', 'Product discovery and enrichment', 'Search-led commerce journeys'],
    productivityGain: {
      latency: '1.18 s p95 search answer',
      quality: '+35% search-to-product CTR',
      cost: '$0.0007 per assisted search',
      revenueImpact: 'More qualified product views per session',
    },
  },
  'ecommerce-cart-intelligence': {
    displayName: 'eCommerce Cart Intelligence',
    oneLiner: 'Scores abandonment risk early enough to change the cart before the shopper leaves.',
  },
  'ecommerce-checkout-support': {
    displayName: 'eCommerce Checkout Support',
    oneLiner: 'Validates payment, address, and fulfillment friction before checkout becomes support debt.',
  },
  'ecommerce-order-status': {
    displayName: 'eCommerce Order Status',
    oneLiner: 'Translates operational state into plain-language order certainty for customers and staff.',
  },
  'ecommerce-product-detail-enrichment': {
    displayName: 'eCommerce Product Detail Enrichment',
    oneLiner: 'Turns thin product content into guided storytelling that can still survive a factual audit.',
  },
  'inventory-health-check': {
    displayName: 'Inventory Health Check',
    oneLiner: 'Surfaces the first signs of stock risk before they become broken promises.',
  },
  'inventory-alerts-triggers': {
    displayName: 'Inventory Alerts & Triggers',
    oneLiner: 'Escalates the right inventory anomalies without turning every fluctuation into noise.',
  },
  'inventory-jit-replenishment': {
    displayName: 'Inventory JIT Replenishment',
    oneLiner: 'Converts a risk signal into a justified replenishment action with lead-time context.',
  },
  'inventory-reservation-validation': {
    displayName: 'Inventory Reservation Validation',
    oneLiner: 'Keeps promised inventory honest when multiple channels compete for the same unit.',
  },
  'logistics-carrier-selection': {
    displayName: 'Logistics Carrier Selection',
    oneLiner: 'Balances cost, service level, and disruption risk before a label is printed.',
  },
  'logistics-eta-computation': {
    displayName: 'Logistics ETA Computation',
    oneLiner: 'Recomputes delivery confidence as conditions change instead of treating ETA as static.',
  },
  'logistics-returns-support': {
    displayName: 'Logistics Returns Support',
    oneLiner: 'Guides return eligibility and resolution paths without forcing a handoff maze.',
  },
  'logistics-route-issue-detection': {
    displayName: 'Logistics Route Issue Detection',
    oneLiner: 'Finds the route disruptions that actually matter before customers ask where their order is.',
  },
  'product-management-acp-transformation': {
    displayName: 'Product Management ACP Transformation',
    oneLiner: 'Publishes structured assortment context in the shape downstream channels can actually use.',
  },
  'product-management-assortment-optimization': {
    displayName: 'Product Management Assortment Optimization',
    oneLiner: 'Highlights assortment gaps and overlap before the merch team wastes a launch window.',
  },
  'product-management-consistency-validation': {
    displayName: 'Product Management Consistency Validation',
    oneLiner: 'Checks whether product truth stays consistent across categories, channels, and governance rules.',
  },
  'product-management-normalization-classification': {
    displayName: 'Product Management Normalization & Classification',
    oneLiner: 'Normalizes raw supplier variation into a taxonomy that search, truth, and merch can share.',
  },
  'search-enrichment-agent': {
    displayName: 'Search Enrichment Agent',
    oneLiner: 'Adds narrative, facets, and semantic lift to a storefront query without losing grounding.',
    collaborates: ['ecommerce-catalog-search', 'truth-enrichment', 'ecommerce-product-detail-enrichment'],
  },
  'truth-ingestion': {
    displayName: 'Truth Ingestion',
    oneLiner: 'Admits raw catalog payloads into the truth layer with traceable provenance from the first step.',
  },
  'truth-enrichment': {
    displayName: 'Truth Enrichment',
    oneLiner: 'Fills critical product gaps fast enough that onboarding becomes a pipeline, not a project.',
    productivityGain: {
      latency: '<10 s for a product enrichment turn',
      quality: '98%+ gap-fill coverage on curated fields',
      cost: '$0.04 per product',
      revenueImpact: 'Faster publish readiness for new assortment',
    },
    collaborates: ['truth-ingestion', 'truth-hitl', 'truth-export', 'search-enrichment-agent'],
  },
  'truth-hitl': {
    displayName: 'Truth HITL Review',
    oneLiner: 'Keeps ambiguous product decisions reviewable so automation can scale without going blind.',
  },
  'truth-export': {
    displayName: 'Truth Export',
    oneLiner: 'Packages approved truth into ACP and UCP outputs that downstream systems can trust.',
  },
};

function inferDomain(slug: string): AgentProfileDomain {
  if (slug.startsWith('crm-')) return 'crm';
  if (slug.startsWith('ecommerce-')) return 'ecommerce';
  if (slug.startsWith('inventory-')) return 'inventory';
  if (slug.startsWith('logistics-')) return 'logistics';
  if (slug.startsWith('product-management-')) return 'product-management';
  if (slug.startsWith('truth-')) return 'truth-layer';
  return 'search';
}

function prettifySlug(slug: string): string {
  return slug
    .split('-')
    .map((part) => {
      if (part === 'crm') return 'CRM';
      if (part === 'hitl') return 'HITL';
      if (part === 'jit') return 'JIT';
      if (part === 'eta') return 'ETA';
      if (part === 'acp') return 'ACP';
      return `${part.slice(0, 1).toUpperCase()}${part.slice(1)}`;
    })
    .join(' ');
}

function defaultCollaborators(slug: string, domain: AgentProfileDomain): string[] {
  const domainPeers = DOMAIN_GROUPS[domain].filter((candidate) => candidate !== slug);
  if (domain === 'search') {
    return ['ecommerce-catalog-search', 'truth-enrichment', 'ecommerce-product-detail-enrichment'];
  }
  if (domain === 'truth-layer') {
    return ['truth-ingestion', 'truth-enrichment', 'truth-hitl', 'truth-export'].filter(
      (candidate) => candidate !== slug,
    );
  }
  return domainPeers.slice(0, 3);
}

function buildSchema(
  description: string,
  properties: AgentJsonSchema['properties'],
  required: string[] = [],
): AgentJsonSchema {
  return {
    type: 'object',
    description,
    properties,
    required,
    additionalProperties: false,
  };
}

function buildInputSchema(slug: AgentProfileSlug, domain: AgentProfileDomain): AgentJsonSchema {
  if (slug === 'crm-campaign-intelligence') {
    return buildSchema(
      'Campaign intelligence request for audience and offer planning.',
      {
        audience_id: { type: 'string', description: 'Audience or cohort identifier.' },
        goal: { type: 'string', description: 'Commercial objective for the campaign.' },
        prompt: { type: 'string', description: 'Operator guidance for campaign generation.' },
      },
      ['audience_id', 'prompt'],
    );
  }

  if (slug === 'ecommerce-catalog-search' || slug === 'search-enrichment-agent') {
    return buildSchema(
      'Catalog discovery request.',
      {
        query: { type: 'string', description: 'Customer search phrase.' },
        category: { type: 'string', description: 'Optional category constraint.' },
        mode: { type: 'string', description: 'Search mode such as intelligent or keyword.' },
      },
      ['query'],
    );
  }

  if (slug === 'ecommerce-cart-intelligence' || slug === 'ecommerce-checkout-support') {
    return buildSchema(
      'Cart or checkout assistance request.',
      {
        cart_id: { type: 'string', description: 'Cart identifier.' },
        customer_id: { type: 'string', description: 'Customer identifier.' },
        prompt: { type: 'string', description: 'Operator or shopper request.' },
      },
      ['cart_id', 'prompt'],
    );
  }

  if (slug === 'ecommerce-order-status' || domain === 'logistics') {
    return buildSchema(
      'Order or shipment tracking request.',
      {
        order_id: { type: 'string', description: 'Order identifier.' },
        tracking_id: { type: 'string', description: 'Tracking number for the shipment.' },
        prompt: { type: 'string', description: 'Question about the order lifecycle.' },
      },
      ['prompt'],
    );
  }

  if (domain === 'inventory') {
    return buildSchema(
      'Inventory request for stock, reservations, or replenishment.',
      {
        sku: { type: 'string', description: 'Product SKU.' },
        request_qty: { type: 'number', description: 'Requested quantity.' },
        location_id: { type: 'string', description: 'Fulfillment location identifier.' },
        prompt: { type: 'string', description: 'Operator context for the decision.' },
      },
      ['sku', 'prompt'],
    );
  }

  if (domain === 'crm') {
    return buildSchema(
      'Customer or contact intelligence request.',
      {
        customer_id: { type: 'string', description: 'Primary customer identifier.' },
        contact_id: { type: 'string', description: 'Optional contact identifier.' },
        prompt: { type: 'string', description: 'Question about profile, support, or segmentation.' },
      },
      ['prompt'],
    );
  }

  if (domain === 'product-management' || slug.startsWith('truth-')) {
    return buildSchema(
      'Product truth or merchandising request.',
      {
        product_id: { type: 'string', description: 'Product identifier.' },
        product_record: { type: 'object', description: 'Raw or partially enriched product payload.' },
        prompt: { type: 'string', description: 'Operator instruction for enrichment, validation, or export.' },
      },
      ['prompt'],
    );
  }

  return buildSchema(
    'Generic agent request.',
    {
      prompt: { type: 'string', description: 'Natural-language instruction for the agent.' },
    },
    ['prompt'],
  );
}

function buildOutputSchema(slug: AgentProfileSlug, domain: AgentProfileDomain): AgentJsonSchema {
  if (slug === 'ecommerce-catalog-search' || slug === 'search-enrichment-agent') {
    return buildSchema(
      'Ranked discovery response.',
      {
        summary: { type: 'string', description: 'Natural-language overview of the result set.' },
        products: { type: 'array', description: 'Ranked product matches.' },
        rationale: { type: 'array', description: 'Reasons products were selected.' },
      },
      ['summary'],
    );
  }

  if (slug === 'ecommerce-order-status' || domain === 'logistics') {
    return buildSchema(
      'Shipment or order outcome.',
      {
        summary: { type: 'string', description: 'Order or shipment summary.' },
        status: { type: 'string', description: 'Current order or shipment state.' },
        eta: { type: 'string', description: 'Projected delivery time.' },
      },
      ['summary'],
    );
  }

  if (domain === 'inventory') {
    return buildSchema(
      'Inventory response with risk and recommendation.',
      {
        summary: { type: 'string', description: 'Inventory assessment summary.' },
        available_qty: { type: 'number', description: 'Available quantity for the SKU.' },
        recommended_action: { type: 'string', description: 'Suggested stock action.' },
      },
      ['summary'],
    );
  }

  if (domain === 'crm') {
    return buildSchema(
      'Customer intelligence summary.',
      {
        summary: { type: 'string', description: 'Customer or cohort briefing.' },
        risk_level: { type: 'string', description: 'Customer risk or opportunity level.' },
        next_best_action: { type: 'string', description: 'Recommended next action.' },
      },
      ['summary'],
    );
  }

  if (domain === 'product-management' || slug.startsWith('truth-')) {
    return buildSchema(
      'Product truth response.',
      {
        summary: { type: 'string', description: 'Product truth or merchandising summary.' },
        enriched_attributes: { type: 'array', description: 'Attributes created or validated.' },
        confidence: { type: 'number', description: 'Overall confidence for the outcome.' },
      },
      ['summary'],
    );
  }

  return buildSchema(
    'Generic response contract.',
    {
      summary: { type: 'string', description: 'Operator-facing summary of the result.' },
      status: { type: 'string', description: 'Outcome status.' },
    },
    ['summary'],
  );
}

function buildSampleInput(slug: AgentProfileSlug, domain: AgentProfileDomain): Record<string, unknown> {
  if (slug === 'crm-campaign-intelligence') {
    return {
      audience_id: 'high-value-loyalists',
      goal: 'boost holiday bundle conversion',
      prompt: 'Recommend the campaign angle and offer for this cohort.',
    };
  }

  if (slug === 'ecommerce-catalog-search' || slug === 'search-enrichment-agent') {
    return {
      query: 'waterproof hiking boots',
      category: 'footwear',
      mode: 'intelligent',
    };
  }

  if (slug === 'ecommerce-cart-intelligence') {
    return {
      cart_id: 'cart-2048',
      customer_id: 'customer-100',
      prompt: 'Suggest the best bundle and explain the tradeoff.',
    };
  }

  if (slug === 'ecommerce-checkout-support') {
    return {
      cart_id: 'cart-2048',
      customer_id: 'customer-100',
      prompt: 'Summarize the checkout blockers and next best action.',
    };
  }

  if (slug === 'ecommerce-order-status' || domain === 'logistics') {
    return {
      order_id: 'ORD-2026-0123',
      tracking_id: 'TRK-00098765',
      prompt: 'Explain the latest order status and any risk to the ETA.',
    };
  }

  if (domain === 'inventory') {
    return {
      sku: 'SKU-TRAIL-2048',
      request_qty: 2,
      location_id: 'wh-sea-01',
      prompt: 'Can we fulfill this request today, and if not, what is the mitigation?',
    };
  }

  if (domain === 'crm') {
    return {
      customer_id: 'customer-100',
      prompt: 'Give me the customer brief and the next best action.',
    };
  }

  if (domain === 'product-management' || slug.startsWith('truth-')) {
    return {
      product_id: 'prod-hike-2048',
      product_record: {
        title: 'Alpine Ridge Trail Boot',
        color: 'graphite',
        category: 'boots',
      },
      prompt: 'Enrich this product and identify the highest-priority gaps.',
    };
  }

  return {
    prompt: `Summarize the current ${prettifySlug(slug)} task and recommended next action.`,
  };
}

function buildProfile(slug: (typeof ALL_AGENT_SLUGS)[number]): AgentProfile {
  const domain = inferDomain(slug);
  const preset = DOMAIN_PRESETS[domain];
  const override = OVERRIDES[slug];

  return {
    slug,
    domain,
    domainLabel: preset.domainLabel,
    primaryMode: PRIMARY_MODE_BY_SLUG[slug],
    displayName: override?.displayName ?? prettifySlug(slug),
    oneLiner:
      override?.oneLiner ??
      `${prettifySlug(slug)} operationalizes ${preset.domainLabel.toLowerCase()} decisions with traceable AI support.`,
    fitFor: override?.fitFor ?? preset.fitFor,
    retailProblem: override?.retailProblem ?? preset.retailProblem,
    productivityGain: override?.productivityGain ?? preset.productivityGain,
    kpisToTrack: preset.kpisToTrack,
    inputSchema: buildInputSchema(slug, domain),
    outputSchema: buildOutputSchema(slug, domain),
    sampleInput: buildSampleInput(slug, domain),
    traceExplorerHref: TRACE_EXPLORER_HREF_BY_SLUG[slug],
    collaborates: override?.collaborates ?? defaultCollaborators(slug, domain),
    accentColor: preset.accentColor,
  };
}

export const AGENT_PROFILES = Object.fromEntries(
  ALL_AGENT_SLUGS.map((slug) => [slug, buildProfile(slug)]),
) as Record<AgentProfileSlug, AgentProfile>;

export const AGENT_PROFILE_LIST = ALL_AGENT_SLUGS.map((slug) => AGENT_PROFILES[slug]);