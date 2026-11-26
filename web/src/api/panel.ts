import type { components } from './client';

export type Teacher = Required<components['schemas']['TeacherSession']>;
export type Pupil = Required<components['schemas']['PupilAccount']>;
export type Credentials = Required<components['schemas']['PupilCredentials']>;
export type NewPupil = Required<components['schemas']['CreatePupil']>;
export type PupilFile = Required<components['schemas']['PupilFileEntry']>;

export class ApiFailure extends Error {
  constructor(public code: string, public status: number) { super(code); }
}

export async function request<T>(path: string, body?: unknown): Promise<T> {
  const headers: Record<string, string> = {};
  if (body !== undefined) {
    const csrf = await request<{ token: string }>('/api/auth/csrf');
    headers['X-CSRF-TOKEN'] = csrf.token;
    headers['Content-Type'] = 'application/json';
  }
  const response = await fetch(path, {
    method: body === undefined ? 'GET' : 'POST',
    credentials: 'same-origin', headers,
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({})) as { code?: string };
    if (response.status === 401 && path !== '/api/auth/login') {
      window.dispatchEvent(new Event('scm-session-expired'));
    }
    throw new ApiFailure(error.code ?? (response.status === 429 ? 'rateLimit' : 'unavailable'), response.status);
  }
  return response.status === 204 ? undefined as T : await response.json() as T;
}

export function errorCode(error: unknown): string {
  return error instanceof ApiFailure ? error.code : 'unavailable';
}

export async function downloadPupilFile(login: string, path: string): Promise<Blob> {
  const response = await fetch(`/api/students/${encodeURIComponent(login)}/download?${new URLSearchParams({ path })}`, { credentials: 'same-origin' });
  if (!response.ok) {
    if (response.status === 401) window.dispatchEvent(new Event('scm-session-expired'));
    const error = await response.json().catch(() => ({})) as { code?: string };
    throw new ApiFailure(error.code ?? 'unavailable', response.status);
  }
  return response.blob();
}
