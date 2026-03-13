import apiClient from '../../lib/api/client';
import { returnsService } from '../../lib/services/returnsService';
import { staffService } from '../../lib/services/staffService';

jest.mock('../../lib/api/client', () => ({
  __esModule: true,
  default: {
    get: jest.fn(),
    post: jest.fn(),
    patch: jest.fn(),
  },
  handleApiError: (error: unknown) => error,
}));

describe('returnsService', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('creates return requests through customer returns endpoint', async () => {
    (apiClient.post as jest.Mock).mockResolvedValueOnce({
      data: { id: 'ret-1', order_id: 'ORD-1', status: 'requested' },
    });

    await returnsService.create({
      order_id: 'ORD-1',
      reason: 'Damaged',
      items: [{ sku: 'SKU-1', quantity: 1 }],
    });

    expect(apiClient.post).toHaveBeenCalledWith('/api/returns', {
      order_id: 'ORD-1',
      reason: 'Damaged',
      items: [{ sku: 'SKU-1', quantity: 1 }],
    });
  });

  it('loads refund progression for customer return', async () => {
    (apiClient.get as jest.Mock).mockResolvedValueOnce({
      data: { id: 'refund-1', return_id: 'ret-1', status: 'issued' },
    });

    await returnsService.getRefundProgress('ret-1');

    expect(apiClient.get).toHaveBeenCalledWith('/api/returns/ret-1/refund');
  });
});

describe('staffService returns lifecycle transitions', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('calls approve transition endpoint', async () => {
    (apiClient.post as jest.Mock).mockResolvedValueOnce({
      data: { id: 'ret-1', status: 'approved' },
    });

    await staffService.approveReturn('ret-1', { reason: 'Validated' });

    expect(apiClient.post).toHaveBeenCalledWith('/api/staff/returns/ret-1/approve', { reason: 'Validated' });
  });

  it('calls refund transition endpoint and refund progression endpoint', async () => {
    (apiClient.post as jest.Mock).mockResolvedValueOnce({
      data: { id: 'ret-1', status: 'refunded' },
    });
    (apiClient.get as jest.Mock).mockResolvedValueOnce({
      data: { id: 'refund-1', return_id: 'ret-1', status: 'issued' },
    });

    await staffService.refundReturn('ret-1', { reason: 'Refund issued' });
    await staffService.getReturnRefundProgress('ret-1');

    expect(apiClient.post).toHaveBeenCalledWith('/api/staff/returns/ret-1/refund', { reason: 'Refund issued' });
    expect(apiClient.get).toHaveBeenCalledWith('/api/staff/returns/ret-1/refund');
  });
});
