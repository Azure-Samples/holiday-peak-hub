'use client';

import { resolveAgentApiClientBaseUrl } from '@/app/api/_shared/base-url-resolver';
import { recordAgentInvocationTelemetry } from '@/lib/hooks/useAgentInvocationTelemetry';
import { getCurrentPageSessionId } from '@/lib/hooks/usePageSession';

const AGENT_API_BASE_URL = resolveAgentApiClientBaseUrl().baseUrl || '';

export interface AgentInvokeStreamCallbacks {
  onResults?: (payload: Record<string, unknown>) => void;
  onToken?: (text: string) => void;
  onDone?: (payload: Record<string, unknown>) => void;
  onError?: (error: Error) => void;
}

function toErrorMessage(data: Record<string, unknown>): string {
  if (typeof data.message === 'string' && data.message.trim()) {
    return data.message;
  }

  if (typeof data.error === 'string' && data.error.trim()) {
    return data.error;
  }

  return 'Agent stream failed.';
}

function dispatchStreamEvent(
  agentSlug: string,
  eventType: string,
  data: Record<string, unknown>,
  callbacks: AgentInvokeStreamCallbacks,
): void {
  switch (eventType) {
    case 'results':
      recordAgentInvocationTelemetry(agentSlug, data);
      callbacks.onResults?.(data);
      break;
    case 'token': {
      const text = typeof data.text === 'string' ? data.text : '';
      if (text) {
        callbacks.onToken?.(text);
      }
      break;
    }
    case 'done':
      callbacks.onDone?.(data);
      break;
    case 'error':
      callbacks.onError?.(new Error(toErrorMessage(data)));
      break;
  }
}

export function streamAgentInvocation(
  agentSlug: string,
  payload: Record<string, unknown>,
  callbacks: AgentInvokeStreamCallbacks,
): AbortController {
  const controller = new AbortController();
  const baseUrl = AGENT_API_BASE_URL.replace(/\/$/, '');
  const streamUrl = `${baseUrl}/${agentSlug}/invoke/stream`;
  const sessionId = getCurrentPageSessionId();

  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  };

  if (sessionId) {
    headers['x-holiday-peak-session-id'] = sessionId;
  }

  if (typeof window !== 'undefined') {
    const token = window.sessionStorage.getItem('auth_token');
    if (token) {
      headers.Authorization = `Bearer ${token}`;
    }
  }

  void fetch(streamUrl, {
    method: 'POST',
    headers,
    body: JSON.stringify({
      intent: 'default',
      payload: sessionId ? { ...payload, session_id: sessionId } : payload,
    }),
    signal: controller.signal,
  })
    .then(async (response) => {
      if (!response.ok || !response.body) {
        throw new Error(`Stream request failed: ${response.status}`);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      // eslint-disable-next-line no-constant-condition
      while (true) {
        const { done, value } = await reader.read();
        if (done) {
          break;
        }

        buffer += decoder.decode(value, { stream: true });
        const chunks = buffer.split('\n\n');
        buffer = chunks.pop() || '';

        for (const chunk of chunks) {
          const lines = chunk.split('\n');
          let currentEvent = '';

          for (const line of lines) {
            if (line.startsWith('event: ')) {
              currentEvent = line.slice(7).trim();
              continue;
            }

            if (!line.startsWith('data: ') || !currentEvent) {
              continue;
            }

            try {
              const data = JSON.parse(line.slice(6)) as Record<string, unknown>;
              dispatchStreamEvent(agentSlug, currentEvent, data, callbacks);
            } catch {
              // Ignore malformed stream payloads.
            }
          }
        }
      }
    })
    .catch((error: unknown) => {
      if (error instanceof Error && error.name === 'AbortError') {
        return;
      }

      const message = error instanceof Error ? error.message : 'Agent stream failed.';
      callbacks.onError?.(new Error(message));
    });

  return controller;
}

export default streamAgentInvocation;