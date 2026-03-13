import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { staffService } from '../services/staffService';
import type {
  CreateTicketRequest,
  EscalateTicketRequest,
  ReturnTransitionRequest,
  ResolveTicketRequest,
  UpdateTicketRequest,
} from '../types/api';

type UpdateTicketMutationArgs = { ticketId: string; request: UpdateTicketRequest };
type ResolveTicketMutationArgs = { ticketId: string; request: ResolveTicketRequest };
type EscalateTicketMutationArgs = { ticketId: string; request: EscalateTicketRequest };
type StaffReturnMutationArgs = { returnId: string; request: ReturnTransitionRequest };

export function useStaffAnalyticsSummary() {
  return useQuery({
    queryKey: ['staff', 'analytics', 'summary'],
    queryFn: () => staffService.getAnalyticsSummary(),
  });
}

export function useStaffTickets() {
  return useQuery({
    queryKey: ['staff', 'tickets'],
    queryFn: () => staffService.listTickets(),
  });
}

export function useStaffReturns() {
  return useQuery({
    queryKey: ['staff', 'returns'],
    queryFn: () => staffService.listReturns(),
  });
}

export function useStaffShipments() {
  return useQuery({
    queryKey: ['staff', 'shipments'],
    queryFn: () => staffService.listShipments(),
  });
}

export function useStaffReturn(returnId: string) {
  return useQuery({
    queryKey: ['staff', 'returns', returnId],
    queryFn: () => staffService.getReturn(returnId),
    enabled: Boolean(returnId),
  });
}

export function useStaffReturnRefundProgress(returnId: string) {
  return useQuery({
    queryKey: ['staff', 'returns', returnId, 'refund'],
    queryFn: () => staffService.getReturnRefundProgress(returnId),
    enabled: Boolean(returnId),
  });
}

export function useCreateStaffTicket() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (request: CreateTicketRequest) => staffService.createTicket(request),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['staff', 'tickets'] });
    },
  });
}

export function useUpdateStaffTicket() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ ticketId, request }: UpdateTicketMutationArgs) =>
      staffService.updateTicket(ticketId, request),
    onSuccess: (_, { ticketId }) => {
      queryClient.invalidateQueries({ queryKey: ['staff', 'tickets'] });
      queryClient.invalidateQueries({ queryKey: ['staff', 'tickets', ticketId] });
    },
  });
}

export function useResolveStaffTicket() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ ticketId, request }: ResolveTicketMutationArgs) =>
      staffService.resolveTicket(ticketId, request),
    onSuccess: (_, { ticketId }) => {
      queryClient.invalidateQueries({ queryKey: ['staff', 'tickets'] });
      queryClient.invalidateQueries({ queryKey: ['staff', 'tickets', ticketId] });
    },
  });
}

export function useEscalateStaffTicket() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ ticketId, request }: EscalateTicketMutationArgs) =>
      staffService.escalateTicket(ticketId, request),
    onSuccess: (_, { ticketId }) => {
      queryClient.invalidateQueries({ queryKey: ['staff', 'tickets'] });
      queryClient.invalidateQueries({ queryKey: ['staff', 'tickets', ticketId] });
    },
  });
}

export function useApproveStaffReturn() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ returnId, request }: StaffReturnMutationArgs) =>
      staffService.approveReturn(returnId, request),
    onSuccess: (_, { returnId }) => {
      queryClient.invalidateQueries({ queryKey: ['staff', 'returns'] });
      queryClient.invalidateQueries({ queryKey: ['staff', 'returns', returnId] });
      queryClient.invalidateQueries({ queryKey: ['staff', 'returns', returnId, 'refund'] });
      queryClient.invalidateQueries({ queryKey: ['returns'] });
      queryClient.invalidateQueries({ queryKey: ['returns', returnId] });
    },
  });
}

export function useRejectStaffReturn() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ returnId, request }: StaffReturnMutationArgs) =>
      staffService.rejectReturn(returnId, request),
    onSuccess: (_, { returnId }) => {
      queryClient.invalidateQueries({ queryKey: ['staff', 'returns'] });
      queryClient.invalidateQueries({ queryKey: ['staff', 'returns', returnId] });
      queryClient.invalidateQueries({ queryKey: ['staff', 'returns', returnId, 'refund'] });
      queryClient.invalidateQueries({ queryKey: ['returns'] });
      queryClient.invalidateQueries({ queryKey: ['returns', returnId] });
    },
  });
}

export function useReceiveStaffReturn() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ returnId, request }: StaffReturnMutationArgs) =>
      staffService.receiveReturn(returnId, request),
    onSuccess: (_, { returnId }) => {
      queryClient.invalidateQueries({ queryKey: ['staff', 'returns'] });
      queryClient.invalidateQueries({ queryKey: ['staff', 'returns', returnId] });
      queryClient.invalidateQueries({ queryKey: ['staff', 'returns', returnId, 'refund'] });
      queryClient.invalidateQueries({ queryKey: ['returns'] });
      queryClient.invalidateQueries({ queryKey: ['returns', returnId] });
    },
  });
}

export function useRestockStaffReturn() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ returnId, request }: StaffReturnMutationArgs) =>
      staffService.restockReturn(returnId, request),
    onSuccess: (_, { returnId }) => {
      queryClient.invalidateQueries({ queryKey: ['staff', 'returns'] });
      queryClient.invalidateQueries({ queryKey: ['staff', 'returns', returnId] });
      queryClient.invalidateQueries({ queryKey: ['staff', 'returns', returnId, 'refund'] });
      queryClient.invalidateQueries({ queryKey: ['returns'] });
      queryClient.invalidateQueries({ queryKey: ['returns', returnId] });
    },
  });
}

export function useRefundStaffReturn() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ returnId, request }: StaffReturnMutationArgs) =>
      staffService.refundReturn(returnId, request),
    onSuccess: (_, { returnId }) => {
      queryClient.invalidateQueries({ queryKey: ['staff', 'returns'] });
      queryClient.invalidateQueries({ queryKey: ['staff', 'returns', returnId] });
      queryClient.invalidateQueries({ queryKey: ['staff', 'returns', returnId, 'refund'] });
      queryClient.invalidateQueries({ queryKey: ['returns'] });
      queryClient.invalidateQueries({ queryKey: ['returns', returnId] });
      queryClient.invalidateQueries({ queryKey: ['returns', returnId, 'refund'] });
    },
  });
}
