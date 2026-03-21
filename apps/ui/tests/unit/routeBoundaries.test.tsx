import React from 'react'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'

import RootErrorBoundary from '../../app/error'
import RootLoadingBoundary from '../../app/loading'
import AdminErrorBoundary from '../../app/admin/error'
import AdminLoadingBoundary from '../../app/admin/loading'
import StaffErrorBoundary from '../../app/staff/error'
import StaffLoadingBoundary from '../../app/staff/loading'
import ShopLoadingBoundary from '../../app/shop/loading'
import CheckoutErrorBoundary from '../../app/checkout/error'
import CheckoutLoadingBoundary from '../../app/checkout/loading'

const trackBoundaryError = jest.fn()

jest.mock('@/lib/utils/telemetry', () => ({
  trackBoundaryError: (...args: unknown[]) => trackBoundaryError(...args),
}))

describe('route boundaries', () => {
  beforeEach(() => {
    jest.clearAllMocks()
  })

  it('renders loading boundaries for root and critical segments', () => {
    render(
      <div>
        <RootLoadingBoundary />
        <AdminLoadingBoundary />
        <StaffLoadingBoundary />
        <ShopLoadingBoundary />
        <CheckoutLoadingBoundary />
      </div>,
    )

    expect(screen.getByText('Loading Holiday Peak Hub...')).toBeInTheDocument()
    expect(screen.getByText('Loading admin tools...')).toBeInTheDocument()
    expect(screen.getByText('Loading staff workspace...')).toBeInTheDocument()
    expect(screen.getByText('Loading shop...')).toBeInTheDocument()
    expect(screen.getByText('Loading checkout...')).toBeInTheDocument()
  })

  it('tracks errors with route scope and supports reset action', async () => {
    const reset = jest.fn()
    const adminError = Object.assign(new Error('admin failed'), { digest: 'ad-1' })
    const staffError = Object.assign(new Error('staff failed'), { digest: 'st-1' })
    const checkoutError = Object.assign(new Error('checkout failed'), { digest: 'co-1' })
    const rootError = Object.assign(new Error('root failed'), { digest: 'rt-1' })

    render(
      <div>
        <AdminErrorBoundary error={adminError} reset={reset} />
        <StaffErrorBoundary error={staffError} reset={reset} />
        <CheckoutErrorBoundary error={checkoutError} reset={reset} />
        <RootErrorBoundary error={rootError} reset={reset} />
      </div>,
    )

    await waitFor(() => {
      expect(trackBoundaryError).toHaveBeenCalledWith('admin', adminError)
      expect(trackBoundaryError).toHaveBeenCalledWith('staff', staffError)
      expect(trackBoundaryError).toHaveBeenCalledWith('checkout', checkoutError)
      expect(trackBoundaryError).toHaveBeenCalledWith('root', rootError)
    })

    fireEvent.click(screen.getAllByRole('button', { name: 'Try Again' })[0])
    expect(reset).toHaveBeenCalledTimes(1)
    expect(screen.getAllByRole('link', { name: 'Back Home' })).toHaveLength(4)
  })
})