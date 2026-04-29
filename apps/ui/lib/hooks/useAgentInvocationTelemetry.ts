'use client';

import { useEffect, useState } from 'react';
import { getCurrentPageSessionId, usePageSession } from '@/lib/hooks/usePageSession';

const STORAGE_PREFIX = 'hp.agent.last_invocation';
const UPDATE_EVENT = 'hp:agent-telemetry';

export interface AgentInvocationTelemetry {
  modelTier?: string;
  totalTokens?: number;
  costUsd?: number;
  latencyMs?: number;
  toolCalls?: number;
  sessionId?: string;
  updatedAt: number;
}

export interface FormattedAgentInvocationTelemetry {
  tier?: string;
  tokens?: string;
  cost?: string;
  latency?: string;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function readString(record: Record<string, unknown>, keys: string[]): string | undefined {
  for (const key of keys) {
    const value = record[key];
    if (typeof value === 'string' && value.trim()) {
      return value.trim();
    }
  }

  return undefined;
}

function readNumber(record: Record<string, unknown>, keys: string[]): number | undefined {
  for (const key of keys) {
    const value = record[key];
    if (typeof value === 'number' && Number.isFinite(value)) {
      return value;
    }
    if (typeof value === 'string' && value.trim()) {
      const parsed = Number(value);
      if (Number.isFinite(parsed)) {
        return parsed;
      }
    }
  }

  return undefined;
}

function getStorageKey(agentSlug: string): string {
  return `${STORAGE_PREFIX}:${agentSlug}`;
}

function formatCompactNumber(value: number): string {
  if (value >= 10_000) {
    return `${Math.round(value / 1000)}k`;
  }
  if (value >= 1_000) {
    return `${(value / 1000).toFixed(1)}k`;
  }
  return `${Math.round(value)}`;
}

function formatCost(value: number): string {
  if (value >= 1) {
    return `$${value.toFixed(2)}`;
  }
  if (value >= 0.01) {
    return `$${value.toFixed(3)}`;
  }
  return `$${value.toFixed(4)}`;
}

export function parseAgentInvocationTelemetry(payload: unknown): AgentInvocationTelemetry | null {
  if (!isRecord(payload)) {
    return null;
  }

  const telemetryRecord = isRecord(payload._telemetry)
    ? payload._telemetry
    : isRecord(payload.telemetry)
      ? payload.telemetry
      : payload;

  const tokenRecord = isRecord(telemetryRecord.tokens) ? telemetryRecord.tokens : null;
  const inputTokens = tokenRecord
    ? readNumber(tokenRecord, ['input', 'input_tokens', 'prompt_tokens'])
    : readNumber(telemetryRecord, ['input_tokens', 'prompt_tokens']);
  const outputTokens = tokenRecord
    ? readNumber(tokenRecord, ['output', 'output_tokens', 'completion_tokens'])
    : readNumber(telemetryRecord, ['output_tokens', 'completion_tokens']);
  const totalTokens = tokenRecord
    ? readNumber(tokenRecord, ['total', 'total_tokens'])
    : readNumber(telemetryRecord, ['total_tokens']);

  const normalizedTelemetry: AgentInvocationTelemetry = {
    modelTier: readString(telemetryRecord, ['model_tier', 'tier']),
    totalTokens:
      totalTokens
      ?? ((inputTokens !== undefined || outputTokens !== undefined)
        ? (inputTokens ?? 0) + (outputTokens ?? 0)
        : undefined),
    costUsd: readNumber(telemetryRecord, ['cost_usd', 'cost']),
    latencyMs: readNumber(telemetryRecord, ['latency_ms', 'duration_ms']),
    toolCalls: Array.isArray(telemetryRecord.tool_calls)
      ? telemetryRecord.tool_calls.length
      : readNumber(telemetryRecord, ['tool_calls']),
    updatedAt: Date.now(),
  };

  if (
    normalizedTelemetry.modelTier === undefined
    && normalizedTelemetry.totalTokens === undefined
    && normalizedTelemetry.costUsd === undefined
    && normalizedTelemetry.latencyMs === undefined
    && normalizedTelemetry.toolCalls === undefined
  ) {
    return null;
  }

  return normalizedTelemetry;
}

export function recordAgentInvocationTelemetry(
  agentSlug: string,
  payload: unknown,
): AgentInvocationTelemetry | null {
  const telemetry = parseAgentInvocationTelemetry(payload);

  if (!telemetry || typeof window === 'undefined') {
    return telemetry;
  }

  const scopedTelemetry: AgentInvocationTelemetry = {
    ...telemetry,
    sessionId: getCurrentPageSessionId() ?? undefined,
  };

  try {
    window.sessionStorage.setItem(getStorageKey(agentSlug), JSON.stringify(scopedTelemetry));
  } catch {
    return scopedTelemetry;
  }

  window.dispatchEvent(
    new CustomEvent(UPDATE_EVENT, {
      detail: {
        agentSlug,
        telemetry: scopedTelemetry,
      },
    }),
  );

  return scopedTelemetry;
}

export function readAgentInvocationTelemetry(agentSlug: string): AgentInvocationTelemetry | null {
  if (typeof window === 'undefined') {
    return null;
  }

  try {
    const rawValue = window.sessionStorage.getItem(getStorageKey(agentSlug));
    if (!rawValue) {
      return null;
    }

    const parsed = JSON.parse(rawValue) as unknown;
    if (!isRecord(parsed)) {
      return null;
    }

    return {
      modelTier: readString(parsed, ['modelTier']),
      totalTokens: readNumber(parsed, ['totalTokens']),
      costUsd: readNumber(parsed, ['costUsd']),
      latencyMs: readNumber(parsed, ['latencyMs']),
      toolCalls: readNumber(parsed, ['toolCalls']),
      sessionId: readString(parsed, ['sessionId']),
      updatedAt: readNumber(parsed, ['updatedAt']) ?? Date.now(),
    };
  } catch {
    return null;
  }
}

export function formatAgentInvocationTelemetry(
  telemetry: AgentInvocationTelemetry | null,
): FormattedAgentInvocationTelemetry | undefined {
  if (!telemetry) {
    return undefined;
  }

  return {
    tier: telemetry.modelTier ? telemetry.modelTier.toUpperCase() : undefined,
    tokens:
      telemetry.totalTokens !== undefined
        ? `${formatCompactNumber(telemetry.totalTokens)} tok`
        : undefined,
    cost: telemetry.costUsd !== undefined ? formatCost(telemetry.costUsd) : undefined,
    latency:
      telemetry.latencyMs !== undefined
        ? `${Math.round(telemetry.latencyMs)} ms`
        : undefined,
  };
}

export function useAgentInvocationTelemetry(agentSlug?: string): AgentInvocationTelemetry | null {
  const { sessionId } = usePageSession();
  const [telemetry, setTelemetry] = useState<AgentInvocationTelemetry | null>(() => (
    agentSlug ? readAgentInvocationTelemetry(agentSlug) : null
  ));

  useEffect(() => {
    if (!agentSlug || typeof window === 'undefined') {
      setTelemetry(null);
      return undefined;
    }

    const initialTelemetry = readAgentInvocationTelemetry(agentSlug);
    setTelemetry(initialTelemetry?.sessionId === sessionId ? initialTelemetry : null);

    const handleUpdate = (event: Event) => {
      const detail = (event as CustomEvent<{ agentSlug?: string; telemetry?: AgentInvocationTelemetry | null }>).detail;
      if (!detail || detail.agentSlug !== agentSlug) {
        return;
      }

      if (detail.telemetry?.sessionId !== sessionId) {
        setTelemetry(null);
        return;
      }

      setTelemetry(detail.telemetry ?? null);
    };

    const handleStorage = (event: StorageEvent) => {
      if (event.key !== getStorageKey(agentSlug)) {
        return;
      }

      const nextTelemetry = readAgentInvocationTelemetry(agentSlug);
      setTelemetry(nextTelemetry?.sessionId === sessionId ? nextTelemetry : null);
    };

    window.addEventListener(UPDATE_EVENT, handleUpdate as EventListener);
    window.addEventListener('storage', handleStorage);

    return () => {
      window.removeEventListener(UPDATE_EVENT, handleUpdate as EventListener);
      window.removeEventListener('storage', handleStorage);
    };
  }, [agentSlug, sessionId]);

  return telemetry;
}

export default useAgentInvocationTelemetry;