import { redirect } from 'next/navigation';

export default function AdminServiceFallbackRedirectPage() {
  redirect('/admin/enrichment-monitor');
}