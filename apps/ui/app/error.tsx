'use client' // Error boundaries must be Client Components
 
import { useEffect } from 'react'

import Link from "next/link";
import Image from "next/image";

import Layout from "@/layouts/centered";
 
export default function Error({
  error,
  reset: _reset,
}: {
  error: Error & { digest?: string }
  reset: () => void
}) {
  useEffect(() => {
    console.error(error)
  }, [error])
 
  return (
    <Layout>
      <div className="flex flex-col w-full max-w-xl text-center">
        <Image
          className="object-contain w-auto mb-8"
          height={64}
          width={64}
          src="/images/illustration.svg"
          alt="Error illustration"
        />
        <h3 className="text-blue-500 mb-4">Oops!</h3>
        {error.digest && (
          <h1 className="text-6xl text-blue-500 mb-4">{error.digest}</h1>
        )}

        <div className="mb-8 text-center text-gray-900 dark:text-white">
          Something went wrong while processing your request. Please try again later.
          If the issue persists, contact support.
        </div>
        <div className="flex w-full">
          <Link href="/" className="w-full px-6 py-3 text-base font-bold text-white uppercase bg-blue-500 rounded-lg hover:bg-blue-600">
            Back Home
          </Link>
        </div>
      </div>
    </Layout>
  )
}