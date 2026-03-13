import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { returnsService } from '../services/returnsService';
import type { CreateReturnRequest } from '../types/api';

export function useReturns() {
  return useQuery({
    queryKey: ['returns'],
    queryFn: () => returnsService.list(),
  });
}

export function useReturn(returnId: string) {
  return useQuery({
    queryKey: ['returns', returnId],
    queryFn: () => returnsService.get(returnId),
    enabled: Boolean(returnId),
  });
}

export function useRefundProgress(returnId: string) {
  return useQuery({
    queryKey: ['returns', returnId, 'refund'],
    queryFn: () => returnsService.getRefundProgress(returnId),
    enabled: Boolean(returnId),
  });
}

export function useCreateReturn() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (request: CreateReturnRequest) => returnsService.create(request),
    onSuccess: (payload) => {
      queryClient.invalidateQueries({ queryKey: ['returns'] });
      queryClient.invalidateQueries({ queryKey: ['orders'] });
      queryClient.invalidateQueries({ queryKey: ['order', payload.order_id] });
    },
  });
}
