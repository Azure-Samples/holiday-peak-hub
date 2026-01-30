import {ReactNode} from 'react'
import {Metadata} from 'next'
import ClientLayout from '@/components/ClientLayout'

import '@/css/tailwind.css'
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
  title: 'MagraSS Madre Cabrini',
  description: 'Dashboard',
  icons: {
    icon: '/icons/favicon-32x32.png',
    apple: '/icons/apple-icon-180x180.png',
  }
}

export default function RootLayout({
  children,
}: {
  children: ReactNode
}) {
  return (
    <body className="font-sans text-sm antialiased disable-scrollbars bg-white dark:bg-gray-900 text-gray-900 dark:text-white">
      <ClientLayout pattern='root'>{children}</ClientLayout>
    </body>
  )
}
