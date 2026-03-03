import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { truthService } from '../services/truthService';
import type { ReviewActionRequest } from '../types/api';

export function useReviewQueue(params?: {
  page?: number;
  page_size?: number;
  category?: string;
  min_confidence?: number;
  max_confidence?: number;
  source?: string;
  sort?: 'confidence_asc' | 'confidence_desc' | 'date_asc' | 'date_desc';
}) {
  return useQuery({
    queryKey: ['staff', 'review', 'queue', params],
    queryFn: () => truthService.getReviewQueue(params),
  });
}

export function useReviewStats() {
  return useQuery({
    queryKey: ['staff', 'review', 'stats'],
    queryFn: () => truthService.getReviewStats(),
  });
}

export function useProductReviewDetail(entityId: string) {
  return useQuery({
    queryKey: ['staff', 'review', 'detail', entityId],
    queryFn: () => truthService.getProductReviewDetail(entityId),
    enabled: Boolean(entityId),
  });
}

export function useAuditHistory(entityId: string) {
  return useQuery({
    queryKey: ['staff', 'review', 'audit', entityId],
    queryFn: () => truthService.getAuditHistory(entityId),
    enabled: Boolean(entityId),
  });
}

export function useReviewAction() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      proposalId,
      action,
    }: {
      proposalId: string;
      action: ReviewActionRequest;
    }) => truthService.submitReviewAction(proposalId, action),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['staff', 'review'] });
    },
  });
}
