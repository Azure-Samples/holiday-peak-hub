/**
 * React Query hooks for inventory health and reservation lifecycle.
 */

import { useMutation, useQueries, useQuery } from '@tanstack/react-query';
import { inventoryService } from '../services/inventoryService';
import type {
  CreateReservationRequest,
  ReservationActionRequest,
} from '../types/api';

export function useInventoryHealth() {
  return useQuery({
    queryKey: ['inventory', 'health'],
    queryFn: () => inventoryService.getHealth(),
    staleTime: 30_000,
  });
}

export function useReservationOutcomeQueries(reservationIds: string[]) {
  return useQueries({
    queries: reservationIds.map((reservationId) => ({
      queryKey: ['inventory', 'reservation', reservationId],
      queryFn: () => inventoryService.getReservation(reservationId),
      enabled: reservationId.length > 0,
      staleTime: 5_000,
    })),
  });
}

export function useCreateReservation() {
  return useMutation({
    mutationFn: (request: CreateReservationRequest) => inventoryService.createReservation(request),
  });
}

export function useConfirmReservation() {
  return useMutation({
    mutationFn: ({
      reservationId,
      request,
    }: {
      reservationId: string;
      request: ReservationActionRequest;
    }) => inventoryService.confirmReservation(reservationId, request),
  });
}

export function useReleaseReservation() {
  return useMutation({
    mutationFn: ({
      reservationId,
      request,
    }: {
      reservationId: string;
      request: ReservationActionRequest;
    }) => inventoryService.releaseReservation(reservationId, request),
  });
}
