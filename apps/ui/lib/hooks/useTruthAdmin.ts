import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { truthAdminService } from '../services/truthAdminService';
import type { CategorySchema, TenantConfig } from '../types/api';

export function useTruthSchemas() {
  return useQuery({
    queryKey: ['truth', 'schemas'],
    queryFn: () => truthAdminService.listSchemas(),
  });
}

export function useTruthSchema(id: string) {
  return useQuery({
    queryKey: ['truth', 'schemas', id],
    queryFn: () => truthAdminService.getSchema(id),
    enabled: !!id,
  });
}

export function useCreateTruthSchema() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (schema: Omit<CategorySchema, 'id' | 'created_at' | 'updated_at'>) =>
      truthAdminService.createSchema(schema),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['truth', 'schemas'] });
    },
  });
}

export function useUpdateTruthSchema() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, schema }: { id: string; schema: Partial<CategorySchema> }) =>
      truthAdminService.updateSchema(id, schema),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['truth', 'schemas'] });
    },
  });
}

export function useDeleteTruthSchema() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => truthAdminService.deleteSchema(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['truth', 'schemas'] });
    },
  });
}

export function useTruthConfig() {
  return useQuery({
    queryKey: ['truth', 'config'],
    queryFn: () => truthAdminService.getConfig(),
  });
}

export function useUpdateTruthConfig() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (config: Partial<TenantConfig>) => truthAdminService.updateConfig(config),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['truth', 'config'] });
    },
  });
}

export function useTruthAnalyticsSummary() {
  return useQuery({
    queryKey: ['truth', 'analytics', 'summary'],
    queryFn: () => truthAdminService.getAnalyticsSummary(),
  });
}

export function useTruthCompletenessBreakdown() {
  return useQuery({
    queryKey: ['truth', 'analytics', 'completeness'],
    queryFn: () => truthAdminService.getCompletenessBreakdown(),
  });
}

export function useTruthPipelineThroughput() {
  return useQuery({
    queryKey: ['truth', 'analytics', 'throughput'],
    queryFn: () => truthAdminService.getPipelineThroughput(),
  });
}
