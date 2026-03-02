'use client';

import { useMemo, useState } from 'react';
import { useSearchParams } from 'next/navigation';
import { MainLayout } from '@/components/templates/MainLayout';
import { Card } from '@/components/molecules/Card';
import { Input } from '@/components/atoms/Input';
import { Button } from '@/components/atoms/Button';
import { Badge } from '@/components/atoms/Badge';
import agentApiClient from '@/lib/api/agentClient';

type ChatEntry = {
  id: string;
  role: 'user' | 'agent';
  content: string;
};

export default function ProductEnrichmentChatPage() {
  const searchParams = useSearchParams();
  const initialSku = searchParams.get('sku') || '';

  const [sku, setSku] = useState(initialSku);
  const [message, setMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const [history, setHistory] = useState<ChatEntry[]>([]);

  const canSend = useMemo(() => message.trim().length > 0, [message]);

  const onSend = async () => {
    const trimmed = message.trim();
    if (!trimmed) {
      return;
    }

    setLoading(true);
    setHistory((prev) => [
      ...prev,
      {
        id: `${Date.now()}-user`,
        role: 'user',
        content: trimmed,
      },
    ]);

    try {
      const response = await agentApiClient.post('/ecommerce-product-detail-enrichment/invoke', {
        sku: sku || undefined,
        query: trimmed,
        message: trimmed,
      });

      const payload = response.data;
      const content = typeof payload === 'string' ? payload : JSON.stringify(payload, null, 2);

      setHistory((prev) => [
        ...prev,
        {
          id: `${Date.now()}-agent`,
          role: 'agent',
          content,
        },
      ]);
    } catch (error: unknown) {
      const detail =
        (error as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        'Agent request failed. Verify APIM route and auth context.';
      setHistory((prev) => [
        ...prev,
        {
          id: `${Date.now()}-error`,
          role: 'agent',
          content: detail,
        },
      ]);
    } finally {
      setMessage('');
      setLoading(false);
    }
  };

  return (
    <MainLayout>
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white">Product Enrichment Agent Chat</h1>
          <p className="text-gray-600 dark:text-gray-400 mt-1">Talk directly to the enrichment agent for product details and diagnostics.</p>
        </div>

        <Card className="p-4 flex flex-col sm:flex-row gap-3">
          <div className="sm:w-72">
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">SKU (optional)</label>
            <Input type="text" value={sku} onChange={(event) => setSku(event.target.value)} placeholder="seed-product-0001" />
          </div>
          <div className="flex-1">
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Message</label>
            <div className="flex gap-2">
              <Input
                type="text"
                value={message}
                onChange={(event) => setMessage(event.target.value)}
                placeholder="Ask about features, rating, inventory, related products..."
                onKeyDown={(event) => {
                  if (event.key === 'Enter') {
                    onSend();
                  }
                }}
              />
              <Button onClick={onSend} disabled={!canSend || loading}>
                {loading ? 'Sending...' : 'Send'}
              </Button>
            </div>
          </div>
        </Card>

        <Card className="p-4 space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Conversation</h2>
            <Badge className="bg-ocean-500 text-white">Agent endpoint: /ecommerce-product-detail-enrichment/invoke</Badge>
          </div>

          {history.length === 0 ? (
            <p className="text-gray-600 dark:text-gray-400">No messages yet. Start a conversation above.</p>
          ) : (
            <div className="space-y-3">
              {history.map((entry) => (
                <div
                  key={entry.id}
                  className={`rounded-lg p-3 text-sm whitespace-pre-wrap ${
                    entry.role === 'user'
                      ? 'bg-ocean-50 dark:bg-ocean-950 text-gray-900 dark:text-gray-100'
                      : 'bg-gray-100 dark:bg-gray-800 text-gray-800 dark:text-gray-200'
                  }`}
                >
                  <p className="font-semibold mb-1">{entry.role === 'user' ? 'You' : 'Agent'}</p>
                  <p>{entry.content}</p>
                </div>
              ))}
            </div>
          )}
        </Card>
      </div>
    </MainLayout>
  );
}
