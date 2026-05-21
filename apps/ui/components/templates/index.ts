/**
 * Templates Barrel Export
 * Page layout templates
 */

export { MainLayout } from './MainLayout';
export type { MainLayoutProps } from './MainLayout';

export { ShopLayout } from './ShopLayout';
export type { ShopLayoutProps } from './ShopLayout';

export { CheckoutLayout } from './CheckoutLayout';
export type { CheckoutLayoutProps } from './CheckoutLayout';

export { OrderTrackingLayout } from './OrderTrackingLayout';
export type { OrderTrackingLayoutProps } from './OrderTrackingLayout';

// ── Audience-router shells (ADR-035 §54 / Issue #1057) ───────────────────────
export { HomeShell } from './HomeShell';
export type { HomeShellProps } from './HomeShell';

export { RetailerShell } from './RetailerShell';
export type { RetailerShellProps } from './RetailerShell';

export { BuilderShell } from './BuilderShell';
export type { BuilderShellProps } from './BuilderShell';

export { DeployShell } from './DeployShell';
export type { DeployShellProps } from './DeployShell';
