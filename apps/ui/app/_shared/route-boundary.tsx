'use client'

import { useEffect } from 'react'

import Image from 'next/image'
import Link from 'next/link'

import Layout from '@/layouts/centered'
import { trackBoundaryError } from '@/lib/utils/telemetry'

type RouteErrorBoundaryProps = {
  scope: string
  error: Error & { digest?: string }
  reset: () => void
}

export function RouteErrorBoundary({
  scope,
  error,
  reset,
}: RouteErrorBoundaryProps) {
  useEffect(() => {
    trackBoundaryError(scope, error)
  }, [scope, error])

  return (
    <Layout>
      <div className="flex flex-col w-full max-w-xl text-center">
        <Image
          className="object-contain w-auto mb-8"
          height={64}
          width={64}
          src="/images/illustration.svg"
          alt="Error illustration"
          loading="eager"
        />
        <h3 className="text-blue-500 mb-4">Oops!</h3>
        {error.digest && (
          <h1 className="text-6xl text-blue-500 mb-4">{error.digest}</h1>
        )}

        <div className="mb-8 text-center text-gray-900 dark:text-white">
          Something went wrong while loading this page. Please try again.
        </div>

        <div className="grid w-full gap-3 sm:grid-cols-2">
          <button
            type="button"
            onClick={reset}
            className="w-full px-6 py-3 text-base font-bold text-white uppercase bg-blue-500 rounded-lg hover:bg-blue-600"
          >
            Try Again
          </button>
          <Link
            href="/"
            className="w-full px-6 py-3 text-base font-bold text-white uppercase bg-blue-500 rounded-lg hover:bg-blue-600"
          >
            Back Home
          </Link>
        </div>
      </div>
    </Layout>
  )
}

type RouteLoadingProps = {
  section: string
}

export function RouteLoading({ section }: RouteLoadingProps) {
  return (
    <div className="mx-auto w-full max-w-5xl space-y-6 p-6" aria-busy="true" aria-live="polite">
      <div className="space-y-3">
        <div className="h-4 w-40 animate-pulse rounded bg-gray-200 dark:bg-gray-700" />
        <div className="h-8 w-80 animate-pulse rounded bg-gray-200 dark:bg-gray-700" />
      </div>

      <div className="rounded-2xl border border-gray-200 p-6 dark:border-gray-800">
        <p className="mb-4 text-sm text-gray-600 dark:text-gray-400">Loading {section}...</p>
        <div className="space-y-3">
          <div className="h-4 w-full animate-pulse rounded bg-gray-200 dark:bg-gray-700" />
          <div className="h-4 w-4/5 animate-pulse rounded bg-gray-200 dark:bg-gray-700" />
          <div className="h-4 w-3/5 animate-pulse rounded bg-gray-200 dark:bg-gray-700" />
        </div>
      </div>
    </div>
  )
}