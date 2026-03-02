import { useQuery } from '@tanstack/react-query';
import { staffService } from '../services/staffService';

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
