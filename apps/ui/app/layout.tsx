import {ReactNode} from 'react'
import {Metadata} from 'next'
import { ThemeProvider } from '@/contexts/ThemeContext'

import '@/css/tailwind.css'
import './globals.css'
import '@/css/main.css'
import '@/css/layouts/layout-1.css'
import '@/css/layouts/e-commerce.css'
import '@/css/animate.css'
import '@/css/components/left-sidebar-1/styles-lg.css'
import '@/css/components/left-sidebar-1/styles-sm.css'
import '@/css/components/nprogress.css'
import '@/css/components/recharts.css'
import '@/css/components/steps.css'
import '@/css/components/left-sidebar-3.css'

export const metadata: Metadata = {
  title: 'Holiday Peak Hub',
  description: 'Intelligent Retail Platform',
  icons: {
    icon: '@/public/icons/favicon-32x32.png',
    apple: '@/public/icons/apple-icon-180x180.png',
  },
  viewport: 'width=device-width, initial-scale=1, shrink-to-fit=no'
}

export default function RootLayout({
  children,
}: {
  children: ReactNode
}) {
  return (
    <html lang="pt-br" suppressHydrationWarning>
      <body className="font-sans text-sm antialiased disable-scrollbars bg-white dark:bg-gray-900 text-gray-900 dark:text-white">
        <ThemeProvider>
          {children}
        </ThemeProvider>
      </body>
    </html>
  )
}
