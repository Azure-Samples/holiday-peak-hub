'use client'

import {useEffect, useRef} from 'react'
import {usePathname, useSearchParams} from 'next/navigation'
import NProgress from 'nprogress'


export default function NProgressHandler() {
  const pathname = usePathname()
  const searchParams = useSearchParams()
  const loadingRef = useRef(false)

  useEffect(() => {
    if (!loadingRef.current) {
      NProgress.start()
      loadingRef.current = true
    }

    NProgress.done()
    loadingRef.current = false
  }, [pathname, searchParams])

  return null
}
