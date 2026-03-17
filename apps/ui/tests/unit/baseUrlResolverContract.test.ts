import {
  resolveAgentApiBaseUrl,
  resolveAgentApiClientBaseUrl,
  resolveCrudApiBaseUrl,
  resolveCrudApiClientBaseUrl,
} from '../../app/api/_shared/base-url-resolver';

describe('base URL resolver contract', () => {
  const originalEnv = process.env;

  beforeEach(() => {
    process.env = { ...originalEnv };
  });

  afterAll(() => {
    process.env = originalEnv;
  });

  describe('resolveCrudApiBaseUrl', () => {
    it('resolves CRUD aliases in stable precedence order', () => {
      const resolved = resolveCrudApiBaseUrl({
        NEXT_PUBLIC_CRUD_API_URL: 'https://primary.example.net/',
        NEXT_PUBLIC_API_URL: 'https://secondary.example.net',
        NEXT_PUBLIC_API_BASE_URL: 'https://tertiary.example.net',
        CRUD_API_URL: 'https://quaternary.example.net',
      } as NodeJS.ProcessEnv);

      expect(resolved).toEqual({
        baseUrl: 'https://primary.example.net',
        sourceKey: 'NEXT_PUBLIC_CRUD_API_URL',
      });
    });

    it('normalizes a trailing api path segment from CRUD aliases', () => {
      const resolved = resolveCrudApiBaseUrl({
        NEXT_PUBLIC_CRUD_API_URL: 'https://primary.example.net/api/',
      } as NodeJS.ProcessEnv);

      expect(resolved).toEqual({
        baseUrl: 'https://primary.example.net',
        sourceKey: 'NEXT_PUBLIC_CRUD_API_URL',
      });
    });
  });

  describe('resolveAgentApiBaseUrl', () => {
    it('prefers explicit agent URL env aliases before CRUD-derived fallbacks', () => {
      const explicitResolution = resolveAgentApiBaseUrl({
        NEXT_PUBLIC_AGENT_API_URL: 'https://agents-public.example.net/',
        AGENT_API_URL: 'https://agents-server.example.net',
        NEXT_PUBLIC_CRUD_API_URL: 'https://crud.example.net',
      } as NodeJS.ProcessEnv);

      expect(explicitResolution).toEqual({
        baseUrl: 'https://agents-public.example.net',
        sourceKey: 'NEXT_PUBLIC_AGENT_API_URL',
      });

      const fallbackResolution = resolveAgentApiBaseUrl({
        NEXT_PUBLIC_API_BASE_URL: 'https://crud-base.example.net/api/',
      } as NodeJS.ProcessEnv);

      expect(fallbackResolution).toEqual({
        baseUrl: 'https://crud-base.example.net/agents',
        sourceKey: 'NEXT_PUBLIC_API_BASE_URL',
      });
    });
  });

  describe('resolveCrudApiClientBaseUrl', () => {
    it('uses browser proxy route in browser runtime when env param is omitted', () => {
      process.env.NEXT_PUBLIC_CRUD_API_URL = 'https://browser-direct.example.net/';

      const browser = resolveCrudApiClientBaseUrl({ runtime: 'browser' });

      expect(browser).toEqual({
        baseUrl: '/api',
        sourceKey: 'BROWSER_PROXY_ROUTE',
        runtime: 'browser',
      });
    });

    it('uses runtime-specific behavior for browser, server, and test', () => {
      const browser = resolveCrudApiClientBaseUrl({
        runtime: 'browser',
        env: {
          NEXT_PUBLIC_CRUD_API_URL: 'https://browser.example.net/',
        } as NodeJS.ProcessEnv,
      });
      expect(browser).toEqual({
        baseUrl: '/api',
        sourceKey: 'BROWSER_PROXY_ROUTE',
        runtime: 'browser',
      });

      const browserFallback = resolveCrudApiClientBaseUrl({ runtime: 'browser', env: {} as NodeJS.ProcessEnv });
      expect(browserFallback).toEqual({
        baseUrl: '/api',
        sourceKey: 'BROWSER_PROXY_ROUTE',
        runtime: 'browser',
      });

      const server = resolveCrudApiClientBaseUrl({
        runtime: 'server',
        env: {
          NEXT_PUBLIC_API_URL: 'https://server.example.net/',
        } as NodeJS.ProcessEnv,
      });
      expect(server).toEqual({
        baseUrl: 'https://server.example.net',
        sourceKey: 'NEXT_PUBLIC_API_URL',
        runtime: 'server',
      });

      const test = resolveCrudApiClientBaseUrl({ runtime: 'test' });
      expect(test).toEqual({
        baseUrl: 'http://localhost:8000',
        sourceKey: 'TEST_DEFAULT_LOCALHOST',
        runtime: 'test',
      });
    });
  });

  describe('resolveAgentApiClientBaseUrl', () => {
    it('uses runtime-specific behavior for browser, server, and test', () => {
      const browser = resolveAgentApiClientBaseUrl({ runtime: 'browser' });
      expect(browser).toEqual({
        baseUrl: '/agent-api',
        sourceKey: 'BROWSER_PROXY_ROUTE',
        runtime: 'browser',
      });

      const server = resolveAgentApiClientBaseUrl({
        runtime: 'server',
        env: {
          AGENT_API_URL: 'https://server-agent.example.net/',
        } as NodeJS.ProcessEnv,
      });
      expect(server).toEqual({
        baseUrl: 'https://server-agent.example.net',
        sourceKey: 'AGENT_API_URL',
        runtime: 'server',
      });

      const test = resolveAgentApiClientBaseUrl({
        runtime: 'test',
        env: {
          NEXT_PUBLIC_CRUD_API_URL: 'https://test-crud.example.net/',
        } as NodeJS.ProcessEnv,
      });
      expect(test).toEqual({
        baseUrl: 'https://test-crud.example.net/agents',
        sourceKey: 'NEXT_PUBLIC_CRUD_API_URL',
        runtime: 'test',
      });
    });
  });
});