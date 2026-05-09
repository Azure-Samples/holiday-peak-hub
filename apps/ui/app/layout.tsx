import {ReactNode} from 'react'
import {Metadata} from 'next'
import Providers from './providers'
import {WebVitalsReporter} from './web-vitals'

import './globals.css'
import '@/css/main.css'
import '@/css/animate.css'
import '@/css/components/nprogress.css'
import '@/css/components/recharts.css'
import '@/css/components/steps.css'
import '@/css/components/left-sidebar-3.css'

export const metadata: Metadata = {
  title: 'Holiday Peak Hub',
  description: 'Intelligent Retail Platform',
  icons: {
    icon: '/icons/favicon-32x32.png',
    apple: '/icons/apple-icon-180x180.png',
  },
}

export const viewport = {
  width: 'device-width',
  initialScale: 1,
  shrinkToFit: 'no',
}

export default function RootLayout({
  children,
}: {
  children: ReactNode
}) {
  return (
    <html lang="en-US" suppressHydrationWarning className="h-full">
      <head>
        <meta name="color-scheme" content="light dark" />
      </head>
      <body className="min-h-full font-sans text-sm antialiased disable-scrollbars bg-[var(--hp-bg)] text-[var(--hp-text)] transition-colors duration-200">
        <WebVitalsReporter />
        <Providers>
          {children}
        </Providers>
      </body>
    </html>
  )
}
