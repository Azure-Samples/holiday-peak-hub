'use client';

import { useMemo, useState } from 'react';
import { Button } from '@/components/atoms/Button';
import { MainLayout } from '@/components/templates/MainLayout';
import { Card } from '@/components/molecules/Card';
import { Input } from '@/components/atoms/Input';
import { Select } from '@/components/atoms/Select';
import { Textarea } from '@/components/atoms/Textarea';
import { Tabs } from '@/components/molecules/Tabs';
import {
  useApproveStaffReturn,
  useCreateStaffTicket,
  useEscalateStaffTicket,
  useReceiveStaffReturn,
  useRefundStaffReturn,
  useRejectStaffReturn,
  useRestockStaffReturn,
  useResolveStaffTicket,
  useStaffReturns,
  useStaffTickets,
  useUpdateStaffTicket,
} from '@/lib/hooks/useStaff';
import type { Return, ReturnStatus, Ticket, TicketStatus } from '@/lib/types/api';

const getReturnLifecycleMessage = (item: Return): string => {
  if (item.status === 'requested') {
    return 'Waiting for review. Review SLA target is 24 hours.';
  }
  if (item.status === 'approved') {
    return 'Approved and waiting for item receipt.';
  }
  if (item.status === 'received') {
    return 'Received and pending restock verification.';
  }
  if (item.status === 'restocked') {
    return 'Restocked; refund SLA target is up to 2 business days.';
  }
  if (item.status === 'refunded') {
    return 'Lifecycle complete. Refund has been issued.';
  }

  return 'Lifecycle closed; no additional transitions expected.';
};

const getReturnRefundMessage = (item: Return): string => {
  if (item.refund?.status === 'issued') {
    return 'Refund issued to original payment method.';
  }
  if (item.status === 'rejected') {
    return 'Refund not applicable after rejection.';
  }
  if (item.status === 'requested' || item.status === 'approved' || item.status === 'received') {
    return 'Refund not yet eligible.';
  }
  if (item.status === 'restocked') {
    return 'Refund pending issuance within target SLA.';
  }

  return 'Refund status unavailable.';
};

const TICKET_STATUS_OPTIONS: Array<{ value: TicketStatus; label: TicketStatus }> = [
  { value: 'open', label: 'open' },
  { value: 'in_progress', label: 'in_progress' },
  { value: 'pending_customer', label: 'pending_customer' },
  { value: 'escalated', label: 'escalated' },
  { value: 'resolved', label: 'resolved' },
  { value: 'closed', label: 'closed' },
];

export default function RequestsPage() {
  const [query, setQuery] = useState('');
  const { data: tickets = [], isLoading: loadingTickets, isError: ticketError } = useStaffTickets();
  const { data: returns = [], isLoading: loadingReturns, isError: returnError } = useStaffReturns();
  const createTicketMutation = useCreateStaffTicket();
  const updateTicketMutation = useUpdateStaffTicket();
  const resolveTicketMutation = useResolveStaffTicket();
  const escalateTicketMutation = useEscalateStaffTicket();
  const approveReturnMutation = useApproveStaffReturn();
  const rejectReturnMutation = useRejectStaffReturn();
  const receiveReturnMutation = useReceiveStaffReturn();
  const restockReturnMutation = useRestockStaffReturn();
  const refundReturnMutation = useRefundStaffReturn();

  const [createUserId, setCreateUserId] = useState('');
  const [createSubject, setCreateSubject] = useState('');
  const [createPriority, setCreatePriority] = useState('medium');
  const [createDescription, setCreateDescription] = useState('');

  const [selectedTicketId, setSelectedTicketId] = useState('');
  const [updateStatus, setUpdateStatus] = useState<TicketStatus | ''>('');
  const [updateAssigneeId, setUpdateAssigneeId] = useState('');
  const [actionReason, setActionReason] = useState('');
  const [resolutionNote, setResolutionNote] = useState('');
  const [selectedReturnId, setSelectedReturnId] = useState('');
  const [returnReason, setReturnReason] = useState('');

  const selectedTicket = useMemo(
    () => tickets.find((ticket) => ticket.id === selectedTicketId),
    [tickets, selectedTicketId]
  );

  const selectedReturn = useMemo(
    () => returns.find((item) => item.id === selectedReturnId),
    [returns, selectedReturnId],
  );

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

  const returnOptions = useMemo(
    () =>
      filteredReturns.map((item) => ({
        value: item.id,
        label: `${item.id} · ${item.status}`,
      })),
    [filteredReturns],
  );

  const ticketOptions = useMemo(
    () =>
      filteredTickets.map((ticket) => ({
        value: ticket.id,
        label: `${ticket.id} · ${ticket.subject}`,
      })),
    [filteredTickets]
  );

  const isTicketActionRunning =
    createTicketMutation.isPending ||
    updateTicketMutation.isPending ||
    resolveTicketMutation.isPending ||
    escalateTicketMutation.isPending;

  const isReturnActionRunning =
    approveReturnMutation.isPending ||
    rejectReturnMutation.isPending ||
    receiveReturnMutation.isPending ||
    restockReturnMutation.isPending ||
    refundReturnMutation.isPending;

  const createUserIdValue = createUserId.trim();
  const createSubjectValue = createSubject.trim();
  const updateAssigneeValue = updateAssigneeId.trim();
  const actionReasonValue = actionReason.trim();
  const selectedAssignee = selectedTicket?.assignee_id ?? '';
  const hasStatusChange = Boolean(selectedTicket && updateStatus && updateStatus !== selectedTicket.status);
  const hasAssigneeChange = Boolean(selectedTicket && updateAssigneeValue !== selectedAssignee);

  const canCreateTicket = Boolean(createUserIdValue && createSubjectValue) && !isTicketActionRunning;
  const canUpdateTicket =
    Boolean(selectedTicketId) &&
    (hasStatusChange || hasAssigneeChange) &&
    !isTicketActionRunning;
  const canEscalateTicket = Boolean(selectedTicketId && actionReasonValue) && !isTicketActionRunning;
  const canResolveTicket = Boolean(selectedTicketId) && !isTicketActionRunning;
  const canRunReturnAction = Boolean(selectedReturnId) && !isReturnActionRunning;

  const canApproveReturn = canRunReturnAction && selectedReturn?.status === 'requested';
  const canRejectReturn = canRunReturnAction && selectedReturn?.status === 'requested';
  const canReceiveReturn = canRunReturnAction && selectedReturn?.status === 'approved';
  const canRestockReturn = canRunReturnAction && selectedReturn?.status === 'received';
  const canRefundReturn = canRunReturnAction && selectedReturn?.status === 'restocked';

  const createValidationHint = !createUserIdValue
    ? 'User ID is required to create a ticket.'
    : !createSubjectValue
      ? 'Subject is required to create a ticket.'
      : null;

  const actionFeedbackMessage = createTicketMutation.isPending
    ? 'Creating ticket...'
    : updateTicketMutation.isPending
      ? 'Updating ticket...'
      : escalateTicketMutation.isPending
        ? 'Escalating ticket...'
        : resolveTicketMutation.isPending
          ? 'Resolving ticket...'
          : null;

  const ticketMutationError =
    createTicketMutation.error ||
    updateTicketMutation.error ||
    resolveTicketMutation.error ||
    escalateTicketMutation.error;

  const returnMutationError =
    approveReturnMutation.error ||
    rejectReturnMutation.error ||
    receiveReturnMutation.error ||
    restockReturnMutation.error ||
    refundReturnMutation.error;

  const returnActionFeedbackMessage = approveReturnMutation.isPending
    ? 'Approving return...'
    : rejectReturnMutation.isPending
      ? 'Rejecting return...'
      : receiveReturnMutation.isPending
        ? 'Marking return as received...'
        : restockReturnMutation.isPending
          ? 'Marking return as restocked...'
          : refundReturnMutation.isPending
            ? 'Issuing refund...'
            : null;

  const onCreateTicket = async () => {
    if (!createUserIdValue || !createSubjectValue) {
      return;
    }

    const ticket = await createTicketMutation.mutateAsync({
      user_id: createUserIdValue,
      subject: createSubjectValue,
      priority: createPriority,
      description: createDescription.trim() || undefined,
    });

    setCreateSubject('');
    setCreateDescription('');
    setSelectedTicketId(ticket.id);
    setActionReason('');
    setResolutionNote('');
  };

  const onUpdateTicket = async () => {
    if (!selectedTicketId || (!hasStatusChange && !hasAssigneeChange)) {
      return;
    }

    const request = {
      status: hasStatusChange ? updateStatus : undefined,
      assignee_id: hasAssigneeChange ? updateAssigneeValue || undefined : undefined,
      reason: actionReasonValue || undefined,
    };

    await updateTicketMutation.mutateAsync({
      ticketId: selectedTicketId,
      request,
    });

    setActionReason('');
  };

  const onEscalateTicket = async () => {
    if (!selectedTicketId || !actionReasonValue) {
      return;
    }

    await escalateTicketMutation.mutateAsync({
      ticketId: selectedTicketId,
      request: { reason: actionReasonValue },
    });

    setActionReason('');
  };

  const onResolveTicket = async () => {
    if (!selectedTicketId) {
      return;
    }

    await resolveTicketMutation.mutateAsync({
      ticketId: selectedTicketId,
      request: {
        reason: actionReasonValue || undefined,
        resolution_note: resolutionNote.trim() || undefined,
      },
    });

    setActionReason('');
    setResolutionNote('');
  };

  const runReturnTransition = async (targetStatus: ReturnStatus) => {
    if (!selectedReturnId) {
      return;
    }

    const request = { reason: returnReason.trim() || undefined };
    if (targetStatus === 'approved') {
      await approveReturnMutation.mutateAsync({ returnId: selectedReturnId, request });
    }
    if (targetStatus === 'rejected') {
      await rejectReturnMutation.mutateAsync({ returnId: selectedReturnId, request });
    }
    if (targetStatus === 'received') {
      await receiveReturnMutation.mutateAsync({ returnId: selectedReturnId, request });
    }
    if (targetStatus === 'restocked') {
      await restockReturnMutation.mutateAsync({ returnId: selectedReturnId, request });
    }
    if (targetStatus === 'refunded') {
      await refundReturnMutation.mutateAsync({ returnId: selectedReturnId, request });
    }

    setReturnReason('');
  };

  return (
    <MainLayout>
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white">Customer Requests</h1>
          <p className="text-gray-600 dark:text-gray-400 mt-1">Consult support tickets and returns from staff CRUD endpoints.</p>
        </div>

        <Card className="p-4">
          <Input
            type="search"
            placeholder="Filter by id, status, subject or order"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            ariaLabel="Filter tickets and returns"
          />
        </Card>

        <Tabs
          tabs={[
            {
              id: 'tickets',
              label: `Tickets (${filteredTickets.length})`,
              content: (
                <div className="space-y-4">
                  <Card className="p-4 space-y-3">
                    <h2 className="text-sm font-semibold text-gray-900 dark:text-white">Create Ticket</h2>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                      <div className="space-y-1">
                        <p className="text-xs font-medium text-gray-700 dark:text-gray-300">User ID *</p>
                        <Input
                          type="text"
                          placeholder="Enter user ID"
                          value={createUserId}
                          onChange={(event) => setCreateUserId(event.target.value)}
                          ariaLabel="User ID for new ticket"
                          required
                        />
                      </div>
                      <div className="space-y-1">
                        <p className="text-xs font-medium text-gray-700 dark:text-gray-300">Subject *</p>
                        <Input
                          type="text"
                          placeholder="Enter ticket subject"
                          value={createSubject}
                          onChange={(event) => setCreateSubject(event.target.value)}
                          ariaLabel="Subject for new ticket"
                          required
                        />
                      </div>
                      <div className="space-y-1">
                        <p className="text-xs font-medium text-gray-700 dark:text-gray-300">Priority</p>
                        <Select
                          options={[
                            { value: 'low', label: 'Low' },
                            { value: 'medium', label: 'Medium' },
                            { value: 'high', label: 'High' },
                            { value: 'urgent', label: 'Urgent' },
                          ]}
                          value={createPriority}
                          onChange={(event) => setCreatePriority(event.target.value)}
                          placeholder="Priority"
                          ariaLabel="Priority for new ticket"
                        />
                      </div>
                    </div>
                    <div className="space-y-1">
                      <p className="text-xs font-medium text-gray-700 dark:text-gray-300">Description</p>
                      <Textarea
                        rows={2}
                        placeholder="Description (optional)"
                        value={createDescription}
                        onChange={(event) => setCreateDescription(event.target.value)}
                        ariaLabel="Description for new ticket"
                      />
                    </div>
                    {createValidationHint && (
                      <p className="text-xs text-amber-700 dark:text-amber-400" role="status" aria-live="polite">
                        {createValidationHint}
                      </p>
                    )}
                    <div className="flex justify-end">
                      <Button
                        onClick={onCreateTicket}
                        loading={createTicketMutation.isPending}
                        disabled={!canCreateTicket}
                        ariaLabel="Create ticket"
                      >
                        {createTicketMutation.isPending ? 'Creating ticket...' : 'Create Ticket'}
                      </Button>
                    </div>
                  </Card>

                  <Card className="p-4 space-y-3">
                    <h2 className="text-sm font-semibold text-gray-900 dark:text-white">Ticket Actions</h2>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                      <div className="space-y-1">
                        <p className="text-xs font-medium text-gray-700 dark:text-gray-300">Ticket *</p>
                        <Select
                          options={ticketOptions}
                          value={selectedTicketId}
                          onChange={(event) => {
                            const ticketId = event.target.value;
                            setSelectedTicketId(ticketId);
                            const ticket = tickets.find((item): item is Ticket => item.id === ticketId);
                            setUpdateStatus(ticket?.status ?? '');
                            setUpdateAssigneeId(ticket?.assignee_id ?? '');
                            setActionReason('');
                            setResolutionNote('');
                          }}
                          placeholder="Select ticket"
                          ariaLabel="Select ticket for action"
                        />
                      </div>
                      <div className="space-y-1">
                        <p className="text-xs font-medium text-gray-700 dark:text-gray-300">Status</p>
                        <Select
                          options={TICKET_STATUS_OPTIONS}
                          value={updateStatus}
                          onChange={(event) => setUpdateStatus(event.target.value as TicketStatus)}
                          placeholder="Status"
                          disabled={!selectedTicketId}
                          ariaLabel="Status update"
                        />
                      </div>
                      <div className="space-y-1">
                        <p className="text-xs font-medium text-gray-700 dark:text-gray-300">Assignee ID</p>
                        <Input
                          type="text"
                          placeholder="Enter assignee ID"
                          value={updateAssigneeId}
                          onChange={(event) => setUpdateAssigneeId(event.target.value)}
                          disabled={!selectedTicketId}
                          ariaLabel="Assignee ID update"
                        />
                      </div>
                    </div>
                    <div className="space-y-1">
                      <p className="text-xs font-medium text-gray-700 dark:text-gray-300">Reason</p>
                      <Input
                        type="text"
                        placeholder="Required for escalate; optional for update/resolve"
                        value={actionReason}
                        onChange={(event) => setActionReason(event.target.value)}
                        disabled={!selectedTicketId}
                        ariaLabel="Reason for update, escalation, or resolution"
                      />
                      {selectedTicketId && !actionReasonValue && (
                        <p className="text-xs text-amber-700 dark:text-amber-400" role="status" aria-live="polite">
                          Escalate requires a reason.
                        </p>
                      )}
                    </div>
                    <div className="space-y-1">
                      <p className="text-xs font-medium text-gray-700 dark:text-gray-300">Resolution note</p>
                      <Textarea
                        rows={2}
                        placeholder="Optional note for resolve"
                        value={resolutionNote}
                        onChange={(event) => setResolutionNote(event.target.value)}
                        disabled={!selectedTicketId}
                        ariaLabel="Resolution note"
                      />
                    </div>
                    <div className="flex flex-wrap gap-2 justify-end">
                      <Button
                        variant="secondary"
                        onClick={onUpdateTicket}
                        loading={updateTicketMutation.isPending}
                        disabled={!canUpdateTicket}
                        ariaLabel="Update selected ticket"
                      >
                        {updateTicketMutation.isPending ? 'Updating...' : 'Update'}
                      </Button>
                      <Button
                        variant="secondary"
                        onClick={onEscalateTicket}
                        loading={escalateTicketMutation.isPending}
                        disabled={!canEscalateTicket}
                        ariaLabel="Escalate selected ticket"
                      >
                        {escalateTicketMutation.isPending ? 'Escalating...' : 'Escalate'}
                      </Button>
                      <Button
                        onClick={onResolveTicket}
                        loading={resolveTicketMutation.isPending}
                        disabled={!canResolveTicket}
                        ariaLabel="Resolve selected ticket"
                      >
                        {resolveTicketMutation.isPending ? 'Resolving...' : 'Resolve'}
                      </Button>
                    </div>
                    {actionFeedbackMessage && (
                      <p className="text-xs text-blue-700 dark:text-blue-300" role="status" aria-live="polite">
                        {actionFeedbackMessage}
                      </p>
                    )}
                    {!selectedTicketId && (
                      <p className="text-xs text-gray-600 dark:text-gray-400" role="status" aria-live="polite">
                        Select a ticket to enable status, assignee, and action controls.
                      </p>
                    )}
                    {selectedTicket && (
                      <p className="text-xs text-gray-600 dark:text-gray-400">
                        Selected: {selectedTicket.id} · {selectedTicket.status}
                        {selectedTicket.assignee_id ? ` · assignee ${selectedTicket.assignee_id}` : ''}
                      </p>
                    )}
                    {ticketMutationError && (
                      <p className="text-sm text-red-600 dark:text-red-400" role="alert" aria-live="assertive">
                        Ticket action failed. Please verify role and status transition.
                      </p>
                    )}
                  </Card>

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
                            <th className="px-4 py-3">Assignee</th>
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
                              <td className="px-4 py-3">{ticket.assignee_id ?? '-'}</td>
                              <td className="px-4 py-3">{new Date(ticket.created_at).toLocaleString()}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    )}
                  </Card>
                </div>
              ),
            },
            {
              id: 'returns',
              label: `Returns (${filteredReturns.length})`,
              content: (
                <div className="space-y-4">
                  <Card className="p-4 space-y-3">
                    <h2 className="text-sm font-semibold text-gray-900 dark:text-white">Return Actions</h2>
                    <p className="text-xs text-gray-600 dark:text-gray-400">
                      Lifecycle sequence is requested → approved/rejected → received → restocked → refunded. Review target is 24 hours; refund
                      target is up to 2 business days after restock.
                    </p>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                      <div className="space-y-1">
                        <p className="text-xs font-medium text-gray-700 dark:text-gray-300">Return *</p>
                        <Select
                          options={returnOptions}
                          value={selectedReturnId}
                          onChange={(event) => {
                            setSelectedReturnId(event.target.value);
                            setReturnReason('');
                          }}
                          placeholder="Select return"
                          ariaLabel="Select return for lifecycle transition"
                        />
                      </div>
                      <div className="space-y-1">
                        <p className="text-xs font-medium text-gray-700 dark:text-gray-300">Reason</p>
                        <Input
                          type="text"
                          placeholder="Optional transition reason"
                          value={returnReason}
                          onChange={(event) => setReturnReason(event.target.value)}
                          disabled={!selectedReturnId}
                          ariaLabel="Reason for return transition"
                        />
                      </div>
                    </div>
                    <div className="flex flex-wrap gap-2 justify-end">
                      <Button variant="secondary" onClick={() => runReturnTransition('approved')} disabled={!canApproveReturn}>
                        Approve
                      </Button>
                      <Button variant="secondary" onClick={() => runReturnTransition('rejected')} disabled={!canRejectReturn}>
                        Reject
                      </Button>
                      <Button variant="secondary" onClick={() => runReturnTransition('received')} disabled={!canReceiveReturn}>
                        Receive
                      </Button>
                      <Button variant="secondary" onClick={() => runReturnTransition('restocked')} disabled={!canRestockReturn}>
                        Restock
                      </Button>
                      <Button onClick={() => runReturnTransition('refunded')} disabled={!canRefundReturn}>
                        Refund
                      </Button>
                    </div>
                    {!selectedReturnId && (
                      <p className="text-xs text-gray-600 dark:text-gray-400" role="status" aria-live="polite">
                        Select a return to enable lifecycle transitions.
                      </p>
                    )}
                    {returnActionFeedbackMessage && (
                      <p className="text-xs text-blue-700 dark:text-blue-300" role="status" aria-live="polite">
                        {returnActionFeedbackMessage}
                      </p>
                    )}
                    {selectedReturn && (
                      <p className="text-xs text-gray-600 dark:text-gray-400" role="status" aria-live="polite">
                        Selected: {selectedReturn.id} · {selectedReturn.status}. {getReturnLifecycleMessage(selectedReturn)}
                      </p>
                    )}
                    {returnMutationError && (
                      <p className="text-sm text-red-600 dark:text-red-400" role="alert" aria-live="assertive">
                        Return action failed. Verify lifecycle sequence and access.
                      </p>
                    )}
                  </Card>

                  <Card className="overflow-x-auto">
                    {loadingReturns ? (
                      <div className="p-6 text-gray-600 dark:text-gray-400" role="status" aria-live="polite">
                        Loading returns...
                      </div>
                    ) : returnError ? (
                      <div className="p-6 text-red-600 dark:text-red-400" role="alert" aria-live="assertive">
                        Returns could not be loaded.
                      </div>
                    ) : (
                      <table className="min-w-full text-sm">
                        <thead className="bg-gray-100 dark:bg-gray-800 text-left">
                          <tr>
                            <th className="px-4 py-3">Return</th>
                            <th className="px-4 py-3">Order</th>
                            <th className="px-4 py-3">Reason</th>
                            <th className="px-4 py-3">Status</th>
                            <th className="px-4 py-3">Refund</th>
                            <th className="px-4 py-3">Requested</th>
                            <th className="px-4 py-3">Approved</th>
                            <th className="px-4 py-3">Received</th>
                            <th className="px-4 py-3">Restocked</th>
                            <th className="px-4 py-3">Refunded</th>
                          </tr>
                        </thead>
                        <tbody>
                          {filteredReturns.map((ret) => (
                            <tr key={ret.id} className="border-t border-gray-200 dark:border-gray-700">
                              <td className="px-4 py-3">{ret.id}</td>
                              <td className="px-4 py-3">{ret.order_id}</td>
                              <td className="px-4 py-3">{ret.reason}</td>
                              <td className="px-4 py-3">
                                <p className="font-medium text-gray-900 dark:text-white">{ret.status}</p>
                                <p className="text-xs text-gray-600 dark:text-gray-400">{getReturnLifecycleMessage(ret)}</p>
                              </td>
                              <td className="px-4 py-3">
                                <p className="font-medium text-gray-900 dark:text-white">{ret.refund?.status ?? '-'}</p>
                                <p className="text-xs text-gray-600 dark:text-gray-400">{getReturnRefundMessage(ret)}</p>
                              </td>
                              <td className="px-4 py-3">{new Date(ret.requested_at).toLocaleString()}</td>
                              <td className="px-4 py-3">{ret.approved_at ? new Date(ret.approved_at).toLocaleString() : '-'}</td>
                              <td className="px-4 py-3">{ret.received_at ? new Date(ret.received_at).toLocaleString() : '-'}</td>
                              <td className="px-4 py-3">{ret.restocked_at ? new Date(ret.restocked_at).toLocaleString() : '-'}</td>
                              <td className="px-4 py-3">{ret.refunded_at ? new Date(ret.refunded_at).toLocaleString() : '-'}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    )}
                  </Card>
                </div>
              ),
            },
          ]}
        />
      </div>
    </MainLayout>
  );
}
