'use client';

import React from 'react';
import { Card } from '@/components/molecules/Card';
import { Badge } from '@/components/atoms/Badge';

interface PipelineStage {
  label: string;
  count: number;
  status: 'active' | 'warning' | 'idle';
}

interface PipelineFlowDiagramProps {
  ingested: number;
  enriched: number;
  autoApproved: number;
  sentToHitl: number;
  exported: number;
  className?: string;
}

export function PipelineFlowDiagram({
  ingested,
  enriched,
  autoApproved,
  sentToHitl,
  exported,
  className,
}: PipelineFlowDiagramProps) {
  const stages: PipelineStage[] = [
    { label: 'Ingested', count: ingested, status: 'active' },
    { label: 'Enriched', count: enriched, status: 'active' },
    { label: 'Auto-Approved', count: autoApproved, status: 'active' },
    { label: 'Sent to HITL', count: sentToHitl, status: sentToHitl > 100 ? 'warning' : 'active' },
    { label: 'Exported', count: exported, status: 'active' },
  ];

  const statusColors = {
    active: 'bg-lime-100 text-lime-700 dark:bg-lime-900 dark:text-lime-300',
    warning: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900 dark:text-yellow-300',
    idle: 'bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400',
  };

  const stageColors = {
    active: 'border-ocean-300 dark:border-ocean-600',
    warning: 'border-yellow-400 dark:border-yellow-600',
    idle: 'border-gray-300 dark:border-gray-600',
  };

  return (
    <Card className={`p-6 ${className ?? ''}`}>
      <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-6">
        Pipeline Flow
      </h3>
      <div className="flex flex-wrap items-center gap-2">
        {stages.map((stage, index) => (
          <React.Fragment key={stage.label}>
            <div
              className={`flex flex-col items-center p-4 border-2 rounded-lg min-w-[100px] ${stageColors[stage.status]}`}
            >
              <span className="text-2xl font-bold text-gray-900 dark:text-white">
                {stage.count.toLocaleString()}
              </span>
              <span className="text-xs text-gray-600 dark:text-gray-400 mt-1">{stage.label}</span>
              <Badge className={`mt-2 text-xs ${statusColors[stage.status]}`}>
                {stage.status.toUpperCase()}
              </Badge>
            </div>
            {index < stages.length - 1 && (
              <span className="text-2xl text-gray-400 dark:text-gray-500 font-bold">→</span>
            )}
          </React.Fragment>
        ))}
      </div>
    </Card>
  );
}

export default PipelineFlowDiagram;
