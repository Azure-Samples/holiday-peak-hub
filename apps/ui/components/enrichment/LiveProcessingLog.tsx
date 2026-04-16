'use client';

import React, { useCallback, useEffect, useRef, useState } from 'react';
import { Card } from '@/components/molecules/Card';

type LogEntryStatus = 'success' | 'processing' | 'error';

interface LogEntry {
  id: string;
  timestamp: string;
  event_type: string;
  entity_id: string;
  status: LogEntryStatus;
}

const API_URL = process.env.NEXT_PUBLIC_API_URL || '';
const MAX_ENTRIES = 50;
const RECONNECT_DELAY_MS = 3000;

function parseStatus(raw: unknown): LogEntryStatus {
  if (raw === 'success' || raw === 'processing' || raw === 'error') return raw;
  return 'processing';
}

const STATUS_STYLES: Record<LogEntryStatus, string> = {
  success: 'bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-300',
  processing: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/40 dark:text-yellow-300',
  error: 'bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-300',
};

export const LiveProcessingLog: React.FC = () => {
  const [entries, setEntries] = useState<LogEntry[]>([]);
  const [connected, setConnected] = useState(false);
  const logEndRef = useRef<HTMLDivElement>(null);
  const eventSourceRef = useRef<EventSource | null>(null);

  const connect = useCallback(() => {
    const es = new EventSource(`${API_URL}/api/demo/events`);
    eventSourceRef.current = es;

    es.onopen = () => setConnected(true);

    es.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data as string) as Record<string, unknown>;
        const entry: LogEntry = {
          id: String(data.id ?? `${Date.now()}-${Math.random().toString(36).slice(2, 7)}`),
          timestamp: String(data.timestamp ?? new Date().toISOString()),
          event_type: String(data.event_type ?? 'unknown'),
          entity_id: String(data.entity_id ?? ''),
          status: parseStatus(data.status),
        };

        setEntries((prev) => {
          const next = [...prev, entry];
          return next.length > MAX_ENTRIES ? next.slice(next.length - MAX_ENTRIES) : next;
        });
      } catch {
        // Ignore malformed messages
      }
    };

    es.onerror = () => {
      setConnected(false);
      es.close();
      eventSourceRef.current = null;
      setTimeout(connect, RECONNECT_DELAY_MS);
    };
  }, []);

  useEffect(() => {
    connect();
    return () => {
      eventSourceRef.current?.close();
      eventSourceRef.current = null;
    };
  }, [connect]);

  useEffect(() => {
    logEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [entries]);

  const handleClear = () => setEntries([]);

  return (
    <Card className="p-0 overflow-hidden">
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center gap-2">
          <span
            className={`inline-block h-2 w-2 rounded-full ${connected ? 'bg-green-500' : 'bg-red-500'}`}
            aria-hidden="true"
          />
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Live Processing Log</h2>
          <span className="text-xs text-gray-500 dark:text-gray-400">
            {connected ? 'Connected' : 'Disconnected'}
          </span>
        </div>
        <button
          type="button"
          onClick={handleClear}
          className="rounded-md border border-gray-300 dark:border-gray-600 px-3 py-1 text-xs font-semibold text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800/40 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
        >
          Clear
        </button>
      </div>

      <div
        className="max-h-72 overflow-y-auto bg-gray-50 dark:bg-gray-900/30"
        role="log"
        aria-live="polite"
        aria-relevant="additions"
        aria-label="Live processing events"
      >
        {entries.length === 0 ? (
          <p className="px-4 py-6 text-center text-sm text-gray-500 dark:text-gray-400">
            No processing events yet.
          </p>
        ) : (
          <table className="min-w-full text-xs">
            <thead className="sticky top-0 bg-gray-100 dark:bg-gray-800">
              <tr>
                <th className="text-left font-semibold text-gray-600 dark:text-gray-400 px-4 py-1.5">Time</th>
                <th className="text-left font-semibold text-gray-600 dark:text-gray-400 px-4 py-1.5">Event</th>
                <th className="text-left font-semibold text-gray-600 dark:text-gray-400 px-4 py-1.5">Entity</th>
                <th className="text-left font-semibold text-gray-600 dark:text-gray-400 px-4 py-1.5">Status</th>
              </tr>
            </thead>
            <tbody>
              {entries.map((entry) => (
                <tr key={entry.id} className="border-t border-gray-200 dark:border-gray-700">
                  <td className="whitespace-nowrap px-4 py-1.5 text-gray-500 dark:text-gray-400 font-mono">
                    {new Date(entry.timestamp).toLocaleTimeString()}
                  </td>
                  <td className="px-4 py-1.5 text-gray-700 dark:text-gray-300">{entry.event_type}</td>
                  <td className="px-4 py-1.5 text-gray-700 dark:text-gray-300 font-mono">{entry.entity_id}</td>
                  <td className="px-4 py-1.5">
                    <span className={`inline-block rounded-full px-2 py-0.5 text-xs font-semibold ${STATUS_STYLES[entry.status]}`}>
                      {entry.status}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
        <div ref={logEndRef} />
      </div>
    </Card>
  );
};
