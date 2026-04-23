import { useQuery, useMutation } from '@tanstack/react-query';
import { AxiosError, AxiosHeaders } from 'axios';
import { agentApiClient } from '../../lib/api/agentClient';
import {
  useAgentQuery,
  useAgentMutation,
  type AgentError,
  type AgentQueryOptions,
  type AgentMutationOptions,
} from '../../lib/hooks/useAgent';

jest.mock('@tanstack/react-query', () => ({
  useQuery: jest.fn(),
  useMutation: jest.fn(),
}));

jest.mock('../../lib/api/agentClient', () => ({
  agentApiClient: {
    get: jest.fn(),
    post: jest.fn(),
  },
}));

const mockGet = agentApiClient.get as jest.Mock;
const mockPost = agentApiClient.post as jest.Mock;

// ---------------------------------------------------------------------------
// useAgentQuery
// ---------------------------------------------------------------------------

describe('useAgentQuery', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    (useQuery as jest.Mock).mockReturnValue({ data: undefined, isLoading: true });
  });

  it('passes correct queryKey and calls agentApiClient.get', async () => {
    const opts: AgentQueryOptions<{ items: string[] }> = {
      service: 'ecommerce-catalog-search',
      endpoint: '/search',
      params: { q: 'shoes', limit: 10 },
    };

    useAgentQuery(opts);

    const call = (useQuery as jest.Mock).mock.calls[0][0];
    // Key includes sorted params
    expect(call.queryKey).toEqual([
      'agent',
      'ecommerce-catalog-search',
      '/search',
      'limit', 10,
      'q', 'shoes',
    ]);

    // Execute the queryFn to verify the GET call
    mockGet.mockResolvedValue({ data: { items: ['a'] } });
    const result = await call.queryFn();
    expect(mockGet).toHaveBeenCalledWith('/ecommerce-catalog-search/search', {
      params: { q: 'shoes', limit: 10 },
    });
    expect(result).toEqual({ items: ['a'] });
  });

  it('handles errors and maps to AgentError', async () => {
    useAgentQuery({ service: 'svc', endpoint: '/ep' });

    const call = (useQuery as jest.Mock).mock.calls[0][0];
    const axiosErr = new AxiosError('timeout', 'ECONNABORTED', undefined, undefined, {
      status: 504,
      data: { detail: 'Gateway Timeout' },
      statusText: 'Gateway Timeout',
      headers: {},
      config: { headers: new AxiosHeaders() },
    });
    mockGet.mockRejectedValue(axiosErr);

    await expect(call.queryFn()).rejects.toEqual<AgentError>({
      status: 504,
      message: 'Gateway Timeout',
      service: 'svc',
      endpoint: '/ep',
    });
  });

  it('respects the enabled flag', () => {
    useAgentQuery({ service: 'svc', endpoint: '/ep', enabled: false });

    const call = (useQuery as jest.Mock).mock.calls[0][0];
    expect(call.enabled).toBe(false);
  });

  it('uses endpoint directly when it starts with /agents/', () => {
    useAgentQuery({ service: 'svc', endpoint: '/agents/invoke' });

    const call = (useQuery as jest.Mock).mock.calls[0][0];
    mockGet.mockResolvedValue({ data: {} });
    call.queryFn();
    expect(mockGet).toHaveBeenCalledWith('/agents/invoke', { params: undefined });
  });

  it('forwards staleTime and refetchInterval', () => {
    useAgentQuery({
      service: 'svc',
      endpoint: '/ep',
      staleTime: 30_000,
      refetchInterval: 5_000,
    });

    const call = (useQuery as jest.Mock).mock.calls[0][0];
    expect(call.staleTime).toBe(30_000);
    expect(call.refetchInterval).toBe(5_000);
  });

  it('filters undefined params from query key', () => {
    useAgentQuery({
      service: 'svc',
      endpoint: '/ep',
      params: { a: 'yes', b: undefined },
    });

    const call = (useQuery as jest.Mock).mock.calls[0][0];
    expect(call.queryKey).toEqual(['agent', 'svc', '/ep', 'a', 'yes']);
  });
});

// ---------------------------------------------------------------------------
// useAgentMutation
// ---------------------------------------------------------------------------

describe('useAgentMutation', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    (useMutation as jest.Mock).mockReturnValue({ mutate: jest.fn() });
  });

  it('posts data through agentApiClient and returns response', async () => {
    const onSuccess = jest.fn();
    const opts: AgentMutationOptions<{ id: string }> = {
      service: 'ecommerce-catalog-search',
      endpoint: '/search',
      onSuccess,
    };

    useAgentMutation(opts);

    const call = (useMutation as jest.Mock).mock.calls[0][0];
    mockPost.mockResolvedValue({ data: { id: '123' } });
    const result = await call.mutationFn({ query: 'shoes' });

    expect(mockPost).toHaveBeenCalledWith('/ecommerce-catalog-search/search', { query: 'shoes' });
    expect(result).toEqual({ id: '123' });
    expect(call.onSuccess).toBe(onSuccess);
  });

  it('handles errors and maps to AgentError', async () => {
    const onError = jest.fn();
    useAgentMutation({ service: 'svc', endpoint: '/ep', onError });

    const call = (useMutation as jest.Mock).mock.calls[0][0];
    const axiosErr = new AxiosError('bad', 'ERR_BAD_REQUEST', undefined, undefined, {
      status: 400,
      data: { detail: 'Validation failed' },
      statusText: 'Bad Request',
      headers: {},
      config: { headers: new AxiosHeaders() },
    });
    mockPost.mockRejectedValue(axiosErr);

    await expect(call.mutationFn({})).rejects.toEqual<AgentError>({
      status: 400,
      message: 'Validation failed',
      service: 'svc',
      endpoint: '/ep',
    });
    expect(call.onError).toBe(onError);
  });

  it('uses endpoint directly when it starts with /agents/', async () => {
    useAgentMutation({ service: 'svc', endpoint: '/agents/invoke' });

    const call = (useMutation as jest.Mock).mock.calls[0][0];
    mockPost.mockResolvedValue({ data: {} });
    await call.mutationFn({ payload: true });

    expect(mockPost).toHaveBeenCalledWith('/agents/invoke', { payload: true });
  });
});
