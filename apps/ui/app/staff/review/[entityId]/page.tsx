'use client';

import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import { MainLayout } from '@/components/templates/MainLayout';
import { Card } from '@/components/molecules/Card';
import { ProposalCard } from '@/components/truth/ProposalCard';
import { CompletenessBar } from '@/components/truth/CompletenessBar';
import { AuditTimeline } from '@/components/truth/AuditTimeline';
import {
  useAuditHistory,
  useProductReviewDetail,
  useReviewAction,
} from '@/lib/hooks/useTruth';

export default function ProductReviewDetailPage() {
  const params = useParams<{ entityId: string }>();
  const entityId = params?.entityId ?? '';
  const router = useRouter();

  const { data: product, isLoading, isError } = useProductReviewDetail(entityId);
  const { data: auditEvents = [] } = useAuditHistory(entityId);
  const reviewAction = useReviewAction();

  const handleApprove = (proposalId: string) => {
    reviewAction.mutate({ proposalId, action: { action: 'approve' } });
  };

  const handleReject = (proposalId: string, reason: string) => {
    reviewAction.mutate({ proposalId, action: { action: 'reject', reason } });
  };

  const handleEdit = (proposalId: string, editedValue: string) => {
    reviewAction.mutate({ proposalId, action: { action: 'edit', edited_value: editedValue } });
  };

  const handleApproveAll = () => {
    if (!product) return;
    product.proposed_attributes
      .filter((p) => p.status === 'pending')
      .forEach((p) => handleApprove(p.id));
  };

  const handleRejectAll = () => {
    if (!product) return;
    product.proposed_attributes
      .filter((p) => p.status === 'pending')
      .forEach((p) =>
        reviewAction.mutate({
          proposalId: p.id,
          action: { action: 'reject', reason: 'Bulk reject' },
        })
      );
  };

  const pendingCount = product?.proposed_attributes.filter((p) => p.status === 'pending').length ?? 0;

  return (
    <MainLayout>
      <div className="space-y-6">
        {/* Breadcrumb */}
        <nav aria-label="Breadcrumb" className="text-sm text-gray-600 dark:text-gray-400">
          <Link
            href="/staff/review"
            className="hover:underline text-blue-600 dark:text-blue-400 focus:outline-none focus:ring-2 focus:ring-blue-500 rounded"
          >
            Review Queue
          </Link>
          <span className="mx-2" aria-hidden="true">/</span>
          <span className="text-gray-900 dark:text-white truncate">
            {product?.product_title ?? entityId}
          </span>
        </nav>

        {/* Loading / Error states */}
        {isLoading && (
          <Card className="p-6 text-gray-600 dark:text-gray-400">
            Loading product review…
          </Card>
        )}

        {isError && (
          <Card className="p-6 border border-red-200 dark:border-red-900 text-red-600 dark:text-red-400">
            Product review could not be loaded.
          </Card>
        )}

        {product && (
          <>
            {/* Product context */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <Card className="md:col-span-2 p-5 space-y-3">
                <div className="flex items-start gap-4">
                  {product.image_url && (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img
                      src={product.image_url}
                      alt={product.product_title}
                      className="h-20 w-20 rounded-lg object-cover flex-shrink-0 border border-gray-200 dark:border-gray-700"
                    />
                  )}
                  <div className="space-y-1 min-w-0">
                    <h1 className="text-2xl font-bold text-gray-900 dark:text-white leading-tight">
                      {product.product_title}
                    </h1>
                    <p className="text-sm text-gray-500 dark:text-gray-400">{product.category}</p>
                    <p className="text-xs text-gray-400 dark:text-gray-500 font-mono">{entityId}</p>
                  </div>
                </div>
                <CompletenessBar value={product.completeness_score} />
              </Card>

              <Card className="p-5 space-y-3">
                <h2 className="font-semibold text-gray-900 dark:text-white">Bulk Actions</h2>
                <p className="text-sm text-gray-600 dark:text-gray-400">
                  {pendingCount} pending proposal{pendingCount !== 1 ? 's' : ''}
                </p>
                <div className="flex flex-col gap-2">
                  <button
                    onClick={handleApproveAll}
                    disabled={pendingCount === 0 || reviewAction.isPending}
                    className="px-4 py-2 rounded-md text-sm font-medium bg-green-600 text-white hover:bg-green-700 disabled:opacity-40 focus:outline-none focus:ring-2 focus:ring-green-500"
                  >
                    Approve All
                  </button>
                  <button
                    onClick={handleRejectAll}
                    disabled={pendingCount === 0 || reviewAction.isPending}
                    className="px-4 py-2 rounded-md text-sm font-medium bg-red-600 text-white hover:bg-red-700 disabled:opacity-40 focus:outline-none focus:ring-2 focus:ring-red-500"
                  >
                    Reject All
                  </button>
                  <button
                    onClick={() => router.push('/staff/review')}
                    className="px-4 py-2 rounded-md text-sm font-medium border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-gray-400"
                  >
                    Back to Queue
                  </button>
                </div>
              </Card>
            </div>

            {/* Proposals */}
            <section aria-label="Proposed attributes">
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-3">
                Proposed Attributes ({product.proposed_attributes.length})
              </h2>
              {product.proposed_attributes.length === 0 ? (
                <Card className="p-6 text-gray-500 dark:text-gray-400 italic">
                  No proposed attributes for this product.
                </Card>
              ) : (
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                  {product.proposed_attributes.map((proposal) => (
                    <ProposalCard
                      key={proposal.id}
                      proposal={proposal}
                      onApprove={handleApprove}
                      onReject={handleReject}
                      onEdit={handleEdit}
                      disabled={reviewAction.isPending}
                    />
                  ))}
                </div>
              )}
            </section>

            {/* Audit history */}
            <section aria-label="Audit history">
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-3">
                Audit History
              </h2>
              <Card className="p-5">
                <AuditTimeline events={auditEvents} />
              </Card>
            </section>
          </>
        )}
      </div>
    </MainLayout>
  );
}
