import { SITE } from '@/content/site';

export type ApiResult<T> =
  | { ok: true; status: number; data: T }
  | { ok: false; status: number; message: string };

async function readMessage(response: Response): Promise<string> {
  try {
    const body = (await response.json()) as {
      message?: string;
      detail?: string;
    };
    return body.message ?? body.detail ?? `Request failed (${response.status})`;
  } catch {
    return `Request failed (${response.status})`;
  }
}

export async function postJson<T>(
  path: string,
  payload: unknown
): Promise<ApiResult<T>> {
  try {
    const response = await fetch(`${SITE.apiBaseUrl}${path}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Accept: 'application/json',
      },
      body: JSON.stringify(payload),
    });
    if (!response.ok) {
      return {
        ok: false,
        status: response.status,
        message: await readMessage(response),
      };
    }
    const data = (response.status === 204 ? null : await response.json()) as T;
    return { ok: true, status: response.status, data };
  } catch {
    return {
      ok: false,
      status: 0,
      message:
        'We could not reach the service. Check your connection and try again; nothing you typed was lost.',
    };
  }
}

export async function getJson<T>(path: string): Promise<ApiResult<T>> {
  try {
    const response = await fetch(`${SITE.apiBaseUrl}${path}`, {
      headers: { Accept: 'application/json' },
    });
    if (!response.ok) {
      return {
        ok: false,
        status: response.status,
        message: await readMessage(response),
      };
    }
    return {
      ok: true,
      status: response.status,
      data: (await response.json()) as T,
    };
  } catch {
    return {
      ok: false,
      status: 0,
      message: 'We could not reach the service. Please try again.',
    };
  }
}

export async function putFile(url: string, file: File): Promise<boolean> {
  try {
    const response = await fetch(url, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/pdf' },
      body: file,
    });
    return response.ok;
  } catch {
    return false;
  }
}
