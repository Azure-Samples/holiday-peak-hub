import { ApiError } from './client';

export function getApiStatusCode(error: unknown): number | null {
  if (error instanceof ApiError) {
    return error.status;
  }

  return null;
}

export function getApiErrorMessage(error: unknown, fallbackMessage: string): string {
  if (error instanceof ApiError) {
    return error.message || fallbackMessage;
  }

  if (error instanceof Error) {
    return error.message || fallbackMessage;
  }

  return fallbackMessage;
}
