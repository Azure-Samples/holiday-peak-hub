'use client';

import { useMemo, useState } from 'react';
import { MainLayout } from '@/components/templates/MainLayout';
import { Card } from '@/components/molecules/Card';
import { Input } from '@/components/atoms/Input';
import { Tabs } from '@/components/molecules/Tabs';
import { useStaffReturns, useStaffTickets } from '@/lib/hooks/useStaff';

export default function RequestsPage() {
  const [query, setQuery] = useState('');
  const { data: tickets = [], isLoading: loadingTickets, isError: ticketError } = useStaffTickets();
  const { data: returns = [], isLoading: loadingReturns, isError: returnError } = useStaffReturns();

  const filteredTickets = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) {
      return tickets;
    }
    return tickets.filter(
      (ticket) =>
        ticket.id.toLowerCase().includes(q) ||
        ticket.subject.toLowerCase().includes(q) ||
        ticket.status.toLowerCase().includes(q)
    );
  }, [tickets, query]);

  const filteredReturns = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) {
      return returns;
    }
    return returns.filter(
      (ret) =>
        ret.id.toLowerCase().includes(q) ||
        ret.order_id.toLowerCase().includes(q) ||
        ret.status.toLowerCase().includes(q)
    );
  }, [returns, query]);

  return (
    <MainLayout>
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white">Customer Requests</h1>
          <p className="text-gray-600 dark:text-gray-400 mt-1">Consult support tickets and returns from staff CRUD endpoints.</p>
        </div>

        <Card className="p-4">
          <Input
            type="text"
            placeholder="Filter by id, status, subject or order"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
          />
        </Card>

        <Tabs
          tabs={[
            {
              id: 'tickets',
              label: `Tickets (${filteredTickets.length})`,
              content: (
                <Card className="overflow-x-auto">
                  {loadingTickets ? (
                    <div className="p-6 text-gray-600 dark:text-gray-400">Loading tickets...</div>
                  ) : ticketError ? (
                    <div className="p-6 text-red-600 dark:text-red-400">Tickets could not be loaded.</div>
                  ) : (
                    <table className="min-w-full text-sm">
                      <thead className="bg-gray-100 dark:bg-gray-800 text-left">
                        <tr>
                          <th className="px-4 py-3">Ticket</th>
                          <th className="px-4 py-3">Subject</th>
                          <th className="px-4 py-3">Priority</th>
                          <th className="px-4 py-3">Status</th>
                          <th className="px-4 py-3">Created</th>
                        </tr>
                      </thead>
                      <tbody>
                        {filteredTickets.map((ticket) => (
                          <tr key={ticket.id} className="border-t border-gray-200 dark:border-gray-700">
                            <td className="px-4 py-3">{ticket.id}</td>
                            <td className="px-4 py-3">{ticket.subject}</td>
                            <td className="px-4 py-3">{ticket.priority}</td>
                            <td className="px-4 py-3">{ticket.status}</td>
                            <td className="px-4 py-3">{new Date(ticket.created_at).toLocaleString()}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  )}
                </Card>
              ),
            },
            {
              id: 'returns',
              label: `Returns (${filteredReturns.length})`,
              content: (
                <Card className="overflow-x-auto">
                  {loadingReturns ? (
                    <div className="p-6 text-gray-600 dark:text-gray-400">Loading returns...</div>
                  ) : returnError ? (
                    <div className="p-6 text-red-600 dark:text-red-400">Returns could not be loaded.</div>
                  ) : (
                    <table className="min-w-full text-sm">
                      <thead className="bg-gray-100 dark:bg-gray-800 text-left">
                        <tr>
                          <th className="px-4 py-3">Return</th>
                          <th className="px-4 py-3">Order</th>
                          <th className="px-4 py-3">Reason</th>
                          <th className="px-4 py-3">Status</th>
                          <th className="px-4 py-3">Created</th>
                        </tr>
                      </thead>
                      <tbody>
                        {filteredReturns.map((ret) => (
                          <tr key={ret.id} className="border-t border-gray-200 dark:border-gray-700">
                            <td className="px-4 py-3">{ret.id}</td>
                            <td className="px-4 py-3">{ret.order_id}</td>
                            <td className="px-4 py-3">{ret.reason}</td>
                            <td className="px-4 py-3">{ret.status}</td>
                            <td className="px-4 py-3">{new Date(ret.created_at).toLocaleString()}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  )}
                </Card>
              ),
            },
          ]}
        />
      </div>
    </MainLayout>
  );
}
