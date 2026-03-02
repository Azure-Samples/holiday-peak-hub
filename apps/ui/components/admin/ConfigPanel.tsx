'use client';

import React, { useState, useEffect } from 'react';
import { Card } from '@/components/molecules/Card';
import { Button } from '@/components/atoms/Button';
import type { TenantConfig } from '@/lib/types/api';

interface ConfigPanelProps {
  config: TenantConfig;
  onSave: (config: Partial<TenantConfig>) => void;
  isSaving?: boolean;
}

export function ConfigPanel({ config, onSave, isSaving }: ConfigPanelProps) {
  const [threshold, setThreshold] = useState(String(config.auto_approve_threshold));
  const [enrichmentEnabled, setEnrichmentEnabled] = useState(config.enrichment_enabled);
  const [hitlEnabled, setHitlEnabled] = useState(config.hitl_enabled);
  const [writebackEnabled, setWritebackEnabled] = useState(config.writeback_enabled);
  const [writebackDryRun, setWritebackDryRun] = useState(config.writeback_dry_run);
  const [featureFlags, setFeatureFlags] = useState<Record<string, boolean>>(config.feature_flags ?? {});
  const [newFlagKey, setNewFlagKey] = useState('');

  useEffect(() => {
    setThreshold(String(config.auto_approve_threshold));
    setEnrichmentEnabled(config.enrichment_enabled);
    setHitlEnabled(config.hitl_enabled);
    setWritebackEnabled(config.writeback_enabled);
    setWritebackDryRun(config.writeback_dry_run);
    setFeatureFlags(config.feature_flags ?? {});
  }, [config]);

  function handleSave() {
    const parsed = parseFloat(threshold);
    onSave({
      auto_approve_threshold: isNaN(parsed) ? config.auto_approve_threshold : parsed,
      enrichment_enabled: enrichmentEnabled,
      hitl_enabled: hitlEnabled,
      writeback_enabled: writebackEnabled,
      writeback_dry_run: writebackDryRun,
      feature_flags: featureFlags,
    });
  }

  function toggleFlag(key: string) {
    setFeatureFlags((prev) => ({ ...prev, [key]: !prev[key] }));
  }

  function addFlag() {
    const key = newFlagKey.trim();
    if (key && !(key in featureFlags)) {
      setFeatureFlags((prev) => ({ ...prev, [key]: false }));
      setNewFlagKey('');
    }
  }

  function removeFlag(key: string) {
    setFeatureFlags((prev) => {
      const next = { ...prev };
      delete next[key];
      return next;
    });
  }

  return (
    <Card className="p-6">
      <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-6">Tenant Configuration</h3>

      <div className="space-y-6">
        {/* Thresholds */}
        <div>
          <h4 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">Thresholds</h4>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm text-gray-600 dark:text-gray-400 mb-1">
                Auto-Approve Threshold (0–1)
              </label>
              <input
                type="number"
                min={0}
                max={1}
                step={0.01}
                value={threshold}
                onChange={(e) => setThreshold(e.target.value)}
                className="w-full rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-sm text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-ocean-500"
              />
            </div>
          </div>
        </div>

        {/* Toggles */}
        <div>
          <h4 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">Pipeline Toggles</h4>
          <div className="space-y-3">
            <ToggleRow
              label="Enrichment Enabled"
              description="Run AI enrichment pipeline on product ingestion"
              checked={enrichmentEnabled}
              onChange={setEnrichmentEnabled}
            />
            <ToggleRow
              label="HITL Review Enabled"
              description="Send low-confidence enrichments to human review queue"
              checked={hitlEnabled}
              onChange={setHitlEnabled}
            />
            <ToggleRow
              label="PIM Writeback Enabled"
              description="Write approved enrichments back to source PIM system"
              checked={writebackEnabled}
              onChange={setWritebackEnabled}
            />
            {writebackEnabled && (
              <ToggleRow
                label="Writeback Dry Run"
                description="Generate diff without writing to source system"
                checked={writebackDryRun}
                onChange={setWritebackDryRun}
              />
            )}
          </div>
        </div>

        {/* Feature Flags */}
        <div>
          <h4 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">Feature Flags</h4>
          <div className="space-y-2 mb-3">
            {Object.entries(featureFlags).map(([key, value]) => (
              <div key={key} className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-800 rounded-lg">
                <div className="flex items-center gap-3">
                  <input
                    type="checkbox"
                    checked={value}
                    onChange={() => toggleFlag(key)}
                    className="accent-ocean-500"
                    id={`flag-${key}`}
                  />
                  <label htmlFor={`flag-${key}`} className="text-sm font-mono text-gray-900 dark:text-white cursor-pointer">
                    {key}
                  </label>
                </div>
                <Button
                  onClick={() => removeFlag(key)}
                  variant="ghost"
                  size="sm"
                  className="text-red-500 hover:text-red-700"
                >
                  Remove
                </Button>
              </div>
            ))}
            {Object.keys(featureFlags).length === 0 && (
              <p className="text-sm text-gray-500 dark:text-gray-400">No feature flags configured.</p>
            )}
          </div>
          <div className="flex gap-2">
            <input
              value={newFlagKey}
              onChange={(e) => setNewFlagKey(e.target.value)}
              placeholder="new_feature_flag"
              className="flex-1 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-sm font-mono text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-ocean-500"
              onKeyDown={(e: React.KeyboardEvent<HTMLInputElement>) => e.key === 'Enter' && addFlag()}
            />
            <Button onClick={addFlag} variant="secondary" size="sm">
              Add Flag
            </Button>
          </div>
        </div>

        <div className="flex justify-end">
          <Button onClick={handleSave} disabled={isSaving}>
            {isSaving ? 'Saving...' : 'Save Configuration'}
          </Button>
        </div>
      </div>
    </Card>
  );
}

function ToggleRow({
  label,
  description,
  checked,
  onChange,
}: {
  label: string;
  description: string;
  checked: boolean;
  onChange: (v: boolean) => void;
}) {
  return (
    <div className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-800 rounded-lg">
      <div>
        <p className="text-sm font-medium text-gray-900 dark:text-white">{label}</p>
        <p className="text-xs text-gray-500 dark:text-gray-400">{description}</p>
      </div>
      <button
        role="switch"
        aria-checked={checked}
        onClick={() => onChange(!checked)}
        className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
          checked ? 'bg-ocean-500' : 'bg-gray-300 dark:bg-gray-600'
        }`}
      >
        <span
          className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
            checked ? 'translate-x-6' : 'translate-x-1'
          }`}
        />
      </button>
    </div>
  );
}

export default ConfigPanel;
