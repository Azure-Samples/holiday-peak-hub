'use client';

import React, { useEffect, useMemo, useRef, useState } from 'react';
import { cn } from '../utils';
import { ThinkingBubble } from '@/components/molecules/ThinkingBubble';

// ── Agent Robot Types ──

export type RobotState = 'idle' | 'thinking' | 'using-tool' | 'talking' | 'entering' | 'waving';

export interface AgentRobotProps {
  agentSlug: string;
  state?: RobotState;
  thinkingMessage?: string;
  /** When true, render an inline streaming-dots indicator inside the bubble. */
  streaming?: boolean;
  size?: number;
  className?: string;
  sticky?: boolean;
  entranceDelay?: number;
  skipEntrance?: boolean;
  onEntranceComplete?: () => void;
  facing?: 'left' | 'right' | 'forward';
  pointAt?: { x: number; y: number } | null;
  lookAt?: React.RefObject<HTMLElement | null> | null;
  toolOverride?: string;
  scenePeer?: 'left' | 'right' | null;
}

// ── Robot personality ──

interface RobotPersonality {
  bodyColor: string;
  visorColor: string;
  tool: string;
  eyeVariant: 'round' | 'oval' | 'wide' | 'narrow';
  antennaVariant: 'single' | 'double' | 'none';
}

const AGENT_PERSONALITIES: Record<string, Partial<RobotPersonality>> = {
  'crm-campaign-intelligence': { bodyColor: '#7c3aed', visorColor: '#a78bfa', tool: '📊', eyeVariant: 'wide', antennaVariant: 'double' },
  'crm-profile-aggregation': { bodyColor: '#2563eb', visorColor: '#60a5fa', tool: '🔍', eyeVariant: 'round', antennaVariant: 'single' },
  'crm-segmentation-personalization': { bodyColor: '#0891b2', visorColor: '#22d3ee', tool: '✂️', eyeVariant: 'oval', antennaVariant: 'double' },
  'crm-support-assistance': { bodyColor: '#059669', visorColor: '#34d399', tool: '🩹', eyeVariant: 'round', antennaVariant: 'single' },
  'ecommerce-catalog-search': { bodyColor: '#d97706', visorColor: '#fbbf24', tool: '🔎', eyeVariant: 'wide', antennaVariant: 'double' },
  'ecommerce-cart-intelligence': { bodyColor: '#dc2626', visorColor: '#f87171', tool: '🛒', eyeVariant: 'round', antennaVariant: 'single' },
  'ecommerce-checkout-support': { bodyColor: '#16a34a', visorColor: '#4ade80', tool: '💳', eyeVariant: 'narrow', antennaVariant: 'none' },
  'ecommerce-order-status': { bodyColor: '#9333ea', visorColor: '#c084fc', tool: '📦', eyeVariant: 'oval', antennaVariant: 'single' },
  'ecommerce-product-detail-enrichment': { bodyColor: '#ea580c', visorColor: '#fb923c', tool: '🪄', eyeVariant: 'wide', antennaVariant: 'double' },
  'inventory-health-check': { bodyColor: '#0d9488', visorColor: '#2dd4bf', tool: '🩺', eyeVariant: 'round', antennaVariant: 'single' },
  'inventory-alerts-triggers': { bodyColor: '#e11d48', visorColor: '#fb7185', tool: '🔔', eyeVariant: 'wide', antennaVariant: 'double' },
  'inventory-jit-replenishment': { bodyColor: '#4f46e5', visorColor: '#818cf8', tool: '📋', eyeVariant: 'oval', antennaVariant: 'single' },
  'inventory-reservation-validation': { bodyColor: '#0284c7', visorColor: '#38bdf8', tool: '✅', eyeVariant: 'narrow', antennaVariant: 'none' },
  'logistics-carrier-selection': { bodyColor: '#b45309', visorColor: '#f59e0b', tool: '🚚', eyeVariant: 'round', antennaVariant: 'single' },
  'logistics-eta-computation': { bodyColor: '#7c2d12', visorColor: '#ea580c', tool: '⏱️', eyeVariant: 'oval', antennaVariant: 'double' },
  'logistics-returns-support': { bodyColor: '#166534', visorColor: '#22c55e', tool: '↩️', eyeVariant: 'round', antennaVariant: 'single' },
  'logistics-route-issue-detection': { bodyColor: '#6d28d9', visorColor: '#a78bfa', tool: '🗺️', eyeVariant: 'wide', antennaVariant: 'double' },
  'product-management-acp-transformation': { bodyColor: '#be123c', visorColor: '#fb7185', tool: '⚙️', eyeVariant: 'narrow', antennaVariant: 'none' },
  'product-management-assortment-optimization': { bodyColor: '#1d4ed8', visorColor: '#3b82f6', tool: '📐', eyeVariant: 'oval', antennaVariant: 'single' },
  'product-management-consistency-validation': { bodyColor: '#047857', visorColor: '#10b981', tool: '🔧', eyeVariant: 'round', antennaVariant: 'double' },
  'product-management-normalization-classification': { bodyColor: '#7e22ce', visorColor: '#a855f7', tool: '🏷️', eyeVariant: 'wide', antennaVariant: 'single' },
  'search-enrichment-agent': { bodyColor: '#c2410c', visorColor: '#f97316', tool: '🧲', eyeVariant: 'oval', antennaVariant: 'double' },
  'truth-ingestion': { bodyColor: '#0e7490', visorColor: '#06b6d4', tool: '📥', eyeVariant: 'round', antennaVariant: 'single' },
  'truth-enrichment': { bodyColor: '#4338ca', visorColor: '#6366f1', tool: '✨', eyeVariant: 'wide', antennaVariant: 'double' },
  'truth-hitl': { bodyColor: '#be185d', visorColor: '#ec4899', tool: '👤', eyeVariant: 'narrow', antennaVariant: 'none' },
  'truth-export': { bodyColor: '#15803d', visorColor: '#22c55e', tool: '📤', eyeVariant: 'oval', antennaVariant: 'single' },
};

const DEFAULT_PERSONALITY: RobotPersonality = {
  bodyColor: '#6366f1',
  visorColor: '#a5b4fc',
  tool: '🔧',
  eyeVariant: 'round',
  antennaVariant: 'single',
};

function getPersonality(agentSlug: string): RobotPersonality {
  const override = AGENT_PERSONALITIES[agentSlug];
  return { ...DEFAULT_PERSONALITY, ...override };
}

export function getAllAgentSlugs(): string[] {
  return Object.keys(AGENT_PERSONALITIES);
}

// ── LED pixel patterns for EVA-like face ──
// Each pattern is a 7×5 grid (rows×cols): 1 = lit, 0 = off

type PixelGrid = number[][];

const EYE_PATTERNS: Record<string, { left: PixelGrid; right: PixelGrid }> = {
  idle: {
    left: [
      [0,1,1,1,0],
      [1,1,1,1,1],
      [1,1,1,1,1],
      [1,1,1,1,1],
      [1,1,1,1,1],
      [1,1,1,1,1],
      [0,1,1,1,0],
    ],
    right: [
      [0,1,1,1,0],
      [1,1,1,1,1],
      [1,1,1,1,1],
      [1,1,1,1,1],
      [1,1,1,1,1],
      [1,1,1,1,1],
      [0,1,1,1,0],
    ],
  },
  happy: {
    left: [
      [0,1,1,1,0],
      [1,1,1,1,1],
      [1,1,1,1,1],
      [1,1,1,1,1],
      [0,1,1,1,0],
      [0,0,1,0,0],
      [0,0,0,0,0],
    ],
    right: [
      [0,1,1,1,0],
      [1,1,1,1,1],
      [1,1,1,1,1],
      [1,1,1,1,1],
      [0,1,1,1,0],
      [0,0,1,0,0],
      [0,0,0,0,0],
    ],
  },
  thinking: {
    left: [
      [0,0,0,0,0],
      [0,0,0,0,0],
      [1,1,1,1,1],
      [1,1,1,1,1],
      [1,1,1,1,1],
      [0,0,0,0,0],
      [0,0,0,0,0],
    ],
    right: [
      [0,0,0,0,0],
      [0,1,1,1,0],
      [1,1,1,1,1],
      [1,1,1,1,1],
      [1,1,1,1,1],
      [0,1,1,1,0],
      [0,0,0,0,0],
    ],
  },
  waving: {
    left: [
      [0,0,1,0,0],
      [0,1,1,1,0],
      [1,1,0,1,1],
      [1,1,0,1,1],
      [0,1,1,1,0],
      [0,0,1,0,0],
      [0,0,0,0,0],
    ],
    right: [
      [0,0,1,0,0],
      [0,1,1,1,0],
      [1,1,0,1,1],
      [1,1,0,1,1],
      [0,1,1,1,0],
      [0,0,1,0,0],
      [0,0,0,0,0],
    ],
  },
  talking: {
    left: [
      [0,1,1,1,0],
      [1,1,1,1,1],
      [1,1,1,1,1],
      [1,1,1,1,1],
      [1,1,1,1,1],
      [1,1,1,1,1],
      [0,1,1,1,0],
    ],
    right: [
      [0,1,1,1,0],
      [1,1,1,1,1],
      [1,1,1,1,1],
      [1,1,1,1,1],
      [1,1,1,1,1],
      [1,1,1,1,1],
      [0,1,1,1,0],
    ],
  },
  blink: {
    left: [
      [0,0,0,0,0],
      [0,0,0,0,0],
      [0,0,0,0,0],
      [1,1,1,1,1],
      [0,0,0,0,0],
      [0,0,0,0,0],
      [0,0,0,0,0],
    ],
    right: [
      [0,0,0,0,0],
      [0,0,0,0,0],
      [0,0,0,0,0],
      [1,1,1,1,1],
      [0,0,0,0,0],
      [0,0,0,0,0],
      [0,0,0,0,0],
    ],
  },
};

const MOUTH_PATTERNS: Record<string, number[]> = {
  neutral: [0,1,1,1,0],
  smile:   [1,0,1,0,1],
  open:    [0,1,1,1,0],
  wide:    [1,1,1,1,1],
};

// ── Pixel Face Canvas Renderer ──

interface PixelFaceProps {
  personality: RobotPersonality;
  state: RobotState;
  size: number;
  gazeX?: number;
}

function PixelFace({ personality, state, size, gazeX = 0 }: PixelFaceProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const animFrameRef = useRef<number>(0);
  const blinkTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const gazeXRef = useRef(gazeX);

  useEffect(() => {
    gazeXRef.current = gazeX;
  }, [gazeX]);

  const visorW = Math.round(size * 0.65);
  const visorH = Math.round(size * 0.38);
  const pixelSize = Math.max(2, Math.round(visorW / 22));
  const gap = Math.max(1, Math.round(pixelSize * 0.25));

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const runningInJsdom =
      typeof navigator !== 'undefined' && /jsdom/i.test(navigator.userAgent);
    if (runningInJsdom) {
      return;
    }

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const dpr = window.devicePixelRatio || 1;
    canvas.width = visorW * dpr;
    canvas.height = visorH * dpr;
    ctx.scale(dpr, dpr);

    let blinking = false;
    let talkFrame = 0;

    function scheduleBlink() {
      blinkTimerRef.current = setTimeout(() => {
        blinking = true;
        setTimeout(() => {
          blinking = false;
          scheduleBlink();
        }, 150);
      }, 2500 + Math.random() * 3000);
    }
    scheduleBlink();

    function getEyePattern(): { left: PixelGrid; right: PixelGrid } {
      if (blinking) return EYE_PATTERNS.blink;
      switch (state) {
        case 'thinking': return EYE_PATTERNS.thinking;
        case 'talking': return talkFrame % 2 === 0 ? EYE_PATTERNS.talking : EYE_PATTERNS.blink;
        case 'waving': return EYE_PATTERNS.waving;
        case 'entering': return EYE_PATTERNS.happy;
        default: return EYE_PATTERNS.idle;
      }
    }

    function getMouthPattern(): number[] {
      switch (state) {
        case 'thinking': return MOUTH_PATTERNS.neutral;
        case 'talking': return talkFrame % 3 === 0 ? MOUTH_PATTERNS.wide : MOUTH_PATTERNS.open;
        case 'waving': return MOUTH_PATTERNS.smile;
        case 'entering': return MOUTH_PATTERNS.smile;
        default: return MOUTH_PATTERNS.neutral;
      }
    }

    function drawPixel(x: number, y: number, lit: boolean, color: string, glow: boolean) {
      const px = x * (pixelSize + gap);
      const py = y * (pixelSize + gap);
      if (lit) {
        if (glow) {
          ctx!.shadowColor = color;
          ctx!.shadowBlur = pixelSize * 1.2;
        }
        ctx!.fillStyle = color;
        ctx!.beginPath();
        ctx!.roundRect(px, py, pixelSize, pixelSize, pixelSize * 0.15);
        ctx!.fill();
        ctx!.shadowBlur = 0;
      } else {
        ctx!.fillStyle = 'rgba(255,255,255,0.04)';
        ctx!.beginPath();
        ctx!.roundRect(px, py, pixelSize, pixelSize, pixelSize * 0.15);
        ctx!.fill();
      }
    }

    function render() {
      ctx!.clearRect(0, 0, visorW, visorH);

      const eyePattern = getEyePattern();
      const mouthPattern = getMouthPattern();
      const color = personality.visorColor;
      const horizontalLookOffset = Math.round(Math.max(-1, Math.min(1, gazeXRef.current)) * 1.2);

      const eyeBlockW = 5 * (pixelSize + gap);
      const eyeGapPx = Math.round(visorW * 0.12);
      const totalEyeW = eyeBlockW * 2 + eyeGapPx;
      const eyeStartX = Math.max(0, Math.round((visorW - totalEyeW) / (2 * (pixelSize + gap))));

      const eyeBlockH = 7 * (pixelSize + gap);
      const mouthH = pixelSize + gap;
      const mouthGapPx = Math.round(visorH * 0.06);
      const totalFaceH = eyeBlockH + mouthGapPx + mouthH;
      const eyeStartY = Math.max(0, Math.round((visorH - totalFaceH) / (2 * (pixelSize + gap))));

      // Left eye
      for (let r = 0; r < 7; r++) {
        for (let c = 0; c < 5; c++) {
          drawPixel(eyeStartX + c + horizontalLookOffset, eyeStartY + r, eyePattern.left[r][c] === 1, color, true);
        }
      }

      // Right eye
      const rightStart = eyeStartX + 5 + Math.round(eyeGapPx / (pixelSize + gap));
      for (let r = 0; r < 7; r++) {
        for (let c = 0; c < 5; c++) {
          drawPixel(rightStart + c + horizontalLookOffset, eyeStartY + r, eyePattern.right[r][c] === 1, color, true);
        }
      }

      // Mouth
      const mouthStartX = eyeStartX + Math.round((rightStart + 5 - eyeStartX - 5) / 2) + horizontalLookOffset;
      const mouthY = eyeStartY + 7 + Math.max(1, Math.round(mouthGapPx / (pixelSize + gap)));
      for (let c = 0; c < 5; c++) {
        drawPixel(mouthStartX + c, mouthY, mouthPattern[c] === 1, color, true);
      }

      // Thinking dots animation
      if (state === 'thinking') {
        const dotPhase = Math.floor(Date.now() / 400) % 3;
        for (let i = 0; i < 3; i++) {
          drawPixel(rightStart + 6 + i, eyeStartY + 2, i <= dotPhase, color, true);
        }
      }

      // Tool-use pulsing border
      if (state === 'using-tool') {
        const pulse = Math.sin(Date.now() / 200) > 0;
        if (pulse) {
          const maxCols = Math.floor(visorW / (pixelSize + gap));
          const maxRows = Math.floor(visorH / (pixelSize + gap));
          for (let c = 0; c < maxCols; c++) {
            drawPixel(c, 0, true, color, false);
            drawPixel(c, maxRows - 1, true, color, false);
          }
        }
      }

      talkFrame++;
      animFrameRef.current = requestAnimationFrame(render);
    }

    animFrameRef.current = requestAnimationFrame(render);
    return () => {
      cancelAnimationFrame(animFrameRef.current);
      if (blinkTimerRef.current) clearTimeout(blinkTimerRef.current);
    };
  }, [state, personality.visorColor, visorW, visorH, pixelSize, gap]);

  return (
    <canvas
      ref={canvasRef}
      style={{ width: visorW, height: visorH }}
      className="pointer-events-none"
      aria-hidden="true"
    />
  );
}

// ── Main Component ──

export const AgentRobot: React.FC<AgentRobotProps> = ({
  agentSlug,
  state: externalState = 'idle',
  thinkingMessage,
  streaming = false,
  size = 160,
  className,
  sticky = true,
  entranceDelay = 0,
  skipEntrance = false,
  onEntranceComplete,
  facing = 'forward',
  pointAt = null,
  lookAt = null,
  toolOverride,
  scenePeer = null,
}) => {
  const personality = useMemo(() => getPersonality(agentSlug), [agentSlug]);

  const [phase, setPhase] = useState<'hidden' | 'entering' | 'waving' | 'settled'>(
    skipEntrance ? 'settled' : 'hidden',
  );
  const [pointAngle, setPointAngle] = useState<number | null>(null);
  const [gazeX, setGazeX] = useState(0);
  const entranceTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const frameRef = useRef<HTMLDivElement>(null);

  const state: RobotState = phase === 'entering'
    ? 'entering'
    : phase === 'waving'
      ? 'waving'
      : externalState;

  useEffect(() => {
    if (skipEntrance) {
      setPhase('settled');
      return;
    }
    const delayTimer = setTimeout(() => {
      setPhase('entering');
      entranceTimerRef.current = setTimeout(() => {
        setPhase('waving');
        entranceTimerRef.current = setTimeout(() => {
          setPhase('settled');
          onEntranceComplete?.();
        }, 1400);
      }, 800);
    }, entranceDelay);
    return () => {
      clearTimeout(delayTimer);
      if (entranceTimerRef.current) clearTimeout(entranceTimerRef.current);
    };
  }, [entranceDelay, skipEntrance, onEntranceComplete]);

  useEffect(() => {
    const updatePointing = () => {
      if (!frameRef.current || !pointAt) {
        setPointAngle(null);
        return;
      }

      const rect = frameRef.current.getBoundingClientRect();
      const shoulderX = rect.right - rect.width * 0.24;
      const shoulderY = rect.top + rect.height * 0.48;
      const signedDeltaX = (pointAt.x - shoulderX) * (facing === 'left' ? -1 : 1);
      const deltaY = pointAt.y - shoulderY;
      const radians = Math.atan2(deltaY, signedDeltaX);
      const degrees = (radians * 180) / Math.PI;
      setPointAngle(Math.max(-160, Math.min(40, degrees)));
    };

    updatePointing();
    window.addEventListener('resize', updatePointing);
    return () => window.removeEventListener('resize', updatePointing);
  }, [facing, pointAt, size]);

  useEffect(() => {
    const updateGaze = () => {
      if (!frameRef.current || !lookAt?.current) {
        setGazeX(0);
        return;
      }

      const rect = frameRef.current.getBoundingClientRect();
      const targetRect = lookAt.current.getBoundingClientRect();
      const robotCenterX = rect.left + rect.width / 2;
      const targetCenterX = targetRect.left + targetRect.width / 2;
      const normalized = (targetCenterX - robotCenterX) / Math.max(rect.width / 2, 1);
      setGazeX(Math.max(-1, Math.min(1, normalized)));
    };

    updateGaze();
    window.addEventListener('resize', updateGaze);
    return () => window.removeEventListener('resize', updateGaze);
  }, [lookAt, size]);

  const { bodyColor, visorColor, tool, antennaVariant } = personality;
  const isThinking = state === 'thinking';
  const isEntering = state === 'entering';
  const isWaving = state === 'waving';
  const isUsingTool = state === 'using-tool';
  const showBubble = Boolean(thinkingMessage) && (isThinking || state === 'talking');
  const renderedTool = toolOverride ?? tool;
  const facingScale = facing === 'left' ? -1 : 1;
  const sceneScale = scenePeer === 'right' ? 0.92 : scenePeer === 'left' ? 1 : 1;
  const sceneOpacity = scenePeer === 'right' ? 0.82 : 1;

  if (phase === 'hidden') return null;

  return (
    <div
      className={cn(
        'relative select-none',
        sticky && 'robot-sticky',
        isEntering && 'robot-entrance',
        className,
      )}
      style={{ width: size, height: size * 1.15 }}
      aria-hidden="true"
    >
      {/* Thinking bubble — anchored above the robot's head */}
      {showBubble && thinkingMessage && (
        <div
          className="robot-bubble pointer-events-none absolute left-1/2 z-30 -translate-x-1/2"
          style={{ bottom: `calc(100% + 8px)` }}
        >
          <ThinkingBubble
            content={thinkingMessage}
            isStreaming={streaming}
            maxWidth={Math.max(200, size * 1.8)}
          />
        </div>
      )}

      <div
        ref={frameRef}
        className="relative"
        style={{
          width: size,
          height: size * 1.15,
          transform: `scaleX(${facingScale}) scale(${sceneScale})`,
          transformOrigin: 'center bottom',
          opacity: sceneOpacity,
        }}
      >
        <div
          className={cn(
            'robot-eva relative flex flex-col items-center',
            state === 'idle' && 'robot-float',
            isThinking && 'robot-think',
            isWaving && 'robot-wave-body',
          )}
          style={{ width: size, height: size * 1.15 }}
        >
        {/* Antenna(s) */}
        {antennaVariant !== 'none' && (
          <div className="absolute z-10 flex items-end justify-center" style={{ top: 0, width: size }}>
            <div style={{ width: size * 0.035, height: size * 0.1, backgroundColor: bodyColor, position: 'relative', borderRadius: size * 0.02 }}>
              <div className="robot-antenna-tip" style={{
                position: 'absolute', top: -size * 0.03, left: '50%', transform: 'translateX(-50%)',
                width: size * 0.055, height: size * 0.055, borderRadius: '50%',
                backgroundColor: visorColor, boxShadow: `0 0 ${size * 0.05}px ${visorColor}`,
              }} />
            </div>
            {antennaVariant === 'double' && (
              <div style={{
                width: size * 0.028, height: size * 0.075, backgroundColor: bodyColor,
                transform: 'rotate(15deg)', transformOrigin: 'bottom', position: 'relative',
                borderRadius: size * 0.015, marginLeft: -size * 0.01,
              }}>
                <div style={{
                  position: 'absolute', top: -size * 0.025, left: '50%', transform: 'translateX(-50%)',
                  width: size * 0.04, height: size * 0.04, borderRadius: '50%',
                  backgroundColor: visorColor, boxShadow: `0 0 ${size * 0.04}px ${visorColor}`,
                }} />
              </div>
            )}
          </div>
        )}

        {/* Head */}
        <div
          className="relative overflow-hidden"
          style={{
            width: size * 0.58, height: size * 0.44,
            borderRadius: size * 0.14,
            background: `linear-gradient(135deg, ${bodyColor}, ${bodyColor}dd)`,
            marginTop: size * 0.1,
            border: `2px solid ${bodyColor}66`,
            boxShadow: `0 0 ${size * 0.08}px ${bodyColor}33, inset 0 2px 4px rgba(255,255,255,0.12)`,
          }}
        >
          {/* Visor screen */}
          <div
            className="absolute flex items-center justify-center"
            style={{
              top: '12%', left: '10%', width: '80%', height: '76%',
              borderRadius: size * 0.08,
              background: 'linear-gradient(180deg, #080818 0%, #0e0e24 100%)',
              border: `1px solid ${visorColor}22`,
              boxShadow: `inset 0 0 ${size * 0.03}px ${visorColor}15`,
            }}
          >
            <PixelFace personality={personality} state={state} size={size} gazeX={gazeX} />
          </div>
        </div>

        {/* Body */}
        <div
          className="relative"
          style={{
            width: size * 0.4, height: size * 0.32,
            borderRadius: `${size * 0.12}px / ${size * 0.13}px`,
            background: `linear-gradient(180deg, ${bodyColor} 0%, ${bodyColor}cc 100%)`,
            border: `2px solid ${bodyColor}66`,
            boxShadow: `0 4px ${size * 0.04}px ${bodyColor}22`,
            marginTop: -2,
          }}
        >
          {/* Chest light */}
          <div className="robot-chest-pulse" style={{
            position: 'absolute', top: '22%', left: '50%', transform: 'translateX(-50%)',
            width: size * 0.05, height: size * 0.05, borderRadius: '50%',
            backgroundColor: visorColor, boxShadow: `0 0 ${size * 0.06}px ${visorColor}`,
          }} />
          <div style={{
            position: 'absolute', top: '48%', left: '50%', transform: 'translateX(-50%)',
            width: size * 0.16, height: 2, backgroundColor: `${visorColor}33`, borderRadius: 1,
          }} />
          <div style={{
            position: 'absolute', top: '58%', left: '50%', transform: 'translateX(-50%)',
            width: size * 0.12, height: 2, backgroundColor: `${visorColor}22`, borderRadius: 1,
          }} />
        </div>

        {/* Left arm */}
        <div
          className={cn(isWaving && 'robot-wave-left')}
          style={{
            position: 'absolute', top: size * 0.5,
            left: size * 0.5 - size * 0.2 - size * 0.22,
            width: size * 0.22, height: size * 0.04,
            borderRadius: size * 0.02, backgroundColor: bodyColor,
            transformOrigin: 'right center',
            transform: isThinking ? 'rotate(-30deg)' : 'rotate(5deg)',
            transition: 'transform 0.5s ease',
          }}
        >
          <div style={{
            position: 'absolute', left: -size * 0.025, top: -size * 0.015,
            width: size * 0.06, height: size * 0.06, borderRadius: '50%',
            backgroundColor: bodyColor, border: `1.5px solid ${bodyColor}88`,
          }} />
        </div>

        {/* Right arm */}
        <div
          className={cn(isWaving && 'robot-wave-right')}
          style={{
            position: 'absolute', top: size * 0.5,
            right: size * 0.5 - size * 0.2 - size * 0.22,
            width: size * 0.22, height: size * 0.04,
            borderRadius: size * 0.02, backgroundColor: bodyColor,
            transformOrigin: 'left center',
            transform:
              pointAngle !== null
                ? `rotate(${pointAngle}deg)`
                : isWaving
                  ? 'rotate(-60deg)'
                  : 'rotate(-5deg)',
            transition: 'transform 0.5s ease',
          }}
        >
          <div style={{
            position: 'absolute', right: -size * 0.025, top: -size * 0.015,
            width: size * 0.06, height: size * 0.06, borderRadius: '50%',
            backgroundColor: bodyColor, border: `1.5px solid ${bodyColor}88`,
          }} />
        </div>

        {/* Tool indicator */}
        {isUsingTool && (
          <div className="robot-tool-bounce" style={{
            position: 'absolute', top: size * 0.4, right: size * 0.06, fontSize: size * 0.1,
          }}>
            {renderedTool}
          </div>
        )}

        {/* Feet */}
        <div className="flex justify-center" style={{ gap: size * 0.05, marginTop: -1 }}>
          <div style={{
            width: size * 0.09, height: size * 0.05, backgroundColor: bodyColor,
            borderBottomLeftRadius: size * 0.04, borderBottomRightRadius: size * 0.04,
          }} />
          <div style={{
            width: size * 0.09, height: size * 0.05, backgroundColor: bodyColor,
            borderBottomLeftRadius: size * 0.04, borderBottomRightRadius: size * 0.04,
          }} />
        </div>

        {/* Ground glow */}
        <div className="robot-ground-glow" style={{
          position: 'absolute', bottom: 0, left: '50%', transform: 'translateX(-50%)',
          width: size * 0.35, height: size * 0.03, borderRadius: '50%',
          backgroundColor: visorColor, opacity: 0.2, filter: `blur(${size * 0.02}px)`,
        }} />
      </div>
      </div>

      <style jsx>{`
        .robot-sticky { position: relative; filter: drop-shadow(2px 4px 8px rgba(0,0,0,0.12)); }
        .robot-entrance { animation: robot-slide-in 0.8s cubic-bezier(0.34,1.56,0.64,1) forwards; }
        @keyframes robot-slide-in {
          0% { opacity: 0; transform: translateY(80px) scale(0.3); }
          60% { opacity: 1; transform: translateY(-8px) scale(1.05); }
          100% { opacity: 1; transform: translateY(0) scale(1); }
        }
        .robot-float { animation: robot-float 4s ease-in-out infinite; }
        .robot-think { animation: robot-think 2.5s ease-in-out infinite; }
        .robot-wave-body { animation: robot-wave-body 1.4s ease-in-out; }
        .robot-wave-right { animation: robot-wave-hand 1.4s ease-in-out; transform-origin: left center; }
        .robot-antenna-tip { animation: antenna-glow 1.5s ease-in-out infinite; }
        .robot-chest-pulse { animation: chest-pulse 2s ease-in-out infinite; }
        .robot-ground-glow { animation: ground-glow 3s ease-in-out infinite; }
        .robot-tool-bounce { animation: tool-bounce 0.6s ease-in-out infinite; }
        .robot-bubble { animation: bubble-appear 0.3s ease-out; }
        @keyframes robot-float { 0%,100% { transform: translateY(0); } 50% { transform: translateY(-6px); } }
        @keyframes robot-think { 0%,100% { transform: translateY(0) rotate(-1deg); } 50% { transform: translateY(-4px) rotate(1deg); } }
        @keyframes robot-wave-body { 0%,100% { transform: rotate(0); } 15% { transform: rotate(-3deg); } 35% { transform: rotate(3deg); } 55% { transform: rotate(-2deg); } 75% { transform: rotate(2deg); } }
        @keyframes robot-wave-hand { 0%,100% { transform: rotate(0); } 12% { transform: rotate(-40deg); } 24% { transform: rotate(-15deg); } 36% { transform: rotate(-40deg); } 48% { transform: rotate(-15deg); } }
        @keyframes antenna-glow { 0%,100% { opacity: 0.7; } 50% { opacity: 1; } }
        @keyframes chest-pulse { 0%,100% { opacity: 0.5; transform: translateX(-50%) scale(1); } 50% { opacity: 1; transform: translateX(-50%) scale(1.2); } }
        @keyframes ground-glow { 0%,100% { opacity: 0.15; transform: translateX(-50%) scaleX(1); } 50% { opacity: 0.3; transform: translateX(-50%) scaleX(1.15); } }
        @keyframes tool-bounce { 0%,100% { transform: translateY(0); } 50% { transform: translateY(-4px); } }
        @keyframes bubble-appear { from { opacity: 0; transform: translateX(-50%) translateY(8px) scale(0.9); } to { opacity: 1; transform: translateX(-50%) translateY(0) scale(1); } }
        @media (prefers-reduced-motion: reduce) {
          .robot-entrance, .robot-float, .robot-think, .robot-wave-body, .robot-wave-right,
          .robot-antenna-tip, .robot-chest-pulse, .robot-ground-glow, .robot-tool-bounce { animation: none !important; }
          .robot-entrance { opacity: 1; transform: none; }
        }
      `}</style>
    </div>
  );
};

AgentRobot.displayName = 'AgentRobot';
