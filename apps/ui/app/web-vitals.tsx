'use client'

import {useReportWebVitals} from 'next/web-vitals'

/**
 * Web Vitals telemetry reporter (Issue #1060).
 *
 * Reports LCP / INP / CLS / TTFB / FCP from production to Application Insights
 * via the official `useReportWebVitals` hook. The endpoint is loaded lazily —
 * if `NEXT_PUBLIC_APPINSIGHTS_CONNECTION_STRING` is unset (e.g. in dev or CI),
 * the metrics are no-op'd (logged to console at debug level only).
 *
 * The App Insights JS SDK loads via `next/script strategy="afterInteractive"`
 * so it does NOT block LCP. Its ~30 KB cost sits in the post-LCP budget.
 */
export function WebVitalsReporter() {
  useReportWebVitals((metric) => {
    if (typeof window === 'undefined') return

    const ai = (window as unknown as {appInsights?: {trackEvent: (e: unknown) => void}}).appInsights
    if (ai?.trackEvent) {
      ai.trackEvent({
        name: 'WebVitals',
        properties: {
          name: metric.name,
          value: metric.value,
          rating: metric.rating,
          id: metric.id,
          navigationType: metric.navigationType,
        },
      })
      return
    }

    // No-op in environments without App Insights (dev, CI, preview without instrumentation).
    if (process.env.NODE_ENV !== 'production') {
      // eslint-disable-next-line no-console
      console.debug('[web-vitals]', metric.name, metric.value, metric.rating)
    }
  })

  return null
}
