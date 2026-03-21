'use client'

import { RouteErrorBoundary } from '../_shared/route-boundary'

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string }
  reset: () => void
}) {
  return <RouteErrorBoundary scope="admin" error={error} reset={reset} />
}