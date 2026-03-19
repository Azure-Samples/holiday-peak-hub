import React from 'react';
import { Card } from '../molecules/Card';

export interface AgentReasoningPanelProps {
  reasoning?: string;
  sourceAssets?: string[];
}

export const AgentReasoningPanel: React.FC<AgentReasoningPanelProps> = ({
  reasoning,
  sourceAssets = [],
}) => {
  return (
    <Card className="p-4 space-y-3">
      <h3 className="text-sm font-semibold text-gray-900 dark:text-white">Agent reasoning</h3>
      <p className="text-sm leading-6 text-gray-700 dark:text-gray-300">
        {reasoning || 'No reasoning details available.'}
      </p>

      {sourceAssets.length > 0 && (
        <div>
          <h4 className="text-xs font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400">
            Source assets
          </h4>
          <ul className="mt-2 space-y-1 text-sm">
            {sourceAssets.map((asset, index) => (
              <li key={`${asset}-${index}`}>
                <a
                  href={asset}
                  target="_blank"
                  rel="noreferrer"
                  className="text-blue-600 underline-offset-2 hover:underline focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 rounded"
                >
                  Asset {index + 1}
                </a>
              </li>
            ))}
          </ul>
        </div>
      )}
    </Card>
  );
};

AgentReasoningPanel.displayName = 'AgentReasoningPanel';
