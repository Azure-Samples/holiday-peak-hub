'use client';

import React, { useState } from 'react';
import { Card } from '@/components/molecules/Card';
import { Button } from '@/components/atoms/Button';
import { Input } from '@/components/atoms/Input';
import { Select } from '@/components/atoms/Select';
import type { CategorySchema, SchemaField } from '@/lib/types/api';

interface SchemaEditorProps {
  schema?: CategorySchema;
  onSave: (data: Omit<CategorySchema, 'id' | 'created_at' | 'updated_at'>) => void;
  onCancel: () => void;
  isSaving?: boolean;
}

const FIELD_TYPES: SchemaField['type'][] = ['string', 'number', 'boolean', 'array', 'object'];

export function SchemaEditor({ schema, onSave, onCancel, isSaving }: SchemaEditorProps) {
  const [category, setCategory] = useState(schema?.category ?? '');
  const [version, setVersion] = useState(schema?.version ?? '1.0.0');
  const [fields, setFields] = useState<SchemaField[]>(schema?.fields ?? []);

  function addField() {
    setFields((prev) => [
      ...prev,
      { name: '', type: 'string', required: false, description: '' },
    ]);
  }

  function removeField(index: number) {
    setFields((prev) => prev.filter((_, i) => i !== index));
  }

  function updateField(index: number, partial: Partial<SchemaField>) {
    setFields((prev) => prev.map((f, i) => (i === index ? { ...f, ...partial } : f)));
  }

  function handleSave() {
    onSave({ category, version, fields });
  }

  const isValid = category.trim() !== '' && version.trim() !== '';

  return (
    <Card className="p-6">
      <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-6">
        {schema ? 'Edit Schema' : 'New Schema'}
      </h3>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            Category
          </label>
          <Input
            name="category"
            value={category}
            onChange={(e) => setCategory(e.target.value)}
            placeholder="e.g. electronics"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            Version
          </label>
          <Input
            name="version"
            value={version}
            onChange={(e) => setVersion(e.target.value)}
            placeholder="e.g. 1.0.0"
          />
        </div>
      </div>

      <div className="mb-4">
        <div className="flex items-center justify-between mb-3">
          <h4 className="text-sm font-semibold text-gray-700 dark:text-gray-300">Fields</h4>
          <Button onClick={addField} variant="secondary" size="sm">
            + Add Field
          </Button>
        </div>

        {fields.length === 0 && (
          <p className="text-sm text-gray-500 dark:text-gray-400 py-4 text-center">
            No fields defined. Add a field to get started.
          </p>
        )}

        <div className="space-y-3">
          {fields.map((field, index) => (
            <div
              key={index}
              className="grid grid-cols-1 md:grid-cols-4 gap-3 p-3 bg-gray-50 dark:bg-gray-800 rounded-lg"
            >
              <Input
                name={`field-name-${index}`}
                value={field.name}
                onChange={(e) => updateField(index, { name: e.target.value })}
                placeholder="Field name"
              />
              <Select
                name={`field-type-${index}`}
                value={field.type}
                onChange={(e) => updateField(index, { type: e.target.value as SchemaField['type'] })}
                options={FIELD_TYPES.map((t) => ({ value: t, label: t }))}
              />
              <Input
                name={`field-desc-${index}`}
                value={field.description ?? ''}
                onChange={(e) => updateField(index, { description: e.target.value })}
                placeholder="Description (optional)"
              />
              <div className="flex items-center gap-3">
                <label className="flex items-center gap-1 text-sm text-gray-700 dark:text-gray-300 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={field.required}
                    onChange={(e) => updateField(index, { required: e.target.checked })}
                    className="accent-ocean-500"
                  />
                  Required
                </label>
                <Button
                  onClick={() => removeField(index)}
                  variant="ghost"
                  size="sm"
                  className="text-red-500 hover:text-red-700"
                >
                  Remove
                </Button>
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="flex gap-3 justify-end mt-6">
        <Button onClick={onCancel} variant="secondary" disabled={isSaving}>
          Cancel
        </Button>
        <Button onClick={handleSave} disabled={!isValid || isSaving}>
          {isSaving ? 'Saving...' : 'Save Schema'}
        </Button>
      </div>
    </Card>
  );
}

export default SchemaEditor;
