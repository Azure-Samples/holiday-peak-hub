'use client';

import React, { useState } from 'react';
import { MainLayout } from '@/components/templates/MainLayout';
import { Card } from '@/components/molecules/Card';
import { Button } from '@/components/atoms/Button';
import { Badge } from '@/components/atoms/Badge';
import { SchemaEditor } from '@/components/admin/SchemaEditor';
import {
  useTruthSchemas,
  useCreateTruthSchema,
  useUpdateTruthSchema,
  useDeleteTruthSchema,
} from '@/lib/hooks/useTruthAdmin';
import type { CategorySchema } from '@/lib/types/api';

export default function SchemasPage() {
  const { data: schemas = [], isLoading, isError } = useTruthSchemas();
  const createMutation = useCreateTruthSchema();
  const updateMutation = useUpdateTruthSchema();
  const deleteMutation = useDeleteTruthSchema();

  const [editingSchema, setEditingSchema] = useState<CategorySchema | null>(null);
  const [isCreating, setIsCreating] = useState(false);

  const isSaving = createMutation.isPending || updateMutation.isPending;

  function handleSave(data: Omit<CategorySchema, 'id' | 'created_at' | 'updated_at'>) {
    if (editingSchema) {
      updateMutation.mutate(
        { id: editingSchema.id, schema: data },
        {
          onSuccess: () => {
            setEditingSchema(null);
          },
        }
      );
    } else {
      createMutation.mutate(data, {
        onSuccess: () => {
          setIsCreating(false);
        },
      });
    }
  }

  function handleDelete(id: string) {
    if (confirm('Delete this schema?')) {
      deleteMutation.mutate(id);
    }
  }

  return (
    <MainLayout>
      <div className="max-w-5xl mx-auto py-8 space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-900 dark:text-white">Schema Management</h1>
            <p className="text-gray-600 dark:text-gray-400 mt-1">
              Define and manage category schemas for the Product Truth Layer.
            </p>
          </div>
          {!isCreating && !editingSchema && (
            <Button onClick={() => setIsCreating(true)}>+ New Schema</Button>
          )}
        </div>

        {(isCreating || editingSchema) && (
          <SchemaEditor
            schema={editingSchema ?? undefined}
            onSave={handleSave}
            onCancel={() => {
              setIsCreating(false);
              setEditingSchema(null);
            }}
            isSaving={isSaving}
          />
        )}

        {isLoading && (
          <Card className="p-6 text-gray-600 dark:text-gray-400">Loading schemas...</Card>
        )}

        {isError && (
          <Card className="p-6 border border-red-200 dark:border-red-900 text-red-600 dark:text-red-400">
            Failed to load schemas.
          </Card>
        )}

        {!isLoading && !isError && schemas.length === 0 && !isCreating && (
          <Card className="p-6 text-center text-gray-500 dark:text-gray-400">
            No schemas defined yet. Create one to get started.
          </Card>
        )}

        <div className="space-y-4">
          {schemas.map((schema) => (
            <Card key={schema.id} className="p-5">
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-3 mb-2">
                    <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                      {schema.category}
                    </h3>
                    <Badge className="bg-ocean-100 text-ocean-700 dark:bg-ocean-900 dark:text-ocean-300 text-xs">
                      v{schema.version}
                    </Badge>
                    <Badge className="bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400 text-xs">
                      {schema.fields.length} field{schema.fields.length !== 1 ? 's' : ''}
                    </Badge>
                  </div>
                  <p className="text-xs text-gray-500 dark:text-gray-400">
                    Last updated: {new Date(schema.updated_at).toLocaleDateString()}
                  </p>
                  <div className="mt-3 flex flex-wrap gap-2">
                    {schema.fields.map((field) => (
                      <span
                        key={field.name}
                        className="text-xs px-2 py-1 bg-gray-100 dark:bg-gray-800 rounded text-gray-700 dark:text-gray-300"
                      >
                        {field.name}
                        <span className="text-gray-400 dark:text-gray-500 ml-1">:{field.type}</span>
                        {field.required && (
                          <span className="text-red-400 ml-1">*</span>
                        )}
                      </span>
                    ))}
                  </div>
                </div>
                <div className="flex gap-2 ml-4">
                  <Button
                    onClick={() => setEditingSchema(schema)}
                    variant="secondary"
                    size="sm"
                    disabled={isCreating || !!editingSchema}
                  >
                    Edit
                  </Button>
                  <Button
                    onClick={() => handleDelete(schema.id)}
                    variant="ghost"
                    size="sm"
                    className="text-red-500 hover:text-red-700"
                    disabled={deleteMutation.isPending}
                  >
                    Delete
                  </Button>
                </div>
              </div>
            </Card>
          ))}
        </div>
      </div>
    </MainLayout>
  );
}
