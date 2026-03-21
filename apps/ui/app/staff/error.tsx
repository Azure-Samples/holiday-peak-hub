'use client'

import { RouteErrorBoundary } from '../_shared/route-boundary'

export default function Error({
  error,
  reset,
}: {
  error: Error & { digest?: string }
  reset: () => void
}) {
  return <RouteErrorBoundary scope="staff" error={error} reset={reset} />
}