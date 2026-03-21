import { trackBoundaryError } from '../../lib/utils/telemetry'

type AppInsightsMock = {
  trackException?: jest.Mock
  trackTrace?: jest.Mock
}

const setAppInsights = (value?: AppInsightsMock) => {
  if (value) {
    ;(window as unknown as { appInsights?: AppInsightsMock }).appInsights = value
    return
  }

  delete (window as unknown as { appInsights?: AppInsightsMock }).appInsights
}

describe('trackBoundaryError', () => {
  const originalConsoleError = console.error

  beforeEach(() => {
    setAppInsights(undefined)
    console.error = jest.fn()
  })

  afterAll(() => {
    console.error = originalConsoleError
  })

  it('uses trackException when available', () => {
    const trackException = jest.fn()
    setAppInsights({ trackException })

    const error = Object.assign(new Error('failed to render'), { digest: 'abc123' })
    trackBoundaryError('checkout', error)

    expect(trackException).toHaveBeenCalledWith({
      exception: error,
      severityLevel: 3,
      properties: {
        scope: 'checkout',
        digest: 'abc123',
      },
    })
  })

  it('falls back to trace when exception tracking is unavailable', () => {
    const trackTrace = jest.fn()
    setAppInsights({ trackTrace })

    const error = Object.assign(new Error('admin unavailable'), { digest: 'def456' })
    trackBoundaryError('admin', error)

    expect(trackTrace).toHaveBeenCalledWith({
      message: 'route_error:admin',
      severityLevel: 3,
      properties: {
        scope: 'admin',
        digest: 'def456',
        message: 'admin unavailable',
      },
    })
  })

  it('falls back to console.error when app insights is unavailable', () => {
    const error = Object.assign(new Error('root crash'), { digest: 'ghi789' })
    trackBoundaryError('root', error)

    expect(console.error).toHaveBeenCalledWith('route_error', {
      scope: 'root',
      digest: 'ghi789',
      message: 'root crash',
    })
  })
})