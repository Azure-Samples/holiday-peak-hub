'use client';

import Link from 'next/link';
import { Badge } from '@/components/atoms/Badge';
import { AgentRobot } from '@/components/organisms/AgentRobot';
import { AGENT_PROFILE_LIST } from '@/lib/agents/profiles';
import type { AgentProfileSlug } from '@/lib/agents/profiles';
import type { AgentHealthCardMetric } from '@/lib/types/api';

const STATUS_VARIANT: Record<AgentHealthCardMetric['status'], 'success' | 'warning' | 'danger' | 'secondary'> = {
  healthy: 'success',
  degraded: 'warning',
  down: 'danger',
  unknown: 'secondary',
};

export interface AgentFriezeProps {
  healthBySlug?: Partial<Record<AgentProfileSlug, AgentHealthCardMetric>>;
  hrefBySlug?: Partial<Record<AgentProfileSlug, string>>;
}

export function AgentFrieze({ healthBySlug = {}, hrefBySlug = {} }: AgentFriezeProps) {
  return (
    <div
      className="agent-frieze-scroller overflow-x-scroll overflow-y-hidden pb-4"
      style={{
        scrollbarGutter: 'stable',
        scrollbarWidth: 'thin',
        scrollbarColor: 'var(--hp-primary) transparent',
      }}
    >
      <ul role="list" className="flex min-w-max gap-3 pr-4">
        {AGENT_PROFILE_LIST.map((profile) => {
          const health = healthBySlug[profile.slug];
          const href = hrefBySlug[profile.slug];
          const tone = STATUS_VARIANT[health?.status ?? 'unknown'];
          const content = (
            <div className="flex min-w-[170px] flex-col gap-3 rounded-3xl border border-[var(--hp-border)] bg-[var(--hp-surface)] px-4 py-4 shadow-[var(--hp-shadow-sm)] transition-transform duration-200 hover:-translate-y-1">
              <div className="flex items-center justify-between gap-3">
                <AgentRobot agentSlug={profile.slug} size={76} sticky={false} skipEntrance />
                <Badge size="xs" variant={tone}>
                  {health?.status ?? 'unknown'}
                </Badge>
              </div>
              <div>
                <p className="text-sm font-semibold text-[var(--hp-text)]">{profile.displayName}</p>
                <p className="mt-1 text-xs text-[var(--hp-text-muted)]">{profile.domainLabel}</p>
              </div>
              <div className="flex items-center justify-between text-[11px] text-[var(--hp-text-muted)]">
                <span>{Math.round(health?.latency_ms ?? 0)} ms</span>
                <span>{Math.round((health?.error_rate ?? 0) * 100)}% err</span>
              </div>
            </div>
          );

          return (
            <li key={profile.slug}>
              {href ? (
                <Link href={href} aria-label={`Open ${profile.displayName} cockpit`}>
                  {content}
                </Link>
              ) : (
                content
              )}
            </li>
          );
        })}
      </ul>
    </div>
  );
}