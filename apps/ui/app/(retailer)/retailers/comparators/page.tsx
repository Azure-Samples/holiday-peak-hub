import type { Metadata } from 'next';

import { CallToAction } from '@/components/molecules/CallToAction';
import {
  ComparatorMatrix,
  type ComparatorMatrixCriterion,
  type ComparatorMatrixVendor,
} from '@/components/molecules/ComparatorMatrix';
import { Hero } from '@/components/molecules/Hero';
import { buildMetadata } from '@/lib/seo';

export const metadata: Metadata = buildMetadata({
  section: 'retailer',
  description:
    'Comparator matrix versus point-solution AI vendors (Algolia, Klaviyo, Yotpo, Einstein for Retail, AWS Bedrock + accelerators, Vertex Agent Builder). Every cell carries a verification date.',
  path: '/retailers/comparators',
});

const CRITERIA: ComparatorMatrixCriterion[] = [
  { key: 'open-source', label: 'Open source', hint: 'codebase + license' },
  { key: 'azure-native', label: 'Azure-native', hint: 'first-class on Azure' },
  { key: 'multi-agent', label: 'Multi-agent', hint: 'bounded contexts' },
  { key: 'tenant-deploy', label: 'Deploys on your tenant' },
  { key: 'exit', label: 'Exit & portability' },
  { key: 'cost-controls', label: 'Per-agent cost ceilings' },
];

const HOLIDAY_PEAK_HUB: ComparatorMatrixVendor = {
  key: 'holiday-peak-hub',
  name: 'Holiday Peak Hub',
  positioning: 'Open-source retail agent platform on Azure',
  cells: {
    'open-source': {
      verdict: 'Yes',
      note: 'MIT-licensed; full source on GitHub.',
      verified: '2025-11-04',
      source: 'github.com/Azure-Samples/holiday-peak-hub',
    },
    'azure-native': {
      verdict: 'Yes',
      note: 'Bicep-defined infra; AGC blue-green; AKS + Cosmos + Foundry.',
      verified: '2025-11-04',
    },
    'multi-agent': {
      verdict: 'Yes',
      note: '26 agents across 7 bounded contexts; MCP-only A2A.',
      verified: '2025-11-04',
    },
    'tenant-deploy': {
      verdict: 'Yes',
      note: 'Deploy script + Bicep onto your subscription.',
      verified: '2025-11-04',
    },
    exit: {
      verdict: 'Yes',
      note: 'Truth-export agent + zero proprietary data formats.',
      verified: '2025-11-04',
    },
    'cost-controls': {
      verdict: 'Yes',
      note: 'Per-agent daily caps; SLM-first routing.',
      verified: '2025-11-04',
    },
  },
};

const VENDORS: ComparatorMatrixVendor[] = [
  HOLIDAY_PEAK_HUB,
  {
    key: 'algolia',
    name: 'Algolia',
    positioning: 'Hosted search + browse',
    cells: {
      'open-source': { verdict: 'No', verified: '2025-11-04', source: 'algolia.com/pricing' },
      'azure-native': { verdict: 'No', note: 'AWS-hosted SaaS.', verified: '2025-11-04' },
      'multi-agent': { verdict: 'No', note: 'Search-only point solution.', verified: '2025-11-04' },
      'tenant-deploy': { verdict: 'No', verified: '2025-11-04' },
      exit: { verdict: 'Partial', note: 'Index export available; reranking models proprietary.', verified: '2025-11-04' },
      'cost-controls': { verdict: 'Partial', note: 'Per-search rate limits; no SLM/LLM tiering.', verified: '2025-11-04' },
    },
  },
  {
    key: 'klaviyo',
    name: 'Klaviyo',
    positioning: 'Marketing automation + AI segmentation',
    cells: {
      'open-source': { verdict: 'No', verified: '2025-11-04' },
      'azure-native': { verdict: 'No', note: 'AWS-hosted SaaS.', verified: '2025-11-04' },
      'multi-agent': { verdict: 'Partial', note: 'Marketing + segmentation only; not retail-wide.', verified: '2025-11-04' },
      'tenant-deploy': { verdict: 'No', verified: '2025-11-04' },
      exit: { verdict: 'Partial', note: 'Segment + audience export; AI models proprietary.', verified: '2025-11-04' },
      'cost-controls': { verdict: 'Partial', note: 'Tiered pricing; no per-decision visibility.', verified: '2025-11-04' },
    },
  },
  {
    key: 'yotpo',
    name: 'Yotpo',
    positioning: 'Reviews + loyalty + SMS',
    cells: {
      'open-source': { verdict: 'No', verified: '2025-11-04' },
      'azure-native': { verdict: 'No', verified: '2025-11-04' },
      'multi-agent': { verdict: 'No', note: 'Customer-comms point solution.', verified: '2025-11-04' },
      'tenant-deploy': { verdict: 'No', verified: '2025-11-04' },
      exit: { verdict: 'Partial', note: 'Review + loyalty data exportable.', verified: '2025-11-04' },
      'cost-controls': { verdict: 'Partial', verified: '2025-11-04' },
    },
  },
  {
    key: 'einstein-retail',
    name: 'Einstein for Retail',
    positioning: 'Salesforce AI for Commerce Cloud',
    cells: {
      'open-source': { verdict: 'No', verified: '2025-11-04' },
      'azure-native': { verdict: 'No', note: 'Salesforce-hosted; AWS infra.', verified: '2025-11-04' },
      'multi-agent': { verdict: 'Partial', note: 'Bound to Commerce Cloud objects only.', verified: '2025-11-04' },
      'tenant-deploy': { verdict: 'No', note: 'SaaS within Salesforce org.', verified: '2025-11-04' },
      exit: { verdict: 'No', note: 'Models proprietary; data lock-in to Commerce Cloud.', verified: '2025-11-04' },
      'cost-controls': { verdict: 'Partial', note: 'Einstein request-based pricing.', verified: '2025-11-04' },
    },
  },
  {
    key: 'aws-bedrock',
    name: 'AWS Bedrock + accelerators',
    positioning: 'Foundation-model hosting + retail accelerators',
    cells: {
      'open-source': { verdict: 'Partial', note: 'Accelerator code OSS; underlying models proprietary.', verified: '2025-11-04' },
      'azure-native': { verdict: 'No', note: 'AWS-only.', verified: '2025-11-04' },
      'multi-agent': { verdict: 'Partial', note: 'Bedrock Agents available; retail-context wiring is your job.', verified: '2025-11-04' },
      'tenant-deploy': { verdict: 'Partial', note: 'In your AWS account, not on-prem / on Azure.', verified: '2025-11-04' },
      exit: { verdict: 'Partial', note: 'Knowledge bases exportable; agent definitions AWS-specific.', verified: '2025-11-04' },
      'cost-controls': { verdict: 'Partial', note: 'Token-based pricing; no per-agent ceilings out of the box.', verified: '2025-11-04' },
    },
  },
  {
    key: 'vertex-agent-builder',
    name: 'Vertex Agent Builder',
    positioning: 'Google Cloud agent platform',
    cells: {
      'open-source': { verdict: 'No', verified: '2025-11-04' },
      'azure-native': { verdict: 'No', note: 'Google Cloud only.', verified: '2025-11-04' },
      'multi-agent': { verdict: 'Partial', note: 'Agent Builder + Gemini; retail-domain wiring not included.', verified: '2025-11-04' },
      'tenant-deploy': { verdict: 'Partial', note: 'In your GCP project; not portable.', verified: '2025-11-04' },
      exit: { verdict: 'Partial', note: 'Agent definitions GCP-specific.', verified: '2025-11-04' },
      'cost-controls': { verdict: 'Partial', verified: '2025-11-04' },
    },
  },
];

/**
 * `/retailers/comparators` — comparator matrix vs. point-solution AI vendors (Issue #1043).
 *
 * Hard rules from Epic #1046:
 *   - Comparator set is point-solution AI vendors, NOT full commerce platforms
 *     (comparing to Salesforce / Shopify / SAP is a category error).
 *   - Every cell carries verification date and source where applicable.
 *   - Quarterly refresh cadence; "Last verified" badge per cell.
 */
export default function RetailerComparatorsPage() {
  return (
    <>
      <Hero
        kind="audience-page"
        headline="Why us, not them?"
        sub="Six point-solution AI vendors lined up against the platform on six criteria. Every cell carries the date it was verified."
        primaryCta={{ label: 'Read the methodology', href: '/docs/methodology/retailer-roi' }}
        secondaryCta={{ label: 'Run the ROI calculator', href: '/retailers/roi' }}
        testId="retailer-comparators-hero"
      />
      <ComparatorMatrix
        testId="retailer-comparators-matrix"
        headline="Capability comparison — point-solution AI vendors"
        description="Quarterly refresh; cells reflect public-domain documentation as of the verification date."
        criteria={CRITERIA}
        vendors={VENDORS}
        maturity="design-partner"
        scopeNote="Scope intentionally excludes full commerce platforms (Salesforce Commerce Cloud, Shopify, SAP CAR). Comparing this platform to commerce platforms is a category error — they are not in the same product category."
      />
      <CallToAction
        tone="audience-pair"
        headline="Want to verify a cell?"
        primary={{ label: 'See how the math works', href: '/docs/methodology/retailer-roi' }}
        secondary={{ label: 'Browse the agent catalog', href: '/retailers/agents' }}
        testId="retailer-comparators-cta-pair"
      />
    </>
  );
}
