type EnvMap = NodeJS.ProcessEnv;

type ResolutionStrategy = {
  key: string;
  resolve: (env: EnvMap) => string | undefined;
};

type ResolutionResult = {
  baseUrl: string | null;
  sourceKey: string | null;
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
    resolve: (env) => env.NEXT_PUBLIC_CRUD_API_URL,
  },
  {
    key: 'NEXT_PUBLIC_API_URL',
    resolve: (env) => env.NEXT_PUBLIC_API_URL,
  },
  {
    key: 'NEXT_PUBLIC_API_BASE_URL',
    resolve: (env) => env.NEXT_PUBLIC_API_BASE_URL,
  },
  {
    key: 'CRUD_API_URL',
    resolve: (env) => env.CRUD_API_URL,
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
      const crudBase = normalizeBaseUrl(env.NEXT_PUBLIC_CRUD_API_URL);
      return crudBase ? `${crudBase}/agents` : undefined;
    },
  },
  {
    key: 'NEXT_PUBLIC_API_URL',
    resolve: (env) => {
      const apiBase = normalizeBaseUrl(env.NEXT_PUBLIC_API_URL);
      return apiBase ? `${apiBase}/agents` : undefined;
    },
  },
  {
    key: 'NEXT_PUBLIC_API_BASE_URL',
    resolve: (env) => {
      const apiBase = normalizeBaseUrl(env.NEXT_PUBLIC_API_BASE_URL);
      return apiBase ? `${apiBase}/agents` : undefined;
    },
  },
  {
    key: 'CRUD_API_URL',
    resolve: (env) => {
      const crudBase = normalizeBaseUrl(env.CRUD_API_URL);
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
