import React from 'react';
import { render, screen, fireEvent, act } from '@testing-library/react';
import { LiveProcessingLog } from '../../components/enrichment/LiveProcessingLog';

// Mock Card
jest.mock('@/components/molecules/Card', () => ({
  Card: ({ children, className }: { children: React.ReactNode; className?: string }) =>
    React.createElement('div', { 'data-testid': 'card', className }, children),
}));

// Mock EventSource
type EventSourceListener = (event: MessageEvent | Event) => void;

class MockEventSource {
  static instances: MockEventSource[] = [];
  onopen: EventSourceListener | null = null;
  onmessage: EventSourceListener | null = null;
  onerror: EventSourceListener | null = null;
  readyState = 0;

  constructor(public url: string) {
    MockEventSource.instances.push(this);
    // Simulate connection on next tick
    setTimeout(() => {
      this.readyState = 1;
      this.onopen?.(new Event('open'));
    }, 0);
  }

  close() {
    this.readyState = 2;
  }

  simulateMessage(data: Record<string, unknown>) {
    const event = new MessageEvent('message', { data: JSON.stringify(data) });
    this.onmessage?.(event);
  }

  simulateError() {
    this.onerror?.(new Event('error'));
  }
}

beforeEach(() => {
  MockEventSource.instances = [];
  (global as Record<string, unknown>).EventSource = MockEventSource as unknown as typeof EventSource;
  Element.prototype.scrollIntoView = jest.fn();
  jest.useFakeTimers();
});

afterEach(() => {
  jest.useRealTimers();
  delete (global as Record<string, unknown>).EventSource;
});

describe('LiveProcessingLog', () => {
  it('renders with "Connected" indicator after open', async () => {
    render(<LiveProcessingLog />);
    // Advance timer to fire the setTimeout in MockEventSource constructor
    await act(async () => {
      jest.advanceTimersByTime(10);
    });
    expect(screen.getByText('Connected')).toBeInTheDocument();
  });

  it('appends log entries on SSE message', async () => {
    render(<LiveProcessingLog />);
    await act(async () => {
      jest.advanceTimersByTime(10);
    });
    const es = MockEventSource.instances[0];
    act(() => {
      es.simulateMessage({
        id: 'evt-1',
        timestamp: '2026-04-16T10:00:00Z',
        event_type: 'enrichment_started',
        entity_id: 'SKU-001',
        status: 'processing',
      });
    });
    expect(screen.getByText('enrichment_started')).toBeInTheDocument();
    expect(screen.getByText('SKU-001')).toBeInTheDocument();
    expect(screen.getByText('processing')).toBeInTheDocument();
  });

  it('auto-scrolls on new entry', async () => {
    const scrollIntoViewMock = jest.fn();
    Element.prototype.scrollIntoView = scrollIntoViewMock;

    render(<LiveProcessingLog />);
    await act(async () => {
      jest.advanceTimersByTime(10);
    });
    const es = MockEventSource.instances[0];
    act(() => {
      es.simulateMessage({
        id: 'evt-2',
        timestamp: '2026-04-16T10:01:00Z',
        event_type: 'enrichment_done',
        entity_id: 'SKU-002',
        status: 'success',
      });
    });
    expect(scrollIntoViewMock).toHaveBeenCalled();
  });

  it('clear button resets entries', async () => {
    render(<LiveProcessingLog />);
    await act(async () => {
      jest.advanceTimersByTime(10);
    });
    const es = MockEventSource.instances[0];
    act(() => {
      es.simulateMessage({
        id: 'evt-3',
        timestamp: '2026-04-16T10:02:00Z',
        event_type: 'enrichment_started',
        entity_id: 'SKU-003',
        status: 'processing',
      });
    });
    expect(screen.getByText('SKU-003')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: /clear/i }));
    expect(screen.queryByText('SKU-003')).not.toBeInTheDocument();
    expect(screen.getByText(/no processing events yet/i)).toBeInTheDocument();
  });

  it('shows "Disconnected" on error event', async () => {
    render(<LiveProcessingLog />);
    await act(async () => {
      jest.advanceTimersByTime(10);
    });
    expect(screen.getByText('Connected')).toBeInTheDocument();
    const es = MockEventSource.instances[0];
    act(() => {
      es.simulateError();
    });
    expect(screen.getByText('Disconnected')).toBeInTheDocument();
  });
});
