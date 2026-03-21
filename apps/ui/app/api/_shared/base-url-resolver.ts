type EnvMap = NodeJS.ProcessEnv;

type ResolutionStrategy = {
  key: string;
  resolve: (env: EnvMap) => string | undefined;
};

type ResolutionResult = {
  baseUrl: string | null;
  sourceKey: string | null;
};

export type RuntimeKind = 'browser' | 'server' | 'test';

type ClientResolutionResult = ResolutionResult & {
  runtime: RuntimeKind;
};

export type ProxyBaseUrlPolicyResult = {
  allowed: boolean;
  violation: 'missing' | 'non-apim' | null;
  policy: 'apim' | 'local-loopback' | 'local-override' | null;
};

function normalizeBaseUrl(candidate: string | undefined): string | null {
  if (!candidate) {
    return null;
  }

  const trimmed = candidate.trim();
  if (!trimmed) {
    return null;
  }

  return trimmed.replace(/\/+$/, '');
}

function normalizeCrudBaseUrl(candidate: string | undefined): string | null {
  const normalized = normalizeBaseUrl(candidate);
  if (!normalized) {
    return null;
  }

  return normalized.replace(/\/api$/i, '');
}

function isApimHostname(hostname: string): boolean {
  return hostname.toLowerCase().endsWith('.azure-api.net');
}

function isLoopbackHostname(hostname: string): boolean {
  const lowered = hostname.toLowerCase();
  return lowered === 'localhost' || lowered === '127.0.0.1' || lowered === '::1';
}

function isLocalNodeRuntime(env: EnvMap): boolean {
  return env.NODE_ENV !== 'production';
}

function allowNonApimOverride(env: EnvMap): boolean {
  return isLocalNodeRuntime(env) && env.UI_ALLOW_NON_APIM_PROXY_URL === 'true';
}

export function validateProxyBaseUrlPolicy(
  candidateBaseUrl: string | null,
  env: EnvMap = process.env,
): ProxyBaseUrlPolicyResult {
  if (!candidateBaseUrl) {
    return {
      allowed: false,
      violation: 'missing',
      policy: null,
    };
  }

  let parsedUrl: URL;
  try {
    parsedUrl = new URL(candidateBaseUrl);
  } catch {
    return {
      allowed: false,
      violation: 'non-apim',
      policy: null,
    };
  }

  if (isApimHostname(parsedUrl.hostname)) {
    return {
      allowed: true,
      violation: null,
      policy: 'apim',
    };
  }

  if (isLocalNodeRuntime(env) && isLoopbackHostname(parsedUrl.hostname)) {
    return {
      allowed: true,
      violation: null,
      policy: 'local-loopback',
    };
  }

  if (allowNonApimOverride(env)) {
    return {
      allowed: true,
      violation: null,
      policy: 'local-override',
    };
  }

  return {
    allowed: false,
    violation: 'non-apim',
    policy: null,
  };
}

// Strategy pattern: evaluate candidate env keys in priority order and pick the first valid URL.
function resolveBaseUrl(strategies: ResolutionStrategy[], env: EnvMap = process.env): ResolutionResult {
  for (const strategy of strategies) {
    const value = normalizeBaseUrl(strategy.resolve(env));
    if (value) {
      return {
        baseUrl: value,
        sourceKey: strategy.key,
      };
    }
  }

  return {
    baseUrl: null,
    sourceKey: null,
  };
}

const CRUD_BASE_URL_STRATEGIES: ResolutionStrategy[] = [
  {
    key: 'NEXT_PUBLIC_CRUD_API_URL',
    resolve: (env) => normalizeCrudBaseUrl(env.NEXT_PUBLIC_CRUD_API_URL) ?? undefined,
  },
  {
    key: 'NEXT_PUBLIC_API_URL',
    resolve: (env) => normalizeCrudBaseUrl(env.NEXT_PUBLIC_API_URL) ?? undefined,
  },
  {
    key: 'NEXT_PUBLIC_API_BASE_URL',
    resolve: (env) => normalizeCrudBaseUrl(env.NEXT_PUBLIC_API_BASE_URL) ?? undefined,
  },
  {
    key: 'CRUD_API_URL',
    resolve: (env) => normalizeCrudBaseUrl(env.CRUD_API_URL) ?? undefined,
  },
];

const AGENT_BASE_URL_STRATEGIES: ResolutionStrategy[] = [
  {
    key: 'NEXT_PUBLIC_AGENT_API_URL',
    resolve: (env) => env.NEXT_PUBLIC_AGENT_API_URL,
  },
  {
    key: 'AGENT_API_URL',
    resolve: (env) => env.AGENT_API_URL,
  },
  {
    key: 'NEXT_PUBLIC_CRUD_API_URL',
    resolve: (env) => {
      const crudBase = normalizeCrudBaseUrl(env.NEXT_PUBLIC_CRUD_API_URL);
      return crudBase ? `${crudBase}/agents` : undefined;
    },
  },
  {
    key: 'NEXT_PUBLIC_API_URL',
    resolve: (env) => {
      const apiBase = normalizeCrudBaseUrl(env.NEXT_PUBLIC_API_URL);
      return apiBase ? `${apiBase}/agents` : undefined;
    },
  },
  {
    key: 'NEXT_PUBLIC_API_BASE_URL',
    resolve: (env) => {
      const apiBase = normalizeCrudBaseUrl(env.NEXT_PUBLIC_API_BASE_URL);
      return apiBase ? `${apiBase}/agents` : undefined;
    },
  },
  {
    key: 'CRUD_API_URL',
    resolve: (env) => {
      const crudBase = normalizeCrudBaseUrl(env.CRUD_API_URL);
      return crudBase ? `${crudBase}/agents` : undefined;
    },
  },
];

export function resolveCrudApiBaseUrl(env?: EnvMap): ResolutionResult {
  return resolveBaseUrl(CRUD_BASE_URL_STRATEGIES, env);
}

export function resolveAgentApiBaseUrl(env?: EnvMap): ResolutionResult {
  return resolveBaseUrl(AGENT_BASE_URL_STRATEGIES, env);
}

function inferRuntimeKind(env: EnvMap = process.env): RuntimeKind {
  if (env.NODE_ENV === 'test') {
    return 'test';
  }

  return typeof window === 'undefined' ? 'server' : 'browser';
}

export function resolveCrudApiClientBaseUrl(params?: {
  env?: EnvMap;
  runtime?: RuntimeKind;
}): ClientResolutionResult {
  const env = params?.env ?? process.env;
  const runtime = params?.runtime ?? inferRuntimeKind(env);

  if (runtime === 'browser') {
    return {
      baseUrl: '',
      sourceKey: 'BROWSER_PROXY_ROUTE',
      runtime,
    };
  }

  if (runtime === 'test') {
    return {
      baseUrl: 'http://localhost:8000',
      sourceKey: 'TEST_DEFAULT_LOCALHOST',
      runtime,
    };
  }

  const resolved = resolveCrudApiBaseUrl(env);
  return {
    ...resolved,
    runtime,
  };
}

export function resolveAgentApiClientBaseUrl(params?: {
  env?: EnvMap;
  runtime?: RuntimeKind;
}): ClientResolutionResult {
  const env = params?.env ?? process.env;
  const runtime = params?.runtime ?? inferRuntimeKind(env);

  if (runtime === 'browser') {
    return {
      baseUrl: '/agent-api',
      sourceKey: 'BROWSER_PROXY_ROUTE',
      runtime,
    };
  }

  if (runtime === 'test') {
    const crudResolution = resolveCrudApiBaseUrl(env);
    return {
      baseUrl: crudResolution.baseUrl ? `${crudResolution.baseUrl}/agents` : '/agents',
      sourceKey: crudResolution.sourceKey,
      runtime,
    };
  }

  const resolved = resolveAgentApiBaseUrl(env);
  return {
    ...resolved,
    runtime,
  };
}
