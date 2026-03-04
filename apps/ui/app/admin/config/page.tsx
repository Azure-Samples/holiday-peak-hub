'use client';

import React from 'react';
import { MainLayout } from '@/components/templates/MainLayout';
import { Card } from '@/components/molecules/Card';
import { ConfigPanel } from '@/components/admin/ConfigPanel';
import { useTruthConfig, useUpdateTruthConfig } from '@/lib/hooks/useTruthAdmin';
import type { TenantConfig } from '@/lib/types/api';

export default function ConfigPage() {
  const { data: config, isLoading, isError } = useTruthConfig();
  const updateMutation = useUpdateTruthConfig();

  function handleSave(partial: Partial<TenantConfig>) {
    updateMutation.mutate(partial);
  }

  return (
    <MainLayout>
      <div className="max-w-3xl mx-auto py-8 space-y-6">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white">Tenant Configuration</h1>
          <p className="text-gray-600 dark:text-gray-400 mt-1">
            Manage thresholds, pipeline toggles, and feature flags for the Product Truth Layer.
          </p>
        </div>

        {updateMutation.isSuccess && (
          <Card className="p-4 border border-lime-300 dark:border-lime-700 bg-lime-50 dark:bg-lime-950 text-lime-700 dark:text-lime-300">
            Configuration saved successfully.
          </Card>
        )}

        {updateMutation.isError && (
          <Card className="p-4 border border-red-200 dark:border-red-900 bg-red-50 dark:bg-red-950 text-red-600 dark:text-red-400">
            Failed to save configuration. Please try again.
          </Card>
        )}

        {isLoading && (
          <Card className="p-6 text-gray-600 dark:text-gray-400">Loading configuration...</Card>
        )}

        {isError && (
          <Card className="p-6 border border-red-200 dark:border-red-900 text-red-600 dark:text-red-400">
            Failed to load configuration.
          </Card>
        )}

        {config && (
          <ConfigPanel
            config={config}
            onSave={handleSave}
            isSaving={updateMutation.isPending}
          />
        )}
      </div>
    </MainLayout>
  );
}
