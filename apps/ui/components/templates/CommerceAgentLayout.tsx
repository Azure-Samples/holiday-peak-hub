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
};

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
  const storedFormattedTelemetry = formatAgentInvocationTelemetry(storedTelemetry);
  const resolvedTelemetry = storedFormattedTelemetry
    ? { ...storedFormattedTelemetry, ...(telemetrySlot?.telemetry ?? {}) }
    : telemetrySlot?.telemetry;
  const hasResolvedTelemetry = Boolean(
    resolvedTelemetry?.tier
    || resolvedTelemetry?.tokens
    || resolvedTelemetry?.cost
    || resolvedTelemetry?.latency,
  );
  const primaryMode = primary?.mode ?? 'lead';
  const sideCastCount = sideCast.filter((slot) => slot.visible !== false).length;

  const content = (
    <>
      {telemetry !== 'hidden' && telemetrySlot && telemetryProfile && (
        <div
          className={cn(
            'fixed right-5 top-20 z-40 max-w-[280px] rounded-[1.5rem] border border-white/10 bg-[radial-gradient(circle_at_top,rgba(56,189,248,0.14),transparent_45%),rgba(8,12,24,0.88)] shadow-[0_25px_80px_rgba(15,23,42,0.35)] backdrop-blur-xl',
            telemetry === 'compact' ? 'px-4 py-3' : 'px-5 py-4',
          )}
        >
          <p className="text-[10px] font-semibold uppercase tracking-[0.24em] text-[var(--hp-text-faint)]">
            {primaryMode === 'hint' ? 'Agent hint' : 'Agent telemetry'}
          </p>
          <p className="mt-2 text-sm font-semibold text-white">{telemetryProfile.displayName}</p>
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

      {children}

      {primary && <AgentRobotOverlay {...primary} />}
      {sideCast.map((slot) => (
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
    <div className="rounded-full border border-white/10 bg-white/5 px-3 py-2">
      <p className="text-[10px] uppercase tracking-[0.2em] text-[var(--hp-text-faint)]">{label}</p>
      <p className="mt-1 text-sm text-white">{value}</p>
    </div>
  );
}

export default CommerceAgentLayout;