/**
 * Shared route-group primitives.
 *
 * Per ADR-034, every audience route group consumes `SectionShell` for the
 * cross-cutting chrome (brand mark, section label, breadcrumb slot, lane-switch
 * slot). Section-specific chrome stays inside each group's own layout.
 */
export { SectionShell } from './SectionShell';
export type { SectionVariant } from './SectionShell';
