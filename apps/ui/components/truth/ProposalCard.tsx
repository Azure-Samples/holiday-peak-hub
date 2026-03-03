'use client';

import React, { useState } from 'react';
import { cn } from '../utils';
import { ConfidenceBadge } from './ConfidenceBadge';
import type { ProposedAttribute } from '../../lib/types/api';

export interface ProposalCardProps {
  proposal: ProposedAttribute;
  onApprove: (id: string) => void;
  onReject: (id: string, reason: string) => void;
  onEdit: (id: string, editedValue: string) => void;
  disabled?: boolean;
}

export const ProposalCard: React.FC<ProposalCardProps> = ({
  proposal,
  onApprove,
  onReject,
  onEdit,
  disabled = false,
}) => {
  const [mode, setMode] = useState<'idle' | 'rejecting' | 'editing'>('idle');
  const [rejectReason, setRejectReason] = useState('');
  const [editedValue, setEditedValue] = useState(proposal.proposed_value);

  const handleApprove = () => {
    onApprove(proposal.id);
    setMode('idle');
  };

  const handleRejectSubmit = () => {
    onReject(proposal.id, rejectReason);
    setRejectReason('');
    setMode('idle');
  };

  const handleEditSubmit = () => {
    onEdit(proposal.id, editedValue);
    setMode('idle');
  };

  const isApproved = proposal.status === 'approved';
  const isRejected = proposal.status === 'rejected';
  const isReviewed = isApproved || isRejected;

  return (
    <div
      className={cn(
        'rounded-lg border p-4 space-y-3',
        isApproved && 'border-green-300 bg-green-50 dark:border-green-700 dark:bg-green-950',
        isRejected && 'border-red-300 bg-red-50 dark:border-red-700 dark:bg-red-950',
        !isReviewed && 'border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800'
      )}
    >
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-2">
        <span className="font-semibold text-gray-900 dark:text-white capitalize">
          {proposal.field_name.replace(/_/g, ' ')}
        </span>
        <div className="flex items-center gap-2">
          <ConfidenceBadge value={proposal.confidence} />
          {isApproved && (
            <span className="text-xs font-semibold text-green-700 dark:text-green-300">
              ✓ Approved
            </span>
          )}
          {isRejected && (
            <span className="text-xs font-semibold text-red-700 dark:text-red-300">
              ✗ Rejected
            </span>
          )}
        </div>
      </div>

      {/* Values comparison */}
      <div className="grid grid-cols-2 gap-3 text-sm">
        <div>
          <p className="text-xs text-gray-500 dark:text-gray-400 mb-1">Current Value</p>
          <p className="text-gray-700 dark:text-gray-300 italic">
            {proposal.current_value ?? <span className="text-gray-400">(empty)</span>}
          </p>
        </div>
        <div>
          <p className="text-xs text-gray-500 dark:text-gray-400 mb-1">Proposed Value</p>
          <p className="text-gray-900 dark:text-white font-medium">
            {proposal.proposed_value}
          </p>
        </div>
      </div>

      {/* Source */}
      <p className="text-xs text-gray-500 dark:text-gray-400">
        Source: <span className="font-medium">{proposal.source}</span>
      </p>

      {/* Actions */}
      {!isReviewed && !disabled && (
        <div className="flex flex-wrap gap-2 pt-1">
          {mode === 'idle' && (
            <>
              <button
                onClick={handleApprove}
                className="px-3 py-1.5 rounded-md text-sm font-medium bg-green-600 text-white hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-green-500"
                aria-label={`Approve ${proposal.field_name}`}
              >
                Approve
              </button>
              <button
                onClick={() => setMode('editing')}
                className="px-3 py-1.5 rounded-md text-sm font-medium bg-blue-600 text-white hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
                aria-label={`Edit ${proposal.field_name}`}
              >
                Edit
              </button>
              <button
                onClick={() => setMode('rejecting')}
                className="px-3 py-1.5 rounded-md text-sm font-medium bg-red-600 text-white hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-red-500"
                aria-label={`Reject ${proposal.field_name}`}
              >
                Reject
              </button>
            </>
          )}

          {mode === 'rejecting' && (
            <div className="w-full space-y-2">
              <label
                htmlFor={`reject-reason-${proposal.id}`}
                className="block text-xs font-medium text-gray-700 dark:text-gray-300"
              >
                Rejection reason
              </label>
              <textarea
                id={`reject-reason-${proposal.id}`}
                value={rejectReason}
                onChange={(e) => setRejectReason(e.target.value)}
                rows={2}
                className="w-full rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white text-sm px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-red-500"
                placeholder="Enter reason for rejection…"
              />
              <div className="flex gap-2">
                <button
                  onClick={handleRejectSubmit}
                  disabled={!rejectReason.trim()}
                  className="px-3 py-1.5 rounded-md text-sm font-medium bg-red-600 text-white hover:bg-red-700 disabled:opacity-50 focus:outline-none focus:ring-2 focus:ring-red-500"
                >
                  Confirm Reject
                </button>
                <button
                  onClick={() => setMode('idle')}
                  className="px-3 py-1.5 rounded-md text-sm font-medium border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-gray-400"
                >
                  Cancel
                </button>
              </div>
            </div>
          )}

          {mode === 'editing' && (
            <div className="w-full space-y-2">
              <label
                htmlFor={`edit-value-${proposal.id}`}
                className="block text-xs font-medium text-gray-700 dark:text-gray-300"
              >
                Edited value
              </label>
              <input
                id={`edit-value-${proposal.id}`}
                type="text"
                value={editedValue}
                onChange={(e) => setEditedValue(e.target.value)}
                className="w-full rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white text-sm px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              <div className="flex gap-2">
                <button
                  onClick={handleEditSubmit}
                  disabled={!editedValue.trim()}
                  className="px-3 py-1.5 rounded-md text-sm font-medium bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50 focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  Save Edit
                </button>
                <button
                  onClick={() => setMode('idle')}
                  className="px-3 py-1.5 rounded-md text-sm font-medium border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-gray-400"
                >
                  Cancel
                </button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

ProposalCard.displayName = 'ProposalCard';
