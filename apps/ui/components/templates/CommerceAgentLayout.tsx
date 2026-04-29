'use client';

import React from 'react';
import { MainLayout } from '@/components/templates/MainLayout';
import { AgentRobotOverlay, type AgentRobotOverlayProps } from '@/components/organisms/AgentRobotOverlay';
import { AGENT_PROFILES } from '@/lib/agents/profiles';
import {
  formatAgentInvocationTelemetry,
  useAgentInvocationTelemetry,
} from '@/lib/hooks/useAgentInvocationTelemetry';
import { cn } from '@/components/utils';

export interface CommerceAgentTelemetry {
  tier?: string;
  latency?: string;
  cost?: string;
  tokens?: string;
}

export interface CommerceAgentSlot extends AgentRobotOverlayProps {
  mode?: 'lead' | 'observe' | 'hint';
  telemetry?: CommerceAgentTelemetry;
}

export interface CommerceAgentLayoutProps {
  children: React.ReactNode;
  primary?: CommerceAgentSlot;
  sideCast?: CommerceAgentSlot[];
  telemetry?: 'hidden' | 'compact' | 'visible';
  useMainLayout?: boolean;
  mainLayoutProps?: Omit<React.ComponentProps<typeof MainLayout>, 'children'>;
}

const STATE_LABELS: Record<NonNullable<CommerceAgentSlot['state']>, string> = {
  idle: 'Idle',
  thinking: 'Thinking',
  talking: 'Narrating',
  'using-tool': 'Using tool',
  entering: 'Entering',
  waving: 'Waving',
};
const TELEMETRY_FRESHNESS_WINDOW_MS = 15_000;
const SIDE_CAST_STACK_CLASSES = [
  'hidden xl:block xl:bottom-24 2xl:bottom-28',
  'hidden 2xl:block 2xl:bottom-48',
  'hidden 2xl:block 2xl:bottom-72',
] as const;

export function resolveCommerceAgentSlot(
  slot: CommerceAgentSlot,
  role: 'primary' | 'side-cast',
  index = 0,
): CommerceAgentSlot {
  if (slot.position === 'inline') {
    return slot;
  }

  if (role === 'primary') {
    const resolvedPosition = slot.position ?? 'bottom-left';

    return {
      ...slot,
      position: resolvedPosition,
      facing: slot.facing ?? (resolvedPosition === 'bottom-left' ? 'right' : 'left'),
      className: cn('max-[420px]:scale-95', slot.className),
    };
  }

  const resolvedPosition = slot.position ?? 'bottom-right';

  return {
    ...slot,
    position: resolvedPosition,
    facing: slot.facing ?? (resolvedPosition === 'bottom-right' ? 'left' : 'right'),
    scenePeer: slot.scenePeer ?? (resolvedPosition === 'bottom-right' ? 'right' : 'left'),
    className: cn(
      resolvedPosition === 'bottom-right'
        ? (SIDE_CAST_STACK_CLASSES[index] ?? SIDE_CAST_STACK_CLASSES[SIDE_CAST_STACK_CLASSES.length - 1])
        : 'hidden xl:block',
      slot.className,
    ),
  };
}

export function CommerceAgentLayout({
  children,
  primary,
  sideCast = [],
  telemetry = 'compact',
  useMainLayout = true,
  mainLayoutProps,
}: CommerceAgentLayoutProps) {
  const telemetrySlot = primary ?? sideCast[0];
  const telemetryProfile = telemetrySlot ? AGENT_PROFILES[telemetrySlot.agentSlug as keyof typeof AGENT_PROFILES] : null;
  const storedTelemetry = useAgentInvocationTelemetry(telemetrySlot?.agentSlug);
  const storedFormattedTelemetry =
    storedTelemetry && Date.now() - storedTelemetry.updatedAt <= TELEMETRY_FRESHNESS_WINDOW_MS
      ? formatAgentInvocationTelemetry(storedTelemetry)
      : undefined;
  const resolvedTelemetry = storedFormattedTelemetry
    ? { ...storedFormattedTelemetry, ...(telemetrySlot?.telemetry ?? {}) }
    : telemetrySlot?.telemetry;
  const hasResolvedTelemetry = Boolean(
    resolvedTelemetry?.tier
    || resolvedTelemetry?.tokens
    || resolvedTelemetry?.cost
    || resolvedTelemetry?.latency,
  );
  const resolvedPrimary = primary ? resolveCommerceAgentSlot(primary, 'primary') : undefined;
  const resolvedSideCast = sideCast.map((slot, index) => resolveCommerceAgentSlot(slot, 'side-cast', index));
  const telemetryMode = telemetrySlot?.mode ?? primary?.mode ?? 'lead';
  const sideCastCount = resolvedSideCast.filter((slot) => slot.visible !== false).length;
  const showTelemetryPanel = Boolean(
    telemetry !== 'hidden'
    && telemetrySlot
    && telemetryProfile
    && !(telemetryMode === 'hint' && !hasResolvedTelemetry),
  );
  const contentSpacingClass = showTelemetryPanel
    ? 'pt-28 sm:pt-0 xl:pr-[20rem]'
    : undefined;

  const content = (
    <>
      {showTelemetryPanel && telemetryProfile && (
        <div
          className={cn(
            'fixed left-4 right-4 top-20 z-40 rounded-[1.5rem] border border-[color:color-mix(in_srgb,var(--hp-border)_88%,transparent)] bg-[radial-gradient(circle_at_top,color-mix(in_srgb,var(--hp-accent)_14%,transparent),transparent_48%),color-mix(in_srgb,var(--hp-surface)_84%,transparent)] text-[var(--hp-text)] shadow-[var(--hp-shadow-lg)] backdrop-blur-xl sm:left-auto sm:right-5 sm:max-w-[280px]',
            telemetry === 'compact' ? 'px-4 py-3' : 'px-5 py-4',
          )}
        >
          <p className="text-[10px] font-semibold uppercase tracking-[0.24em] text-[var(--hp-text-faint)]">
            {telemetryMode === 'hint' ? 'Agent hint' : 'Agent telemetry'}
          </p>
          <p className="mt-2 text-sm font-semibold text-[var(--hp-text)]">{telemetryProfile.displayName}</p>
          <div className="mt-2 flex flex-wrap gap-2 text-xs text-[var(--hp-text-muted)]">
            <span>{STATE_LABELS[telemetrySlot.state ?? 'idle']}</span>
            <span>{telemetryProfile.domainLabel}</span>
            {sideCastCount > 0 && <span>{sideCastCount} side cast live</span>}
          </div>
          <div className="mt-3 min-h-5 text-[11px] font-medium tracking-[0.08em] text-[var(--hp-text-muted)]">
            {hasResolvedTelemetry ? (
              <div className="flex flex-wrap items-center gap-2 font-mono">
                {resolvedTelemetry?.tier ? <TelemetryInlineItem value={resolvedTelemetry.tier} /> : null}
                {resolvedTelemetry?.tokens ? <TelemetryInlineItem value={resolvedTelemetry.tokens} /> : null}
                {resolvedTelemetry?.cost ? <TelemetryInlineItem value={resolvedTelemetry.cost} /> : null}
                {resolvedTelemetry?.latency ? <TelemetryInlineItem value={resolvedTelemetry.latency} /> : null}
              </div>
            ) : (
              <span className="font-mono text-[var(--hp-text-faint)]">Awaiting invocation telemetry</span>
            )}
          </div>
          {telemetry === 'visible' && (
            <div className="mt-3 grid gap-2 text-xs text-[var(--hp-text-muted)] sm:grid-cols-2">
              <MetricPill label="Tier" value={resolvedTelemetry?.tier ?? 'Awaiting call'} />
              <MetricPill label="Latency" value={resolvedTelemetry?.latency ?? 'Awaiting call'} />
              <MetricPill label="Cost" value={resolvedTelemetry?.cost ?? 'Awaiting call'} />
              <MetricPill label="Tokens" value={resolvedTelemetry?.tokens ?? 'Awaiting call'} />
            </div>
          )}
        </div>
      )}

      <div className={contentSpacingClass}>{children}</div>

      {resolvedPrimary && <AgentRobotOverlay {...resolvedPrimary} />}
      {resolvedSideCast.map((slot) => (
        <AgentRobotOverlay key={`${slot.agentSlug}-${slot.position ?? 'overlay'}`} {...slot} />
      ))}
    </>
  );

  if (!useMainLayout) {
    return content;
  }

  return <MainLayout {...mainLayoutProps}>{content}</MainLayout>;
}

function TelemetryInlineItem({ value }: { value: string }) {
  return <span>{value}</span>;
}

function MetricPill({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-full border border-[var(--hp-border)] bg-[color:color-mix(in_srgb,var(--hp-surface-strong)_92%,transparent)] px-3 py-2">
      <p className="text-[10px] uppercase tracking-[0.2em] text-[var(--hp-text-faint)]">{label}</p>
      <p className="mt-1 text-sm text-[var(--hp-text)]">{value}</p>
    </div>
  );
}

export default CommerceAgentLayout;