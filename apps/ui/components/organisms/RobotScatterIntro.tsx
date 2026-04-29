'use client';

import React, { useEffect, useMemo, useRef, useState } from 'react';
import { AgentRobot, getAllAgentSlugs } from './AgentRobot';

type Phase = 'gathering' | 'waving' | 'scattering' | 'done';

const GATHER_DURATION = 600;
const WAVE_DURATION = 2200;
const SCATTER_DURATION = 900;
const FADE_OUT_DURATION = 400;

interface ScatterTarget {
  x: number;
  y: number;
  rotation: number;
}

function randomScatterTarget(): ScatterTarget {
  const angle = Math.random() * Math.PI * 2;
  const distance = 800 + Math.random() * 600;

  return {
    x: Math.cos(angle) * distance,
    y: Math.sin(angle) * distance,
    rotation: (Math.random() - 0.5) * 720,
  };
}

function gridPosition(index: number, _total: number): { x: number; y: number } {
  const rings = [
    { count: 1, radius: 0 },
    { count: 6, radius: 72 },
    { count: 10, radius: 148 },
    { count: 9, radius: 224 },
  ];

  let currentIndex = index;
  for (const ring of rings) {
    if (currentIndex < ring.count) {
      if (ring.radius === 0) {
        return { x: 0, y: 0 };
      }

      const angle = (currentIndex / ring.count) * Math.PI * 2 - Math.PI / 2;
      return {
        x: Math.cos(angle) * ring.radius,
        y: Math.sin(angle) * ring.radius,
      };
    }

    currentIndex -= ring.count;
  }

  const angle = (currentIndex / 5) * Math.PI * 2;
  return {
    x: Math.cos(angle) * 290,
    y: Math.sin(angle) * 290,
  };
}

export interface RobotScatterIntroProps {
  onComplete?: () => void;
  skip?: boolean;
}

// No GoF pattern applies — timed overlay choreography with local phase state.
export const RobotScatterIntro: React.FC<RobotScatterIntroProps> = ({
  onComplete,
  skip = false,
}) => {
  const [phase, setPhase] = useState<Phase>(skip ? 'done' : 'gathering');
  const [opacity, setOpacity] = useState(skip ? 0 : 1);
  const containerRef = useRef<HTMLDivElement>(null);

  const slugs = useMemo(() => getAllAgentSlugs(), []);
  const scatterTargets = useMemo(() => slugs.map(() => randomScatterTarget()), [slugs]);

  useEffect(() => {
    if (skip) {
      setPhase('done');
      return;
    }

    const gatheringTimer = setTimeout(() => setPhase('waving'), GATHER_DURATION);
    const wavingTimer = setTimeout(
      () => setPhase('scattering'),
      GATHER_DURATION + WAVE_DURATION,
    );
    const scatteringTimer = setTimeout(() => {
      setOpacity(0);
      setTimeout(() => {
        setPhase('done');
        onComplete?.();
      }, FADE_OUT_DURATION);
    }, GATHER_DURATION + WAVE_DURATION + SCATTER_DURATION);

    return () => {
      clearTimeout(gatheringTimer);
      clearTimeout(wavingTimer);
      clearTimeout(scatteringTimer);
    };
  }, [skip, onComplete]);

  if (phase === 'done') {
    return null;
  }

  return (
    <div
      ref={containerRef}
      className="fixed inset-0 z-[9999] flex items-center justify-center overflow-hidden bg-[var(--hp-bg)]/80 backdrop-blur-md"
      style={{
        opacity,
        transition: `opacity ${FADE_OUT_DURATION}ms ease-out`,
      }}
      aria-hidden="true"
    >
      <div className="relative" style={{ width: 600, height: 600 }}>
        {slugs.map((slug, index) => {
          const position = gridPosition(index, slugs.length);
          const scatter = scatterTargets[index];
          const isScattering = phase === 'scattering';

          return (
            <div
              key={slug}
              className="absolute"
              style={{
                left: '50%',
                top: '50%',
                transform: isScattering
                  ? `translate(calc(-50% + ${scatter.x}px), calc(-50% + ${scatter.y}px)) rotate(${scatter.rotation}deg) scale(0.2)`
                  : `translate(calc(-50% + ${position.x}px), calc(-50% + ${position.y}px))`,
                opacity: isScattering ? 0 : 1,
                transition: isScattering
                  ? `transform ${SCATTER_DURATION}ms cubic-bezier(0.36, 0, 0.66, -0.56), opacity ${SCATTER_DURATION * 0.8}ms ease-in`
                  : `transform ${GATHER_DURATION}ms cubic-bezier(0.34, 1.56, 0.64, 1)`,
                transitionDelay: isScattering ? `${Math.random() * 200}ms` : `${index * 30}ms`,
              }}
            >
              <AgentRobot
                agentSlug={slug}
                size={48}
                sticky={false}
                skipEntrance={phase !== 'gathering'}
                entranceDelay={index * 40}
                state={phase === 'waving' ? 'waving' : 'idle'}
              />
            </div>
          );
        })}
      </div>

      <div
        className="absolute bottom-16 left-0 right-0 text-center"
        style={{
          opacity: phase === 'scattering' ? 0 : 1,
          transform: phase === 'scattering' ? 'translateY(20px)' : 'translateY(0)',
          transition: 'opacity 400ms ease, transform 400ms ease',
        }}
      >
        <p className="text-lg font-medium tracking-wide text-[var(--hp-text-muted)]">
          Getting your Holiday Peak shopping assistant ready
        </p>
      </div>
    </div>
  );
};

RobotScatterIntro.displayName = 'RobotScatterIntro';
