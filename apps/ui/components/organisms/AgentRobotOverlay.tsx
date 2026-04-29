'use client';

import React, { useEffect, useState } from 'react';
import {
  AgentRobot,
  type AgentRobotProps,
  type RobotState,
} from '@/components/organisms/AgentRobot';
import { cn } from '@/components/utils';

// ── Types ──

export type OverlayPosition = 'bottom-right' | 'bottom-left' | 'inline';
export type OverlaySize = number | 'sm' | 'md' | 'lg';

const SIZE_PRESETS: Record<Exclude<OverlaySize, number>, number> = {
  sm: 64,
  md: 88,
  lg: 112,
};

function resolveOverlaySize(size: OverlaySize): number {
  if (typeof size === 'number') {
    return size;
  }

  return SIZE_PRESETS[size];
}

export interface AgentRobotOverlayProps {
  /** Agent slug determines the robot personality */
  agentSlug: string;
  /** Current animation state */
  state?: RobotState;
  /** Message shown in the thinking bubble */
  thinkingMessage?: string;
  /** Overlay position — sticky viewport corners or inline */
  position?: OverlayPosition;
  /** Size in px or preset token (default sm) */
  size?: OverlaySize;
  /** Extra CSS classes */
  className?: string;
  /** Whether the robot is visible (default true) */
  visible?: boolean;
  /** Robot facing direction */
  facing?: AgentRobotProps['facing'];
  /** Override the robot tool icon */
  toolOverride?: AgentRobotProps['toolOverride'];
  /** Stage the robot as a left/right peer in multi-agent scenes */
  scenePeer?: AgentRobotProps['scenePeer'];
}

const POSITION_CLASSES: Record<OverlayPosition, string> = {
  'bottom-right': 'fixed bottom-6 right-6 z-50',
  'bottom-left': 'fixed bottom-6 left-6 z-50',
  inline: 'relative',
};

/**
 * Wrapper that positions the AgentRobot with entrance/exit animations.
 * Use with `useAgentRobotState()` to connect to agent lifecycle events.
 *
 * ```tsx
 * const { state, thinkingMessage } = useAgentRobotState('ecommerce-catalog-search');
 * <AgentRobotOverlay agentSlug="ecommerce-catalog-search" state={state} thinkingMessage={thinkingMessage} />
 * ```
 */
export function AgentRobotOverlay({
  agentSlug,
  state = 'idle',
  thinkingMessage,
  position = 'bottom-right',
  size = 'sm',
  className,
  visible = true,
  facing = 'forward',
  toolOverride,
  scenePeer = null,
}: AgentRobotOverlayProps) {
  const [mounted, setMounted] = useState(false);
  const resolvedSize = resolveOverlaySize(size);

  useEffect(() => {
    if (visible) {
      setMounted(true);
    } else {
      const timer = setTimeout(() => setMounted(false), 500);
      return () => clearTimeout(timer);
    }
  }, [visible]);

  if (!mounted) return null;

  return (
    <div
      className={cn(
        POSITION_CLASSES[position],
        'transition-all duration-500',
        visible
          ? 'opacity-100 translate-y-0'
          : 'opacity-0 translate-y-4 pointer-events-none',
        className,
      )}
      aria-hidden={!visible}
    >
      <AgentRobot
        agentSlug={agentSlug}
        state={state}
        thinkingMessage={thinkingMessage}
        size={resolvedSize}
        sticky={false}
        facing={facing}
        toolOverride={toolOverride}
        scenePeer={scenePeer}
      />
    </div>
  );
}
