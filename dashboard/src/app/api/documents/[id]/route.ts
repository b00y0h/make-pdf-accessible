import { NextRequest, NextResponse } from 'next/server';
import { forwardToApi } from '@/lib/dashboard-api-proxy';

const UUID_PATTERN =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

export async function DELETE(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const { id } = await params;

  // The API expects a UUID; rejecting anything else keeps this route from
  // reaching other API paths with the internal dashboard credentials.
  if (!UUID_PATTERN.test(id)) {
    return NextResponse.json({ error: 'Invalid document ID' }, { status: 400 });
  }

  const confirm = request.nextUrl.searchParams.get('confirm_deletion');
  const query = confirm
    ? `?confirm_deletion=${encodeURIComponent(confirm)}`
    : '';

  return forwardToApi(request, `/documents/${id}${query}`, {
    method: 'DELETE',
  });
}
