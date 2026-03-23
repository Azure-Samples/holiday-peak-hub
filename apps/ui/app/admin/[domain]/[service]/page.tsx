'use client';

import { useParams } from 'next/navigation';
import AdminServiceDashboardPage from '@/components/admin/AdminServiceDashboardPage';
import type { AdminServiceDomain } from '@/lib/types/api';

const ALLOWED_DOMAINS: AdminServiceDomain[] = ['crm', 'ecommerce', 'inventory', 'logistics', 'products'];

function normalizeParam(value: string | string[] | undefined): string {
  if (Array.isArray(value)) {
    return value[0] || '';
  }
  return value || '';
}

export default function AdminServicePage() {
  const params = useParams<{ domain?: string | string[]; service?: string | string[] }>();
  const domainValue = normalizeParam(params?.domain);
  const serviceValue = normalizeParam(params?.service);

  const domain = ALLOWED_DOMAINS.includes(domainValue as AdminServiceDomain)
    ? (domainValue as AdminServiceDomain)
    : 'ecommerce';
  const service = serviceValue || 'catalog';

  return <AdminServiceDashboardPage domain={domain} service={service} />;
}