import { NextRequest, NextResponse } from 'next/server';
import { auth } from '@/lib/auth-server';

const API_URL =
  process.env.API_URL ||
  process.env.NEXT_PUBLIC_API_URL ||
  'http://localhost:8000';

/**
 * Forward a signed-in user's request to an API endpoint that uses internal
 * dashboard authentication (X-Dashboard-Secret).
 *
 * Server-only: the shared secret is read from DASHBOARD_INTERNAL_SECRET and is
 * never sent to the browser. Do not import this from client components.
 */
export async function forwardToApi(
  request: NextRequest,
  path: string,
  init: { method: string; body?: string }
): Promise<NextResponse> {
  const session = await auth.api.getSession({ headers: request.headers });
  if (!session?.user) {
    return NextResponse.json(
      { error: 'Authentication required' },
      { status: 401 }
    );
  }

  const secret = process.env.DASHBOARD_INTERNAL_SECRET;
  if (!secret) {
    console.error('DASHBOARD_INTERNAL_SECRET is not set');
    return NextResponse.json(
      { error: 'Dashboard API access is not configured' },
      { status: 500 }
    );
  }

  const headers: Record<string, string> = {
    'X-Dashboard-Internal': 'true',
    'X-Dashboard-Secret': secret,
  };
  if (init.body !== undefined) {
    headers['Content-Type'] = 'application/json';
  }

  const response = await fetch(`${API_URL}${path}`, {
    method: init.method,
    headers,
    body: init.body,
    cache: 'no-store',
  });

  const body = response.status === 204 ? null : await response.text();
  return new NextResponse(body, {
    status: response.status,
    headers: {
      'Content-Type':
        response.headers.get('Content-Type') || 'application/json',
    },
  });
}
