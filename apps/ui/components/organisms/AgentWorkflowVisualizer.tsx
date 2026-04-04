'use client';

import React, { useEffect, useRef, useState } from 'react';
import { FaPlay, FaRobot, FaNetworkWired, FaCheckCircle, FaExclamationCircle } from 'react-icons/fa';
import { clsx } from 'clsx';

// Types
export type NodeType = 'trigger' | 'orchestrator' | 'specialist' | 'action' | 'condition';
export type NodeStatus = 'idle' | 'running' | 'success' | 'failed' | 'skipped';

export interface WorkflowNode {
  id: string;
  stage: number; // Column index (0, 1, 2...)
  order: number; // Row index within the stage
  type: NodeType;
  label: string;
  description?: string;
  status: NodeStatus;
  metrics?: { latency?: string; tokens?: string; cost?: string };
}

export interface WorkflowEdge {
  source: string;
  target: string;
  animated?: boolean;
  label?: string;
}

export interface WorkflowGraph {
  nodes: WorkflowNode[];
  edges: WorkflowEdge[];
}

interface VisualizerProps {
  graph: WorkflowGraph;
  activeNodeId?: string | null;
  onNodeClick?: (nodeId: string) => void;
}

// Icon Map
const typeIcons = {
  trigger: <span className="text-amber-500">⚡</span>,
  orchestrator: <FaNetworkWired className="text-purple-500" />,
  specialist: <FaRobot className="text-blue-500" />,
  action: <FaPlay className="text-green-500" />,
  condition: <span className="text-rose-500">?</span>,
};

const statusColors = {
  idle: 'border-gray-200 bg-gray-50 text-gray-500 dark:border-gray-700 dark:bg-gray-800',
  running: 'border-blue-400 bg-blue-50 shadow-[0_0_15px_rgba(59,130,246,0.5)] ring-2 ring-blue-500 animate-pulse text-blue-900 dark:bg-blue-900/30 dark:text-blue-100',
  success: 'border-green-300 bg-green-50 text-green-900 dark:border-green-800 dark:bg-green-900/20 dark:text-green-100',
  failed: 'border-red-300 bg-red-50 text-red-900 dark:border-red-800 dark:bg-red-900/20 dark:text-red-100',
  skipped: 'border-dashed border-gray-300 bg-gray-100/50 text-gray-400 dark:border-gray-600 dark:bg-gray-800/30 opacity-60',
};

const statusGlow = {
  idle: '',
  running: 'shadow-[0_0_20px_rgba(59,130,246,0.6)]',
  success: 'shadow-[0_0_15px_rgba(34,197,94,0.3)]',
  failed: 'shadow-[0_0_15px_rgba(239,68,68,0.5)]',
  skipped: '',
}

export function AgentWorkflowVisualizer({ graph, activeNodeId, onNodeClick }: VisualizerProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [nodeRects, setNodeRects] = useState<Record<string, { x: number; y: number; w: number; h: number }>>({});

  // Calculate layout and coordinates
  useEffect(() => {
    const updateLayout = () => {
      if (!containerRef.current) return;
      const cRect = containerRef.current.getBoundingClientRect();

      const newRects: Record<string, { x: number; y: number; w: number; h: number }> = {};
      graph.nodes.forEach((n) => {
        const el = document.getElementById(`wf-node-${n.id}`);
        if (el) {
          const elRect = el.getBoundingClientRect();
          newRects[n.id] = {
            x: elRect.left - cRect.left,
            y: elRect.top - cRect.top,
            w: elRect.width,
            h: elRect.height,
          };
        }
      });
      setNodeRects(newRects);
    };

    updateLayout();
    window.addEventListener('resize', updateLayout);
    // Small timeout to allow DOM layout to settle if fonts load
    const timer = setTimeout(updateLayout, 100);
    return () => {
      window.removeEventListener('resize', updateLayout);
      clearTimeout(timer);
    };
  }, [graph]);

  // Group nodes by stage to build grid
  const maxStage = Math.max(...graph.nodes.map(n => n.stage), 0);
  const stages = Array.from({ length: maxStage + 1 }, (_, i) => 
    graph.nodes.filter(n => n.stage === i).sort((a,b) => a.order - b.order)
  );

  return (
    <div className="relative w-full h-[600px] overflow-hidden bg-slate-50 dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 shadow-inner" ref={containerRef}>
      
      {/* SVG Layer for edges */}
      <svg className="absolute inset-0 pointer-events-none z-10" width="100%" height="100%">
        <defs>
          <linearGradient id="gradient-line" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="#3b82f6" />
            <stop offset="100%" stopColor="#8b5cf6" />
          </linearGradient>
          
          <marker id="arrowhead" markerWidth="6" markerHeight="4" refX="6" refY="2" orient="auto">
            <polygon points="0 0, 6 2, 0 4" fill="#9ca3af" />
          </marker>

          <marker id="arrowhead-active" markerWidth="6" markerHeight="4" refX="6" refY="2" orient="auto">
            <polygon points="0 0, 6 2, 0 4" fill="#3b82f6" />
          </marker>
        </defs>

        {graph.edges.map((edge, idx) => {
          const sRef = nodeRects[edge.source];
          const tRef = nodeRects[edge.target];
          if (!sRef || !tRef) return null;

          // Connect from right side of source to left side of target
          const startX = sRef.x + sRef.w;
          const startY = sRef.y + sRef.h / 2;
          const endX = tRef.x;
          const endY = tRef.y + tRef.h / 2;

          // Curve control points
          const cp1X = startX + (endX - startX) / 2;
          const cp1Y = startY;
          const cp2X = startX + (endX - startX) / 2;
          const cp2Y = endY;

          const d = `M ${startX} ${startY} C ${cp1X} ${cp1Y}, ${cp2X} ${cp2Y}, ${endX} ${endY}`;
          const isAnimated = edge.animated || 
            (graph.nodes.find(n => n.id === edge.source)?.status === 'running');
            
          const isSourceFailed = graph.nodes.find(n => n.id === edge.source)?.status === 'failed';

          return (
            <g key={`edge-${idx}`}>
              {/* Invisible thicker path for hovering/clicking (if we added interactions later) */}
              <path d={d} fill="none" stroke="transparent" strokeWidth="15" />
              
              {/* Base Path */}
              <path 
                d={d} 
                fill="none" 
                stroke={isSourceFailed ? '#ef4444' : isAnimated ? '#3b82f6' : '#9ca3af'} 
                strokeWidth={isAnimated ? 2.5 : 1.5}
                strokeDasharray={isAnimated ? '6,4' : 'none'}
                markerEnd={`url(#arrowhead${isAnimated ? '-active' : ''})`}
                className={clsx(
                  "transition-all duration-500",
                  isAnimated && "animate-[dash-move_1s_linear_infinite] opacity-80"
                )}
              />
              
              {/* Edge Label */}
              {edge.label && (
                <text 
                  x={(startX + endX) / 2} 
                  y={(startY + endY) / 2 - 8} 
                  textAnchor="middle" 
                  className="text-[10px] fill-gray-500 dark:fill-gray-400 font-mono"
                >
                  {edge.label}
                </text>
              )}
            </g>
          );
        })}
      </svg>

      {/* Nodes HTML Layer */}
      <div className="absolute inset-0 z-20 overflow-auto p-8 layout-container">
        <div 
          className="flex flex-row justify-between h-full min-w-max gap-16 lg:gap-24 items-center"
        >
          {stages.map((stageNodes, sIdx) => (
            <div key={`stage-${sIdx}`} className="flex flex-col gap-8 justify-center min-w-[240px]">
              {stageNodes.map(node => {
                const isActive = activeNodeId === node.id;
                
                return (
                  <div
                    key={node.id}
                    id={`wf-node-${node.id}`}
                    onClick={() => onNodeClick?.(node.id)}
                    className={clsx(
                      "relative flex flex-col p-4 rounded-lg border-2 transition-all duration-300 cursor-pointer shadow-sm hover:shadow-md",
                      statusColors[node.status],
                      statusGlow[node.status],
                      isActive && "ring-2 ring-offset-2 ring-offset-white dark:ring-offset-gray-900 ring-blue-500 scale-[1.02]",
                      (!isActive && activeNodeId) && "opacity-50 grayscale pt-0", // dim non-active
                      "backdrop-blur-sm backdrop-saturate-150"
                    )}
                  >
                    {/* Node Header - Icon & Type */}
                    <div className="flex items-center gap-2 mb-2">
                      <div className={clsx(
                        "w-8 h-8 rounded-full flex items-center justify-center bg-white dark:bg-gray-800 shadow-sm border border-gray-200 dark:border-gray-700",
                        node.status === 'running' && 'animate-spin-slow'
                      )}>
                        {typeIcons[node.type]}
                      </div>
                      <div>
                        <div className="text-[10px] font-bold uppercase tracking-wider opacity-70">
                          {node.type}
                        </div>
                        <div className="font-semibold text-sm leading-tight max-w-[160px] truncate">
                          {node.label}
                        </div>
                      </div>
                    </div>
                    
                    {/* Node Body - Description */}
                    {node.description && (
                      <div className="text-xs mt-1 mb-2 opacity-80 leading-relaxed text-balance">
                        {node.description}
                      </div>
                    )}
                    
                    {/* Status & Metrics */}
                    <div className="mt-auto pt-2 border-t border-black/5 dark:border-white/5 flex gap-3 text-[10px] font-mono justify-between">
                       <span className="flex items-center gap-1 font-medium">
                         {node.status === 'success' && <FaCheckCircle className="text-green-500"/>}
                         {node.status === 'failed' && <FaExclamationCircle className="text-red-500"/>}
                         {node.status === 'running' && <span className="w-2 h-2 rounded-full bg-blue-500 animate-ping"/>}
                         <span className="capitalize">{node.status}</span>
                       </span>
                       
                       {node.metrics && (
                         <span className="opacity-70 flex gap-2">
                           {node.metrics.latency && <span>⏱ {node.metrics.latency}</span>}
                           {node.metrics.tokens && <span>{node.metrics.tokens} tk</span>}
                         </span>
                       )}
                    </div>
                    
                  </div>
                );
              })}
            </div>
          ))}
        </div>
      </div>
      
      <style dangerouslySetInnerHTML={{__html: `
        @keyframes dash-move {
          to { stroke-dashoffset: -10; }
        }
        .layout-container {
          scrollbar-width: thin;
          scrollbar-color: rgba(156, 163, 175, 0.5) transparent;
        }
      `}} />
    </div>
  );
}
