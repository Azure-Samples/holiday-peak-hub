import {ReactNode} from 'react'
import {Metadata} from 'next'
import ClientLayout from '@/components/utils/ClientLayout'

export const metadata: Metadata = {
  title: 'MagraSS Madre Cabrini',
  description: 'Dashboard',
  icons: {
    icon: '/icons/favicon-32x32.png',
    apple: '/icons/apple-icon-180x180.png',
  }
}

export default function AuthLayout({
  children,
}: {
  children: ReactNode
}) {
  return (
    <ClientLayout pattern='root'>{children}</ClientLayout>
  )
}
