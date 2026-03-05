import React from 'react';
import { cn } from '../utils';
import type { AuditEvent } from '../../lib/types/api';

export interface AuditTimelineProps {
  events: AuditEvent[];
  className?: string;
}

function actionColor(action: string): string {
  if (action === 'approved') return 'bg-green-500';
  if (action === 'rejected') return 'bg-red-500';
  if (action === 'edited') return 'bg-blue-500';
  if (action === 'ingested') return 'bg-purple-500';
  return 'bg-gray-400';
}

export const AuditTimeline: React.FC<AuditTimelineProps> = ({ events, className }) => {
  if (events.length === 0) {
    return (
      <p className="text-sm text-gray-500 dark:text-gray-400 italic">No audit events yet.</p>
    );
  }

  return (
    <ol
      aria-label="Audit history"
      className={cn('relative border-l border-gray-200 dark:border-gray-700 space-y-4 pl-4', className)}
    >
      {events.map((event) => (
        <li key={event.id} className="relative">
          {/* Dot */}
          <span
            className={cn(
              'absolute -left-[1.125rem] top-1 h-3 w-3 rounded-full border-2 border-white dark:border-gray-900',
              actionColor(event.action)
            )}
            aria-hidden="true"
          />
          <div className="flex flex-col gap-0.5">
            <p className="text-sm font-semibold text-gray-900 dark:text-white capitalize">
              {event.action}
              {event.field_name && (
                <span className="font-normal text-gray-600 dark:text-gray-400">
                  {' '}— {event.field_name.replace(/_/g, ' ')}
                </span>
              )}
            </p>
            {(event.old_value !== undefined || event.new_value !== undefined) && (
              <p className="text-xs text-gray-600 dark:text-gray-400">
                {event.old_value != null && (
                  <span>
                    <span className="text-red-600 dark:text-red-400 line-through">{event.old_value}</span>
                    {' → '}
                  </span>
                )}
                {event.new_value != null && (
                  <span className="text-green-700 dark:text-green-400">{event.new_value}</span>
                )}
              </p>
            )}
            {event.reason && (
              <p className="text-xs text-gray-500 dark:text-gray-400 italic">
                &ldquo;{event.reason}&rdquo;
              </p>
            )}
            <p className="text-xs text-gray-400 dark:text-gray-500">
              {event.actor} · {new Date(event.timestamp).toLocaleString()}
            </p>
          </div>
        </li>
      ))}
    </ol>
  );
};

AuditTimeline.displayName = 'AuditTimeline';
