'use client';

import { useMemo, useState } from 'react';
import { MainLayout } from '@/components/templates/MainLayout';
import { Card } from '@/components/molecules/Card';
import { Input } from '@/components/atoms/Input';
import { useStaffShipments } from '@/lib/hooks/useStaff';

export default function LogisticsTrackingPage() {
  const [query, setQuery] = useState('');
  const { data: shipments = [], isLoading, isError } = useStaffShipments();

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) {
      return shipments;
    }
    return shipments.filter(
      (shipment) =>
        shipment.id.toLowerCase().includes(q) ||
        shipment.order_id.toLowerCase().includes(q) ||
        shipment.tracking_number.toLowerCase().includes(q) ||
        shipment.status.toLowerCase().includes(q)
    );
  }, [shipments, query]);

  return (
    <MainLayout>
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white">Logistics Tracking</h1>
          <p className="text-gray-600 dark:text-gray-400 mt-1">Consult shipment status from the staff shipments endpoint.</p>
        </div>

        <Card className="p-4">
          <Input
            type="text"
            placeholder="Filter by shipment id, order id, tracking number or status"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
          />
        </Card>

        <Card className="overflow-x-auto">
          {isLoading ? (
            <div className="p-6 text-gray-600 dark:text-gray-400">Loading shipments...</div>
          ) : isError ? (
            <div className="p-6 text-red-600 dark:text-red-400">Shipments could not be loaded.</div>
          ) : (
            <table className="min-w-full text-sm">
              <thead className="bg-gray-100 dark:bg-gray-800 text-left">
                <tr>
                  <th className="px-4 py-3">Shipment</th>
                  <th className="px-4 py-3">Order</th>
                  <th className="px-4 py-3">Carrier</th>
                  <th className="px-4 py-3">Tracking</th>
                  <th className="px-4 py-3">Status</th>
                  <th className="px-4 py-3">Created</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((shipment) => (
                  <tr key={shipment.id} className="border-t border-gray-200 dark:border-gray-700">
                    <td className="px-4 py-3">{shipment.id}</td>
                    <td className="px-4 py-3">{shipment.order_id}</td>
                    <td className="px-4 py-3">{shipment.carrier}</td>
                    <td className="px-4 py-3">{shipment.tracking_number}</td>
                    <td className="px-4 py-3">{shipment.status}</td>
                    <td className="px-4 py-3">{new Date(shipment.created_at).toLocaleString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </Card>
      </div>
    </MainLayout>
  );
}
