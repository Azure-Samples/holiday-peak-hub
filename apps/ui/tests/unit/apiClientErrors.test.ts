import { handleApiError, resolveServerCrudApiBaseUrl } from '../../lib/api/client';

describe('handleApiError', () => {
  it('uses backend error payload message when available', () => {
    const error = {
      isAxiosError: true,
      message: 'Request failed with status code 500',
      response: {
        status: 500,
        data: {
          error: 'API proxy could not reach upstream service.',
        },
      },
    };

    const parsed = handleApiError(error);

    expect(parsed.status).toBe(500);
    expect(parsed.message).toBe('API proxy could not reach upstream service.');
  });

  it('falls back to axios error message when payload has no known message keys', () => {
    const error = {
      isAxiosError: true,
      message: 'timeout of 30000ms exceeded',
      response: {
        status: 504,
        data: {
          code: 'GATEWAY_TIMEOUT',
        },
      },
    };

    const parsed = handleApiError(error);

    expect(parsed.status).toBe(504);
    expect(parsed.message).toBe('timeout of 30000ms exceeded');
  });

  it('extracts message from detail object-array payload', () => {
    const error = {
      isAxiosError: true,
      message: 'Request failed with status code 422',
      response: {
        status: 422,
        data: {
          detail: [
            {
              loc: ['body', 'name'],
              msg: 'Field required',
              type: 'missing',
            },
          ],
        },
      },
    };

    const parsed = handleApiError(error);

    expect(parsed.status).toBe(422);
    expect(parsed.message).toBe('Field required');
  });
});

describe('resolveServerCrudApiBaseUrl', () => {
  it('uses NEXT_PUBLIC_CRUD_API_URL first when multiple aliases are present', () => {
    const resolved = resolveServerCrudApiBaseUrl({
      NEXT_PUBLIC_CRUD_API_URL: 'https://primary.example.net/',
      NEXT_PUBLIC_API_URL: 'https://secondary.example.net',
      CRUD_API_URL: 'https://tertiary.example.net',
    } as NodeJS.ProcessEnv);

    expect(resolved).toEqual({
      baseUrl: 'https://primary.example.net',
      sourceKey: 'NEXT_PUBLIC_CRUD_API_URL',
    });
  });

  it('falls back to NEXT_PUBLIC_API_URL then CRUD_API_URL', () => {
    const fallbackToPublic = resolveServerCrudApiBaseUrl({
      NEXT_PUBLIC_API_URL: 'https://fallback-public.example.net/',
    } as NodeJS.ProcessEnv);

    expect(fallbackToPublic).toEqual({
      baseUrl: 'https://fallback-public.example.net',
      sourceKey: 'NEXT_PUBLIC_API_URL',
    });

    const fallbackToBase = resolveServerCrudApiBaseUrl({
      NEXT_PUBLIC_API_BASE_URL: 'https://fallback-base.example.net/',
    } as NodeJS.ProcessEnv);

    expect(fallbackToBase).toEqual({
      baseUrl: 'https://fallback-base.example.net',
      sourceKey: 'NEXT_PUBLIC_API_BASE_URL',
    });

    const fallbackToServerOnly = resolveServerCrudApiBaseUrl({
      CRUD_API_URL: 'https://fallback-server.example.net/',
    } as NodeJS.ProcessEnv);

    expect(fallbackToServerOnly).toEqual({
      baseUrl: 'https://fallback-server.example.net',
      sourceKey: 'CRUD_API_URL',
    });
  });
});
